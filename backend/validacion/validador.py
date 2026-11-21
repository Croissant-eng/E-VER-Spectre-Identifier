"""MOD-03 · Validador · la puerta del módulo.

Recibe lo que MOD-02 entrega —**contenido como texto**, nombre e indicador de
tamaño correcto (contrato de la sección 5)— y devuelve un **veredicto**: válido
sí o no y, si no, el código de UT-02 que explica el motivo.

El texto llega tal como lo dejó MOD-02: sin la marca de orden de bytes (BOM) y
con los bytes que no eran texto válido convertidos en el carácter de reemplazo
«�» (U+FFFD). Esa marca es justamente una de las pistas de la capa «¿es texto?».

**Tres funciones, porque son dos preguntas distintas:**

- `validar_formato` — T-04: «¿es de verdad este formato?» (`formato.py`).
- `validar_requisitos` — T-05: «¿cumple los puntos y el rango?»
  (`requisitos.py`).
- `validar` — las dos en orden, y es la que usa la API (T-07). Si el formato
  falla, no se mide nada: no tiene sentido contar los puntos de un archivo que
  ni es un espectro.

Las dos primeras existen porque cada tarea se prueba aislada (sección 9 del
plan), y porque así se ve de un golpe a qué pregunta pertenece cada rechazo.

**Lo que MOD-03 no hace:** no normaliza, no ordena y no convierte (eso es
MOD-04, incremento 2); no arma mensajes (devuelve el **código** y UT-02 pone el
texto con motivo y acción, que la capa HTTP traduce para MOD-02 y MOD-03 en el
mismo lugar); y no importa MOD-02 ni nada de FastAPI, así que se puede probar
con texto simulado.

**Robustez (CA-02.4):** ninguna entrada hace que este módulo levante una
excepción. Un archivo vacío, truncado o lleno de basura sale por la puerta del
veredicto, con su motivo, y el servidor sigue atendiendo.

El registro guarda nombre, resultado y la capa que rechazó; **nunca** el
contenido del espectro (RNF-09).
"""

from __future__ import annotations

from backend.nucleo import obtener_registro
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion.formato import revisar as revisar_formato
from backend.validacion.requisitos import revisar as revisar_requisitos
from backend.validacion.comun import (
    CODIGO_POR_CAPA,
    Fallo,
    Veredicto,
    extension_de,
)

_registro = obtener_registro("mod-03")


def validar_formato(
    nombre: str,
    contenido: str,
    *,
    tamano_correcto: bool = True,
    configuracion: Configuracion | None = None,
) -> Veredicto:
    """T-04 · ¿el contenido es de verdad del formato que declara el nombre?

    Args:
        nombre: el nombre que entregó MOD-02 (ya limpio).
        contenido: el archivo como texto, tal como lo entregó MOD-02.
        tamano_correcto: el indicador del contrato de la sección 5. Si viene en
            ``False`` no se revisa nada: MOD-02 no confirmó el tamaño, así que
            no hay contenido confiable que mirar.
        configuracion: los parámetros con los que se trabaja. Si es ``None`` se
            usan los de UT-03; el parámetro existe para las pruebas.

    Returns:
        El `Veredicto` de T-04. **Nunca levanta** una excepción por culpa del
        archivo.
    """
    parametros = _parametros(configuracion)
    extension = extension_de(nombre)
    fallo = revisar_formato(
        contenido, extension, parametros, tamano_correcto=tamano_correcto
    )
    return _veredicto(nombre, extension, fallo)


def validar_requisitos(
    nombre: str,
    contenido: str,
    *,
    configuracion: Configuracion | None = None,
) -> Veredicto:
    """T-05 · ¿cumple los puntos mínimos y el rango que pide UT-03?

    Se usa después de `validar_formato`; por sí sola no comprueba que el
    archivo sea del formato que dice ser.
    """
    parametros = _parametros(configuracion)
    extension = extension_de(nombre)
    fallo = revisar_requisitos(contenido, extension, parametros)
    return _veredicto(nombre, extension, fallo)


def validar(
    nombre: str,
    contenido: str,
    *,
    tamano_correcto: bool = True,
    configuracion: Configuracion | None = None,
) -> Veredicto:
    """Todo MOD-03: primero el formato (T-04) y luego los requisitos (T-05).

    Es la función que llama la API (T-07) y la que entrega el veredicto del
    contrato de la sección 5.
    """
    parametros = _parametros(configuracion)
    extension = extension_de(nombre)

    fallo = revisar_formato(
        contenido, extension, parametros, tamano_correcto=tamano_correcto
    )
    if fallo is None:
        fallo = revisar_requisitos(contenido, extension, parametros)

    return _veredicto(nombre, extension, fallo)


# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


def _parametros(configuracion: Configuracion | None) -> Configuracion:
    return configuracion if configuracion is not None else obtener_configuracion()


def _veredicto(nombre: str, extension: str | None, fallo: Fallo | None) -> Veredicto:
    """Convierte el resultado de las capas en veredicto, y lo deja en el registro."""
    if fallo is None:
        _registro.info("MOD-03 veredicto | nombre=%s | resultado=%s", nombre, "valido")
        return Veredicto(valido=True, nombre=nombre, extension=extension)

    codigo = CODIGO_POR_CAPA[fallo.capa]
    _registro.warning(
        "MOD-03 veredicto | nombre=%s | resultado=%s | capa=%s | detalle=%s",
        nombre,
        codigo,
        fallo.capa,
        fallo.detalle,
    )
    return Veredicto(
        valido=False,
        nombre=nombre,
        extension=extension,
        codigo=codigo,
        capa=fallo.capa,
        detalle=fallo.detalle,
    )
