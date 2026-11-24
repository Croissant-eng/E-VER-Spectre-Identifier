"""El único espectro local que no calibró nada: benzonitrilo (T-15d).

MOD-04 lo rechaza porque su eje viene en micrómetros. Aquí se convierte a cm⁻¹
**en memoria**, solo para esta comprobación; el archivo no se toca y MOD-04
tampoco. Debe dar GF-04 y GF-07, y nada más.

    python -m herramientas.comprobar_benzonitrilo
"""

from __future__ import annotations

import logging
import re
import sys

from backend.preprocesamiento import procesar
from herramientas.medir_fuerza import CARPETA, umbral_de_ut03
from motor_identificacion.reglas import evaluar

ARCHIVO = "100-47-0-IR(Benzonitrile).jdx"
ESPERADOS = {"GF-04", "GF-07"}

#: 1 cm = 10 000 µm: de longitud de onda a número de onda.
MICROMETROS_POR_CM = 1e4


def main() -> None:
    logging.disable(logging.CRITICAL)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    texto = (CARPETA / ARCHIVO).read_text(encoding="latin-1")

    def etiqueta(nombre: str) -> str:
        return re.search(rf"##{nombre}=\s*(.+)", texto).group(1).strip()

    if etiqueta("XUNITS") != "MICROMETERS":
        raise SystemExit("el archivo ya no viene en micrómetros; revise este script")
    ys: list[float] = []
    for linea in texto.split("##XYDATA=")[1].split("##END")[0].splitlines()[1:]:
        numeros = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", linea)
        ys += [float(n) * float(etiqueta("YFACTOR")) for n in numeros[1:]]
    if len(ys) != int(etiqueta("NPOINTS")):
        raise SystemExit("los puntos leídos no coinciden con NPOINTS")

    primero, ultimo = float(etiqueta("FIRSTX")), float(etiqueta("LASTX"))
    paso = (ultimo - primero) / (len(ys) - 1)
    # El CSV declara su unidad: sin eso MOD-04 lo rechaza, y hace bien (D-11).
    csv = "cm-1,transmitancia\n" + "\n".join(
        f"{MICROMETROS_POR_CM / (primero + paso * i):.4f},{y:.6f}"
        for i, y in enumerate(ys)
    )
    resultado = procesar("benzonitrilo.csv", csv)
    if resultado.espectro is None:
        raise SystemExit(f"MOD-04 rechazó la conversión: {resultado.detalle}")

    detectados = set()
    for p in evaluar(resultado.espectro).puntajes:
        print(f"{p.grupo} {p.score:.2f} {p.ajustes}")
        if p.score >= umbral_de_ut03():
            detectados.add(p.grupo)
    print("detectados:", sorted(detectados), "· esperados:", sorted(ESPERADOS))


if __name__ == "__main__":
    main()
