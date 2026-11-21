"""Apoyo compartido de las pruebas del backend.

Los archivos de prueba se reparten en dos grupos (sección 11 del plan):

- Los **chicos** están commiteados en `datos/pruebas/` y se usan tal cual.
- Los **pesados** —el de tamaño máximo exacto, el de un byte de más y el de
  ~3 MB— **no van al repositorio**: nadie quiere megabytes en el historial de
  git. Se generan aquí, una vez por corrida, en la carpeta temporal de pytest, y
  desaparecen con ella.

El tamaño máximo sale de UT-03, no de un número escrito aquí: si el equipo
cambia el límite, CA-01.2 y CA-02.2 siguen probando el límite de verdad.

La generación vive en `herramientas/`, fuera de la aplicación. Las pruebas la
importan de ahí para no tener una segunda copia de la misma lógica; ningún
módulo de `backend/` la importa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.generador_espectros import csv_de_tamano_exacto
from herramientas.generar_fixtures import BYTES_TRES_MEGAS, DESDE, HASTA

RAIZ = Path(__file__).resolve().parents[2]

#: Los archivos de prueba commiteados.
CARPETA_FIXTURES = RAIZ / "datos" / "pruebas"


@pytest.fixture(scope="session")
def carpeta_fixtures() -> Path:
    """La carpeta de los archivos de prueba commiteados."""
    assert CARPETA_FIXTURES.is_dir(), (
        f"faltan los archivos de prueba en {CARPETA_FIXTURES}; "
        "regenérelos con «python -m herramientas.generar_fixtures»"
    )
    return CARPETA_FIXTURES


@pytest.fixture(scope="session")
def archivos_grandes(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Los tres archivos pesados, generados al arrancar la corrida.

    Devuelve las rutas por nombre corto: «maximo», «un_byte_de_mas» y
    «tres_megas».
    """
    configuracion = obtener_configuracion()
    maximo = configuracion.archivo.tamano_maximo_bytes
    minimos = configuracion.validacion.puntos_minimos

    carpeta = tmp_path_factory.mktemp("espectros_grandes")

    tamanos = {
        "maximo": maximo,
        "un_byte_de_mas": maximo + 1,
        "tres_megas": BYTES_TRES_MEGAS,
    }

    rutas: dict[str, Path] = {}
    for nombre, bytes_objetivo in tamanos.items():
        ruta = carpeta / f"espectro-{nombre}.csv"
        ruta.write_bytes(
            csv_de_tamano_exacto(
                bytes_objetivo, DESDE, HASTA, puntos_minimos=minimos
            )
        )
        rutas[nombre] = ruta
    return rutas


@pytest.fixture(scope="session")
def csv_tamano_maximo(archivos_grandes: dict[str, Path]) -> Path:
    """CSV válido de exactamente el tamaño máximo de UT-03 (CA-01.2)."""
    return archivos_grandes["maximo"]


@pytest.fixture(scope="session")
def csv_un_byte_de_mas(archivos_grandes: dict[str, Path]) -> Path:
    """CSV de un byte por encima del tamaño máximo (CA-02.2)."""
    return archivos_grandes["un_byte_de_mas"]


@pytest.fixture(scope="session")
def csv_tres_megas(archivos_grandes: dict[str, Path]) -> Path:
    """CSV válido de ~3 MB: pasa de 1 MB y obliga al temporal de FastAPI (RNF-09)."""
    return archivos_grandes["tres_megas"]
