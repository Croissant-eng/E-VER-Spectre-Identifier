"""Saca las capturas de evidencia de MOD-01 (T-06).

Uso, desde la raíz del repositorio:

    python -m herramientas.capturar_interfaz

Deja los PNG en `docs/evidencia/`: la pantalla inicial, un documento aprobado y
un rechazo, en escritorio y a 360 px de ancho, que es la pantalla más angosta
que el diseño debe sostener (adelanto de RNF-05).

**Cómo lo hace, y por qué así:**

- Las capturas son de la **página de verdad**: copia `frontend/` a una carpeta
  temporal y le agrega un solo archivo, `simulacion.js`, que pinta un veredicto
  simulado. Los archivos del repositorio no se tocan: la interfaz no lleva
  ganchos de prueba.
- Sirve la copia por `http://127.0.0.1` con un puerto libre, porque un módulo
  ES no se puede cargar desde `file://`. Es la máquina hablando consigo misma;
  no sale a internet.
- Dibuja con Chrome o Edge en modo headless, el que esté instalado.
- **Las capturas de 360 px van dentro de un marco de 360 px de ancho**, no en
  una ventana de 360: el modo headless no deja ventanas de menos de unos 500 px
  y, si se le piden, recorta la imagen y aparenta un diseño roto que no lo
  está. El marco da el ancho de verdad y, de paso, deja **medir**: la
  herramienta compara el ancho del contenido contra el del marco y avisa si hay
  desplazamiento horizontal (adelanto de RNF-05).

**Esto no es código de la aplicación**: vive en `herramientas/` y ningún módulo
de `backend/` ni de `frontend/` lo importa.
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FRONTEND = RAIZ / "frontend"
EVIDENCIA = RAIZ / "docs" / "evidencia"

#: Dónde buscar un navegador, en orden de preferencia.
NAVEGADORES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)

#: Tamaño de ventana de las capturas de escritorio.
ESCRITORIO = (1280, 900)

#: El ancho que debe sostener el diseño (RNF-05) y el alto del marco.
ANCHO_MOVIL = 360
ALTO_MOVIL = 820

#: Ventana para las capturas del marco de 360 px. El modo headless no admite
#: ventanas mucho más angostas, así que se le deja aire alrededor al marco.
VENTANA_MOVIL = (520, ALTO_MOVIL + 90)

#: El veredicto aceptado del contrato de la sección 5.
VEREDICTO_ACEPTADO = {
    "valido": True,
    "nombre": "acetona.jdx",
    "bytes": 307200,
}

#: Un rechazo con los textos que redacta UT-02 (se leen del catálogo, no se
#: escriben aquí).
CODIGO_DEL_RECHAZO = "TAMANO_EXCEDIDO"

#: Lo que se captura: archivo, estado, si va dentro del marco de 360 y ventana.
CAPTURAS = (
    ("t-06-escritorio-inicial.png", "inicial", False, ESCRITORIO),
    ("t-06-escritorio-aceptado.png", "aceptado", False, ESCRITORIO),
    ("t-06-escritorio-rechazado.png", "rechazado", False, ESCRITORIO),
    ("t-06-movil-360-aceptado.png", "aceptado", True, VENTANA_MOVIL),
    ("t-06-movil-360-rechazado.png", "rechazado", True, VENTANA_MOVIL),
)

PLANTILLA_SIMULACION = """/**
 * Pinta un veredicto simulado para las capturas de evidencia (T-06).
 *
 * Lo genera `herramientas/capturar_interfaz.py` en una copia temporal de la
 * interfaz; **no vive en el repositorio** ni lo carga la página de verdad.
 */

import {{ elementosDe, pintar }} from "./pintar.js";
import {{ vistaDeVeredicto, vistaInicial }} from "./vista.js";

const VEREDICTOS = {veredictos};
const estado = new URLSearchParams(location.search).get("estado") ?? "inicial";

const elementos = elementosDe(document);
pintar(
  estado === "inicial" ? vistaInicial() : vistaDeVeredicto(VEREDICTOS[estado]),
  elementos,
);

