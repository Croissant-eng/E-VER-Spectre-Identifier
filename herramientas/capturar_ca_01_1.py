"""Evidencia de CA-01.1 · el flujo completo, contra el servidor de verdad.

A diferencia de `capturar_interfaz.py` (T-06, veredictos simulados), aquí **no
hay nada simulado**: se levanta la aplicación real con `uvicorn`, el navegador
abre la página que sirve esa aplicación, sube el `.jdx` fabricado de
`datos/pruebas/` por `POST /api/validar` y la captura muestra lo que respondió
el servidor después de pasar por MOD-02 y MOD-03.

Cómo se corre, desde la raíz del repositorio:

    python -m herramientas.capturar_ca_01_1

Dos cosas que conviene saber:

- **El repositorio no lleva ganchos de prueba.** La herramienta copia
  `frontend/interfaz/` y `frontend/servicios/` a una carpeta temporal y a la
  copia le agrega un archivo que elige el espectro y envía el formulario solo
  (el navegador en modo headless no tiene a nadie que haga clic). La aplicación
  sirve esa copia; los archivos del repositorio quedan intactos.
- **No se guarda una captura que no demuestre nada.** Antes de fotografiar, la
  herramienta lee el DOM y exige encontrar el nombre del archivo y el botón
  «Analizar» habilitado. Si el veredicto no llegó, falla en vez de dejar una
  imagen bonita y vacía.

La captura de 360 px va dentro de un marco, por lo mismo que explica
`docs/evidencia/LEEME.md`: el modo headless no acepta ventanas tan angostas y
sin el marco recortaría la imagen.
"""

from __future__ import annotations

import argparse
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FRONTEND = RAIZ / "frontend"
EVIDENCIA = RAIZ / "docs" / "evidencia"

#: El espectro de CA-01.1: el `.jdx` fabricado y versionado.
ESPECTRO = RAIZ / "datos" / "pruebas" / "espectro-valido.jdx"

#: Dónde buscar un navegador, en orden de preferencia.
NAVEGADORES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)

ESCRITORIO = (1280, 900)
ANCHO_MOVIL = 360
ALTO_MOVIL = 820
VENTANA_MOVIL = (520, ALTO_MOVIL + 90)

#: Tiempo virtual que se le da al navegador. El modo headless detiene este
#: reloj mientras haya peticiones pendientes, así que alcanza para que la subida
#: vaya y vuelva aunque la máquina esté ocupada.
TIEMPO_VIRTUAL_MS = 15000

NOMBRE_ESCRITORIO = "t-07-escritorio-ca-01-1.png"
NOMBRE_MOVIL = "t-07-movil-360-ca-01-1.png"

PLANTILLA_SUBIDA = """/**
 * Sube el espectro solo, para la captura de evidencia de CA-01.1.
 *
 * Lo genera `herramientas/capturar_ca_01_1.py` en una copia temporal de la
 * interfaz; **no vive en el repositorio** ni lo carga la página de verdad. Lo
 * único que hace es lo que haría una persona: elegir el archivo y enviar el
 * formulario. De ahí en adelante todo es el código real —`interfaz.js`,
 * `servicios/validacion.js`, `POST /api/validar`— y el veredicto lo escribe el
 * servidor.
 */

const NOMBRE = {nombre};

const entrada = document.getElementById("archivo");
const formulario = document.getElementById("formulario");

const datos = await fetch(NOMBRE).then((respuesta) => respuesta.arrayBuffer());
const archivo = new File([datos], NOMBRE, {{ type: "application/octet-stream" }});

// Es la única forma de poner un archivo en el selector sin un clic humano.
const transferencia = new DataTransfer();
transferencia.items.add(archivo);
entrada.files = transferencia.files;
entrada.dispatchEvent(new Event("change"));

formulario.requestSubmit();
"""

