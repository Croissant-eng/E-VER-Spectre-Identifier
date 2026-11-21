"""Pruebas de T-06 · MOD-01 Interfaz mínima.

La lógica «veredicto → vista» se prueba en JavaScript, con el corredor que ya
trae Node (`frontend/pruebas/*.test.js`): es la prueba más ligera posible para
JS puro —sin instalar nada, sin `node_modules` y sin build— y corre la misma
función que corre el navegador, no una copia.

Este archivo hace tres cosas desde `pytest`, para que el equipo siga teniendo
**un solo comando**:

1. Corre las pruebas de JavaScript (y se salta con un mensaje claro si quien
   corre la suite no tiene Node instalado).
2. Pasa los **ocho mensajes reales de UT-02** por la vista de verdad, para que
   ningún texto se copie a mano en el JavaScript: si mañana cambia una
   redacción en UT-02, esto sigue probando la pantalla con el texto nuevo.
3. Revisa a mano lo que no es lógica: que la página no dependa de internet, que
   el botón «Analizar» no tenga acción (D-4), que el código del rechazo no
   aparezca en el HTML y que no haya anchos fijos que rompan a 360 px.

Nada de esto toca la red: el `fetch` de las pruebas de JavaScript es simulado y
aquí no se levanta ningún servidor (el endpoint es T-07).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from backend.utilerias import mensajes

RAIZ = Path(__file__).resolve().parents[2]
FRONTEND = RAIZ / "frontend"
INTERFAZ = FRONTEND / "interfaz"
SERVICIOS = FRONTEND / "servicios"
PRUEBAS_JS = FRONTEND / "pruebas"

PAGINA = INTERFAZ / "index.html"
ESTILOS = INTERFAZ / "estilos.css"

#: Node trae su propio corredor de pruebas desde la versión 18; no se instala
#: nada. Si no está, estas pruebas se saltan en vez de fallar: el backend no
#: necesita Node para funcionar.
NODE = shutil.which("node")

SIN_NODE = "hace falta Node para correr las pruebas de JavaScript de MOD-01"

#: Ancho de la pantalla más angosta que el diseño debe sostener (RNF-05).
ANCHO_MINIMO_PX = 360


def _correr_node(argumentos: list[str], entrada: str | None = None):
    return subprocess.run(
        [str(NODE), *argumentos],
        cwd=RAIZ,
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


# --------------------------------------------------------------------------- #
# Los archivos de MOD-01 existen
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "ruta",
    [
        "frontend/interfaz/index.html",
        "frontend/interfaz/estilos.css",
        "frontend/interfaz/vista.js",
        "frontend/interfaz/pintar.js",
        "frontend/interfaz/interfaz.js",
        "frontend/servicios/validacion.js",
        "frontend/pruebas/vista.test.js",
        "frontend/pruebas/servicios.test.js",
    ],
)
def prueba_el_archivo_de_mod_01_existe(ruta: str) -> None:
    assert (RAIZ / ruta).is_file(), f"falta {ruta}"


# --------------------------------------------------------------------------- #
# Las pruebas de JavaScript
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(NODE is None, reason=SIN_NODE)
def prueba_las_pruebas_de_javascript_pasan() -> None:
    """La lógica «veredicto → vista» y el servicio, probados en su propio
    lenguaje con veredictos simulados."""
    archivos = sorted(str(p.relative_to(RAIZ)) for p in PRUEBAS_JS.glob("*.test.js"))
    assert archivos, "no hay pruebas de JavaScript que correr"

    completado = _correr_node(["--test", *archivos])

    assert completado.returncode == 0, (
        "fallaron las pruebas de JavaScript de MOD-01:\n"
        f"{completado.stdout}\n{completado.stderr}"
    )


@pytest.mark.skipif(NODE is None, reason=SIN_NODE)
def prueba_los_mensajes_reales_de_ut02_se_pintan_completos() -> None:
    """Los ocho códigos del catálogo, con su texto de verdad, por la vista real.

    Es el puente entre UT-02 (Python) y MOD-01 (JavaScript): así los textos no
    se copian en dos lugares. La vista tiene que mostrar título, mensaje y
    acción, y **no** el código.
    """
    codigos = mensajes.codigos()
    assert len(codigos) >= 8, "el catálogo de UT-02 se quedó corto"

    casos = []
    for codigo in codigos:
        mensaje = mensajes.obtener(codigo)
        casos.append(
            {
                "codigo": codigo,
                "veredicto": {
                    "valido": False,
                    "codigo": mensaje.codigo,
                    "titulo": mensaje.titulo,
                    "mensaje": mensaje.texto,
                    "accion": mensaje.accion,
                },
            }
        )

    completado = _correr_node(
        ["frontend/pruebas/revisar-veredictos.js"],
        entrada=json.dumps(casos, ensure_ascii=False),
    )

    assert completado.returncode == 0, completado.stderr or completado.stdout
    assert str(len(casos)) in completado.stdout


# --------------------------------------------------------------------------- #
# La página no depende de internet ni de un framework
# --------------------------------------------------------------------------- #


def prueba_la_pagina_no_descarga_nada_de_internet() -> None:
    """HTML/CSS/JS puro: sin CDN, sin framework y sin fuentes externas.

    Además de la decisión de stack, es privacidad: nadie de fuera se entera de
    que alguien abrió la página.
    """
    sospechosos: list[str] = []
    for archivo in sorted(FRONTEND.rglob("*")):
        if not archivo.is_file() or archivo.suffix not in {".html", ".css", ".js"}:
            continue
        texto = archivo.read_text(encoding="utf-8")
        for patron in ("http://", "https://", "//cdn.", "cdnjs", "unpkg", "jsdelivr"):
            if patron in texto:
                sospechosos.append(f"{archivo.relative_to(RAIZ).as_posix()}: {patron}")

    assert not sospechosos, (
        f"la interfaz no debe depender de internet: {sospechosos}"
    )


def prueba_la_pagina_declara_lo_minimo_para_moverse_en_movil() -> None:
    html = PAGINA.read_text(encoding="utf-8")

    assert 'lang="es"' in html, "la página está en español y debe decirlo"
    assert 'name="viewport"' in html, "sin viewport, el móvil finge ser escritorio"
    assert "width=device-width" in html
    assert 'rel="stylesheet" href="estilos.css"' in html
    assert 'type="module" src="interfaz.js"' in html


def prueba_la_pagina_no_trae_los_parametros_de_ut03() -> None:
    """Regla 1: los valores viven en UT-03, no escritos en la interfaz.

    Por eso tampoco hay `accept` en el selector: además de duplicar la lista de
    formatos, impediría elegir un `.png` y ver el mensaje de formato, que es lo
    que CA-01.3 necesita probar.
    """
    html = PAGINA.read_text(encoding="utf-8")
    cuerpo = html.split("<body")[1]

    for valor in ("5 MB", "5242880", "5,242,880", "300 puntos", "1400", "3700"):
        assert valor not in cuerpo, f"«{valor}» es de UT-03, no de la interfaz"
    assert "accept=" not in cuerpo


# --------------------------------------------------------------------------- #
# D-4 · «Analizar» presente, habilitado al aceptar y sin acción
# --------------------------------------------------------------------------- #


def prueba_el_boton_analizar_existe_y_nace_sin_poder_usarse() -> None:
    html = PAGINA.read_text(encoding="utf-8")

    assert 'id="analizar"' in html, "D-4 pide que el botón esté presente"
    assert 'id="bloque-analizar"' in html
    assert re.search(r'id="bloque-analizar"[^>]*hidden', html), (
        "antes de aprobar un documento, el botón no se muestra"
    )


def prueba_el_boton_analizar_no_tiene_accion() -> None:
    """D-4: presente y habilitado, **sin acción**. RF-04 es del incremento 3.

    La forma de garantizarlo es que nadie le ponga un escuchador de clic ni un
    `onclick`: si alguien se lo agrega, esta prueba falla.
    """
    html = PAGINA.read_text(encoding="utf-8")
    assert "onclick" not in html

    for archivo in sorted(INTERFAZ.glob("*.js")):
        texto = archivo.read_text(encoding="utf-8")
        for linea in texto.splitlines():
            if "addEventListener" in linea and "analizar" in linea.lower():
                pytest.fail(
                    f"{archivo.name}: «Analizar» no debe tener acción todavía "
                    f"(D-4): {linea.strip()}"
                )


def prueba_el_codigo_del_rechazo_no_aparece_en_la_pantalla() -> None:
    """El código es interno: va al registro, no a la vista."""
    html = PAGINA.read_text(encoding="utf-8")
    pintar = (INTERFAZ / "pintar.js").read_text(encoding="utf-8")

    for codigo in mensajes.codigos():
        assert codigo not in html, f"{codigo} no debe estar en el HTML"
    assert "codigo" not in pintar, (
        "pintar.js no debe tocar el código del veredicto: no se muestra"
    )


# --------------------------------------------------------------------------- #
# RNF-05 (adelanto) · nada que rompa a 360 px
# --------------------------------------------------------------------------- #


def prueba_no_hay_anchos_fijos_que_rompan_en_una_pantalla_angosta() -> None:
    """La causa más común de desplazamiento horizontal es un ancho en píxeles.

    La prueba formal de RNF-05 es del incremento 2; esto es el cerrojo barato
    que evita el error típico. Las capturas de `docs/evidencia/` son la
    evidencia visual.
    """
    css = ESTILOS.read_text(encoding="utf-8")
    anchos = re.findall(
        r"(?:min-)?width\s*:\s*(\d+(?:\.\d+)?)px", css, flags=re.IGNORECASE
    )
    grandes = [ancho for ancho in anchos if float(ancho) > ANCHO_MINIMO_PX]

    assert not grandes, (
        f"estos anchos fijos pasan de {ANCHO_MINIMO_PX} px y provocarían "
        f"desplazamiento horizontal: {grandes}"
    )


def prueba_esconder_con_hidden_funciona_de_verdad() -> None:
    """Sin esta regla, `hidden` no esconde lo que tiene `display` en una clase.

    Lo encontró una captura de evidencia: tras un rechazo seguía viéndose el
    botón «Analizar», porque el `display: flex` de su bloque le gana a la regla
    con que el navegador esconde los elementos marcados con `hidden`. Como
    `pintar.js` esconde así, esta regla es la que hace que funcione.
    """
    css = ESTILOS.read_text(encoding="utf-8")

    assert re.search(r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important", css), (
        "falta la regla [hidden] { display: none !important } en estilos.css"
    )


def prueba_el_css_toma_las_precauciones_de_una_pantalla_angosta() -> None:
    css = ESTILOS.read_text(encoding="utf-8")

    assert "box-sizing: border-box" in css, (
        "sin border-box, el relleno suma al ancho y la caja se desborda"
    )
    assert "overflow-wrap: anywhere" in css or "word-break" in css, (
        "un nombre de archivo largo sin espacios tiene que poder cortarse"
    )
    assert "max-width" in css, "el contenido necesita un techo y centrarse"


def prueba_las_capturas_de_evidencia_estan_guardadas() -> None:
    """T-06 pide evidencia visual: escritorio y 360 px."""
    evidencia = RAIZ / "docs" / "evidencia"
    faltantes = [
        nombre
        for nombre in (
            "t-06-escritorio-inicial.png",
            "t-06-escritorio-aceptado.png",
            "t-06-escritorio-rechazado.png",
            "t-06-movil-360-aceptado.png",
            "t-06-movil-360-rechazado.png",
        )
        if not (evidencia / nombre).is_file()
    ]

    assert not faltantes, f"faltan capturas de T-06: {faltantes}"
