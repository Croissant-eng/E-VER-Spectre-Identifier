"""T-16b: paridad entre la ruta de entrenamiento y la de producción.

Un mismo archivo se pasa por las dos rutas y los vectores tienen que ser
idénticos, número por número. La de producción es la de verdad: el archivo
sube por /api/procesar, la página reenvía el espectro a /api/analizar y el
motor recorta la ventana que ve el modelo. La de entrenamiento es
herramientas/entrenamiento/preparar.py.

Esta prueba no entrena nada y no usa red: corre con los archivos de
datos/pruebas, que son de la suite.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import RUTA_PROCESAR, crear_aplicacion
from backend.api.entrada_analisis import espectro_desde
from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.entrenamiento.preparar import preparar
from motor_identificacion.inferencia import ventana_del_modelo

RAIZ = Path(__file__).resolve().parents[2]
PREPARAR = RAIZ / "herramientas" / "entrenamiento" / "preparar.py"

#: Archivos de datos/pruebas que pasan MOD-03 y MOD-04. Cubren JCAMP-DX
#: comprimido, descendente, con factores, CSV con encabezado y en porcentaje.
ACEPTADOS = (
    "espectro-valido.jdx",
    "espectro-comprimido.jdx",
    "espectro-descendente.jdx",
    "espectro-factores.jdx",
    "espectro-con-encabezado.csv",
    "espectro-porcentaje.csv",
)


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    with TestClient(crear_aplicacion()) as abierto:
        yield abierto


def _por_produccion(cliente: TestClient, ruta: Path) -> tuple[float, ...]:
    respuesta = cliente.post(
        RUTA_PROCESAR, files={"archivo": (ruta.name, ruta.read_bytes(), "text/plain")}
    ).json()
    assert respuesta["valido"], respuesta
    configuracion = obtener_configuracion()
    espectro = espectro_desde(respuesta, configuracion)
    assert espectro is not None
    return ventana_del_modelo(espectro, configuracion)


@pytest.mark.parametrize("archivo", ACEPTADOS)
def prueba_las_dos_rutas_dan_el_mismo_vector(cliente, carpeta_fixtures, archivo) -> None:
    ruta = carpeta_fixtures / archivo
    produccion = _por_produccion(cliente, ruta)

    entrenamiento = preparar(ruta.name, ruta.read_text(encoding="latin-1"))

    assert entrenamiento.codigo is None
    assert entrenamiento.vector == produccion


def prueba_un_archivo_que_rechaza_la_aplicacion_tampoco_entra_al_entrenamiento(
    carpeta_fixtures,
) -> None:
    ruta = carpeta_fixtures / "espectro-linea-plana.csv"

    resultado = preparar(ruta.name, ruta.read_text(encoding="latin-1"))

    assert resultado.vector is None
    assert resultado.codigo


def prueba_el_vector_tiene_el_largo_de_la_ventana(carpeta_fixtures) -> None:
    configuracion = obtener_configuracion()
    minimo, maximo = configuracion.validacion.rango_requerido_cm1
    puntos = configuracion.procesamiento.puntos_rejilla
    menor, mayor = configuracion.procesamiento.rango_rejilla_cm1
    paso = (mayor - menor) / (puntos - 1)
    esperado = sum(1 for i in range(puntos) if minimo <= mayor - paso * i <= maximo)

    ruta = carpeta_fixtures / "espectro-valido.jdx"
    vector = preparar(ruta.name, ruta.read_text(encoding="latin-1")).vector

    assert vector is not None
    assert len(vector) == esperado


def prueba_la_ruta_de_entrenamiento_no_tiene_cuentas_propias() -> None:
    """Usa MOD-03, MOD-04 y la ventana de la fusión; no los copia."""
    arbol = ast.parse(PREPARAR.read_text(encoding="utf-8"))
    importados = {
        nodo.module
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom) and nodo.module
    }
    for modulo in (
        "backend.preprocesamiento",
        "backend.validacion",
        "motor_identificacion.inferencia",
        "backend.api.veredicto",
    ):
        assert modulo in importados

    prohibidos = {"numpy", "scipy", "math"}
    assert not importados & prohibidos
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            assert not {alias.name for alias in nodo.names} & prohibidos
