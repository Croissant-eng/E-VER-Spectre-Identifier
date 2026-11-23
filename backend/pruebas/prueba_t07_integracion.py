"""Pruebas de T-07 · integración MOD-01 → `api` → MOD-02 → MOD-03.

**El método E2E, para la bitácora:** `TestClient` de FastAPI (sobre `httpx`, ya
en `requirements.txt`). Levanta la aplicación **real** dentro del proceso de
pytest y le manda un `multipart/form-data` de verdad, así que la petición pasa
por el mismo camino que en producción: FastAPI arma el `UploadFile` —con su
archivo temporal en disco cuando la subida pasa de 1 MB—, MOD-02 lo lee por
bloques y MOD-03 emite el veredicto. No hay navegador, ni servidor aparte, ni
red: es lo más ligero que de verdad ejercita el flujo.

El último eslabón, «y la pantalla lo muestra», se cierra pasando el cuerpo
**real** de la respuesta por la vista **real** de MOD-01 con Node
(`frontend/pruebas/revisar-aceptado.js` y `revisar-veredictos.js`). De punta a
punta queda: HTTP → MOD-02 → MOD-03 → UT-02 → servicio → vista. Lo único que
no se automatiza es el clic de la persona, y de eso hay captura en
`docs/evidencia/`.

Ningún texto de UT-02 ni valor de UT-03 se escribe aquí: se piden al catálogo y
a la configuración, igual que el código que se prueba.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import CAMPO_ARCHIVO, RUTA_VALIDAR, crear_aplicacion
from backend.api import veredicto as traductor
from backend.api import aplicacion as capa_http
from backend.utilerias import mensajes
from backend.utilerias.configuracion import ErrorDeConfiguracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion import Veredicto

RAIZ = Path(__file__).resolve().parents[2]
PRUEBAS_JS = RAIZ / "frontend" / "pruebas"

NODE = shutil.which("node")
SIN_NODE = "hace falta Node para pasar la respuesta real por la vista de MOD-01"

#: Palabras que delatarían un detalle técnico en una respuesta (RNF-01).
RASTROS_TECNICOS = (
    "Traceback",
    "RuntimeError",
    "Exception",
    "backend",
    ".py",
    "File \"",
    "line ",
)


# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    """La aplicación real, con la configuración real de UT-03."""
    with TestClient(crear_aplicacion()) as abierto:
        yield abierto


def _enviar(cliente: TestClient, ruta: Path, *, nombre: str | None = None):
    """Sube un archivo tal como lo haría el navegador (contrato D-5)."""
    with ruta.open("rb") as flujo:
        return cliente.post(
            RUTA_VALIDAR,
            files={CAMPO_ARCHIVO: (nombre or ruta.name, flujo, "application/octet-stream")},
        )


def _mensaje(codigo: str) -> mensajes.Mensaje:
    return mensajes.obtener(codigo)


def _correr_node(argumentos: list[str], entrada: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(NODE), *argumentos],
        cwd=RAIZ,
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def _revisar_que_no_filtra_nada_tecnico(cuerpo: dict) -> None:
    crudo = json.dumps(cuerpo, ensure_ascii=False)
    for rastro in RASTROS_TECNICOS:
        assert rastro not in crudo, (
            f"la respuesta filtra un detalle técnico («{rastro}»): {crudo}"
        )


# --------------------------------------------------------------------------- #
# CA-01.1 · el camino completo, de punta a punta
# --------------------------------------------------------------------------- #


def prueba_ca_01_1_el_jdx_valido_se_acepta_de_punta_a_punta(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """Sube el `.jdx` válido y el servidor responde el veredicto de aceptación."""
    ruta = carpeta_fixtures / "espectro-valido.jdx"

    respuesta = _enviar(cliente, ruta)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valido"] is True
    assert cuerpo["nombre"] == ruta.name
    assert cuerpo["bytes"] == ruta.stat().st_size


def prueba_la_respuesta_aceptada_trae_solo_las_llaves_del_contrato(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """Sección 5: `{valido, nombre, bytes}`, ni una llave de más."""
    respuesta = _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx")

    assert set(respuesta.json()) == {"valido", "nombre", "bytes"}


def prueba_rnf_09_la_respuesta_no_devuelve_el_contenido_del_espectro(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """El contenido se procesó en memoria y no sale por ninguna parte."""
    ruta = carpeta_fixtures / "espectro-valido.jdx"
    primera_linea = ruta.read_text(encoding="utf-8").splitlines()[0]

    respuesta = _enviar(cliente, ruta)

    assert "contenido" not in respuesta.json()
    assert primera_linea not in respuesta.text


@pytest.mark.skipif(NODE is None, reason=SIN_NODE)
def prueba_ca_01_1_la_vista_real_muestra_el_nombre_y_analizar_habilitado(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """El cierre de CA-01.1: la respuesta real, por la vista real de MOD-01.

    Es el eslabón que faltaba en T-06, donde los veredictos eran simulados: aquí
    el cuerpo lo escribió el servidor de verdad.
    """
    respuesta = _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx")
    assert respuesta.status_code == 200

    completado = _correr_node(
        ["frontend/pruebas/revisar-aceptado.js"], respuesta.text
    )

    assert completado.returncode == 0, completado.stderr or completado.stdout
    assert "analizar=habilitado" in completado.stdout


# --------------------------------------------------------------------------- #
# Aceptaciones · lo que ya validaban T-04 y T-05, ahora por HTTP
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("archivo", "criterio"),
    [
        ("espectro-valido-900-puntos.csv", "CA-02.1"),
        ("espectro-puntos-minimos.csv", "CA-02.6 · justo en 300 puntos"),
        ("espectro-con-encabezado.csv", "Requerimientos §6.1 · encabezado"),
        ("espectro-punto-y-coma.csv", "Requerimientos §6.1 · separador ;"),
    ],
)
def prueba_el_espectro_valido_se_acepta(
    cliente: TestClient, carpeta_fixtures: Path, archivo: str, criterio: str
) -> None:
    respuesta = _enviar(cliente, carpeta_fixtures / archivo)

    assert respuesta.status_code == 200, criterio
    assert respuesta.json()["valido"] is True, criterio


def prueba_ca_01_2_el_archivo_del_tamano_maximo_exacto_se_acepta(
    cliente: TestClient, csv_tamano_maximo: Path
) -> None:
    """El límite de UT-03 es inclusivo, también cruzando la capa HTTP."""
    respuesta = _enviar(cliente, csv_tamano_maximo)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valido"] is True
    assert cuerpo["bytes"] == obtener_configuracion().archivo.tamano_maximo_bytes


# --------------------------------------------------------------------------- #
# Rechazos · cada uno con su mensaje de UT-02
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("archivo", "codigo", "criterio"),
    [
        ("imagen.png", mensajes.FORMATO_NO_SOPORTADO, "CA-01.3"),
        ("binario-disfrazado.csv", mensajes.ARCHIVO_NO_ES_TEXTO, "CA-02.5"),
        ("archivo-vacio.csv", mensajes.ESTRUCTURA_INVALIDA, "CA-02.4 · 0 bytes"),
        ("espectro-truncado.jdx", mensajes.ESTRUCTURA_INVALIDA, "CA-02.4 · truncado"),
        ("espectro-un-punto-menos.csv", mensajes.PUNTOS_INSUFICIENTES, "CA-02.6"),
        ("espectro-rango-corto.csv", mensajes.RANGO_INSUFICIENTE, "CA-02.3"),
    ],
)
def prueba_el_rechazo_llega_con_el_mensaje_de_ut_02(
    cliente: TestClient,
    carpeta_fixtures: Path,
    archivo: str,
    codigo: str,
    criterio: str,
) -> None:
    """200 con veredicto de rechazo, con el texto exacto del catálogo."""
    esperado = _mensaje(codigo)

    respuesta = _enviar(cliente, carpeta_fixtures / archivo)

    assert respuesta.status_code == 200, criterio
    cuerpo = respuesta.json()
    assert cuerpo == {
        "valido": False,
        "codigo": esperado.codigo,
        "titulo": esperado.titulo,
        "mensaje": esperado.texto,
        "accion": esperado.accion,
    }, criterio


def prueba_ca_02_2_el_archivo_que_pasa_del_limite_se_rechaza_con_su_texto(
    cliente: TestClient, csv_un_byte_de_mas: Path
) -> None:
    """Un byte de más → el texto literal que exige CA-02.2, armado desde UT-03."""
    esperado = _mensaje(mensajes.TAMANO_EXCEDIDO)

    respuesta = _enviar(cliente, csv_un_byte_de_mas)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == mensajes.TAMANO_EXCEDIDO
    assert cuerpo["mensaje"] == esperado.texto


def prueba_el_limite_lo_aplica_mod_02_y_no_la_infraestructura(
    cliente: TestClient, csv_un_byte_de_mas: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """La condición de la sección 5: el que corta es el código del equipo.

    Si lo cortara FastAPI o el servidor, la respuesta sería un error de
    transporte (413) o una conexión rota, y en el registro **no** habría una
    línea de MOD-02. Las dos cosas se comprueban aquí.
    """
    with caplog.at_level("WARNING", logger="e-ver.mod-02"):
        respuesta = _enviar(cliente, csv_un_byte_de_mas)

    assert respuesta.status_code == 200, (
        "un rechazo por tamaño es resultado de negocio, no error de transporte"
    )
    assert any(
        "MOD-02 recepcion" in registro.getMessage()
        and mensajes.TAMANO_EXCEDIDO in registro.getMessage()
        for registro in caplog.records
    ), "el rechazo por tamaño no salió de MOD-02"


@pytest.mark.skipif(NODE is None, reason=SIN_NODE)
def prueba_los_rechazos_reales_se_pintan_completos_en_la_vista(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """Cada rechazo que emite el servidor se muestra con motivo y acción (RNF-01).

    Lo mismo que probó T-06 con veredictos simulados, ahora con los cuerpos que
    escribe el servidor de verdad: título, mensaje y acción visibles, el código
    fuera de la pantalla y «Analizar» sin ofrecerse.
    """
    casos = []
    for archivo in (
        "imagen.png",
        "binario-disfrazado.csv",
        "archivo-vacio.csv",
        "espectro-truncado.jdx",
        "espectro-un-punto-menos.csv",
        "espectro-rango-corto.csv",
    ):
        cuerpo = _enviar(cliente, carpeta_fixtures / archivo).json()
        casos.append({"codigo": cuerpo["codigo"], "veredicto": cuerpo})

    completado = _correr_node(
        ["frontend/pruebas/revisar-veredictos.js"],
        json.dumps(casos, ensure_ascii=False),
    )

    assert completado.returncode == 0, completado.stderr or completado.stdout
    assert str(len(casos)) in completado.stdout


def prueba_ningun_rechazo_filtra_detalles_tecnicos(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """RNF-01: ni rutas, ni nombres de módulos, ni excepciones."""
    for archivo in sorted(carpeta_fixtures.glob("*")):
        if archivo.suffix not in {".csv", ".jdx", ".png"}:
            continue
        cuerpo = _enviar(cliente, archivo).json()
        if cuerpo["valido"]:
            continue
        _revisar_que_no_filtra_nada_tecnico(cuerpo)
        assert set(cuerpo) == {"valido", "codigo", "titulo", "mensaje", "accion"}
        assert cuerpo["titulo"] and cuerpo["mensaje"] and cuerpo["accion"]


# --------------------------------------------------------------------------- #
# CA-02.4 · robustez: el servidor sigue atendiendo
# --------------------------------------------------------------------------- #


def prueba_ca_02_4_despues_de_los_archivos_rotos_atiende_la_siguiente_peticion(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """«No se detiene de forma abrupta y atiende la siguiente petición»."""
    for archivo in (
        "archivo-vacio.csv",
        "espectro-truncado.jdx",
        "binario-disfrazado.csv",
        "imagen.png",
    ):
        assert _enviar(cliente, carpeta_fixtures / archivo).status_code == 200

    respuesta = _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx")

    assert respuesta.status_code == 200
    assert respuesta.json()["valido"] is True


def prueba_un_nombre_hostil_no_rompe_nada(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    """El nombre lo escribe el cliente: MOD-02 lo limpia y aquí se ve limpio."""
    respuesta = _enviar(
        cliente,
        carpeta_fixtures / "espectro-valido.jdx",
        nombre="..\\..\\windows\\system32\\espectro-valido.jdx",
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valido"] is True
    assert cuerpo["nombre"] == "espectro-valido.jdx"


def prueba_la_peticion_sin_el_campo_archivo_no_filtra_el_error_de_fastapi(
    cliente: TestClient,
) -> None:
    """Una petición mal armada tampoco muestra detalles técnicos (regla 2).

    FastAPI respondería un 422 con la ruta del campo y el tipo esperado; aquí se
    cambia por el mensaje genérico de UT-02. El 400 es la única parte que el
    contrato de la sección 5 no nombra: no hay veredicto que emitir (no llegó
    archivo) y tampoco falló nada por dentro. Queda anotado para el equipo.
    """
    esperado = _mensaje(mensajes.FALLO_INTERNO)

    respuesta = cliente.post(RUTA_VALIDAR, files={"otro_campo": ("x.csv", b"1,2")})

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["mensaje"] == esperado.texto
    assert "loc" not in respuesta.text and "body" not in respuesta.text
    _revisar_que_no_filtra_nada_tecnico(cuerpo)


def prueba_el_endpoint_solo_atiende_post(cliente: TestClient) -> None:
    assert cliente.get(RUTA_VALIDAR).status_code == 405


# --------------------------------------------------------------------------- #
# RNF-09 en integración · no queda ningún archivo del usuario
# --------------------------------------------------------------------------- #


def prueba_rnf_09_no_queda_temporal_despues_de_una_peticion_grande(
    cliente: TestClient,
    csv_tres_megas: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pasa de 1 MB, así que FastAPI crea un temporal en disco: tiene que irse."""
    carpeta = tmp_path / "temporales"
    carpeta.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(carpeta))

    antes = sorted(carpeta.iterdir())
    respuesta = _enviar(cliente, csv_tres_megas)
    despues = sorted(carpeta.iterdir())

    assert respuesta.status_code == 200
    assert respuesta.json()["valido"] is True
    assert despues == antes == [], (
        f"quedó algo del usuario en el directorio temporal: {despues}"
    )


