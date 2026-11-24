"""La tabla de 56 celdas del motor **actual** contra la verdad de D-21.

    python -m herramientas.tabla_56              # la tabla
    python -m herramientas.tabla_56 ruta.json    # y además la guarda

`*` marca un grupo presente según D-21; `!` marca una celda equivocada.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from herramientas.medir_fuerza import VERDAD, cargar_espectros, umbral_de_ut03
from motor_identificacion.reglas import evaluar


def celdas() -> dict[str, dict]:
    salida = {}
    for nombre, espectro in cargar_espectros().items():
        for p in evaluar(espectro).puntajes:
            salida[f"{nombre}|{p.grupo}"] = {
                "score": p.score,
                "pico_cm1": p.pico_cm1,
                "ajustes": list(p.ajustes),
            }
    return salida


def equivocadas(tabla: dict[str, dict], umbral: float) -> list[str]:
    fallos = []
    for clave, celda in tabla.items():
        nombre, grupo = clave.split("|")
        presente = grupo in VERDAD[nombre][1]
        if (celda["score"] >= umbral) != presente:
            fallos.append(f"{'falta' if presente else 'sobra'} {nombre}/{grupo}")
    return fallos


def imprimir(tabla: dict[str, dict]) -> None:
    umbral = umbral_de_ut03()
    fallos = equivocadas(tabla, umbral)
    grupos = [f"GF-0{i}" for i in range(1, 8)]
    print(f"{'':>15} " + " ".join(f"{g:>7}" for g in grupos))
    for nombre, (_, presentes) in VERDAD.items():
        fila = []
        for g in grupos:
            marca = "*" if g in presentes else " "
            mal = "!" if any(f.endswith(f"{nombre}/{g}") for f in fallos) else " "
            fila.append(f"{tabla[f'{nombre}|{g}']['score']:.2f}{marca}{mal}".rjust(7))
        print(f"{nombre:>15} " + " ".join(fila))
    completos = sum(not any(f" {n}/" in f for f in fallos) for n in VERDAD)
    print(f"aciertos {56 - len(fallos)}/56 · conjuntos {completos}/8 · {fallos}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tabla = celdas()
    imprimir(tabla)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(
            json.dumps(tabla, ensure_ascii=False, indent=1), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
