"""Saca las capturas de evidencia de la gráfica de MOD-05 (T-12 y T-13).

Uso, desde la raíz del repositorio:

    python -m herramientas.capturar_grafica

Deja tres PNG en `docs/evidencia/`:

- `t-12-escritorio-grafica.png`: el `.jdx` válido, aprobado y dibujado con el
  eje de 4000 a 400 (CA-04.1).
- `t-13-movil-360-grafica.png`: lo mismo dentro de un marco de 360 px, con la
  medida del ancho (CA-04.2).
- `t-13-movil-360-sin-grafica.png`: la línea plana, que MOD-03 aprueba y MOD-04
  rechaza; en lugar de una gráfica vacía va el mensaje de UT-02 (CA-04.3).

Funciona igual que `capturar_ca_01_1.py`: levanta la aplicación real en
localhost con una copia del frontend, y a esa copia le agrega un archivo que
elige el espectro y envía el formulario, porque en modo headless no hay quien
haga clic. Antes de fotografiar revisa el DOM, y la medida de 360 px se lee del
navegador, no se juzga a ojo.

Para usar otro navegador, se pone su ruta en la variable `EVER_NAVEGADOR`.

**Esto no es código de la aplicación**: vive en `herramientas/` y ningún módulo
de `backend/` ni de `frontend/` lo importa.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from herramientas.capturar_ca_01_1 import (  # noqa: E402
    ALTO_MOVIL,
    ANCHO_MOVIL,
    ESCRITORIO,
    NAVEGADORES,
    TIEMPO_VIRTUAL_MS,
    VENTANA_MOVIL,
    _servir,
)

FRONTEND = RAIZ / "frontend"
EVIDENCIA = RAIZ / "docs" / "evidencia"
DATOS = RAIZ / "datos" / "pruebas"

#: Navegadores de Linux, además de los de Windows de la herramienta de T-07.
NAVEGADORES_LINUX = (
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
    Path("/usr/bin/chromium-browser"),
    Path("/opt/pw-browsers/chromium"),
)

#: Lo que se captura: archivo de salida, espectro, si va en el marco de 360 y
#: qué estado de la gráfica se exige antes de fotografiar.
CAPTURAS = (
    ("t-12-escritorio-grafica.png", "espectro-valido.jdx", False, "lista"),
    ("t-13-movil-360-grafica.png", "espectro-valido.jdx", True, "lista"),
    ("t-13-movil-360-sin-grafica.png", "espectro-linea-plana.csv", True, "sin-espectro"),
)

PLANTILLA_SUBIDA = """/**
 * Sube un espectro solo, para las capturas de MOD-05.
 *
 * Lo genera `herramientas/capturar_grafica.py` en una copia temporal de la
 * interfaz; no vive en el repositorio. Hace lo que haría una persona: elige el
 * archivo y envía el formulario. Cuando la gráfica termina, anota en la página
 * cuántos puntos dibujó Chart.js, para que la herramienta lo pueda revisar.
 */

const NOMBRE = new URLSearchParams(location.search).get("archivo");

const entrada = document.getElementById("archivo");
const formulario = document.getElementById("formulario");
const seccion = document.getElementById("grafica");

const datos = await fetch(NOMBRE).then((respuesta) => respuesta.arrayBuffer());
const archivo = new File([datos], NOMBRE, { type: "application/octet-stream" });
const transferencia = new DataTransfer();
transferencia.items.add(archivo);
entrada.files = transferencia.files;
entrada.dispatchEvent(new Event("change"));
formulario.requestSubmit();

const vigia = new MutationObserver(() => {
  const estado = seccion.dataset.estado;
  if (estado === "lista") {
    const grafica = globalThis.Chart.getChart(document.getElementById("grafica-lienzo"));
    const x = grafica.scales.x;
    document.body.dataset.graficaPuntos = String(grafica.data.datasets[0].data.length);
    document.body.dataset.graficaEje = `${x.getValueForPixel(x.left)}->${x.getValueForPixel(x.right)}`;
  }
  if (estado === "lista" || estado === "sin-espectro") {
    document.body.dataset.graficaEstado = estado;
  }
});
vigia.observe(seccion, { attributes: true, attributeFilter: ["data-estado"] });
"""

PLANTILLA_MARCO = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <title>MOD-05 a {ancho} px</title>
    <style>
      body {{ margin: 0; padding: 1rem; background: #6b7280; color: #ffffff;
             font-family: system-ui, sans-serif; font-size: 0.8rem; }}
      p {{ margin: 0 0 0.5rem; }}
      iframe {{ width: {ancho}px; height: {alto}px; border: 0; background: #ffffff; }}
    </style>
  </head>
  <body>
    <p>MOD-05 contra el servidor real, ancho simulado: {ancho} px (CA-04.2)</p>
    <iframe id="marco" title="La interfaz a {ancho} px"></iframe>
    <p id="medida">midiendo…</p>
    <script>
      const marco = document.getElementById("marco");
      const archivo = new URLSearchParams(location.search).get("archivo");
      marco.src = `index.html?archivo=${{encodeURIComponent(archivo)}}`;
      marco.addEventListener("load", () => {{
        const revisar = () => {{
          const dentro = marco.contentDocument;
          if (!dentro.body.dataset.graficaEstado) {{
            setTimeout(revisar, 100);
            return;
          }}
          // Con la gráfica o el mensaje ya pintados, la página baja hasta la
          // sección y se mide el ancho.
          dentro.getElementById("grafica").scrollIntoView();
          const raiz = dentro.documentElement;
          const lienzo = dentro.getElementById("grafica-lienzo");
          const desborda = raiz.scrollWidth > raiz.clientWidth;
          document.getElementById("medida").textContent =
            `MEDIDA360 ancho=${{raiz.clientWidth}} contenido=${{raiz.scrollWidth}} ` +
            `lienzo=${{Math.round(lienzo.getBoundingClientRect().width)}} ` +
            `desborda=${{desborda ? "si" : "no"}}`;
        }};
        revisar();
      }});
    </script>
  </body>
</html>
"""


