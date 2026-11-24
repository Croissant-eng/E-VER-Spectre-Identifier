"""Mide lo que D-21 pide antes de tocar el puntaje (T-15c).

1. **Causa B** · barre el margen de la línea base y reporta GF-01.
2. **Causa A** · mide la fuerza de la banda en las 56 celdas, separadas en
   presentes y ausentes con la tabla de verdad de D-21.

Es instrumental fuera de la aplicación: usa el motor **congelado de T-15c**
(`herramientas/motor_t15c`), que es sobre el que se tomaron los números de
D-21, para que se sigan reproduciendo aunque el motor cambie. La configuración
se cambia **en memoria** y no se escribe nada.

    python -m herramientas.medir_fuerza
"""

from __future__ import annotations

import dataclasses
import json
import logging
import sys
from math import sqrt
from pathlib import Path

from backend.preprocesamiento import procesar
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.motor_t15c.evaluador import evaluar
from herramientas.motor_t15c.picos import Rejilla

CARPETA = Path(__file__).resolve().parents[1] / "datos" / "referencia"

#: La verdad de referencia de D-21, copiada tal cual: no se infiere aquí.
VERDAD: dict[str, tuple[str, set[str]]] = {
    "ciclohexano": ("110-82-7-IR(Cyclohexane).jdx", {"GF-03"}),
    "acetona": ("67-64-1-IR.jdx", {"GF-03", "GF-05"}),
    "ácido benzoico": ("65-85-0-IR.jdx", {"GF-01", "GF-05", "GF-07"}),
    "tolueno": ("108-88-3-IR(Toluene).jdx", {"GF-03", "GF-07"}),
    "ciclohexeno": ("110-83-8-IR(Cyclohexene).jdx", {"GF-03", "GF-06"}),
    "acetonitrilo": ("75-05-8-IR(Acetonitrile).jdx", {"GF-03", "GF-04"}),
    "anilina": ("62-53-3-IR.jdx", {"GF-02", "GF-07"}),
    "1-butanol": ("71-36-3-IR(1-Butanol).jdx", {"GF-01", "GF-03"}),
}

#: Las clases de intensidad, como las agrupa D-21.
CLASES = {
    "fuerte": ("GF-01", "GF-05"),
    "media": ("GF-02", "GF-03", "GF-04", "GF-07"),
    "media/débil": ("GF-06",),
}

MARGENES = (50, 100, 200, 400, 600, 800, 1000)
VERDADEROS_GF01 = ("ácido benzoico", "1-butanol")
FALSOS_GF01 = ("ciclohexano", "acetona", "acetonitrilo")

#: Cuatro formas de decir «fuerza». La primera es la literal de D-21: el valor
#: en la escala normalizada. Se miden todas para no elegir a ciegas.
METRICAS = {
    "altura": "máximo en la región, escala 0–1",
    "sobre_base": "máximo − mínimo de (región ± margen)",
    "media_base": "media de la región − mínimo de (región ± margen)",
    "prominencia": "mayor prominencia topográfica en la región",
}


def cargar_espectros() -> dict:
    espectros = {}
    for nombre, (archivo, _) in VERDAD.items():
        ruta = CARPETA / archivo
        if not ruta.is_file():
            raise SystemExit(f"falta {archivo} en datos/referencia")
        resultado = procesar(archivo, ruta.read_text(encoding="latin-1"))
        if resultado.espectro is None:
            raise SystemExit(f"MOD-04 rechazó {archivo}: {resultado.detalle}")
        espectros[nombre] = resultado.espectro
    return espectros


def con_margen(margen: float):
    """La configuración del repositorio con otro margen, solo en memoria."""
    base = obtener_configuracion()
    metodo = dataclasses.replace(
        base.motor.definicion_metodo, margen_linea_base_cm1=float(margen)
    )
    motor = dataclasses.replace(base.motor, definicion_metodo=metodo)
    return dataclasses.replace(base, motor=motor)


def umbral_de_ut03() -> float:
    datos = json.loads(obtener_configuracion().ruta.read_text(encoding="utf-8"))
    return float(datos["motor"]["umbral_confianza"])


def rejilla(espectro, configuracion) -> Rejilla:
    return Rejilla(
        espectro.eje_cm1,
        espectro.intensidad,
        espectro.rango_medido_cm1,
        configuracion.motor.definicion_metodo.margen_linea_base_cm1,
    )


def fuerzas(reja: Rejilla, region: tuple[float, float]) -> dict[str, float]:
    indices = reja.indices_en(*region)
    maximo = max(reja.intensidad[i] for i in indices)
    base = reja.linea_base(*region)
    picos = reja.picos_en(*region)
    return {
        "altura": maximo,
        "sobre_base": maximo - base,
        "media_base": reja.promedio_en(*region) - base,
        "prominencia": max((p.prominencia for p in picos), default=0.0),
    }


