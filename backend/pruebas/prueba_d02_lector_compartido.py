"""Pruebas de D-2: MOD-03 y MOD-04 leen el archivo con el mismo lector.

El plan del incremento 2 pide un lector compartido para que los dos módulos
vean exactamente el mismo archivo. Si cada uno partiera el CSV o leyera las
etiquetas a su manera, uno podría aprobar un archivo que el otro entiende
distinto.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.nucleo import lector_espectro
from backend.preprocesamiento import lector as lector_mod04
from backend.validacion import comun as comun_mod03
from backend.validacion import requisitos


@pytest.mark.parametrize(
    "nombre",
    ["espectro-con-encabezado.csv", "espectro-punto-y-coma.csv", "espectro-porcentaje.csv"],
)
def prueba_mod03_y_mod04_ven_los_mismos_pares(carpeta_fixtures: Path, nombre: str) -> None:
    texto = (carpeta_fixtures / nombre).read_text(encoding="ascii")

    de_mod03 = comun_mod03.leer_csv(texto)
    de_mod04 = lector_mod04.leer_csv(texto)

    assert isinstance(de_mod03, comun_mod03.FilasCsv)
    assert de_mod03.pares == de_mod04.pares


def prueba_los_dos_modulos_usan_la_misma_funcion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si el lector compartido cambia, los dos módulos lo notan a la vez."""
    llamadas: list[str] = []
    original = lector_espectro.leer_tabla_csv

    def vigilada(contenido, **opciones):
        llamadas.append("leida")
        return original(contenido, **opciones)

    monkeypatch.setattr(lector_espectro, "leer_tabla_csv", vigilada)
    monkeypatch.setattr(lector_mod04, "leer_tabla_csv", vigilada)
    texto = "onda,absorbancia\n400,0.1\n404,0.2\n"

    comun_mod03.leer_csv(texto)
    lector_mod04.leer_csv(texto)

    assert llamadas == ["leida", "leida"]


def prueba_las_etiquetas_del_jdx_se_leen_igual(carpeta_fixtures: Path) -> None:
    texto = (carpeta_fixtures / "espectro-valido.jdx").read_text(encoding="ascii")
    cabecera = lector_espectro.leer_cabecera_jdx(texto)

    for etiqueta in (requisitos.ETIQUETA_PUNTOS, requisitos.ETIQUETA_PRIMERA_X,
                     requisitos.ETIQUETA_ULTIMA_X):
        nombre = lector_espectro.nombre_de_etiqueta(etiqueta)
        assert requisitos._valor_de_etiqueta(texto, etiqueta) == cabecera.etiquetas[nombre]


def prueba_el_lector_compartido_no_conoce_mensajes_ni_configuracion() -> None:
    """Es lectura de bajo nivel: validar y convertir es de cada módulo."""
    codigo = Path(lector_espectro.__file__).read_text(encoding="utf-8")
    assert "mensajes" not in codigo.split('"""', 2)[2]
    assert "configuracion" not in codigo.split('"""', 2)[2]