if (estado !== "inicial") {{
  // Para la captura: el selector ya no se ve vacío y el botón vuelve a estar
  // disponible, como queda tras una validación de verdad.
  document.getElementById("validar").disabled = false;
}}
"""


PLANTILLA_MARCO = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <title>MOD-01 a {ancho} px</title>
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
    <p>Ancho de pantalla simulado: {ancho} px (RNF-05)</p>
    <iframe id="marco" title="La interfaz a {ancho} px"></iframe>
    <p id="medida">midiendo…</p>
    <script>
      const marco = document.getElementById("marco");
      const estado = new URLSearchParams(location.search).get("estado") ?? "inicial";
      marco.src = `index.html?estado=${{estado}}`;
      marco.addEventListener("load", () => {{
        const dentro = marco.contentDocument.documentElement;
        const desborda = dentro.scrollWidth > dentro.clientWidth;
        document.getElementById("medida").textContent =
          `MEDIDA360 ancho=${{dentro.clientWidth}} contenido=${{dentro.scrollWidth}} ` +
          `desborda=${{desborda ? "si" : "no"}}`;
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


def _veredicto_rechazado() -> dict[str, object]:
    """El rechazo, con el texto de UT-02 tal como lo vería la persona."""
    from backend.utilerias import mensajes

    mensaje = mensajes.obtener(CODIGO_DEL_RECHAZO)
    return {
        "valido": False,
        "codigo": mensaje.codigo,
        "titulo": mensaje.titulo,
        "mensaje": mensaje.texto,
        "accion": mensaje.accion,
    }


def _preparar_copia(destino: Path) -> Path:
    """Copia la interfaz y le agrega el archivo de simulación."""
    import json

    shutil.copytree(FRONTEND / "interfaz", destino / "interfaz")
    shutil.copytree(FRONTEND / "servicios", destino / "servicios")
    # Desde el incremento 2 la interfaz importa la gráfica y sus librerías.
    for carpeta in ("visor-espectro", "vendor"):
        if (FRONTEND / carpeta).is_dir():
            shutil.copytree(FRONTEND / carpeta, destino / carpeta)

    veredictos = {
        "aceptado": VEREDICTO_ACEPTADO,
        "rechazado": _veredicto_rechazado(),
    }
    (destino / "interfaz" / "simulacion.js").write_text(
        PLANTILLA_SIMULACION.format(
            veredictos=json.dumps(veredictos, ensure_ascii=False, indent=2)
        ),
        encoding="utf-8",
    )

    pagina = destino / "interfaz" / "index.html"
    html = pagina.read_text(encoding="utf-8")
    html = html.replace(
        '<script type="module" src="interfaz.js"></script>',
        '<script type="module" src="interfaz.js"></script>\n'
        '    <script type="module" src="simulacion.js"></script>',
    )
    pagina.write_text(html, encoding="utf-8")

    (destino / "interfaz" / "marco-360.html").write_text(
        PLANTILLA_MARCO.format(ancho=ANCHO_MOVIL, alto=ALTO_MOVIL), encoding="utf-8"
    )
    return pagina


def _puerto_libre() -> int:
    with socket.socket() as sonda:
        sonda.bind(("127.0.0.1", 0))
        return sonda.getsockname()[1]


def _servir(carpeta: Path) -> tuple[ThreadingHTTPServer, int]:
    puerto = _puerto_libre()
    manejador = partial(SimpleHTTPRequestHandler, directory=str(carpeta))
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    return servidor, puerto


def _capturar(
    navegador: Path, perfil: Path, url: str, salida: Path, tamano: tuple[int, int]
) -> None:
    ancho, alto = tamano
    completado = subprocess.run(
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
            "--virtual-time-budget=3000",
            f"--screenshot={salida}",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if not salida.is_file():
        raise SystemExit(
            f"el navegador no generó {salida.name}:\n"
            f"{completado.stdout}\n{completado.stderr}"
        )


def _medir_360(navegador: Path, perfil: Path, puerto: int) -> str:
    """Pregunta al navegador si el contenido cabe a lo ancho en el marco."""
    completado = subprocess.run(
        [
            str(navegador),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            f"--user-data-dir={perfil}",
            f"--window-size={VENTANA_MOVIL[0]},{VENTANA_MOVIL[1]}",
            "--virtual-time-budget=3000",
            "--dump-dom",
            f"http://127.0.0.1:{puerto}/interfaz/marco-360.html?estado=rechazado",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    for linea in (completado.stdout or "").splitlines():
        if "MEDIDA360" in linea:
            return linea.strip().removeprefix("<p id=\"medida\">").removesuffix("</p>")
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

    with tempfile.TemporaryDirectory(prefix="e-ver-capturas-") as temporal:
        carpeta = Path(temporal)
        copia = carpeta / "sitio"
        copia.mkdir()
        _preparar_copia(copia)
        perfil = carpeta / "perfil"

        servidor, puerto = _servir(copia)
        try:
            print(f"Navegador: {navegador.name}")
            for nombre, estado, en_marco, tamano in CAPTURAS:
                pagina = "marco-360.html" if en_marco else "index.html"
                url = f"http://127.0.0.1:{puerto}/interfaz/{pagina}?estado={estado}"
                salida = argumentos.destino / nombre
                salida.unlink(missing_ok=True)
                _capturar(navegador, perfil, url, salida, tamano)
                ancho = f"{ANCHO_MOVIL} px (marco)" if en_marco else f"{tamano[0]} px"
                print(f"  {nombre:<34} {ancho}")

            medida = _medir_360(navegador, perfil, puerto)
            print(f"\n{medida}")
            if "desborda=si" in medida:
                raise SystemExit(
                    "el diseño se desborda a lo ancho en la pantalla angosta "
                    "(RNF-05): revise los estilos antes de dar T-06 por hecha"
                )
        finally:
            servidor.shutdown()

    print(f"\nCapturas en {argumentos.destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