def prueba_rnf_09_tampoco_queda_temporal_cuando_se_rechaza(
    cliente: TestClient,
    csv_un_byte_de_mas: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El rechazo por tamaño corta la lectura, y el temporal igual desaparece."""
    carpeta = tmp_path / "temporales"
    carpeta.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(carpeta))

    respuesta = _enviar(cliente, csv_un_byte_de_mas)

    assert respuesta.json()["codigo"] == mensajes.TAMANO_EXCEDIDO
    assert sorted(carpeta.iterdir()) == []


# --------------------------------------------------------------------------- #
# El 500 · fallo interno, mensaje genérico
# --------------------------------------------------------------------------- #


_SECRETO = "detalle tecnico que nadie debe ver"


@pytest.mark.parametrize("pieza", ["recibir", "validar"])
def prueba_un_fallo_interno_responde_500_con_el_mensaje_generico(
    cliente: TestClient,
    carpeta_fixtures: Path,
    monkeypatch: pytest.MonkeyPatch,
    pieza: str,
) -> None:
    """Falle MOD-02 o falle MOD-03, el usuario ve el mismo mensaje de UT-02."""
    esperado = _mensaje(mensajes.FALLO_INTERNO)

    def reventar(*argumentos, **nombrados):
        raise RuntimeError(_SECRETO)

    async def reventar_async(*argumentos, **nombrados):
        raise RuntimeError(_SECRETO)

    monkeypatch.setattr(
        capa_http,
        pieza,
        reventar_async if pieza == "recibir" else reventar,
    )

    respuesta = _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx")

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo == {
        "valido": False,
        "codigo": esperado.codigo,
        "titulo": esperado.titulo,
        "mensaje": esperado.texto,
        "accion": esperado.accion,
    }
    assert _SECRETO not in respuesta.text
    _revisar_que_no_filtra_nada_tecnico(cuerpo)


def prueba_un_codigo_que_no_esta_en_ut_02_es_fallo_interno(
    cliente: TestClient, carpeta_fixtures: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si un módulo inventara un código, es error del programa, no del usuario.

    No se le muestra el código inventado: sale el mensaje genérico y el 500.
    """

    def inventar(*argumentos, **nombrados) -> Veredicto:
        return Veredicto(
            valido=False,
            nombre="espectro-valido.jdx",
            extension=".jdx",
            codigo="CODIGO_INVENTADO",
            capa="ninguna",
        )

    monkeypatch.setattr(capa_http, "validar", inventar)

    respuesta = _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx")

    assert respuesta.status_code == 500
    assert "CODIGO_INVENTADO" not in respuesta.text
    assert respuesta.json()["codigo"] == mensajes.FALLO_INTERNO


def prueba_un_fallo_interno_no_tumba_el_servidor(
    cliente: TestClient, carpeta_fixtures: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Después del 500, la siguiente petición se atiende normal."""

    def reventar(*argumentos, **nombrados):
        raise RuntimeError(_SECRETO)

    monkeypatch.setattr(capa_http, "validar", reventar)
    assert _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx").status_code == 500

    monkeypatch.undo()

    respuesta = _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx")
    assert respuesta.status_code == 200
    assert respuesta.json()["valido"] is True


@pytest.mark.skipif(NODE is None, reason=SIN_NODE)
def prueba_el_mensaje_del_500_tambien_se_pinta_completo(
    cliente: TestClient, carpeta_fixtures: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El cuerpo del 500 llega completo a la pantalla, con motivo y acción."""

    def reventar(*argumentos, **nombrados):
        raise RuntimeError(_SECRETO)

    monkeypatch.setattr(capa_http, "validar", reventar)

    cuerpo = _enviar(cliente, carpeta_fixtures / "espectro-valido.jdx").json()

    completado = _correr_node(
        ["frontend/pruebas/revisar-veredictos.js"],
        json.dumps([{"codigo": cuerpo["codigo"], "veredicto": cuerpo}]),
    )

    assert completado.returncode == 0, completado.stderr or completado.stdout


# --------------------------------------------------------------------------- #
# La traducción vive en un solo lugar
# --------------------------------------------------------------------------- #


def prueba_solo_la_capa_http_arma_los_mensajes_de_ut_02() -> None:
    """Un solo lugar traduce códigos a texto; si aparece otro, esto falla.

    MOD-02 y MOD-03 devuelven **códigos**: ninguno arma el mensaje. Es lo que
    evita que el mismo rechazo se redacte distinto en dos pantallas.
    """
    culpables = []
    for archivo in sorted((RAIZ / "backend").rglob("*.py")):
        relativo = archivo.relative_to(RAIZ).as_posix()
        if relativo.startswith(("backend/pruebas/", "backend/utilerias/mensajes/")):
            continue
        if "mensajes.obtener" in archivo.read_text(encoding="utf-8"):
            culpables.append(relativo)

    assert culpables == ["backend/api/veredicto.py"], (
        f"el mensaje de UT-02 se arma en más de un lugar: {culpables}"
    )


def prueba_todos_los_codigos_de_ut_02_se_pueden_traducir() -> None:
    """Ningún código del catálogo deja a la capa HTTP sin respuesta."""
    for codigo in mensajes.codigos():
        cuerpo = traductor.rechazado(codigo)
        assert cuerpo["valido"] is False
        assert cuerpo["codigo"] == codigo
        assert cuerpo["titulo"] and cuerpo["mensaje"] and cuerpo["accion"]
        assert set(cuerpo) == {"valido", "codigo", "titulo", "mensaje", "accion"}


def _cadenas_de(archivo: Path) -> list[str]:
    """Las cadenas que el código **escribe**, sin documentación ni comentarios.

    Se leen del árbol sintáctico y no con una expresión regular: buscar comillas
    a mano confunde «el final de una cadena y el principio de la siguiente» con
    una cadena larguísima, y la prueba acusa en falso. Esto ve lo que ve Python.
    """
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))

    documentacion: set[int] = set()
    con_documentacion = (
        ast.Module,
        ast.ClassDef,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
    )
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, con_documentacion):
            continue
        primero = nodo.body[0] if nodo.body else None
        if (
            isinstance(primero, ast.Expr)
            and isinstance(primero.value, ast.Constant)
            and isinstance(primero.value.value, str)
        ):
            documentacion.add(id(primero.value))

    return [
        nodo.value
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant)
        and isinstance(nodo.value, str)
        and id(nodo) not in documentacion
    ]