PLANTILLA_MARCO = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <title>CA-01.1 a {ancho} px</title>
    <style>
      body {{
        margin: 0;
        padding: 1rem;
        background: #6b7280;
        color: #ffffff;
        font-family: system-ui, sans-serif;
        font-size: 0.8rem;
      }}
      p {{ margin: 0 0 0.5rem; }}
      iframe {{
        width: {ancho}px;
        height: {alto}px;
        border: 0;
        background: #ffffff;
      }}
    </style>
  </head>
  <body>
    <p>CA-01.1 contra el servidor real · ancho simulado: {ancho} px (RNF-05)</p>
    <iframe id="marco" src="index.html" title="La interfaz a {ancho} px"></iframe>
    <p id="medida">midiendo…</p>
    <script>
      const marco = document.getElementById("marco");
      marco.addEventListener("load", () => {{
        // El veredicto llega después de que carga el marco, así que se mide
        // cuando la respuesta ya está pintada.
        setTimeout(() => {{
          const dentro = marco.contentDocument.documentElement;
          const desborda = dentro.scrollWidth > dentro.clientWidth;
          document.getElementById("medida").textContent =
            `MEDIDA360 ancho=${{dentro.clientWidth}} contenido=${{dentro.scrollWidth}} ` +
            `desborda=${{desborda ? "si" : "no"}}`;
        }}, 1500);
      }});
    </script>
  </body>
