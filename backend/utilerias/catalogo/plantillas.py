"""UT-01, las plantillas de explicación de los grupos (T-20).

Viven en datos/catalogo/plantillas.json, junto al catálogo, y se leen solo
aquí. MOD-07 las pide a esta función igual que pide el catálogo.

Cada plantilla trae solo el porqué del grupo y, si hace falta, el texto que lo
distingue de un grupo vecino (CA-07.2). No trae números: la región, el pico y
el rasgo los arma MOD-07 con el catálogo. Para no romper esa regla sin darse
cuenta, el lector rechaza una plantilla que tenga cifras o una marca que no
sepa llenar.

Que falte la plantilla de un grupo no es un error de carga. Es el caso de
CA-07.3, y lo resuelve MOD-07 mostrando «Explicación no disponible».
"""

from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.utilerias.catalogo.lector import CARPETA, ErrorDeCatalogo

#: El archivo de las plantillas, junto al catálogo.
RUTA_PLANTILLAS: Path = CARPETA / "plantillas.json"

#: Las marcas que una plantilla puede usar y que MOD-07 sabe llenar. La única
#: hoy es el rango de la región acompañante que confirma el grupo.
MARCAS_PERMITIDAS: frozenset[str] = frozenset({"confirmacion"})

_CIFRA = re.compile(r"\d")


@dataclass(frozen=True)
class Distincion:
    """Por qué se atribuyó al grupo y no a su vecino de región."""

    frente_a: str
    texto: str


@dataclass(frozen=True)
class Plantilla:
    """La plantilla de un grupo, tal como la recibe MOD-07."""

    grupo: str
    por_que: str
    distincion: Distincion | None
    fuentes: tuple[str, ...]
    revisado_por: str | None
    fecha_revision: str | None


@dataclass(frozen=True)
class Plantillas:
    """Todas las plantillas, por grupo."""

    version: str
    por_grupo: dict[str, Plantilla]
    ruta: Path

    def de(self, grupo: str) -> Plantilla | None:
        return self.por_grupo.get(grupo)


def _error(detalle: str, ruta: Path) -> ErrorDeCatalogo:
    return ErrorDeCatalogo(f"UT-01, plantillas: {detalle} (archivo: {ruta})")


def _texto_limpio(valor: Any, donde: str, ruta: Path) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise _error(f"{donde} debe ser un texto no vacío", ruta)
    if _CIFRA.search(valor):
        raise _error(
            f"{donde} trae cifras; los números se toman del catálogo, no se "
            "escriben en la plantilla",
            ruta,
        )
    marcas = {nombre for _, nombre, _, _ in string.Formatter().parse(valor) if nombre}
    desconocidas = marcas - MARCAS_PERMITIDAS
    if desconocidas:
        raise _error(f"{donde} usa marcas que nadie llena: {sorted(desconocidas)}", ruta)
    return valor.strip()


def _texto_o_nulo(valor: Any, donde: str, ruta: Path) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str) or not valor.strip():
        raise _error(f"{donde} debe ser un texto o null", ruta)
    return valor.strip()


def _plantilla(valor: Any, ruta: Path) -> Plantilla:
    if not isinstance(valor, dict):
        raise _error("cada plantilla debe ser un objeto", ruta)
    grupo = valor.get("grupo")
    if not isinstance(grupo, str) or not grupo.strip():
        raise _error("una plantilla no dice de qué grupo es", ruta)
    grupo = grupo.strip()

    distincion = None
    crudo = valor.get("distincion")
    if crudo is not None:
        if not isinstance(crudo, dict):
            raise _error(f"la distinción de {grupo} debe ser un objeto o null", ruta)
        frente_a = crudo.get("frente_a")
        if not isinstance(frente_a, str) or not frente_a.strip():
            raise _error(f"la distinción de {grupo} no dice frente a qué grupo", ruta)
        distincion = Distincion(
            frente_a=frente_a.strip(),
            texto=_texto_limpio(crudo.get("texto"), f"la distinción de {grupo}", ruta),
        )

    fuentes = valor.get("fuentes")
    if not isinstance(fuentes, list) or not fuentes or not all(
        isinstance(f, str) and f.strip() for f in fuentes
    ):
        raise _error(f"la plantilla de {grupo} debe nombrar sus fuentes", ruta)

    return Plantilla(
        grupo=grupo,
        por_que=_texto_limpio(valor.get("por_que"), f"el porqué de {grupo}", ruta),
        distincion=distincion,
        fuentes=tuple(f.strip() for f in fuentes),
        revisado_por=_texto_o_nulo(valor.get("revisado_por"), "revisado_por", ruta),
        fecha_revision=_texto_o_nulo(valor.get("fecha_revision"), "fecha_revision", ruta),
    )


def cargar_plantillas(ruta: Path | str | None = None) -> Plantillas:
    """Lee y revisa las plantillas.

    Raises:
        ErrorDeCatalogo: si el archivo no existe, no es JSON, una plantilla
            está incompleta, trae cifras o un grupo aparece dos veces.
    """
    ruta_final = Path(ruta) if ruta is not None else RUTA_PLANTILLAS
    if not ruta_final.is_file():
        raise _error("no se encontró el archivo de plantillas", ruta_final)
    try:
        datos = json.loads(ruta_final.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise _error(f"no es JSON válido (línea {error.lineno})", ruta_final) from error
    if not isinstance(datos, dict) or not isinstance(datos.get("plantillas"), list):
        raise _error("falta la lista «plantillas»", ruta_final)
    version = datos.get("version")
    if not isinstance(version, str) or not version.strip():
        raise _error("falta la versión", ruta_final)

    por_grupo: dict[str, Plantilla] = {}
    for crudo in datos["plantillas"]:
        plantilla = _plantilla(crudo, ruta_final)
        if plantilla.grupo in por_grupo:
            raise _error(f"{plantilla.grupo} tiene dos plantillas", ruta_final)
        por_grupo[plantilla.grupo] = plantilla

    return Plantillas(version=version.strip(), por_grupo=por_grupo, ruta=ruta_final)


_plantillas: Plantillas | None = None


def obtener_plantillas() -> Plantillas:
    """Las plantillas del repositorio, leídas una sola vez."""
    global _plantillas
    if _plantillas is None:
        _plantillas = cargar_plantillas()
    return _plantillas