def prueba_la_capa_http_no_escribe_ningun_texto_para_el_usuario() -> None:
    """Regla 2: los textos son de UT-02. La capa HTTP solo los reenvía.

    Lo que el usuario puede llegar a leer es el cuerpo JSON, y el cuerpo se arma
    en un solo archivo: `veredicto.py`. Si ahí apareciera una cadena larga,
    sería una redacción escrita a mano; las llaves del contrato son cortas.
    """
    largas = [
        cadena
        for cadena in _cadenas_de(RAIZ / "backend" / "api" / "veredicto.py")
        if len(cadena) >= 30
    ]

    assert not largas, f"veredicto.py redacta texto propio: {largas}"


def prueba_solo_veredicto_py_arma_el_cuerpo_de_la_respuesta() -> None:
    """Las llaves del veredicto no se escriben en ningún otro archivo de `api/`."""
    for archivo in sorted((RAIZ / "backend" / "api").glob("*.py")):
        if archivo.name == "veredicto.py":
            continue
        cadenas = _cadenas_de(archivo)
        for clave in ("titulo", "mensaje", "accion"):
            assert clave not in cadenas, (
                f"{archivo.name} arma el cuerpo por su cuenta: la llave "
                f"«{clave}» solo va en veredicto.py"
            )


# --------------------------------------------------------------------------- #
# Arranque · UT-03 manda, y si falta algo no arranca en silencio
# --------------------------------------------------------------------------- #


