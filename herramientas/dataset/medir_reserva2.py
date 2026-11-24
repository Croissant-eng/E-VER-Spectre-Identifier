"""Lo que se puede medir sin etiquetas sobre los supervivientes (T-16a-1).

    python -m herramientas.dataset.medir_reserva2

1. Cuántos espectros **distintos** hay detrás de los archivos que pasan.
2. Sanidad de la conversión de MOD-04 (solo se observa; no se cambia nada).
3. Reserva 2 de D-23: el estadístico de referencia del puntaje, los picos
   resueltos y su relación con el relleno, frente a los ocho de referencia.

Lee el motor de reglas tal como está en HEAD (`Rejilla`) y no lo modifica. Lee
`indice.csv`, así que se corre después del embudo. No usa etiquetas.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import sys
from collections import Counter, defaultdict
from statistics import median

from backend.preprocesamiento import procesar
from backend.preprocesamiento.conversion import PORCENTAJE, TRANSMITANCIA_MINIMA
from backend.preprocesamiento.lector import leer
from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.dataset.descargar_chemotion import DESTINO
from herramientas.dataset.embudo_chemotion import (
    INDICE,
    PASA,
    adjuntos,
    commit_atado,
    recibir_archivo,
    tipo_adjunto,
)
from herramientas.dataset.estadistica import cuantil, percentil_de, spearman
from herramientas.medir_fuerza import cargar_espectros, umbral_de_ut03
from motor_identificacion.reglas import Rejilla

CUANTILES = (0, 0.05, 0.25, 0.5, 0.75, 0.95, 1)
MEDIDAS = ("vara", "ruido", "picos", "picos_ventana", "picos_fuertes")


def medir(espectro, configuracion) -> dict:
    """Los números del detector, sin grupos ni puntajes."""
    reja = Rejilla(
        espectro.eje_cm1,
        espectro.intensidad,
        espectro.rango_medido_cm1,
        configuracion.motor.definicion_metodo.margen_linea_base_cm1,
    )
    desde, hasta = configuracion.validacion.rango_requerido_cm1
    piso = configuracion.motor.fuerza_minima_relativa["debil"].piso
    return {
        "vara": reja.escala_prominencia,
        "ruido": reja.ruido,
        "picos": len(reja.maximos),
        "picos_ventana": sum(desde <= reja.eje[i] <= hasta for i in reja.maximos),
        "picos_fuertes": sum(p >= piso for p in reja.prominencias.values()),
    }


def cargar() -> list[dict]:
    extra = {a["archivo"]: a for a in adjuntos()}
    with INDICE.open(encoding="utf-8", newline="") as flujo:
        filas = [f for f in csv.DictReader(flujo) if f["veredicto"] == PASA]
    for n, f in enumerate(filas, start=1):
        ruta = DESTINO / f"{f['archivo']}.jdx"
        contenido = recibir_archivo(ruta).contenido
        f["espectro"] = procesar(ruta.name, contenido).espectro
        f["tipo"] = tipo_adjunto(extra[f["archivo"]]["nombre_original"])
        f["analysis_id"] = extra[f["archivo"]]["analysis_id"]
        f["relleno"] = float(f["fraccion_relleno"])
        f["huella"] = hashlib.sha256(repr(f["espectro"].intensidad).encode()).hexdigest()
        # Seis decimales es el redondeo del contrato MOD-04 -> MOD-06.
        f["huella6"] = hashlib.sha256(
            repr([round(x, 6) for x in f["espectro"].intensidad]).encode()
        ).hexdigest()
        crudas = [y for _, y in leer(ruta.name, contenido).pares]
        f["y_min"], f["y_max"] = min(crudas), max(crudas)
        # El cero de un espectro normalizado es su punto menos absorbente: si
        # la mediana queda arriba, la línea base está arriba.
        medido = [
            y
            for x, y in zip(f["espectro"].eje_cm1, f["espectro"].intensidad)
            if f["espectro"].rango_medido_cm1[0] <= x <= f["espectro"].rango_medido_cm1[1]
        ]
        f["mediana"] = median(medido)
        if n % 1000 == 0:
            print(f"  ... {n}", file=sys.stderr, flush=True)
    return filas


def _cuantiles(valores, decimales=4) -> str:
    return "  ".join(f"p{100 * q:g}={cuantil(valores, q):.{decimales}f}" for q in CUANTILES)


# --------------------------------------------------------------------------- #


def redundancia(filas: list[dict]) -> list[dict]:
    """Imprime la redundancia y devuelve un representante por espectro."""
    print("\n## 1 · ¿Cuántos espectros distintos?")
    por_analisis = defaultdict(list)
    for f in filas:
        por_analisis[f["analysis_id"]].append(f)

    print("archivos por análisis:", Counter(len(v) for v in por_analisis.values()))
    diferencias = []
    for grupo in por_analisis.values():
        for i, a in enumerate(grupo):
            for b in grupo[i + 1 :]:
                d = max(
                    abs(x - y)
                    for x, y in zip(a["espectro"].intensidad, b["espectro"].intensidad)
                )
                diferencias.append((d, "+".join(sorted((a["tipo"], b["tipo"]))), a, b))
    tramos = Counter()
    for d, tipos, _, _ in diferencias:
        tramo = (
            "0 exacto"
            if d == 0
            else "<1e-6" if d < 1e-6
            else "<1e-3" if d < 1e-3
            else "<1e-2" if d < 1e-2
            else "<0.1" if d < 0.1
            else ">=0.1"
        )
        tramos[(tipos, tramo)] += 1
    print("pares dentro de un mismo análisis, por diferencia máxima del vector:")
    for clave, n in sorted(tramos.items(), key=lambda x: -x[1]):
        print("  ", clave, n)

    for d, tipos, a, b in diferencias:
        if d >= 0.1:
            print(f"   d={d:.3f} {tipos} {a['archivo']} y=[{a['y_min']:.4g}, {a['y_max']:.4g}]"
                  f" · {b['archivo']} y=[{b['y_min']:.4g}, {b['y_max']:.4g}]")

    print("vectores distintos (exacto):", len({f["huella"] for f in filas}))
    print("vectores distintos (a 6 decimales, el contrato):", len({f["huella6"] for f in filas}))

    por_huella = defaultdict(list)
    for f in filas:
        por_huella[f["huella6"]].append(f)
    mezclados = [
        g for g in por_huella.values() if len({f["inchikey"] for f in g}) > 1
    ]
    print(
        "mismo vector con InChIKey distinto:", len(mezclados), "vectores,",
        sum(len(g) for g in mezclados), "archivos",
    )
    for g in mezclados[:15]:
        print("   ", sorted({(f["inchikey"], f["analysis_id"]) for f in g}))
    entre = [
        g for g in por_huella.values()
        if len({f["analysis_id"] for f in g}) > 1 and len({f["inchikey"] for f in g}) == 1
    ]
    print("mismo vector en análisis distintos del mismo compuesto:", len(entre))

    # Representante: uno por análisis, el original antes que el derivado.
    orden = {".dx": 0, ".jdx": 1, ".peak.jdx": 2, ".edit.jdx": 3}
    unicos, vistos = [], set()
    for grupo in por_analisis.values():
        f = min(grupo, key=lambda f: (orden[f["tipo"]], f["archivo"]))
        if f["huella6"] not in vistos:
            vistos.add(f["huella6"])
            unicos.append(f)
    print(
        "representantes (uno por análisis, sin vectores repetidos):", len(unicos),
        "· InChIKey:", len({f["inchikey"] for f in unicos if f["inchikey"]}),
    )
    repetidos(unicos)
    por_compuesto = Counter(Counter(f["inchikey"] for f in unicos if f["inchikey"]).values())
    print("espectros por compuesto:", sorted(por_compuesto.items()))
    return unicos


def repetidos(unicos: list[dict]) -> None:
    """Espectros casi iguales en análisis distintos, con la tolerancia a la vista."""
    for f in unicos:
        f["cima"] = max(range(len(f["espectro"].intensidad)), key=f["espectro"].intensidad.__getitem__)
    cubetas = defaultdict(list)
    for f in unicos:
        cubetas[f["cima"]].append(f)
    for tolerancia in (1e-4, 1e-3, 1e-2):
        mismo, distinto, ejemplos = 0, 0, []
        for cima, grupo in cubetas.items():
            # La cima puede caer en el punto vecino: se compara con ella también.
            vecinos = grupo + cubetas.get(cima + 1, [])
            for i, a in enumerate(grupo):
                for b in vecinos[i + 1 :]:
                    if all(
                        abs(x - y) <= tolerancia
                        for x, y in zip(a["espectro"].intensidad, b["espectro"].intensidad)
                    ):
                        if a["inchikey"] == b["inchikey"]:
                            mismo += 1
                        else:
                            distinto += 1
                            ejemplos.append((a["analysis_id"], b["analysis_id"]))
        print(f"pares casi iguales entre representantes (dif. máx. <= {tolerancia:g}): "
              f"mismo InChIKey {mismo}, InChIKey distinto {distinto} {sorted(ejemplos)[:12]}")


def sanidad(filas: list[dict]) -> None:
    print("\n## 2 · Sanidad de la conversión (se observa, no se corrige)")
    pct = [f for f in filas if f["espectro"].unidad_original == PORCENTAJE]
    print("tratados como porcentaje:", len(pct), "· y_max", _cuantiles([f["y_max"] for f in pct], 2))
    print("  de ellos con y_max < 10 (¿fracción ruidosa tomada por %?):",
          [(f["archivo"], round(f["y_max"], 3), f["instrument"]) for f in pct if f["y_max"] < 10])
    fr = [f for f in filas if f["espectro"].unidad_original == "transmitancia"]
    print("tratados como fracción:", len(fr), "· y_max", _cuantiles([f["y_max"] for f in fr], 3),
          "· y_min", _cuantiles([f["y_min"] for f in fr], 3))
    print("  fracción con y_max > 1:", sum(f["y_max"] > 1 for f in fr),
          "· > 1.2:", sum(f["y_max"] > 1.2 for f in fr))
    tr = fr + pct
    recortados = [f for f in tr if f["y_min"] <= TRANSMITANCIA_MINIMA * (100 if f in pct else 1)]
    print("transmitancia <= mínimo (MOD-04 la recorta y sale absorbancia 6):", len(recortados))
    for f in recortados[:12]:
        print("   ", f["archivo"], f["y_min"], f["tipo"], f["instrument"], "mediana norm.", round(f["mediana"], 4))
    print("mediana del vector normalizado:", _cuantiles([f["mediana"] for f in filas]))
    altos = [f for f in filas if f["mediana"] > 0.5]
    print("mediana > 0.5 (línea base arriba, ¿unidad mal declarada?):", len(altos),
          Counter((f["unidad_original"], f["instrument"]) for f in altos).most_common(12))
    for f in altos:
        print("   ", f["archivo"], f["tipo"], f["analysis_id"], f"y=[{f['y_min']:.4g}, {f['y_max']:.4g}] mediana={f['mediana']:.3f}")
    bajos = [f for f in filas if f["mediana"] < 0.01]
    print("mediana < 0.01 (un punto domina la escala):", len(bajos))


def reserva2(unicos: list[dict]) -> None:
    cfg = obtener_configuracion()
    for f in unicos:
        f |= medir(f["espectro"], cfg)
    refs = {n: medir(e, cfg) for n, e in cargar_espectros().items()}

    print("\n## 3 · Reserva 2 de D-23 (n =", len(unicos), "espectros, uno por análisis)")
    for m in MEDIDAS:
        d = 5 if m in ("vara", "ruido") else 1
        poblacion = [f[m] for f in unicos]
        print(f"\n[{m}] Chemotion  {_cuantiles(poblacion, d)}")
        print(f"[{m}] los ocho   {_cuantiles([r[m] for r in refs.values()], d)}")
        print("   razón de medianas Chemotion / ocho:",
              round(cuantil(poblacion, .5) / cuantil([r[m] for r in refs.values()], .5), 3))
        print("   ", {n: (round(r[m], d), f"P{percentil_de(r[m], poblacion):.0f}") for n, r in refs.items()})
        minimo, maximo = min(r[m] for r in refs.values()), max(r[m] for r in refs.values())
        print(f"   Chemotion por encima del mayor de los ocho: {100 * sum(p > maximo for p in poblacion) / len(poblacion):.1f} %"
              f" · por debajo del menor: {100 * sum(p < minimo for p in poblacion) / len(poblacion):.1f} %")

    iguales = sum(f["vara"] == f["ruido"] for f in unicos)
    print()
    print(f"vara == ruido (manda el piso de ruido): Chemotion {iguales}/{len(unicos)}"
          f" · los ocho {sum(r['vara'] == r['ruido'] for r in refs.values())}/8")
    print("razón vara/ruido: Chemotion", _cuantiles([f["vara"] / f["ruido"] for f in unicos], 2))
    print("                  los ocho ", _cuantiles([r["vara"] / r["ruido"] for r in refs.values()], 2))

    u = umbral_de_ut03()
    print(f"\nprominencia que hace falta para que la evidencia alcance {u} (= vara·u/(1-u)):")
    k = u / (1 - u)
    print("   Chemotion", _cuantiles([k * f["vara"] for f in unicos]))
    print("   los ocho ", _cuantiles([k * r["vara"] for r in refs.values()]))

    print("\ncorrelaciones de rangos (Spearman):")
    def rho(a, b, g=unicos):
        s = spearman([f[a] for f in g], [f[b] for f in g])
        return "constante" if s is None else f"{s:+.3f}"
    for a, b in (("relleno", "vara"), ("relleno", "ruido"), ("relleno", "picos"),
                 ("picos", "vara"), ("picos_fuertes", "vara"), ("ruido", "vara")):
        print(f"   {a:>14} vs {b:<6} {rho(a, b)}")

    print("\nvara y picos por nivel de relleno:")
    grupos = defaultdict(list)
    for f in unicos:
        grupos[f["relleno"]].append(f)
    for r, g in sorted(grupos.items()):
        print(f"   relleno {r:.6f} n={len(g):>5} vara mediana {median(x['vara'] for x in g):.5f} "
              f"ruido {median(x['ruido'] for x in g):.5f} picos {median(x['picos'] for x in g):.0f} "
              f"instrumentos {Counter(x['instrument'] for x in g).most_common(3)}")

    print("\npor modo de medición declarado (archivo representante):")
    grupos = defaultdict(list)
    for f in unicos:
        grupos[f["modo_medicion"]].append(f)
    for r, g in sorted(grupos.items()):
        print(f"   {r:<12} n={len(g):>5} " + " ".join(f"{m}={median(x[m] for x in g):.5g}" for m in MEDIDAS))

    print("\nvara por cuartil de densidad (picos_fuertes):")
    orden = sorted(unicos, key=lambda f: f["picos_fuertes"])
    cuarto = len(orden) // 4
    for i in range(4):
        g = orden[i * cuarto : (i + 1) * cuarto if i < 3 else None]
        print(f"   Q{i + 1} picos_fuertes {g[0]['picos_fuertes']}–{g[-1]['picos_fuertes']} "
              f"vara mediana {median(f['vara'] for f in g):.5f}")


def main() -> None:
    logging.disable(logging.CRITICAL)
    sys.stdout.reconfigure(encoding="utf-8")
    print("commit:", commit_atado())
    filas = cargar()
    unicos = redundancia(filas)
    sanidad(filas)
    reserva2(unicos)


if __name__ == "__main__":
    main()
