"""Lo que T-15c midió con scripts temporales, ahora reproducible (D-21).

1. Barrido del margen hasta el extremo, y escalado con el ancho de la región.
2. Simulación de los pisos de fuerza **fuera del motor**.
3. Dónde está el O–H: medias por tramo y mediana del `indicio`.
4. Las celdas equivocadas de T-15c y el pico con el que ganaban.

Corre sobre el motor congelado de T-15c, como `medir_fuerza`.

    python -m herramientas.medir_d21_complemento
"""

from __future__ import annotations

import logging
import sys
from statistics import median

from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.medir_fuerza import (
    CLASES,
    FALSOS_GF01,
    VERDAD,
    VERDADEROS_GF01,
    cargar_espectros,
    con_margen,
    medir_celdas,
    rejilla,
    umbral_de_ut03,
)
from herramientas.motor_t15c.evaluador import evaluar

#: Tramos de número de onda de la tabla del O–H: son de esta medición.
TRAMOS = (
    (3600, 3700), (3400, 3550), (3200, 3400), (3100, 3200),
    (2960, 3100), (2500, 2850), (2400, 2500),
)

#: Juegos de pisos simulados: clase -> (medida, valor).
SIMULACIONES = {
    "sin pisos": (("altura", 0), ("altura", 0), ("altura", 0)),
    "altura .063/.025/.070": (("altura", 0.063), ("altura", 0.025), ("altura", 0.070)),
    "altura .063/.025 + prominencia .029": (
        ("altura", 0.063), ("altura", 0.025), ("prominencia", 0.029)),
    "aprobado en D-22: .10/.025 + prominencia .029": (
        ("altura", 0.10), ("altura", 0.025), ("prominencia", 0.029)),
}


def barrido_extremo(espectros: dict) -> None:
    umbral = umbral_de_ut03()
    print("== margen extremo · GF-01 ==")
    for margen in (1000, 1500, 2000, 3600):
        cfg = con_margen(margen)
        scores = {n: evaluar(e, configuracion=cfg).scores() for n, e in espectros.items()}
        aciertos = sum(
            (s >= umbral) == (g in VERDAD[n][1])
            for n, fila in scores.items() for g, s in fila.items()
        )
        print(margen, {n: round(f["GF-01"], 3) for n, f in scores.items()}, aciertos)

    region = obtener_catalogo().por_id("GF-01").region_cm1
    print("\n== margen = k x ancho de la región de GF-01 ==")
    for k in (0.5, 1, 1.5, 2, 3):
        margen = k * (region[1] - region[0])
        cfg = con_margen(margen)
        print(k, margen, {
            n: round(evaluar(espectros[n], configuracion=cfg).scores()["GF-01"], 3)
            for n in VERDADEROS_GF01 + FALSOS_GF01
        })


def simular_pisos(espectros: dict) -> None:
    umbral = umbral_de_ut03()
    fuerzas = medir_celdas(espectros)
    scores = {n: evaluar(e).scores() for n, e in espectros.items()}
    print("\n== pisos simulados fuera del motor (score pasa y fuerza >= piso) ==")
    for nombre, pisos in SIMULACIONES.items():
        por_clase = dict(zip(CLASES, pisos))
        mal = []
        for n, fila in scores.items():
            for g, s in fila.items():
                clase = next(c for c, grupos in CLASES.items() if g in grupos)
                medida, piso = por_clase[clase]
                pasa = s >= umbral and fuerzas[n, g][medida] >= piso
                if pasa != (g in VERDAD[n][1]):
                    mal.append(f"{'sobra' if pasa else 'falta'} {n}/{g}")
        completos = sum(not any(f" {n}/" in m for m in mal) for n in VERDAD)
        print(f"{nombre:48} {56 - len(mal)}/56, conjuntos {completos}/8: {mal}")


def mediana_del_indicio(espectros: dict) -> None:
    cfg = obtener_configuracion()
    indicio = obtener_catalogo().por_id("GF-01").acompanantes_por_rol("indicio")[0].rango
    print("\n== dónde está el O–H: media por tramo y mediana del indicio ==")
    print(f"{'':15}", *[f"{a}-{b}" for a, b in TRAMOS], "| mediana indicio")
    for n, e in espectros.items():
        reja = rejilla(e, cfg)
        valores = [reja.intensidad[i] for i in reja.indices_en(*indicio)]
        print(f"{n:15}", *[f"{reja.promedio_en(*t):9.4f}" for t in TRAMOS],
              f"| {median(valores):.4f}")


def celdas_equivocadas(espectros: dict) -> None:
    umbral = umbral_de_ut03()
    print("\n== celdas equivocadas de T-15c ==")
    for n, e in espectros.items():
        for p in evaluar(e).puntajes:
            presente = p.grupo in VERDAD[n][1]
            if (p.score >= umbral) == presente:
                continue
            dentro = p.pico_cm1 is not None and (
                p.region_cm1[0] <= p.pico_cm1 <= p.region_cm1[1])
            pico = "-" if p.pico_cm1 is None else f"{p.pico_cm1:.0f}"
            print(f"{'FN' if presente else 'FP'} {n:15} {p.grupo} {p.score:.2f} "
                  f"pico {pico} en región {dentro} ancho50 {p.ancho_cm1:.0f}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    espectros = cargar_espectros()
    barrido_extremo(espectros)
    simular_pisos(espectros)
    mediana_del_indicio(espectros)
    celdas_equivocadas(espectros)


if __name__ == "__main__":
    main()