</html>
"""


def _navegador() -> Path:
    for ruta in NAVEGADORES:
        if ruta.is_file():
            return ruta
    raise SystemExit(
        "no se encontró Chrome ni Edge; instale uno o saque las capturas a mano"
    )


def _preparar_copia(destino: Path) -> None:
    """Copia la interfaz, el espectro y el archivo que dispara la subida."""
    import json

    shutil.copytree(FRONTEND / "interfaz", destino / "interfaz")
    shutil.copytree(FRONTEND / "servicios", destino / "servicios")
    # Desde el incremento 2 la interfaz importa la gráfica y sus librerías.
    for carpeta in ("visor-espectro", "vendor"):
        if (FRONTEND / carpeta).is_dir():
            shutil.copytree(FRONTEND / carpeta, destino / carpeta)

    if not ESPECTRO.is_file():
        raise SystemExit(
            f"falta {ESPECTRO.relative_to(RAIZ).as_posix()}; regenérelo con "
            "«python -m herramientas.generar_fixtures»"
        )
    shutil.copy2(ESPECTRO, destino / "interfaz" / ESPECTRO.name)

    (destino / "interfaz" / "subida.js").write_text(
        PLANTILLA_SUBIDA.format(nombre=json.dumps(ESPECTRO.name)), encoding="utf-8"
    )

    pagina = destino / "interfaz" / "index.html"
    html = pagina.read_text(encoding="utf-8")
    etiqueta = '<script type="module" src="interfaz.js"></script>'
    if etiqueta not in html:
        raise SystemExit("la página cambió: no se encontró dónde enganchar la subida")
    pagina.write_text(
        html.replace(
            etiqueta,
            f'{etiqueta}\n    <script type="module" src="subida.js"></script>',
        ),
        encoding="utf-8",
    )

    (destino / "interfaz" / "marco-360.html").write_text(
        PLANTILLA_MARCO.format(ancho=ANCHO_MOVIL, alto=ALTO_MOVIL), encoding="utf-8"
    )


def _puerto_libre() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return sonda.getsockname()[1]


def _servir(copia: Path) -> tuple[object, int]:
    """Levanta la aplicación real con uvicorn, en un hilo, solo en localhost."""
    import uvicorn

    from backend.api import crear_aplicacion

    puerto = _puerto_libre()
    servidor = uvicorn.Server(
        uvicorn.Config(
            crear_aplicacion(carpeta_frontend=copia),
            host="127.0.0.1",
            port=puerto,
            log_level="warning",
        )
    )
    threading.Thread(target=servidor.run, daemon=True).start()

    limite = time.monotonic() + 30
    while not servidor.started:
        if time.monotonic() > limite:
            raise SystemExit("la aplicación no terminó de arrancar")
        time.sleep(0.05)
    return servidor, puerto


def _navegar(
    navegador: Path,
    perfil: Path,
    url: str,
    ventana: tuple[int, int],
    extra: list[str],
) -> subprocess.CompletedProcess:
    ancho, alto = ventana
    return subprocess.run(
        [
            str(navegador),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={perfil}",
            f"--window-size={ancho},{alto}",
            # A propósito NO se usa --hide-scrollbars: una barra horizontal en
            # la captura de 360 px sería la prueba de que el diseño se rompe.
            f"--virtual-time-budget={TIEMPO_VIRTUAL_MS}",
            *extra,
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def _revisar_el_dom(navegador: Path, perfil: Path, url: str) -> None:
    """Exige que el veredicto del servidor esté pintado antes de fotografiar."""
    completado = _navegar(navegador, perfil, url, ESCRITORIO, ["--dump-dom"])
    dom = completado.stdout or ""

    faltantes = []
    if ESPECTRO.name not in dom:
        faltantes.append("el nombre del archivo")
    if 'data-estado="aceptado"' not in dom:
        faltantes.append("el estado «aceptado»")
    if re.search(r'id="analizar"[^>]*disabled', dom):
        faltantes.append("«Analizar» habilitado")
    if re.search(r'id="bloque-analizar"[^>]*hidden', dom):
        faltantes.append("el bloque de «Analizar» visible")

    if faltantes:
        raise SystemExit(
            "la pantalla no muestra lo que CA-01.1 exige: "
            + ", ".join(faltantes)
            + "\nNo se guardan capturas que no demuestren nada."
        )
    print("  DOM revisado: nombre, estado «aceptado» y «Analizar» habilitado")


def _capturar(
    navegador: Path,
    perfil: Path,
    url: str,
    salida: Path,
    ventana: tuple[int, int],
) -> None:
    salida.unlink(missing_ok=True)
    completado = _navegar(
        navegador, perfil, url, ventana, [f"--screenshot={salida}"]
    )
    if not salida.is_file():
        raise SystemExit(
            f"el navegador no generó {salida.name}:\n"
            f"{completado.stdout}\n{completado.stderr}"
        )


def _medir_360(navegador: Path, perfil: Path, puerto: int) -> str:
    completado = _navegar(
        navegador,
        perfil,
        f"http://127.0.0.1:{puerto}/interfaz/marco-360.html",
        VENTANA_MOVIL,
        ["--dump-dom"],
    )
    for linea in (completado.stdout or "").splitlines():
        if "MEDIDA360" in linea:
            return (
                linea.strip().removeprefix('<p id="medida">').removesuffix("</p>")
            )
    return "no se pudo medir el ancho del contenido"


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--destino",
        type=Path,
        default=EVIDENCIA,
        help="carpeta donde guardar los PNG (por omisión docs/evidencia)",
    )
    argumentos = analizador.parse_args()

    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))

    navegador = _navegador()
    argumentos.destino.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="e-ver-ca-01-1-") as temporal:
        carpeta = Path(temporal)
        copia = carpeta / "sitio"
        copia.mkdir()
        _preparar_copia(copia)
        perfil = carpeta / "perfil"

        servidor, puerto = _servir(copia)
        try:
            print(f"Navegador: {navegador.name}")
            print(f"Servidor:  http://127.0.0.1:{puerto}/ (aplicación real)")

            pagina = f"http://127.0.0.1:{puerto}/interfaz/index.html"
            _revisar_el_dom(navegador, perfil, pagina)

            _capturar(
                navegador,
                perfil,
                pagina,
                argumentos.destino / NOMBRE_ESCRITORIO,
                ESCRITORIO,
            )
            print(f"  {NOMBRE_ESCRITORIO:<32} {ESCRITORIO[0]} px")

            _capturar(
                navegador,
                perfil,
                f"http://127.0.0.1:{puerto}/interfaz/marco-360.html",
                argumentos.destino / NOMBRE_MOVIL,
                VENTANA_MOVIL,
            )
            print(f"  {NOMBRE_MOVIL:<32} {ANCHO_MOVIL} px (marco)")

            medida = _medir_360(navegador, perfil, puerto)
            print(f"\n{medida}")
            if "desborda=si" in medida:
                raise SystemExit(
                    "el diseño se desborda a lo ancho en la pantalla angosta "
                    "(RNF-05): revise los estilos antes de dar T-07 por hecha"
                )
        finally:
            servidor.should_exit = True

    print(f"\nCapturas en {argumentos.destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
