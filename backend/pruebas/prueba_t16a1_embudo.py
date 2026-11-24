"""Pruebas del instrumental de T-16a-1 (herramientas/dataset).

No necesitan ni el conjunto ni RDKit: miran las reglas que, si fallan,
falsearían el índice sin que nadie lo notara.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from herramientas.dataset.embudo_chemotion import (
    ATR,
    COLUMNAS,
    DESCONOCIDO,
    TRANSMISION,
    etapa_del_embudo,
    fraccion_relleno,
    modo_medicion,
)
from herramientas.dataset.estadistica import cuantil, spearman

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("instrumento", "cabeceras", "esperado"),
    [
        ("Bruker Alpha ATR", {}, ATR),
        ("Bruker, model IFS 88", {"SAMPLINGPROCEDURE": "Diamant-ATR"}, ATR),
        (None, {"SAMPLINGPROCEDURE": "ATR platinum Diamond 1 Refl"}, ATR),
        (None, {"SAMPLINGPROCEDURE": "KBr pellet"}, TRANSMISION),
        # La unidad NO es el modo: un ATR también se guarda en transmitancia.
        ("IR", {"YUNITS": "TRANSMITTANCE"}, DESCONOCIDO),
        # Que el Alpha-P sea un módulo ATR es saber del producto, no del archivo.
        ("Bruker Alpha-P", {}, DESCONOCIDO),
        ("SHIMADZU IRTRACER-100", {}, DESCONOCIDO),
        ("Thermo Scientific Nicolet Avatar 380", {}, DESCONOCIDO),
        # Plantilla sin llenar.
        (None, {"SAMPLINGPROCEDURE": "Instrument type and / or accessory"}, DESCONOCIDO),
        (None, {}, DESCONOCIDO),
        # Si las dos fuentes se contradicen no se elige una.
        ("Bruker Alpha ATR", {"SAMPLINGPROCEDURE": "KBr pellet"}, DESCONOCIDO),
    ],
)
def prueba_modo_de_medicion_no_adivina(instrumento, cabeceras, esperado) -> None:
    assert modo_medicion(instrumento, cabeceras) == esperado


def prueba_fraccion_de_relleno_cuenta_puntos_fuera_de_lo_medido() -> None:
    eje = (4000.0, 3000.0, 2000.0, 1000.0)
    assert fraccion_relleno(eje, (1000.0, 4000.0)) == 0.0
    assert fraccion_relleno(eje, (1500.0, 3500.0)) == 0.5


def prueba_el_indice_no_lleva_etiquetas_ni_split() -> None:
    """Son de T-16a-2, bloqueada por D-24."""
    prohibidas = {"split", "etiquetas"} | {f"gf-0{i}" for i in range(1, 8)}
    assert not {c.lower() for c in COLUMNAS} & prohibidas


@pytest.mark.parametrize(
    ("smiles", "mod03", "mod04", "esperado"),
    [
        (False, None, None, "SMILES_NO_PARSEABLE"),
        (False, "RANGO_INSUFICIENTE", None, "SMILES_NO_PARSEABLE"),
        (True, "RANGO_INSUFICIENTE", None, "MOD-03:RANGO_INSUFICIENTE"),
        (True, None, "DATOS_ILEGIBLES", "MOD-04:DATOS_ILEGIBLES"),
        (True, None, None, "PASA"),
    ],
)
def prueba_el_veredicto_es_la_primera_etapa_que_falla(
    smiles, mod03, mod04, esperado
) -> None:
    assert etapa_del_embudo(smiles, mod03, mod04) == esperado


def prueba_los_espectros_y_los_pesos_no_entran_a_git() -> None:
    """D-12 y D-18. Se le pregunta a git, no al texto de .gitignore.

    Así habría caído la regla con guion que no se aplicaba a nada (D-23.6).
    """
    for ruta in ("datos/dataset/espectros/x.jdx", "motor_identificacion/modelo/x.bin"):
        salida = subprocess.run(
            ["git", "check-ignore", "-q", ruta], cwd=RAIZ, check=False
        )
        if salida.returncode == 128:
            pytest.skip("no es un clon de git")
        assert salida.returncode == 0, f"git versionaría {ruta}"


def prueba_spearman_y_cuantiles() -> None:
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 1, 2, 2], [1, 1, 2, 2]) == pytest.approx(1.0)
    assert spearman([1, 1, 1], [1, 2, 3]) is None
    assert cuantil([1, 2, 3, 4, 5], 0.5) == 3
    assert cuantil([0, 10], 0.25) == 2.5