def prueba_el_arranque_falla_ruidoso_si_ut_03_esta_incompleta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-01: configuración incompleta → no arranca, y se sabe por qué."""

    def reventar() -> None:
        raise ErrorDeConfiguracion("UT-03: falta la llave obligatoria «archivo.x»")

    monkeypatch.setattr(capa_http, "obtener_configuracion", reventar)

    with pytest.raises(ErrorDeConfiguracion) as falla:
        crear_aplicacion()

    assert "UT-03" in str(falla.value)


def prueba_el_arranque_deja_en_el_registro_el_codigo_de_ut_02(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """El equipo ve `CONFIGURACION_INCOMPLETA` en el registro, no un rastro suelto."""

    def reventar() -> None:
        raise ErrorDeConfiguracion("UT-03: falta una llave")

    monkeypatch.setattr(capa_http, "obtener_configuracion", reventar)

    with caplog.at_level("CRITICAL", logger="e-ver.api"):
        with pytest.raises(ErrorDeConfiguracion):
            crear_aplicacion()

    assert any(
        mensajes.CONFIGURACION_INCOMPLETA in registro.getMessage()
        for registro in caplog.records
    )


def prueba_cambiar_ut_03_cambia_el_veredicto_sin_tocar_codigo(
    carpeta_fixtures: Path,
) -> None:
    """La prueba de que UT-03 manda de verdad en toda la cadena.

    Se levanta la aplicación con una configuración que pide muchos más puntos: el
    mismo CSV de 900 puntos, que antes se aceptaba, ahora se rechaza y el mensaje
    dice el número nuevo. Ninguna línea de código cambió.
    """
    real = obtener_configuracion()
    exigente = dataclasses.replace(
        real,
        validacion=dataclasses.replace(real.validacion, puntos_minimos=5000),
    )

    with TestClient(crear_aplicacion(exigente)) as otro:
        respuesta = _enviar(otro, carpeta_fixtures / "espectro-valido-900-puntos.csv")

    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == mensajes.PUNTOS_INSUFICIENTES
    assert cuerpo["mensaje"] == mensajes.obtener(
        mensajes.PUNTOS_INSUFICIENTES, exigente
    ).texto
    assert "5000" in cuerpo["mensaje"]


def prueba_el_tamano_maximo_tambien_viaja_hasta_mod_02(
    carpeta_fixtures: Path,
) -> None:
    """La otra mitad: la configuración llega a MOD-02, no solo a MOD-03.

    Con un límite ridículo, el mismo `.jdx` que siempre se acepta se rechaza por
    tamaño. Si la capa HTTP se olvidara de pasarle los parámetros a MOD-02, MOD-02
    usaría los de UT-03 y esta prueba fallaría.
    """
    real = obtener_configuracion()
    estrecha = dataclasses.replace(
        real,
        archivo=dataclasses.replace(real.archivo, tamano_maximo_bytes=100),
    )

    with TestClient(crear_aplicacion(estrecha)) as otro:
        respuesta = _enviar(otro, carpeta_fixtures / "espectro-valido.jdx")

    assert respuesta.status_code == 200
    assert respuesta.json()["codigo"] == mensajes.TAMANO_EXCEDIDO


# --------------------------------------------------------------------------- #
# Mismo origen · el frontend se sirve desde aquí
# --------------------------------------------------------------------------- #


def prueba_la_raiz_lleva_a_la_interfaz(cliente: TestClient) -> None:
    respuesta = cliente.get("/", follow_redirects=False)

    assert respuesta.status_code in {301, 302, 303, 307, 308}
    assert respuesta.headers["location"] == "/interfaz/"


def prueba_la_pagina_se_sirve_y_es_la_del_repositorio(cliente: TestClient) -> None:
    respuesta = cliente.get("/interfaz/")

    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "Validar un espectro" in respuesta.text


@pytest.mark.parametrize(
    ("ruta", "tipo", "pista"),
    [
        ("/interfaz/estilos.css", "css", "[hidden]"),
        ("/interfaz/interfaz.js", "javascript", "conectar"),
        ("/interfaz/vista.js", "javascript", "vistaDeVeredicto"),
        ("/servicios/validacion.js", "javascript", "validarEspectro"),
    ],
)
def prueba_las_piezas_del_frontend_se_sirven(
    cliente: TestClient, ruta: str, tipo: str, pista: str
) -> None:
    """Mismo origen: el `fetch` del navegador no cruza dominios."""
    respuesta = cliente.get(ruta)

    assert respuesta.status_code == 200
    assert tipo in respuesta.headers["content-type"]
    assert pista in respuesta.text


def prueba_las_pruebas_de_javascript_no_se_sirven(cliente: TestClient) -> None:
    """`frontend/pruebas/` (D-9) es del equipo, no de la web."""
    assert cliente.get("/pruebas/vista.test.js").status_code == 404
    assert cliente.get("/pruebas/revisar-aceptado.js").status_code == 404


def prueba_se_puede_servir_una_copia_del_frontend(tmp_path: Path) -> None:
    """Para qué existe `carpeta_frontend`: la evidencia sirve una copia.

    La herramienta de captura le agrega a esa copia un archivo que elige el
    espectro y envía el formulario solo, porque el navegador en modo headless no
    tiene a nadie que haga clic. Así el frontend del repositorio no lleva ni un
    gancho de prueba.
    """
    (tmp_path / "interfaz").mkdir()
    (tmp_path / "servicios").mkdir()
    (tmp_path / "interfaz" / "index.html").write_text(
        "<p>copia</p>", encoding="utf-8"
    )

    with TestClient(crear_aplicacion(carpeta_frontend=tmp_path)) as otro:
        assert "copia" in otro.get("/interfaz/").text


def prueba_la_evidencia_de_ca_01_1_esta_guardada() -> None:
    """T-07 pide evidencia del flujo completo: escritorio y 360 px."""
    evidencia = RAIZ / "docs" / "evidencia"
    faltantes = [
        nombre
        for nombre in (
            "t-07-escritorio-ca-01-1.png",
            "t-07-movil-360-ca-01-1.png",
        )
        if not (evidencia / nombre).is_file()
    ]

    assert not faltantes, f"faltan capturas de CA-01.1: {faltantes}"


def prueba_la_ruta_que_llama_el_frontend_es_la_del_endpoint() -> None:
    """La ruta está escrita en dos lenguajes: que no se separen.

    `servicios/validacion.js` no puede importar una constante de Python, así que
    esta prueba es el pegamento: si alguien cambia una, falla.
    """
    javascript = (RAIZ / "frontend" / "servicios" / "validacion.js").read_text(
        encoding="utf-8"
    )

    assert f'RUTA_VALIDAR = "{RUTA_VALIDAR}"' in javascript
    assert f'CAMPO_ARCHIVO = "{CAMPO_ARCHIVO}"' in javascript
