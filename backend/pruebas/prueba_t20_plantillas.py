"""T-20: las plantillas de explicación de los siete grupos.

Prueba de cobertura del plan: los siete grupos del catálogo tienen plantilla.
Además se revisa la regla de que los números no se escriben en la plantilla,
que cada una nombra sus dos fuentes y que la distinción apunta a un grupo que
existe. La revisión química que pide el plan (dos fuentes comparadas, otra
persona que apruebe y, si se puede, un profesor) no se puede probar con
código: se registra en revisado_por y fecha_revision, que hoy están vacíos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.utilerias.catalogo import (
    ErrorDeCatalogo,
    RUTA_PLANTILLAS,
    cargar_plantillas,
    obtener_plantillas,
)
from backend.utilerias.catalogo import obtener as obtener_catalogo

FUENTES_DEL_PLAN = ("University of Colorado Boulder", "LibreTexts")


def prueba_los_siete_grupos_tienen_plantilla() -> None:
    plantillas = obtener_plantillas()
    for grupo in obtener_catalogo().orden_canonico:
        assert plantillas.de(grupo) is not None, f"{grupo} no tiene plantilla"


def prueba_no_hay_plantillas_de_grupos_que_no_existen() -> None:
    existentes = set(obtener_catalogo().orden_canonico)
    assert set(obtener_plantillas().por_grupo) <= existentes


def prueba_cada_plantilla_cita_las_dos_fuentes_del_plan() -> None:
    for plantilla in obtener_plantillas().por_grupo.values():
        juntas = " ".join(plantilla.fuentes)
        for fuente in FUENTES_DEL_PLAN:
            assert fuente in juntas, f"{plantilla.grupo} no cita {fuente}"


def prueba_la_distincion_apunta_a_un_grupo_del_catalogo() -> None:
    catalogo = obtener_catalogo()
    for plantilla in obtener_plantillas().por_grupo.values():
        if plantilla.distincion is not None:
            catalogo.por_id(plantilla.distincion.frente_a)


def prueba_el_nh_trae_su_distincion_frente_al_oh() -> None:
    """Lo necesita CA-07.2."""
    distincion = obtener_plantillas().de("GF-02").distincion

    assert distincion is not None
    assert distincion.frente_a == "GF-01"
    assert "angosta" in distincion.texto


def _escribir(tmp_path: Path, cambio) -> Path:
    datos = json.loads(RUTA_PLANTILLAS.read_text(encoding="utf-8"))
    cambio(datos)
    ruta = tmp_path / "plantillas.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def _poner(campo: str, valor):
    def cambio(datos):
        datos["plantillas"][4][campo] = valor
    return cambio


@pytest.mark.parametrize(
    "caso, cambio",
    [
        ("una región escrita a mano", _poner("por_que", "Absorbe entre 1670 y 1780 cm⁻¹.")),
        ("una marca que nadie llena", _poner("por_que", "Aparece en {region}.")),
        ("sin porqué", _poner("por_que", "")),
        ("sin fuentes", _poner("fuentes", [])),
        ("grupo repetido", lambda d: d["plantillas"].append(d["plantillas"][0])),
    ],
)
def prueba_el_lector_rechaza_una_plantilla_mal_hecha(tmp_path, caso, cambio) -> None:
    with pytest.raises(ErrorDeCatalogo):
        cargar_plantillas(_escribir(tmp_path, cambio))


def prueba_una_plantilla_que_falta_no_impide_cargar(tmp_path) -> None:
    """CA-07.3 se resuelve en MOD-07, no tirando la carga."""
    ruta = _escribir(tmp_path, lambda d: d["plantillas"].pop())

    plantillas = cargar_plantillas(ruta)

    assert plantillas.de("GF-07") is None
    assert plantillas.de("GF-01") is not None
