"""Pruebas de T-12 y T-13: el espectro llega a la gráfica de MOD-05.

El archivo aprobado se vuelve a mandar a `POST /api/procesar`, que lo pasa por
MOD-02, MOD-03 y MOD-04 y devuelve el espectro normalizado. La parte que
decide de MOD-05 se prueba en JavaScript (`frontend/pruebas/grafica.test.js`);
aquí se prueba la ruta y se pasa su respuesta real por esas mismas funciones
con Node, igual que hizo T-07 con la vista de MOD-01.

CA-04.1 pide el eje de 4000 a 400 con la intensidad vertical. CA-04.2 pide
que la gráfica quepa a 360 px; eso se mide en la captura de
`herramientas/capturar_grafica.py`, y aquí se revisa lo que lo hace posible.
CA-04.3 pide que un archivo que no pasa no deje una gráfica vacía.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import CAMPO_ARCHIVO, RUTA_PROCESAR, RUTA_VALIDAR, crear_aplicacion
from backend.utilerias import mensajes
from backend.utilerias.configuracion import obtener as obtener_configuracion

RAIZ = Path(__file__).resolve().parents[2]
FRONTEND = RAIZ / "frontend"
LIBRERIAS = FRONTEND / "vendor"
NODE = shutil.which("node")
SIN_NODE = "hace falta Node para pasar la respuesta por MOD-05"


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    with TestClient(crear_aplicacion()) as abierto:
        yield abierto


def _procesar(cliente: TestClient, ruta: Path, *, nombre: str | None = None):
    with ruta.open("rb") as flujo:
        return cliente.post(
            RUTA_PROCESAR,
            files={CAMPO_ARCHIVO: (nombre or ruta.name, flujo, "application/octet-stream")},
        )


def _correr_node(argumentos: list[str], entrada: str):
    return subprocess.run(
        [str(NODE), *argumentos],
        cwd=RAIZ,
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


# CA-04.1: el espectro que llega a la gráfica


@pytest.mark.parametrize(
    "archivo",
    ["espectro-valido.jdx", "espectro-con-encabezado.csv", "espectro-porcentaje.csv"],
)
def prueba_el_archivo_aprobado_llega_como_espectro_normalizado(
    cliente: TestClient, carpeta_fixtures: Path, archivo: str
) -> None:
    respuesta = _procesar(cliente, carpeta_fixtures / archivo)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valido"] is True
    assert cuerpo["nombre"] == archivo

    procesamiento = obtener_configuracion().procesamiento
    espectro = cuerpo["espectro"]
    assert len(espectro["eje_cm1"]) == procesamiento.puntos_rejilla
    assert len(espectro["intensidad"]) == procesamiento.puntos_rejilla
    assert espectro["eje_cm1"][0] == max(procesamiento.rango_rejilla_cm1)
    assert espectro["eje_cm1"][-1] == min(procesamiento.rango_rejilla_cm1)
    assert all(0.0 <= valor <= 1.0 for valor in espectro["intensidad"])


@pytest.mark.skipif(NODE is None, reason=SIN_NODE)
def prueba_ca_04_1_la_respuesta_real_se_dibuja_con_el_eje_invertido(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    respuesta = _procesar(cliente, carpeta_fixtures / "espectro-valido.jdx")

    completado = _correr_node(["frontend/pruebas/revisar-grafica.js", "lista"], respuesta.text)

    assert completado.returncode == 0, completado.stderr or completado.stdout
    assert "invertido=true" in completado.stdout


# CA-04.3: sin espectro, mensaje y no gráfica


@pytest.mark.parametrize(
    ("archivo", "codigo"),
    [
        ("espectro-linea-plana.csv", mensajes.SIN_SENAL),
        ("espectro-valido-900-puntos.csv", mensajes.UNIDAD_SIN_DECLARAR),
        ("imagen.png", mensajes.FORMATO_NO_SOPORTADO),
        ("espectro-truncado.jdx", mensajes.ESTRUCTURA_INVALIDA),
    ],
)
def prueba_un_archivo_que_no_llega_a_espectro_trae_su_mensaje(
    cliente: TestClient, carpeta_fixtures: Path, archivo: str, codigo: str
) -> None:
    respuesta = _procesar(cliente, carpeta_fixtures / archivo)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valido"] is False
    assert cuerpo["codigo"] == codigo
    assert "espectro" not in cuerpo
    assert cuerpo["titulo"] and cuerpo["mensaje"] and cuerpo["accion"]


@pytest.mark.skipif(NODE is None, reason=SIN_NODE)
@pytest.mark.parametrize("archivo", ["espectro-linea-plana.csv", "imagen.png"])
def prueba_ca_04_3_la_respuesta_real_deja_mensaje_y_no_grafica(
    cliente: TestClient, carpeta_fixtures: Path, archivo: str
) -> None:
    respuesta = _procesar(cliente, carpeta_fixtures / archivo)

    completado = _correr_node(
        ["frontend/pruebas/revisar-grafica.js", "sin-espectro"], respuesta.text
    )

    assert completado.returncode == 0, completado.stderr or completado.stdout


def prueba_el_contrato_de_validar_no_cambia(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """El incremento 2 no toca D-5: /api/validar sigue sin espectro."""
    with (carpeta_fixtures / "espectro-valido.jdx").open("rb") as flujo:
        respuesta = cliente.post(
            RUTA_VALIDAR, files={CAMPO_ARCHIVO: ("a.jdx", flujo, "text/plain")}
        )
    assert set(respuesta.json()) == {"valido", "nombre", "bytes"}


def prueba_rnf_09_la_respuesta_no_trae_el_archivo_original(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    ruta = carpeta_fixtures / "espectro-valido.jdx"
    texto = ruta.read_text(encoding="ascii")
    respuesta = _procesar(cliente, ruta)

    for linea in texto.splitlines()[:12]:
        if linea.strip():
            assert linea.strip() not in respuesta.text


def prueba_un_fallo_interno_da_el_mensaje_generico(
    carpeta_fixtures: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.api import aplicacion as capa_http

    def fallar(*args, **kwargs):
        raise RuntimeError("detalle que no debe salir")

    monkeypatch.setattr(capa_http, "procesar", fallar)
    with TestClient(crear_aplicacion()) as propio:
        respuesta = _procesar(propio, carpeta_fixtures / "espectro-valido.jdx")

    assert respuesta.status_code == 500
    assert respuesta.json()["codigo"] == mensajes.FALLO_INTERNO
    assert "detalle" not in respuesta.text


# La página carga la gráfica sin internet (D-1)


def prueba_la_pagina_carga_chart_js_y_anotaciones_del_repositorio() -> None:
    html = (FRONTEND / "interfaz" / "index.html").read_text(encoding="utf-8")

    libreria = html.index('src="../vendor/chart.umd.js"')
    anotaciones = html.index('src="../vendor/chartjs-plugin-annotation.min.js"')
    modulo = html.index('type="module" src="interfaz.js"')
    assert libreria < anotaciones < modulo, "las librerías van antes de la interfaz"


def prueba_las_librerias_son_las_de_la_tabla() -> None:
    """Nadie cambia una librería sin dejarlo escrito en vendor/LEEME.md."""
    tabla = (LIBRERIAS / "LEEME.md").read_text(encoding="utf-8")
    for archivo in ("chart.umd.js", "chartjs-plugin-annotation.min.js"):
        huella = hashlib.sha256((LIBRERIAS / archivo).read_bytes()).hexdigest()
        assert huella in tabla, f"la huella de {archivo} no coincide con vendor/LEEME.md"


@pytest.mark.parametrize(
    "ruta",
    [
        "/visor-espectro/configuracion.js",
        "/visor-espectro/visor.js",
        "/servicios/procesamiento.js",
        "/vendor/chart.umd.js",
        "/vendor/chartjs-plugin-annotation.min.js",
    ],
)
def prueba_el_servidor_entrega_los_archivos_de_la_grafica(
    cliente: TestClient, ruta: str
) -> None:
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200
    assert "javascript" in respuesta.headers["content-type"]


def prueba_las_pruebas_del_frontend_siguen_sin_publicarse(cliente: TestClient) -> None:
    assert cliente.get("/pruebas/grafica.test.js").status_code == 404


# CA-04.2: lo que deja caber la gráfica en 360 px


def prueba_la_grafica_no_trae_anchos_fijos() -> None:
    css = (FRONTEND / "interfaz" / "estilos.css").read_text(encoding="utf-8")
    bloque = re.search(r"\.grafica-contenedor\s*\{([^}]*)\}", css)
    assert bloque, "falta el estilo del contenedor de la gráfica"
    assert "width: 100%" in bloque.group(1)
    assert not re.search(r"\bwidth:\s*\d+px", bloque.group(1))
