"""UT-01 · Catálogo de grupos funcionales · carga y validación.

Este módulo es la **única puerta** al catálogo de los 7 grupos funcionales. Los
rangos viven solo en el archivo que nombra `NOMBRE_ARCHIVO`; ningún otro módulo
los repite. Un número de región escrito a mano en la vía de reglas es un
defecto, no un atajo (plan del incremento 3, sección 3, regla 2).

Tres propiedades que este módulo garantiza:

1. **Se carga una vez.** `obtener()` lee el archivo la primera vez y guarda el
   resultado en memoria: el catálogo es de solo lectura y no cambia mientras el
   backend corre (persistencia v2, sin base de datos).
2. **Es de solo lectura de verdad.** Todo lo que sale de aquí son `dataclass`
   congeladas y tuplas: quien lo reciba no puede modificarlo por descuido.
3. **No arranca en silencio.** Si el archivo falta, está corrupto, le falta un
   grupo o a un grupo le falta su región o un rasgo, se levanta
   `ErrorDeCatalogo`. Es el mismo patrón que UT-03 estrenó en T-01.

El **orden canónico** GF-01 … GF-07 es el del vector de etiquetas de T-16 y de
la salida del CNN. Se fija en el archivo, una sola vez, y aquí se verifica que
el arreglo de grupos lo respete. `indice_de()` existe justamente para que T-16
no vuelva a decidir ese orden por su cuenta.

Este módulo no depende de UT-02 ni de UT-03: el catálogo son datos, no lógica,
y no decide nada. Tampoco sale a la red: abre un archivo local y nada más.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Raíz del repositorio, calculada desde este archivo
#: (`backend/utilerias/catalogo/lector.py` → tres niveles arriba).
RAIZ: Path = Path(__file__).resolve().parents[3]

#: Carpeta de datos del catálogo (Diseño Modular v2 y persistencia v2: UT-01 son
#: `backend/utilerias/catalogo/` —el lector— más `datos/catalogo/` —los datos—).
CARPETA: Path = RAIZ / "datos" / "catalogo"

#: Nombre del archivo del catálogo. Vive solo aquí: el lector y las pruebas lo
#: leen de esta constante, así un renombre futuro toca una sola línea.
NOMBRE_ARCHIVO: str = "grupos.json"

#: Patrón para detectar variantes del catálogo. Si aparece una segunda, alguna
#: deja de ser la fuente única y hay que volver a decidir.
PATRON_ARCHIVO: str = "grupos*.json"

#: Ruta completa del catálogo.
RUTA_CATALOGO: Path = CARPETA / NOMBRE_ARCHIVO

#: Cuántos grupos debe traer el catálogo. No es un parámetro configurable: es el
#: alcance del proyecto (RF-04 pide siete grupos funcionales, ni seis ni ocho).
#: Si algún día el alcance cambia, cambia el requerimiento, no la configuración.
GRUPOS_ESPERADOS: int = 7

#: Vocabulario cerrado del campo `rol` de una región acompañante. Es una lista
#: cerrada a propósito: T-15 decide qué hacer con cada rol sin interpretar texto
#: libre, y un rol mal escrito se detecta al cargar, no en producción.
#:
#: - `confirmacion`: desempate R-2. Sin esa banda, el score del grupo se acota
#:   por debajo del umbral (quien lo aplica es T-15, no este módulo).
#: - `par`: una de las bandas del par característico, dentro de la región
#:   principal. GF-07 exige las dos.
#: - `indicio`: señala un subtipo. Informativa; no condiciona la detección.
ROLES_VALIDOS: frozenset[str] = frozenset({"confirmacion", "par", "indicio"})

#: Cuántas bandas forma un par (D-20.1). No es un parámetro: es lo que la
#: palabra significa, y R-2 lo exige literalmente — GF-07 necesita el **par**
#: de bandas del anillo, no una de las dos.
#:
#: Por qué se valida al cargar: si un dedazo borra una de las dos bandas, R-2 se
#: debilita en silencio —el catálogo sigue siendo JSON válido y el lector lo
#: aceptaría— y el aromático se volvería más fácil de afirmar sin que nada lo
#: detecte. Un grupo trae cero bandas `par` o trae las dos.
BANDAS_DEL_PAR: int = 2

#: Campos de un grupo que deben venir y no pueden estar vacíos.
_TEXTOS_OBLIGATORIOS: tuple[str, ...] = (
    "id",
    "nombre",
    "enlace_vibracion",
    "intensidad",
    "pista",
)


class ErrorDeCatalogo(Exception):
    """El catálogo falta, no se puede leer o está incompleto.

    Es un error de arranque, no un rechazo de negocio: el usuario final nunca lo
    ve. Traducirlo a un mensaje de UT-02 es trabajo de la capa HTTP, igual que
    con `ErrorDeConfiguracion` de UT-03.
    """


@dataclass(frozen=True)
class RegionAcompanante:
    """Una banda que acompaña a la región principal de un grupo.

    No es decoración: para GF-06 y GF-07 es el desempate de la regla R-2.
    `rango` puede tener mínimo igual a máximo cuando el plan da una posición
    aproximada en vez de un intervalo (las dos bandas del par de GF-07); la
    tolerancia alrededor de ese punto es parámetro de UT-03.
    """

    rango: tuple[float, float]
    rol: str


@dataclass(frozen=True)
class SubtipoDeGrupo:
    """Un subtipo informativo de un grupo (hoy, los de C=O).

    En el incremento 3 **no** son detecciones separadas: RF-04 pide los siete
    grupos, no sus subtipos. Están cargados para las explicaciones de T-20.
    """

    nombre: str
    region_cm1: tuple[float, float]


@dataclass(frozen=True)
class GrupoFuncional:
    """Un grupo funcional del catálogo, tal como lo recibe MOD-06."""

    id: str
    nombre: str
    enlace_vibracion: str
    region_cm1: tuple[float, float]
    regiones_acompanantes: tuple[RegionAcompanante, ...]
    intensidad: str
    forma: str | None
    pista: str
    subtipos: tuple[SubtipoDeGrupo, ...]

    def acompanantes_por_rol(self, rol: str) -> tuple[RegionAcompanante, ...]:
        """Las regiones acompañantes de un rol dado, en el orden del catálogo."""
        return tuple(r for r in self.regiones_acompanantes if r.rol == rol)


@dataclass(frozen=True)
class Catalogo:
    """El catálogo ya validado, listo para usarse en solo lectura."""

    version: str
    orden_canonico: tuple[str, ...]
    grupos: tuple[GrupoFuncional, ...]
    ruta: Path

    def por_id(self, identificador: str) -> GrupoFuncional:
        """El grupo con ese ID.

        Raises:
            ErrorDeCatalogo: si el ID no es de los siete del catálogo. Pedir un
                grupo que no existe es un defecto de programación, y es mejor
                que reviente aquí que que viaje como `None`.
        """
        for grupo in self.grupos:
            if grupo.id == identificador:
                return grupo
        raise ErrorDeCatalogo(
            f"UT-01: el grupo «{identificador}» no está en el catálogo; "
            f"los válidos son {list(self.orden_canonico)}"
        )

    def indice_de(self, identificador: str) -> int:
        """La posición del grupo en el vector de etiquetas (orden canónico).

        Es la función que evita que T-16 vuelva a decidir el orden: el modelo
        pregunta aquí en qué posición va cada etiqueta.
        """
        self.por_id(identificador)
        return self.orden_canonico.index(identificador)


# --------------------------------------------------------------------------- #
# Validación
# --------------------------------------------------------------------------- #

_ACCION = (
    "Corrija el catálogo de grupos funcionales de UT-01 y vuelva a iniciar el "
    "backend."
)


def _error(detalle: str, ruta: Path) -> ErrorDeCatalogo:
    return ErrorDeCatalogo(f"UT-01: {detalle} (archivo: {ruta}). {_ACCION}")


def _texto(
    datos: dict[str, Any], llave: str, ruta: Path, prefijo: str
) -> str:
    if llave not in datos:
        raise _error(f"falta la llave obligatoria «{prefijo}.{llave}»", ruta)
    valor = datos[llave]
    if not isinstance(valor, str) or not valor.strip():
        raise _error(
            f"«{prefijo}.{llave}» debe ser un texto no vacío; "
            f"se encontró {valor!r}",
            ruta,
        )
    return valor.strip()


def _texto_o_nulo(
    datos: dict[str, Any], llave: str, ruta: Path, prefijo: str
) -> str | None:
    """Un rasgo que el plan puede no dar.

    La llave **tiene que estar**: `null` dice «el plan no lo especifica», y que
    falte dice «este catálogo está a medio escribir». No son lo mismo y quien lo
    lea no debería tener que adivinar.
    """
    if llave not in datos:
        raise _error(f"falta la llave obligatoria «{prefijo}.{llave}»", ruta)
    valor = datos[llave]
    if valor is None:
        return None
    if not isinstance(valor, str) or not valor.strip():
        raise _error(
            f"«{prefijo}.{llave}» debe ser un texto no vacío o null; "
            f"se encontró {valor!r}",
            ruta,
        )
    return valor.strip()


def _rango(
    valor: Any, ruta: Path, prefijo: str, *, permitir_punto: bool
) -> tuple[float, float]:
    if not isinstance(valor, list) or len(valor) != 2:
        raise _error(
            f"«{prefijo}» debe ser una lista de dos números [mínimo, máximo]; "
            f"se encontró {valor!r}",
            ruta,
        )

    numeros: list[float] = []
    for elemento in valor:
        # `bool` es subclase de `int`: sin esta guarda, `true` pasaría por un
        # número válido.
        if isinstance(elemento, bool) or not isinstance(elemento, (int, float)):
            raise _error(
                f"«{prefijo}» debe contener solo números; "
                f"se encontró {elemento!r}",
                ruta,
            )
        numeros.append(float(elemento))

    minimo, maximo = numeros
    if minimo <= 0 or maximo <= 0:
        raise _error(f"«{prefijo}» debe tener números de onda positivos", ruta)
    if minimo > maximo:
        raise _error(
            f"«{prefijo}» está invertido: el mínimo ({minimo:g}) debe ser menor "
            f"que el máximo ({maximo:g})",
            ruta,
        )
    if minimo == maximo and not permitir_punto:
        raise _error(
            f"«{prefijo}» tiene ancho cero: una región principal necesita dos "
            f"números distintos, no {minimo:g}",
            ruta,
        )
    return minimo, maximo


def _lista(valor_padre: dict[str, Any], llave: str, ruta: Path, prefijo: str) -> list[Any]:
    """Una lista que puede venir vacía, pero no puede faltar."""
    if llave not in valor_padre:
        raise _error(f"falta la llave obligatoria «{prefijo}.{llave}»", ruta)
    valor = valor_padre[llave]
    if not isinstance(valor, list):
        raise _error(
            f"«{prefijo}.{llave}» debe ser una lista (puede ir vacía); "
            f"se encontró {type(valor).__name__}",
            ruta,
        )
    return valor


def _region_acompanante(
    valor: Any, ruta: Path, prefijo: str
) -> RegionAcompanante:
    if not isinstance(valor, dict):
        raise _error(
            f"«{prefijo}» debe ser un objeto con «rango» y «rol»; "
            f"se encontró {type(valor).__name__}",
            ruta,
        )
    if "rango" not in valor:
        raise _error(f"falta la llave obligatoria «{prefijo}.rango»", ruta)

    rango = _rango(valor["rango"], ruta, f"{prefijo}.rango", permitir_punto=True)
    rol = _texto(valor, "rol", ruta, prefijo)
    if rol not in ROLES_VALIDOS:
        raise _error(
            f"«{prefijo}.rol» vale «{rol}», que no está en el vocabulario del "
            f"catálogo: {sorted(ROLES_VALIDOS)}",
            ruta,
        )
    return RegionAcompanante(rango=rango, rol=rol)


def _subtipo(valor: Any, ruta: Path, prefijo: str) -> SubtipoDeGrupo:
    if not isinstance(valor, dict):
        raise _error(
            f"«{prefijo}» debe ser un objeto con «nombre» y «region_cm1»; "
            f"se encontró {type(valor).__name__}",
            ruta,
        )
    nombre = _texto(valor, "nombre", ruta, prefijo)
    if "region_cm1" not in valor:
        raise _error(f"falta la llave obligatoria «{prefijo}.region_cm1»", ruta)
    region = _rango(
        valor["region_cm1"], ruta, f"{prefijo}.region_cm1", permitir_punto=True
    )
    return SubtipoDeGrupo(nombre=nombre, region_cm1=region)


def _grupo(valor: Any, ruta: Path, posicion: int) -> GrupoFuncional:
    prefijo = f"grupos[{posicion}]"
    if not isinstance(valor, dict):
        raise _error(
            f"«{prefijo}» debe ser un objeto con los datos del grupo; "
            f"se encontró {type(valor).__name__}",
            ruta,
        )

    # El ID primero: a partir de aquí los mensajes lo nombran, para que quien
    # arranque el backend sepa de inmediato qué grupo mirar.
    identificador = _texto(valor, "id", ruta, prefijo)
    prefijo = f"grupos[{posicion}] ({identificador})"

    for llave in _TEXTOS_OBLIGATORIOS:
        _texto(valor, llave, ruta, prefijo)

    if "region_cm1" not in valor:
        raise _error(f"falta la llave obligatoria «{prefijo}.region_cm1»", ruta)
    region = _rango(
        valor["region_cm1"], ruta, f"{prefijo}.region_cm1", permitir_punto=False
    )

    acompanantes = tuple(
        _region_acompanante(
            elemento, ruta, f"{prefijo}.regiones_acompanantes[{indice}]"
        )
        for indice, elemento in enumerate(
            _lista(valor, "regiones_acompanantes", ruta, prefijo)
        )
    )
    # D-20.1: un par son dos bandas. Cero está bien (solo GF-07 tiene par);
    # una sola es un catálogo roto que debilitaría R-2 sin avisar.
    pares = tuple(r for r in acompanantes if r.rol == "par")
    if pares and len(pares) != BANDAS_DEL_PAR:
        raise _error(
            f"«{prefijo}» declara {len(pares)} banda(s) con rol «par» y un par "
            f"son {BANDAS_DEL_PAR}. R-2 exige las dos bandas del par: con una "
            f"sola, el desempate se debilita en silencio",
            ruta,
        )

    subtipos = tuple(
        _subtipo(elemento, ruta, f"{prefijo}.subtipos[{indice}]")
        for indice, elemento in enumerate(_lista(valor, "subtipos", ruta, prefijo))
    )

    return GrupoFuncional(
        id=identificador,
        nombre=_texto(valor, "nombre", ruta, prefijo),
        enlace_vibracion=_texto(valor, "enlace_vibracion", ruta, prefijo),
        region_cm1=region,
        regiones_acompanantes=acompanantes,
        intensidad=_texto(valor, "intensidad", ruta, prefijo),
        forma=_texto_o_nulo(valor, "forma", ruta, prefijo),
        pista=_texto(valor, "pista", ruta, prefijo),
        subtipos=subtipos,
    )


def _orden_canonico(datos: dict[str, Any], ruta: Path) -> tuple[str, ...]:
    if "orden_canonico" not in datos:
        raise _error(
            "falta la llave obligatoria «orden_canonico»: es el orden del "
            "vector de etiquetas de T-16 y tiene que estar escrito, no "
            "deducirse",
            ruta,
        )
    valor = datos["orden_canonico"]
    if not isinstance(valor, list):
        raise _error("«orden_canonico» debe ser una lista de identificadores", ruta)

    identificadores: list[str] = []
    for elemento in valor:
        if not isinstance(elemento, str) or not elemento.strip():
            raise _error(
                f"«orden_canonico» debe contener solo identificadores no vacíos; "
                f"se encontró {elemento!r}",
                ruta,
            )
        identificadores.append(elemento.strip())

    if len(set(identificadores)) != len(identificadores):
        raise _error("«orden_canonico» tiene identificadores repetidos", ruta)
    if len(identificadores) != GRUPOS_ESPERADOS:
        raise _error(
            f"«orden_canonico» debe nombrar los {GRUPOS_ESPERADOS} grupos de "
            f"RF-04; nombra {len(identificadores)}",
            ruta,
        )
    return tuple(identificadores)


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #


def cargar(ruta: Path | str | None = None) -> Catalogo:
    """Lee y valida el catálogo de grupos funcionales.

    Args:
        ruta: archivo a leer. Si es ``None`` se usa `RUTA_CATALOGO`, el archivo
            del repositorio. El parámetro existe para las pruebas; la
            aplicación no lo pasa.

    Returns:
        El catálogo validado, en solo lectura.

    Raises:
        ErrorDeCatalogo: si el archivo no existe, no es JSON válido, falta un
            grupo, falta una llave obligatoria, el orden canónico no coincide
            con el de los grupos o algún valor es incoherente.
    """
    ruta_final = Path(ruta) if ruta is not None else RUTA_CATALOGO

    if not ruta_final.is_file():
        raise _error("no se encontró el catálogo de grupos funcionales", ruta_final)

    try:
        contenido = ruta_final.read_text(encoding="utf-8")
    except OSError as error:
        raise _error(
            f"no se pudo leer el catálogo ({error.strerror})", ruta_final
        ) from error

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError as error:
        raise _error(
            f"el catálogo no es JSON válido (línea {error.lineno}, "
            f"columna {error.colno})",
            ruta_final,
        ) from error

    if not isinstance(datos, dict):
        raise _error(
            "el catálogo debe contener un objeto JSON en su raíz", ruta_final
        )

    version = _texto(datos, "version", ruta_final, "catálogo")
    orden = _orden_canonico(datos, ruta_final)

    if "grupos" not in datos:
        raise _error("falta la llave obligatoria «grupos» del catálogo", ruta_final)
    crudos = datos["grupos"]
    if not isinstance(crudos, list):
        raise _error("«grupos» debe ser una lista de grupos", ruta_final)

    grupos = tuple(
        _grupo(elemento, ruta_final, posicion)
        for posicion, elemento in enumerate(crudos)
    )

    identificadores = tuple(g.id for g in grupos)
    if len(set(identificadores)) != len(identificadores):
        raise _error(
            f"hay identificadores de grupo repetidos: {list(identificadores)}",
            ruta_final,
        )

    faltantes = [i for i in orden if i not in identificadores]
    if faltantes:
        raise _error(
            f"faltan grupos en el catálogo: {faltantes}. RF-04 pide los "
            f"{GRUPOS_ESPERADOS} grupos completos",
            ruta_final,
        )
    sobrantes = [i for i in identificadores if i not in orden]
    if sobrantes:
        raise _error(
            f"hay grupos que el orden canónico no nombra: {sobrantes}",
            ruta_final,
        )

    # La comprobación que protege a T-16: el arreglo de grupos tiene que venir
    # en el orden canónico, no solo contener los mismos identificadores. Si se
    # reordena, el modelo acierta con las etiquetas cruzadas y nadie lo nota.
    if identificadores != orden:
        raise _error(
            "los grupos no están en el orden canónico: el catálogo declara "
            f"{list(orden)} y el arreglo trae {list(identificadores)}. Ese es "
            "el orden del vector de etiquetas de T-16",
            ruta_final,
        )

    return Catalogo(
        version=version,
        orden_canonico=orden,
        grupos=grupos,
        ruta=ruta_final,
    )


_catalogo: Catalogo | None = None


def obtener() -> Catalogo:
    """Devuelve el catálogo, leyéndolo del disco la primera vez.

    Es la puerta que usan los demás módulos (MOD-06 ahora; MOD-07 y MOD-08
    después). El resultado se guarda en memoria: el archivo es de solo lectura y
    no cambia mientras el backend corre.
    """
    global _catalogo
    if _catalogo is None:
        _catalogo = cargar()
    return _catalogo


def recargar(ruta: Path | str | None = None) -> Catalogo:
    """Vuelve a leer el catálogo y reemplaza lo que haya en memoria.

    Pensado para las pruebas y para verificar en vivo que cambiar el archivo
    cambia el comportamiento del sistema.
    """
    global _catalogo
    _catalogo = cargar(ruta)
    return _catalogo
