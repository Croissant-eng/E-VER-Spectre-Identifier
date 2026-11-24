"""MOD-07, la capa educativa: explica cada grupo detectado (T-21 y T-22).

Para cada detección de MOD-06 arma una explicación con las cuatro partes que
pide CA-07.1:

1. La región característica, tomada del catálogo de UT-01.
2. La posición observada del pico, tal como la dio la vía de reglas. Si el
   motor no la dio, se dice así y se resalta la región completa (CA-06.3).
3. El rasgo que lo delata, armado con la intensidad y la forma del catálogo,
   por ejemplo «pico intenso y agudo» para el carbonilo.
4. Por qué corresponde al grupo, que es el texto de la plantilla (T-20).

Si el pico cae también en la región del grupo vecino que nombra la plantilla,
se agrega la distinción, por ejemplo por qué es N–H y no O–H (CA-07.2).

Cuando un grupo no tiene plantilla no se inventa nada: se devuelve una
explicación marcada como no disponible y quien llama registra el error y la
pasa a UT-02 (CA-07.3). Los demás grupos se explican igual.

Este módulo no redacta mensajes de error. Esos son de UT-02 y se convierten
en texto en backend/api/veredicto.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.utilerias.catalogo import Catalogo, GrupoFuncional, Plantillas
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.catalogo import obtener_plantillas

#: Cómo se dice cada intensidad del catálogo, en masculino y en femenino.
INTENSIDADES: dict[str, tuple[str, str]] = {
    "fuerte": ("intenso", "intensa"),
    "media": ("de intensidad media", "de intensidad media"),
    "media o débil": ("de intensidad media o débil", "de intensidad media o débil"),
}

#: Cómo se nombra cada forma del catálogo: el sustantivo, si es femenino y el
#: adjetivo que la describe. None es la forma que el diseño no le asigna al
#: alqueno; se describe solo por su intensidad.
FORMAS: dict[str | None, tuple[str, bool, str | None]] = {
    "aguda": ("pico", False, "agudo"),
    "ancha": ("banda", True, "ancha"),
    "angosta": ("banda", True, "angosta"),
    "par de bandas": ("par de bandas", False, None),
    None: ("banda", True, None),
}

#: El rol de la región acompañante que llena la marca {confirmacion}.
ROL_CONFIRMACION = "confirmacion"

UNIDAD = "cm⁻¹"


class VocabularioDesconocido(ValueError):
    """El catálogo usa una intensidad o una forma que MOD-07 no sabe decir."""


@dataclass(frozen=True)
class Explicacion:
    """La explicación de un grupo detectado."""

    grupo: str
    disponible: bool
    region: str = ""
    posicion: str = ""
    rasgo: str = ""
    por_que: str = ""
    distincion: str | None = None

    def como_diccionario(self) -> dict[str, Any]:
        return {
            "disponible": self.disponible,
            "region": self.region,
            "posicion": self.posicion,
            "rasgo": self.rasgo,
            "por_que": self.por_que,
            "distincion": self.distincion,
        }


def _numero(valor: float) -> str:
    """Un número de onda sin decimales, como se lee en una tabla de IR."""
    return f"{round(valor):d}"


def _rango(rango: tuple[float, float]) -> str:
    menor, mayor = rango
    if menor == mayor:
        return f"cerca de {_numero(menor)} {UNIDAD}"
    return f"entre {_numero(menor)} y {_numero(mayor)} {UNIDAD}"


def rasgo_de(grupo: GrupoFuncional) -> str:
    """El rasgo del pico con las palabras del catálogo, por ejemplo
    «pico intenso y agudo»."""
    if grupo.intensidad not in INTENSIDADES or grupo.forma not in FORMAS:
        raise VocabularioDesconocido(
            f"{grupo.id}: intensidad «{grupo.intensidad}» o forma «{grupo.forma}» "
            "sin traducción en MOD-07"
        )
    sustantivo, femenino, adjetivo = FORMAS[grupo.forma]
    intensidad = INTENSIDADES[grupo.intensidad][1 if femenino else 0]
    if adjetivo is None:
        return f"{sustantivo} {intensidad}"
    if intensidad.startswith("de "):
        return f"{sustantivo} {adjetivo} {intensidad}"
    return f"{sustantivo} {intensidad} y {adjetivo}"


def _confirmacion(grupo: GrupoFuncional) -> str:
    regiones = grupo.acompanantes_por_rol(ROL_CONFIRMACION)
    if not regiones:
        return ""
    return _rango(regiones[0].rango)


def _dentro(valor: float, rango: tuple[float, float]) -> bool:
    return rango[0] <= valor <= rango[1]


def explicar(
    grupo_id: str,
    pico_cm1: float | None,
    catalogo: Catalogo | None = None,
    plantillas: Plantillas | None = None,
) -> Explicacion:
    """La explicación de un grupo detectado.

    Args:
        grupo_id: el identificador del grupo, por ejemplo GF-05.
        pico_cm1: la posición que dio la vía de reglas, o None.
        catalogo: el de UT-01. Por omisión, el del repositorio.
        plantillas: las de UT-01. Por omisión, las del repositorio.

    Returns:
        La explicación. Si el grupo no tiene plantilla, una con disponible en
        False y sin texto: el aviso lo pone UT-02.
    """
    datos = catalogo if catalogo is not None else obtener_catalogo()
    textos = plantillas if plantillas is not None else obtener_plantillas()

    plantilla = textos.de(grupo_id)
    if plantilla is None:
        return Explicacion(grupo=grupo_id, disponible=False)

    grupo = datos.por_id(grupo_id)
    region = f"Su región característica está {_rango(grupo.region_cm1)}."
    if pico_cm1 is None:
        posicion = (
            "El análisis no dio la posición exacta del pico, así que se resalta "
            "la región completa."
        )
    else:
        posicion = f"El pico observado está en {_numero(pico_cm1)} {UNIDAD}."
    articulo = "una" if FORMAS[grupo.forma][1] else "un"
    rasgo = f"Lo delata {articulo} {rasgo_de(grupo)}."
    por_que = plantilla.por_que.format(confirmacion=_confirmacion(grupo))

    distincion = None
    if plantilla.distincion is not None:
        vecino = datos.por_id(plantilla.distincion.frente_a)
        referencia = pico_cm1 if pico_cm1 is not None else sum(grupo.region_cm1) / 2
        if _dentro(referencia, vecino.region_cm1):
            distincion = plantilla.distincion.texto

    return Explicacion(
        grupo=grupo_id,
        disponible=True,
        region=region,
        posicion=posicion,
        rasgo=rasgo,
        por_que=por_que,
        distincion=distincion,
    )
