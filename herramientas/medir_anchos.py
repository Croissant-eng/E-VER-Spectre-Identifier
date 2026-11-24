"""Mide los dos umbrales de ancho que D-20 deja como SUPUESTO (T-15a).

Qué mide y por qué, en una línea cada uno:

- **R-1** necesita el corte entre el O–H ancho y el N–H angosto. Se mide el
  ancho a media altura de la banda principal en **1-butanol** (O–H ancho por
  puentes de hidrógeno) y en **anilina** (N–H angosto, dos picos).
- **R-4** necesita el corte entre un pico agudo y resuelto y un hombro ancho.
  Se mide en la zona de GF-03 en **ciclohexano** (C–H alifático agudo de
  verdad) y en **ácido benzoico** (la envolvente ancha de O–H sobre esa misma
  zona, en un compuesto que **no tiene** C–H alifático).

Tres decisiones de método, que son las que hacen que el número sirva:

1. **Se mide sobre el espectro ya procesado por MOD-04**, llamando a la misma
   función que usa producción. Medir sobre el archivo crudo daría un umbral en
   otra escala, y el motor nunca ve el archivo crudo.
2. **Las regiones se le piden a UT-01**, no se escriben aquí. Un número de
   región en este archivo sería el defecto que la regla 1 de CLAUDE.md prohíbe.
3. **Línea base local, no cero.** La normalización de MOD-04 es global (el
   mínimo de todo el espectro va a 0), así que la media altura de una banda se
   mide contra el mínimo de su propio vecindario. Medirla contra cero infla el
   ancho de cualquier banda que se asiente sobre señal de fondo.

Esto es **instrumental de medición, no MOD-06**: no detecta picos para
identificar nada ni calcula scores. T-15b escribe su propia detección de picos
dentro del motor y **no debe importar de aquí** (la aplicación nunca importa de
`herramientas/`).

Uso:

    python -m herramientas.medir_anchos
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from backend.preprocesamiento import procesar
from backend.utilerias.catalogo import obtener as obtener_catalogo

RAIZ = Path(__file__).resolve().parents[1]
CARPETA_REFERENCIA = RAIZ / "datos" / "referencia"

#: Los espectros ya descargados se guardan en latin-1, como los lee el resto de
#: las pruebas de archivos reales.
CODIFICACION = "latin-1"

#: Cuánto se extiende el vecindario a cada lado de la región para estimar la
#: línea base local, en cm⁻¹. No es un rango espectral de ningún grupo: es un
#: parámetro de esta medición. Lo bastante ancho para salir de la banda y lo
#: bastante angosto para no cruzar media huella dactilar.
MARGEN_CONTEXTO_CM1 = 200.0


@dataclass(frozen=True)
class Medicion:
    """El resultado de medir una banda, con todo lo que hace falta para auditarlo."""

    archivo: str
    compuesto: str
    grupo: str
    region_cm1: tuple[float, float]
    pico_cm1: float
    altura_pico: float
    linea_base: float
    media_altura: float
    cruce_alto_cm1: float
    cruce_bajo_cm1: float
    ancho_cm1: float
    saturado: bool

    def linea(self) -> str:
        marca = "  (SATURADO: no cruzó la media altura dentro de lo medido)"
        return (
            f"{self.compuesto:<16} {self.grupo}  "
            f"región {self.region_cm1[0]:.0f}–{self.region_cm1[1]:.0f}  "
            f"pico {self.pico_cm1:7.1f}  "
            f"base {self.linea_base:.4f}  alt {self.altura_pico:.4f}  "
            f"mitad {self.media_altura:.4f}  "
            f"cruces {self.cruce_alto_cm1:7.1f}→{self.cruce_bajo_cm1:7.1f}  "
            f"ANCHO {self.ancho_cm1:7.1f} cm⁻¹"
            + (marca if self.saturado else "")
        )


def _procesar_archivo(archivo: str):
    """Pasa un espectro de referencia por el pipeline real de MOD-04."""
    ruta = CARPETA_REFERENCIA / archivo
    if not ruta.is_file():
        raise SystemExit(
            f"falta {archivo} en datos/referencia; bájelo con "
            "«python -m herramientas.descargar_espectros_nist»"
        )

    resultado = procesar(ruta.name, ruta.read_text(encoding=CODIFICACION))
    if not resultado.valido or resultado.espectro is None:
        raise SystemExit(
            f"MOD-04 rechazó {archivo}: {resultado.codigo} · {resultado.detalle}"
        )
    return resultado.espectro


def _indices_en(eje: tuple[float, ...], desde: float, hasta: float) -> list[int]:
    return [i for i, onda in enumerate(eje) if desde <= onda <= hasta]


def _cruce(
    eje: tuple[float, ...],
    intensidad: tuple[float, ...],
    inicio: int,
    paso: int,
    nivel: float,
    limites: tuple[int, int],
) -> tuple[float, bool]:
    """Camina desde el pico hasta que la señal baja del nivel de media altura.

    Devuelve el número de onda del cruce, interpolado entre los dos puntos de la
    rejilla, y si la caminata se agotó sin cruzar (saturada). Interpolar importa:
    el paso de la rejilla es de unos 3.5 cm⁻¹, y sin interpolar el ancho vendría
    cuantizado en múltiplos de eso.
    """
    primero, ultimo = limites
    indice = inicio
    while primero <= indice + paso <= ultimo:
        siguiente = indice + paso
        if intensidad[siguiente] <= nivel:
            anterior, posterior = intensidad[indice], intensidad[siguiente]
            amplitud = anterior - posterior
            fraccion = 0.0 if amplitud == 0 else (anterior - nivel) / amplitud
            return (
                eje[indice] + (eje[siguiente] - eje[indice]) * fraccion,
                False,
            )
        indice = siguiente
    return eje[indice], True


def medir(archivo: str, compuesto: str, grupo: str) -> Medicion:
    """Ancho a media altura de la banda principal de `grupo` en ese archivo."""
    espectro = _procesar_archivo(archivo)
    eje, intensidad = espectro.eje_cm1, espectro.intensidad
    region = obtener_catalogo().por_id(grupo).region_cm1

    # Solo se mira el tramo que el archivo de verdad midió: fuera de ahí la
    # intensidad vale 0 por relleno, y un 0 de relleno no es absorbancia cero.
    medido_min, medido_max = espectro.rango_medido_cm1
    utiles = _indices_en(eje, medido_min, medido_max)
    limites = (min(utiles), max(utiles))

    en_region = [i for i in _indices_en(eje, *region) if i in set(utiles)]
    if not en_region:
        raise SystemExit(f"{archivo}: la región de {grupo} quedó fuera de lo medido")

    pico = max(en_region, key=lambda i: intensidad[i])

    contexto = _indices_en(
        eje,
        max(region[0] - MARGEN_CONTEXTO_CM1, medido_min),
        min(region[1] + MARGEN_CONTEXTO_CM1, medido_max),
    )
    linea_base = min(intensidad[i] for i in contexto)

    altura = intensidad[pico] - linea_base
    nivel = linea_base + altura / 2

    # El eje va de mayor a menor número de onda: índice que crece es onda que
    # baja. Hacia índices menores se sube en cm⁻¹.
    alto, saturado_alto = _cruce(eje, intensidad, pico, -1, nivel, limites)
    bajo, saturado_bajo = _cruce(eje, intensidad, pico, +1, nivel, limites)

    return Medicion(
        archivo=archivo,
        compuesto=compuesto,
        grupo=grupo,
        region_cm1=region,
        pico_cm1=eje[pico],
        altura_pico=intensidad[pico],
        linea_base=linea_base,
        media_altura=nivel,
        cruce_alto_cm1=alto,
        cruce_bajo_cm1=bajo,
        ancho_cm1=alto - bajo,
        saturado=saturado_alto or saturado_bajo,
    )


#: Los cuatro pares de calibración de D-20. El grupo dice qué región del
#: catálogo se mide; el compuesto, contra qué se está midiendo.
CALIBRACION = {
    "R-1 · O–H ancho vs N–H angosto": [
        ("71-36-3-IR(1-Butanol).jdx", "1-butanol", "GF-01"),
        ("62-53-3-IR.jdx", "anilina", "GF-02"),
    ],
    "R-4 · pico agudo vs hombro ancho": [
        ("110-82-7-IR(Cyclohexane).jdx", "ciclohexano", "GF-03"),
        ("65-85-0-IR.jdx", "ácido benzoico", "GF-03"),
    ],
}


def main() -> None:
    # La consola de Windows llega en cp1252 y no sabe escribir «→» ni «cm⁻¹».
    # Sin esto, el script muere al imprimir en vez de al medir.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    todas: list[Medicion] = []
    for regla, casos in CALIBRACION.items():
        print(f"\n{regla}")
        print("-" * len(regla))
        for archivo, compuesto, grupo in casos:
            medicion = medir(archivo, compuesto, grupo)
            todas.append(medicion)
            print(medicion.linea())

    print("\nResumen en JSON (para docs/evidencia/):")
    print(
        json.dumps(
            [
                {
                    "compuesto": m.compuesto,
                    "archivo": m.archivo,
                    "grupo": m.grupo,
                    "pico_cm1": round(m.pico_cm1, 1),
                    "ancho_cm1": round(m.ancho_cm1, 1),
                    "saturado": m.saturado,
                }
                for m in todas
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