def barrido(espectros: dict) -> None:
    umbral = umbral_de_ut03()
    region = obtener_catalogo().por_id("GF-01").region_cm1
    ancho = region[1] - region[0]
    columnas = VERDADEROS_GF01 + FALSOS_GF01

    print("== CAUSA B · GF-01 según el margen de línea base ==")
    print(
        f"{'margen':>7} {'efectivo':>9} "
        + " ".join(f"{c:>14}" for c in columnas)
        + "   aciertos/56"
    )
    for margen in MARGENES:
        cfg = con_margen(margen)
        scores = {
            n: evaluar(e, configuracion=cfg).scores() for n, e in espectros.items()
        }
        aciertos = sum(
            (s >= umbral) == (g in VERDAD[n][1])
            for n, fila in scores.items()
            for g, s in fila.items()
        )
        print(
            f"{margen:>7} {'±' + format(margen + ancho, '.0f'):>9} "
            + " ".join(f"{scores[c]['GF-01']:>14.3f}" for c in columnas)
            + f"   {aciertos}"
        )

    print("\n-- lo que hay detrás (ventana efectiva del motor) --")
    print(
        f"{'margen':>7} {'compuesto':>15} {'base':>8} {'mínimo en':>10} "
        f"{'media reg.':>10} {'lift':>7} {'vara':>7}"
    )
    for margen in (200, 600, 1000):
        cfg = con_margen(margen)
        for nombre in columnas:
            reja = rejilla(espectros[nombre], cfg)
            base = reja.linea_base(region[0] - ancho, region[1] + ancho)
            vecinos = reja.indices_en(
                region[0] - ancho - margen, region[1] + ancho + margen
            )
            donde = reja.eje[min(vecinos, key=lambda i: reja.intensidad[i])]
            media = reja.promedio_en(*region)
            print(
                f"{margen:>7} {nombre:>15} {base:8.4f} {donde:10.0f} {media:10.4f} "
                f"{media - base:7.4f} {reja.escala_prominencia:7.4f}"
            )

    print("\n-- cuánto se mueven los anchos que calibraron 175 y 160 --")
    casos = [
        ("1-butanol", "GF-01", "r1"),
        ("anilina", "GF-02", "r1"),
        ("1-butanol", "GF-03", "r4"),
        ("ácido benzoico", "GF-03", "r4"),
    ]
    print(f"{'margen':>7} " + " ".join(f"{' '.join(c):>24}" for c in casos))
    for margen in MARGENES:
        cfg = con_margen(margen)
        metodo = cfg.motor.definicion_metodo
        fila = []
        for nombre, grupo, regla in casos:
            reja = rejilla(espectros[nombre], cfg)
            cima = reja.cima_en(*obtener_catalogo().por_id(grupo).region_cm1)
            fraccion = metodo.fraccion_r1 if regla == "r1" else metodo.fraccion_r4
            fila.append(reja.ancho(cima, fraccion).cm1)
        print(f"{margen:>7} " + " ".join(f"{v:>24.1f}" for v in fila))


def medir_celdas(espectros: dict) -> dict:
    cfg = obtener_configuracion()
    return {
        (n, g.id): fuerzas(rejilla(e, cfg), g.region_cm1)
        for n, e in espectros.items()
        for g in obtener_catalogo().grupos
    }


def separar(celdas: dict, grupos, metrica: str) -> tuple[list, list]:
    presentes, ausentes = [], []
    for (n, g), f in celdas.items():
        if g in grupos:
            (presentes if g in VERDAD[n][1] else ausentes).append((f[metrica], n, g))
    return sorted(presentes), sorted(ausentes)


def causa_a(celdas: dict) -> None:
    grupos = obtener_catalogo().orden_canonico
    for metrica, texto in METRICAS.items():
        print(f"\n== CAUSA A · {metrica}: {texto} (* = PRESENTE en D-21) ==")
        print(f"{'':>15} " + " ".join(f"{g:>8}" for g in grupos))
        for n in VERDAD:
            print(
                f"{n:>15} "
                + " ".join(
                    f"{celdas[n, g][metrica]:7.4f}"
                    + ("*" if g in VERDAD[n][1] else " ")
                    for g in grupos
                )
            )
        conjuntos = [(f"CLASE {c}", gs) for c, gs in CLASES.items()]
        conjuntos += [(g, (g,)) for g in grupos]
        for nombre, gs in conjuntos:
            si, no = separar(celdas, gs, metrica)
            texto_si = f"[{si[0][0]:.4f}, {si[-1][0]:.4f}] n={len(si)}"
            texto_no = f"[{no[0][0]:.4f}, {no[-1][0]:.4f}] n={len(no)}"
            if si[0][0] > no[-1][0]:
                corte = sqrt(si[0][0] * max(no[-1][0], 1e-9))
                razon = si[0][0] / max(no[-1][0], 1e-9)
                fin = f"SEPARA x{razon:.2f}, media geométrica {corte:.4f}"
            else:
                fuera = sum(v < si[0][0] for v, _, _ in no)
                fin = (
                    f"NO SEPARA: menor presente {si[0][1]}/{si[0][2]}, mayor ausente "
                    f"{no[-1][1]}/{no[-1][2]}; sin perder presentes un piso quita "
                    f"{fuera}/{len(no)}"
                )
            print(f"  {nombre:<18} si {texto_si:<23} no {texto_no:<24} {fin}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    espectros = cargar_espectros()
    barrido(espectros)
    causa_a(medir_celdas(espectros))


if __name__ == "__main__":
    main()
