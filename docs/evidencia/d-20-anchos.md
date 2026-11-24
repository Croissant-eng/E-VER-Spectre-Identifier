# D-20 · Medición de los dos umbrales de ancho (T-15a)

Evidencia de la medición que D-20 pide para `ancho_media_altura_umbral_cm1`
(regla **R-1**) y `ancho_pico_agudo_max_cm1` (regla **R-4**). Los dos umbrales
siguen en `null` en `parametros.json`: **son SUPUESTO hasta que el equipo
apruebe un valor.**

Se reproduce desde la raíz del repositorio con:

```bash
python -m herramientas.medir_anchos
```

## Método

- Los cuatro espectros pasan por el **pipeline real de MOD-04**
  (`backend.preprocesamiento.procesar`), el mismo que usa producción. Se mide
  sobre el vector ya normalizado 0–1, no sobre el archivo crudo: el motor nunca
  ve el archivo crudo, y medir en otra escala daría un umbral que no sirve.
- Las regiones se le **piden a UT-01**; no están escritas en la herramienta.
- **Línea base local.** La normalización de MOD-04 es global (el mínimo de todo
  el espectro va a 0), así que la media altura de cada banda se mide contra el
  mínimo de su propio vecindario (la región ±200 cm⁻¹, recortada al tramo que
  el archivo de verdad midió). Medirla contra cero infla cualquier banda que se
  asiente sobre señal de fondo.
- Los cruces se **interpolan** entre puntos de la rejilla: el paso es de unos
  3.5 cm⁻¹ y sin interpolar el ancho vendría cuantizado en múltiplos de eso.
- Solo se recorre el tramo dentro de `rango_medido_cm1`. Fuera de ahí la
  intensidad vale 0 por relleno, y un 0 de relleno no es absorbancia cero.

## R-1 · O–H ancho vs N–H angosto → se propone 175 cm⁻¹

Los dos pares de calibración de D-20, al ancho a media altura:

| Compuesto | Archivo | Grupo | Pico | **Ancho a media altura** |
|---|---|---|---|---|
| 1-butanol | `71-36-3-IR(1-Butanol).jdx` | GF-01 · O–H | 3349.0 | **408.9 cm⁻¹** |
| Anilina | `62-53-3-IR.jdx` | GF-02 · N–H | 3359.5 | **74.0 cm⁻¹** |

**Verificación añadida.** R-1 actúa en el traslape 3300–3500, así que la banda
se midió también en la región del *otro* grupo, y con un tercer O–H —el de
ácido, que es el caso extremo:

| Compuesto | Tiene | Medido en GF-01 (3200–3550) | Medido en GF-02 (3300–3500) |
|---|---|---|---|
| 1-butanol | O–H | 408.9 | 404.0 |
| Ácido benzoico | O–H de ácido | 965.9 | 1099.6 |
| Anilina | N–H | 74.0 | 74.0 |

El ancho **no depende de en qué región se mida** (anilina da el mismo número en
las dos; butanol varía 1 %), que es justo lo que hace falta para una regla que
opera en la zona traslapada. Y el O–H de ácido queda todavía más ancho, en la
dirección correcta.

**Umbral propuesto: 175 cm⁻¹.** Es la media geométrica de 74.0 y 404.0
(172.9, redondeada). Margen: **2.4× por encima** del N–H angosto y **2.3× por
debajo** del O–H más angosto de los medidos. Se redondea porque la precisión
real son dos compuestos, no tres cifras significativas.

## R-4 · pico agudo vs hombro ancho → sin umbral todavía

Los dos pares de calibración, al ancho a media altura:

| Compuesto | Archivo | Pico en 2850–2960 | **Ancho a media altura** |
|---|---|---|---|
| Ciclohexano | `110-82-7-IR(Cyclohexane).jdx` | 2926.7 | **22.9 cm⁻¹** |
| Ácido benzoico | `65-85-0-IR.jdx` | 2873.9 | **305.3 cm⁻¹** |

Vistos solos, estos dos números invitan a poner el umbral alrededor de 84 cm⁻¹
(su media geométrica). **Sería un error**, y por eso se midió la misma zona en
los demás espectros reales disponibles:

| Compuesto | ¿Tiene C–H alifático? | Ancho a media altura |
|---|---|---|
| Ciclohexano | Sí | 22.9 |
| Ciclohexeno | Sí | 44.7 |
| **Acetona** | **Sí** | **145.4** |
| **Tolueno** | **Sí** | **184.4** |
| **1-butanol** | **Sí** | **152.9** |
| Ácido benzoico | No | 305.3 |
| Anilina | No | 760.5 |

Tres compuestos que **sí** tienen C–H alifático miden entre 145 y 184 cm⁻¹: muy
por encima de ese 84, y a menos de un factor 2 del ácido benzoico. Un umbral
sacado solo de los dos archivos prescritos habría negado el C–H alifático de la
acetona y del tolueno. **A media altura, la medida no separa las dos clases**:
cuando la banda es débil, el nivel de media altura queda cerca de la línea base
y la caminata hacia afuera se funde con la estructura vecina (en el tolueno
cruza en 3101.9 cm⁻¹, ya dentro del C–H aromático).

### Lo que sí separa: medir el ancho al 80 % de la altura del pico

Mismo recorrido, mismo pipeline, pero el nivel se pone al 80 % de la altura del
pico en vez de al 50 %:

| Compuesto | ¿C–H alifático? | @50 % | **@80 %** |
|---|---|---|---|
| Ciclohexano | Sí | 22.9 | **12.6** |
| Ciclohexeno | Sí | 44.7 | **22.1** |
| Tolueno | Sí | 184.4 | **16.5** |
| Acetona | Sí | 145.4 | **19.5** |
| 1-butanol | Sí | 152.9 | **118.3** |
| Ácido benzoico | No | 305.3 | **216.5** |
| Anilina | No | 760.5 | **639.2** |

Al 80 % los siete espectros quedan **bien clasificados** por un solo corte: los
cinco que tienen C–H alifático caen entre 12.6 y 118.3, y los dos que no lo
tienen quedan en 216.5 y 639.2. El corte natural es la media geométrica del
hueco, **160 cm⁻¹**, que deja **1.35× de margen a cada lado**.

**Por qué el valor se queda en `null` de todos modos.** Medir al 80 % en vez de
a media altura **cambia la definición del ancho**, y eso es decidir cómo R-4
mide, que es trabajo de **T-15b**, no de esta medición. Lo que T-15a entrega es
el hallazgo y los números; el umbral entra a `parametros.json` cuando el equipo
apruebe **las dos cosas**: la definición y el valor.

## Pendiente del equipo

| Parámetro | Valor propuesto | Estado |
|---|---|---|
| `tolerancia_banda_puntual_cm1` | 15 | Ya escrito: es el valor de arranque que propone D-20, recalibrable |
| `ancho_media_altura_umbral_cm1` | **175** | `null` · esperando aprobación |
| `ancho_pico_agudo_max_cm1` | **160**, medido al 80 % de la altura | `null` · esperando aprobación de la definición **y** del valor |

Mientras los dos sigan en `null`, T-15b no puede aplicar R-1 ni R-4. Es
intencional: mejor detenerse que arrancar con un número inventado.