def _navegador() -> Path:
    propio = os.environ.get("EVER_NAVEGADOR")
    if propio and Path(propio).is_file():
        return Path(propio)
    for ruta in (*NAVEGADORES, *NAVEGADORES_LINUX):
        if ruta.is_file():
            return ruta
    raise SystemExit(
        "no se encontró Chrome, Edge ni Chromium; ponga la ruta en EVER_NAVEGADOR"
    )


def _preparar_copia(destino: Path) -> None:
    for carpeta in ("interfaz", "servicios", "visor-espectro", "vendor"):
        shutil.copytree(FRONTEND / carpeta, destino / carpeta)
    for _, espectro, _, _ in CAPTURAS:
        shutil.copy2(DATOS / espectro, destino / "interfaz" / espectro)
    (destino / "interfaz" / "subida.js").write_text(PLANTILLA_SUBIDA, encoding="utf-8")

    pagina = destino / "interfaz" / "index.html"
    html = pagina.read_text(encoding="utf-8")
    etiqueta = '<script type="module" src="interfaz.js"></script>'
    if etiqueta not in html:
        raise SystemExit("la página cambió: no se encontró dónde enganchar la subida")
    pagina.write_text(
        html.replace(etiqueta, f'{etiqueta}\n    <script type="module" src="subida.js"></script>'),
        encoding="utf-8",
    )
    (destino / "interfaz" / "marco-360.html").write_text(
        PLANTILLA_MARCO.format(ancho=ANCHO_MOVIL, alto=ALTO_MOVIL), encoding="utf-8"
    )


def _navegar(navegador: Path, perfil: Path, url: str, ventana, extra: list[str]):
    ancho, alto = ventana
    return subprocess.run(
        [
            str(navegador),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={perfil}",
            f"--window-size={ancho},{alto}",
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


def _revisar_el_dom(navegador: Path, perfil: Path, url: str, esperado: str) -> str:
    """Exige que la gráfica o el mensaje estén pintados antes de fotografiar."""
    dom = _navegar(navegador, perfil, url, ESCRITORIO, ["--dump-dom"]).stdout or ""
    estado = re.search(r'data-grafica-estado="([^"]+)"', dom)
    if not estado or estado.group(1) != esperado:
        raise SystemExit(
            f"la gráfica no quedó en «{esperado}» ({estado.group(1) if estado else 'sin estado'}).\n"
            "No se guardan capturas que no demuestren nada."
        )
    if esperado == "lista":
        puntos = re.search(r'data-grafica-puntos="(\d+)"', dom)
        eje = re.search(r'data-grafica-eje="([^"]+)"', dom)
        if not puntos or int(puntos.group(1)) < 2:
            raise SystemExit("Chart.js no dibujó puntos")
        return f"puntos={puntos.group(1)} eje={eje.group(1) if eje else '?'}"
    if re.search(r'id="grafica-contenedor"(?![^>]*hidden)', dom):
        raise SystemExit("sin espectro, el lienzo no debe verse (CA-04.3)")
    return "mensaje en lugar de gráfica, lienzo escondido"


def _medir(navegador: Path, perfil: Path, url: str) -> str:
    completado = _navegar(navegador, perfil, url, VENTANA_MOVIL, ["--dump-dom"])
    for linea in (completado.stdout or "").splitlines():
        if "MEDIDA360" in linea:
            return linea.strip().removeprefix('<p id="medida">').removesuffix("</p>")
    return "no se pudo medir el ancho del contenido"


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--destino", type=Path, default=EVIDENCIA)
    argumentos = analizador.parse_args()

    navegador = _navegador()
    argumentos.destino.mkdir(parents=True, exist_ok=True)
    fallas = []

    with tempfile.TemporaryDirectory(prefix="e-ver-grafica-") as temporal:
        carpeta = Path(temporal)
        copia = carpeta / "sitio"
        copia.mkdir()
        _preparar_copia(copia)
        perfil = carpeta / "perfil"

        servidor, puerto = _servir(copia)
        try:
            print(f"Navegador: {navegador.name}")
            base = f"http://127.0.0.1:{puerto}/interfaz"
            for nombre, espectro, en_marco, esperado in CAPTURAS:
                consulta = f"?archivo={espectro}"
                revisado = _revisar_el_dom(
                    navegador, perfil, f"{base}/index.html{consulta}", esperado
                )
                pagina = "marco-360.html" if en_marco else "index.html"
                ventana = VENTANA_MOVIL if en_marco else ESCRITORIO
                salida = argumentos.destino / nombre
                salida.unlink(missing_ok=True)
                _navegar(navegador, perfil, f"{base}/{pagina}{consulta}", ventana,
                         [f"--screenshot={salida}"])
                if not salida.is_file():
                    raise SystemExit(f"el navegador no generó {nombre}")
                print(f"  {nombre:<34} {revisado}")
                if en_marco:
                    medida = _medir(navegador, perfil, f"{base}/marco-360.html{consulta}")
                    print(f"  {'':<34} {medida}")
                    if "desborda=no" not in medida:
                        fallas.append(f"{nombre}: {medida}")
        finally:
            servidor.should_exit = True

    if fallas:
        raise SystemExit("la pantalla angosta se desborda (CA-04.2):\n" + "\n".join(fallas))
    print(f"\nCapturas en {argumentos.destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
