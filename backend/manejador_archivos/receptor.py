"""MOD-02 · Manejador de archivos · recepción de la subida.

Es la primera puerta del sistema: recibe el archivo que subió el usuario, le
aplica el **tamaño máximo de UT-03** y lo entrega **como texto** a MOD-03, o
devuelve un **rechazo con código** de UT-02 (contrato de la sección 5 del plan
del incremento 1).

Lo que MOD-02 **no** hace, a propósito:

- No mira el formato ni la estructura, ni cuenta puntos, ni revisa el rango: eso
  es MOD-03 (T-04 y T-05). Por eso un `.png` chico, un archivo vacío y un
  binario disfrazado de `.csv` **pasan** por aquí: su tamaño está bien. El que
  los rechaza, por su contenido, es MOD-03.
- No guarda nada. No tiene estado entre peticiones ni escribe en disco.

Las cuatro reglas que el código de abajo existe para sostener:

1. **El límite lo aplica este módulo** (sección 5), leyéndolo de UT-03, no
   FastAPI ni el servidor web: si lo cortara la infraestructura, CA-02.2 no
   probaría nada del equipo.
2. **Se lee por bloques** y se corta en el primer byte que pasa el límite, así
   que de un archivo enorme nunca se leen más que el límite más un byte
   (RNF-03). Y **no se consulta el tamaño que declara el navegador**: ese dato
   lo manda el cliente y puede mentir.
3. **El contenido vive solo en memoria** y se suelta al terminar (RNF-09).
4. **La subida se cierra siempre**, en un `finally`: arriba de 1 MB FastAPI
   guarda la subida en un archivo temporal en disco, y ese temporal tiene que
   desaparecer con éxito o con error.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from backend.nucleo import obtener_registro
from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion

_registro = obtener_registro("mod-02")

#: Cuántos bytes se piden por lectura. **No es un parámetro de negocio**, así
#: que no vive en UT-03: no cambia qué se acepta ni qué se rechaza, solo cuánta
#: memoria se usa de una vez. Lo único que importa es que sea bastante menor que
#: el límite, para que un archivo enorme no entre de un golpe.
BLOQUE_BYTES: int = 64 * 1024

#: Con qué se interpreta el archivo. `utf-8-sig` descarta la marca de orden de
#: bytes (BOM) que ponen algunos programas de Windows; si no se quitara, MOD-03
#: vería un carácter invisible antes de `##TITLE=` y creería que la etiqueta no
#: está al principio de la primera línea.
CODIFICACION: str = "utf-8-sig"

#: Los bytes que no son texto válido se vuelven «caracteres de reemplazo» en vez
#: de romper la lectura. Decidir si el archivo *es* texto le toca a MOD-03
#: (CA-02.5), y para eso necesita verlo: los bytes nulos del binario llegan
#: intactos y los demás quedan marcados.
ERRORES_DE_DECODIFICACION: str = "replace"

#: Hasta cuántos caracteres del nombre se conservan. El nombre lo escribe quien
#: sube el archivo, y solo se usa para mostrarlo y registrarlo.
LARGO_MAXIMO_NOMBRE: int = 120

#: Lo que se muestra cuando la subida llega sin nombre.
NOMBRE_DESCONOCIDO: str = "(sin nombre)"

#: Hasta qué largo se considera «extensión» al recortar un nombre larguísimo.
#: MOD-03 necesita la extensión (CA-01.3), así que se conserva.
_LARGO_MAXIMO_EXTENSION: int = 10


@runtime_checkable
class ArchivoSubido(Protocol):
    """Lo único que MOD-02 necesita de una subida.

    `UploadFile` de FastAPI lo cumple. Se describe como protocolo —y no se
    importa FastAPI aquí— por dos razones: MOD-02 no depende del framework, y
    las pruebas pueden envolver la subida para observar cómo se leyó.

    Nótese que `size` **no** está en la lista: el tamaño que declara el cliente
    no se consulta nunca.
    """

    filename: str | None

    def read(self, cantidad: int = -1) -> Any:
        """Devuelve hasta `cantidad` bytes (o una espera que los devuelva)."""

    def close(self) -> Any:
        """Cierra la subida y borra su temporal (o devuelve una espera)."""


@dataclass(frozen=True)
class Recepcion:
    """Lo que MOD-02 entrega: el archivo leído, o el motivo del rechazo.

    Attributes:
        aceptado: ``True`` si el archivo pasó el filtro de tamaño y se leyó
            completo. Un ``False`` aquí **no** quiere decir que el espectro sea
            inválido: eso lo dice MOD-03 después.
        nombre: el nombre ya limpio (sin rutas ni caracteres de control).
        bytes_leidos: cuántos bytes se leyeron de verdad, contados por MOD-02.
        tamano_correcto: el «indicador de tamaño correcto» del contrato de la
            sección 5. Es ``False`` si se pasó del límite y también si la
            lectura se interrumpió, porque entonces el tamaño no se conoció.
        contenido: el archivo como texto, listo para MOD-03. ``None`` cuando
            hubo rechazo: un rechazo no entrega contenido.
        codigo: el código de UT-02 que explica el rechazo, o ``None`` si se
            aceptó.
    """

    aceptado: bool
    nombre: str
    bytes_leidos: int
    tamano_correcto: bool
    contenido: str | None = None
    codigo: str | None = None

    def __post_init__(self) -> None:
        # Red de seguridad contra un error de programación: aceptado y
        # rechazado son excluyentes, y cada uno trae una cosa y solo una.
        if self.aceptado and (self.contenido is None or self.codigo is not None):
            raise ValueError(
                "una recepción aceptada trae contenido y ningún código de "
                "rechazo"
            )
        if not self.aceptado and (self.contenido is not None or self.codigo is None):
            raise ValueError(
                "una recepción rechazada trae código de rechazo y ningún "
                "contenido"
            )


def nombre_seguro(declarado: str | None) -> str:
    """Limpia el nombre que declaró el navegador (RNF-03).

    El nombre llega del cliente, así que se trata como texto sospechoso aunque
    solo se use para mostrarlo y registrarlo:

    - se queda **solo el nombre del archivo**, sin carpetas, para que un
      `..\\..\\algo.csv` no parezca una ruta en ninguna pantalla ni registro;
    - los caracteres de control se vuelven `_`; el salto de línea es el
      peligroso, porque permitiría inventar una línea falsa en el registro;
    - un nombre larguísimo se recorta conservando la extensión, que es lo que
      MOD-03 necesita para CA-01.3.

    Args:
        declarado: el nombre tal como lo mandó el navegador.

    Returns:
        Un nombre corto y mostrable; `NOMBRE_DESCONOCIDO` si no quedó nada.
    """
    if not declarado:
        return NOMBRE_DESCONOCIDO

    solo_nombre = declarado.replace("\\", "/").rsplit("/", 1)[-1]
    sin_control = "".join(
        "_" if ord(caracter) < 32 or ord(caracter) == 127 else caracter
        for caracter in solo_nombre
    )
    limpio = sin_control.strip()

    if len(limpio) > LARGO_MAXIMO_NOMBRE:
        punto = limpio.rfind(".")
        extension = (
            limpio[punto:]
            if punto > 0 and len(limpio) - punto <= _LARGO_MAXIMO_EXTENSION
            else ""
        )
        limpio = limpio[: LARGO_MAXIMO_NOMBRE - len(extension)] + extension

    return limpio or NOMBRE_DESCONOCIDO


async def recibir(
    archivo: ArchivoSubido,
    configuracion: Configuracion | None = None,
    *,
    bloque_bytes: int = BLOQUE_BYTES,
) -> Recepcion:
    """Recibe la subida, aplica el tamaño máximo y la entrega como texto.

    Args:
        archivo: la subida (el `UploadFile` que arma FastAPI).
        configuracion: los parámetros con los que se trabaja. Si es ``None`` se
            usan los de UT-03; el parámetro existe para las pruebas.
        bloque_bytes: cuántos bytes se piden por lectura. Detalle de
            implementación, no parámetro de negocio.

    Returns:
        Una `Recepcion` con el contenido, o con el código del rechazo.
        **Nunca levanta** una excepción por culpa del archivo: un archivo
        gigante o una lectura interrumpida son resultados, no fallas.
    """
    if bloque_bytes < 1:
        raise ValueError("el bloque de lectura debe ser de al menos un byte")

    parametros = configuracion if configuracion is not None else obtener_configuracion()
    maximo = parametros.archivo.tamano_maximo_bytes
    nombre = nombre_seguro(getattr(archivo, "filename", None))

    bloques: list[bytes] = []
    leidos = 0

    try:
        try:
            # Se lee hasta el límite **más un byte**: ese byte extra es toda la
            # prueba que hace falta para saber que el archivo se pasó, y así de
            # un archivo enorme no se lee el resto.
            while leidos <= maximo:
                por_pedir = min(bloque_bytes, maximo + 1 - leidos)
                bloque = await _leer(archivo, por_pedir)
                if not bloque:
                    break
                leidos += len(bloque)
                bloques.append(bloque)
        except Exception:
            # No se filtra el detalle técnico: el usuario ve el mensaje de
            # UT-02 y el registro guarda solo el resultado (RNF-01, RNF-09).
            return _rechazo(nombre, mensajes.LECTURA_INTERRUMPIDA, leidos)

        if leidos > maximo:
            return _rechazo(nombre, mensajes.TAMANO_EXCEDIDO, leidos)

        contenido = b"".join(bloques).decode(
            CODIFICACION, errors=ERRORES_DE_DECODIFICACION
        )
        _registro.info(
            "MOD-02 recepcion | nombre=%s | bytes=%d | resultado=%s",
            nombre,
            leidos,
            "aceptado",
        )
        return Recepcion(
            aceptado=True,
            nombre=nombre,
            bytes_leidos=leidos,
            tamano_correcto=True,
            contenido=contenido,
        )
    finally:
        # Suelta los bloques crudos (el contenido ya decodificado se lo lleva
        # quien llamó) y, sobre todo, cierra la subida: si FastAPI creó un
        # temporal en disco, aquí es donde desaparece.
        bloques.clear()
        await _cerrar(archivo)


def _rechazo(nombre: str, codigo: str, bytes_leidos: int) -> Recepcion:
    """Arma el rechazo y lo deja en el registro (solo nombre, tamaño, código)."""
    _registro.warning(
        "MOD-02 recepcion | nombre=%s | bytes=%d | resultado=%s",
        nombre,
        bytes_leidos,
        codigo,
    )
    return Recepcion(
        aceptado=False,
        nombre=nombre,
        bytes_leidos=bytes_leidos,
        tamano_correcto=False,
        codigo=codigo,
    )


async def _leer(archivo: ArchivoSubido, cantidad: int) -> bytes:
    """Lee un bloque, sirva la subida de forma asíncrona o síncrona."""
    return await _resolver(archivo.read(cantidad))


async def _cerrar(archivo: ArchivoSubido) -> None:
    """Cierra la subida sin dejar que un fallo al cerrar tape el resultado."""
    try:
        await _resolver(archivo.close())
    except Exception:  # pragma: no cover - red de seguridad
        _registro.warning("MOD-02 no se pudo cerrar la subida")


async def _resolver(valor: Any) -> Any:
    """Espera el resultado si hace falta.

    `UploadFile.read` y `UploadFile.close` son asíncronos, pero un archivo
    común no lo es. Aceptar los dos deja probar MOD-02 sin montar la API.
    """
    if inspect.isawaitable(valor):
        return await valor
    return valor
