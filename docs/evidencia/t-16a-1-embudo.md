# T-16a-1 · El embudo de Chemotion IR

**Commit al que están atados todos los números:** `962b2853b9bec161c4f7b3293ca1b93be728837b`
**Fecha:** 24/11/2026 · **Python** 3.14.5 · **RDKit** 2026.09.2 · **N** = 1024 (UT-03)
**Suma de `indice.csv`** (SHA-256): `46025293522900311dafd768ef4032a5ac855d472e1a0d880d784e4f72a3940d`; dos corridas dan el mismo archivo y el mismo reporte.

Los scripts comprueban que `backend/`, `motor_identificacion/` y `datos/catalogo/` estén idénticos a HEAD antes de contar. MOD-03, MOD-04, el motor de reglas, UT-01 y UT-03 **no se modificaron** (en UT-03, solo la nota del paso 0). Aquí no hay etiquetas, ni split, ni entrenamiento.

```bash
python -m herramientas.dataset.embudo_chemotion    # secciones 1 y 2 (necesita RDKit)
python -m herramientas.dataset.medir_reserva2      # secciones 3 y 4
```

---

## 0. El paquete

4 183 archivos y `meta_data.json`, con correspondencia 1 a 1. Los 8 md5 del manifiesto coinciden. **Cuadra**, con dos precisiones:

- Los archivos son UUID **sin extensión**; la de `meta_data.json` es casi siempre `.dx`. Se pasaron a MOD-03 como `<uuid>.jdx`. Con su nombre real, MOD-03 rechazaría los **2 176** `.dx` (52 %) por extensión.
- El metadato tiene **2 116 registros** (análisis), no 4 183. Lo explica la sección 3.

## 1. El embudo

| Etapa | Archivos | Se caen | Análisis | SMILES distintos | InChIKey |
|---|---:|---:|---:|---:|---:|
| En el paquete | 4 183 | — | 2 116 | 1 926 | 1 922 |
| `cano_smiles` presente y parseable | 4 181 | 2 | 2 115 | 1 925 | 1 922 |
| Pasan MOD-03 | 4 172 | 9 | 2 113 | 1 924 | 1 921 |
| **Pasan MOD-04** | **4 168** | 4 | **2 113** | 1 924 | **1 921** |
| *Espectros distintos (sección 3)* | | | ***2 086*** | | ***1 915*** |

MOD-02 (tamaño y decodificación) no rechazó ninguno. Ningún módulo levantó una excepción.

| Veredicto | n | Causa |
|---|---:|---|
| `PASA` | 4 168 | |
| `MOD-03:ESTRUCTURA_INVALIDA` | 7 | Traen `##XYPOINTS=`; UT-03 solo admite `##XYDATA=` y `##PEAK TABLE=` |
| `MOD-03:ESTRUCTURA_INVALIDA` | 1 | `##FIRSTX=` no trae un número |
| `MOD-03:RANGO_INSUFICIENTE` | 1 | Cubre 202–800: es UV-Vis en nanómetros, no IR |
| `MOD-04:SIN_SENAL` | 4 | Intensidad constante. Son derivados; su original `.dx` sí pasa |
| `SMILES_NO_PARSEABLE` | 2 | Un complejo de renio, `[O]#C[Re](C#[O])(C#[O])Br.…` (original y derivado) |

- MOD-03 visto solo, sobre los 4 183: 9 rechazos. MOD-04 visto solo, sobre los 4 174 que pasan MOD-03: 4.
- `UNIDAD_NO_SOPORTADA`, `UNIDAD_SIN_DECLARAR`, `DATOS_ILEGIBLES` y `PUNTOS_INSUFICIENTES`: **cero**.
- **Solo 3 de 2 116 análisis se pierden por completo:** el UV-Vis, el de renio y uno de hierro con `##XYPOINTS=`.
- 3 SMILES (6 archivos) parsean pero RDKit no les da InChIKey: pasan, con la columna vacía.

## 2. Las cuatro distribuciones

### 2.1 `instrument` y `kind` (verificación 1 de D-12)

`kind`, sobre los 4 183: IR 3 999 (95.6 %) · ATR-FTIR 158 (3.8 %) · FTIR 24 (0.6 %) · UV-VIS-NIR 2 (0.05 %).

`instrument` es texto libre con 56 valores más vacíos. Agrupado **solo para leerlo** (el índice guarda el original), por análisis superviviente:

| Familia | Análisis |
|---|---:|
| Bruker Alpha, sin decir módulo | 1 061 |
| Bruker Alpha, dice ATR | 587 |
| Bruker IFS 88 | 145 |
| «IR», sin más | 93 |
| Bruker Alpha-T | 45 |
| Shimadzu IRTracer-100 | 44 |
| **Equipo que no es IR (RMN, masas) o texto sin sentido** | **36** |
| (vacío) | 35 |
| Bruker Alpha P | 27 |
| Jasco FT/IR | 22 |
| Perkin Elmer | 14 |
| Otros | 4 |

**Fase:** nada en `instrument`, `kind` ni en las cabeceras declara fase gas. Donde se declara el modo es ATR, que se hace con la muestra en contacto con el cristal, o sea condensada. Para el 9.3 % sin modo declarado, la fase es `SUPUESTO`. Los 36 de «RMN o masas» traen cabecera `INFRARED SPECTRUM` y eje en cm⁻¹: `SUPUESTO` que es un campo mal llenado.

### 2.2 `modo_medicion`

| | ATR | transmisión | desconocido |
|---|---:|---:|---:|
| Archivos, los 4 183 | 2 526 (60.4 %) | 0 | 1 657 (39.6 %) |
| Archivos que pasan | 2 520 (60.5 %) | 0 | 1 648 (39.5 %) |
| **Análisis que pasan, juntando sus archivos** | **1 916 (90.7 %)** | **0** | **197 (9.3 %)** |

- Se dedujo **solo** de `instrument` y de las cabeceras del propio archivo, y solo si lo dicen. `YUNITS=TRANSMITTANCE` no cuenta como modo, y «Alpha-P» tampoco.
- El 39.5 % por archivo es engañoso: casi todo son **derivados** que perdieron la cabecera `##SAMPLING PROCEDURE=`; su original sí la trae.
- **No usado en la columna**, pero existe: el campo `content` (texto del autor). En los 197 análisis desconocidos dice ATR en **192**, KBr en 3 y nada en 2. Otros 6 archivos declaran ATR en su cabecera y KBr en `content`: se contradicen.

### 2.3 `##YUNITS=`

| | `TRANSMITTANCE` | `ABSORBANCE` |
|---|---:|---:|
| Los 4 183 | 4 178 | 5 |
| Pasan | 4 165 | 3 |
| Rechazados | 13 | 2 (por `##XYPOINTS=` o `##FIRSTX=`, no por unidad) |

MOD-04 trató 4 053 como fracción, 112 como porcentaje y 3 como absorbancia. Los 112 tienen máximos entre 90.8 y 246, así que ninguno es una fracción tomada por porcentaje.

**Para la decisión abierta de §12:** Chemotion **no aporta ningún caso** de unidad no admitida. Eso **no** debilita el argumento: `SUPUESTO`, el conversor del repositorio uniformó la etiqueta al importar. El único archivo fuera de IR se cayó por **rango**, no por unidad. El caso sigue siendo el del estireno.

### 2.4 `fraccion_relleno`

| Relleno | Puntos de 1024 | Archivos | |
|---:|---:|---:|---|
| 0.000977 | 1 | 4 030 (96.7 %) | el archivo termina en 3997 y la rejilla en 4000 |
| 0 | 0 | 83 (2.0 %) | |
| 0.014648 | 15 | 6 | corte en 450 |
| 0.028320 | 29 | 4 | corte en 500 |
| 0.041992 | 43 | 1 | corte en 550 |
| 0.070312 | 72 | 44 (1.1 %) | corte en 650 |

Máximo **7 %**. El 90 % de los archivos mide 374–3997 cm⁻¹. La hipótesis de un corte ATR generalizado en 650 **no se cumple**: son 44 archivos, todos Jasco.

---

## 3. Cuántos espectros hay de verdad

**Los 4 168 archivos son 2 086 espectros distintos, de 1 915 compuestos con InChIKey.**

Chemotion guarda, junto a cada original (`.dx`), una versión derivada (`.edit.jdx` / `.peak.jdx`) con los mismos datos y una tabla de picos. Comparando los vectores de MOD-04 **dentro de cada análisis** (2 076 pares):

| Diferencia máxima entre los dos vectores | Pares |
|---|---:|
| Idénticos o < 10⁻⁶ | 2 002 |
| < 10⁻³ | 70 |
| ≥ 0.1 (hallazgo H-3) | 4 |

- De 2 113 análisis quedan 2 086 vectores distintos: **27 pares de análisis** comparten vector exacto. 19 son del mismo compuesto y **8 pares tienen InChIKey distinto** — el mismo espectro atribuido a dos moléculas. En al menos una de las dos, la estructura no corresponde (o los dos difieren solo en algo que el InChIKey distingue y el IR no).
- Fuera de esos, ningún par de análisis se parece a menos de 0.01.
- Espectros por compuesto: 1 777 compuestos con uno; 138 con entre 2 y 6.

## 4. Reserva 2 de D-23

Se midió sobre los **2 086** espectros (uno por análisis, el original antes que el derivado), no sobre una submuestra. El motor se leyó (`Rejilla`), no se tocó, y **no se llamó a `evaluar`**: no hay puntajes ni grupos.

- **vara** = `escala_prominencia`: la mediana de las prominencias sin la mayor, con el ruido como piso. Es la referencia con la que el puntaje divide.
- **ruido** = mediana del salto entre puntos vecinos.

| | | p0 | p5 | p25 | **p50** | p75 | p95 | p100 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **vara** | Chemotion | 0.0004 | 0.0012 | 0.0021 | **0.0031** | 0.0045 | 0.0082 | 0.0367 |
| | los ocho | 0.0007 | 0.0009 | 0.0013 | **0.0035** | 0.0093 | 0.0176 | 0.0207 |
| **ruido** | Chemotion | 0.0004 | 0.0012 | 0.0019 | **0.0028** | 0.0038 | 0.0065 | 0.0224 |
| | los ocho | 0.0001 | 0.0001 | 0.0003 | **0.0006** | 0.0008 | 0.0028 | 0.0034 |
| **vara ÷ ruido** | Chemotion | 1.00 | 1.00 | 1.00 | **1.11** | 1.24 | 1.45 | 2.22 |
| | los ocho | 1.27 | 1.68 | 5.36 | **8.42** | 9.87 | 18.31 | 21.03 |
| **picos** (todos los máximos) | Chemotion | 60 | 140 | 162 | **175** | 187 | 207 | 289 |
| | los ocho | 44 | 46 | 53 | **58.5** | 61 | 73 | 76 |
| **picos en 1400–3700** | Chemotion | 40 | 91 | 109 | **120** | 130 | 146 | 203 |
| | los ocho | 24 | 27 | 33 | **37** | 41 | 49 | 52 |
| **picos con prominencia ≥ piso débil (0.029)** | Chemotion | 9 | 18 | 26 | **31** | 37 | 48 | 153 |
| | los ocho | 5 | 6 | 10 | **15.5** | 18 | 21 | 22 |

**Dónde cae cada uno de los ocho en la distribución de la vara de Chemotion:** acetonitrilo P0 · acetona P3 · ciclohexano P7 · ciclohexeno P54 · tolueno P60 · 1-butanol P95 · anilina P98 · ácido benzoico P100.

**Correlaciones de rangos (Spearman, n = 2 086):**

| | ρ |
|---|---:|
| relleno – vara | −0.030 |
| relleno – ruido | −0.039 |
| relleno – picos | −0.129 |
| picos ≥ piso – vara | **+0.643** |
| picos – vara | +0.303 |
| ruido – vara | **+0.976** |

### Qué dice

1. **La vara no está deflactando los scores frente a los ocho.** La mediana es 0.90 veces la de los ocho; solo el 0.3 % de Chemotion supera al mayor de ellos.
2. **El mecanismo sí existe dentro de Chemotion:** la vara crece con la densidad (+0.643); del cuartil menos denso al más denso pasa de 0.0021 a 0.0053 (×2.5). Cautela: parte de esa correlación puede ser que un espectro de poco contraste tiene a la vez más ruido y más baches por encima del piso.
3. **La vara mide cosas distintas en los dos conjuntos.** En los ocho vale 8 veces el ruido: mide bandas secundarias reales. En Chemotion vale 1.1 veces el ruido, y en el 28 % **es** el piso de ruido (585 de 2 086; 0 de 8 en los ocho). Que las medianas se parezcan es coincidencia.
4. **El riesgo que asoma es el contrario al de la reserva 2.** Para que la evidencia llegue a 0.60 basta una prominencia de 1.5 × vara ≈ **0.0047** (mediana de Chemotion), seis veces menos que el piso débil (0.029). El espectro mediano tiene **31** picos por encima de ese piso, contra 15.5 en los ocho; y 120 máximos en la ventana, contra 37. La evidencia casi no discrimina y queda todo en manos de los pisos. Apunta a **falsos positivos**, pero **es una hipótesis**: sin etiquetas no se puede decir si esos picos son química.
5. **El relleno no interviene.** Por construcción: `Rejilla` calcula vara y ruido solo dentro de `rango_medido_cm1`. Y empíricamente apenas hay variación que correlacionar (2 014 de 2 086 tienen el mismo valor). Los 22 con relleno de 7 % tienen una vara más alta (0.0055), pero los 22 son Jasco: no se puede separar relleno de instrumento, y lo que el código hace apunta al instrumento.
6. **`SUPUESTO`:** los ocho son digitalizaciones de papel (Coblentz), curvas más suaves que un espectro digital. La diferencia en número de picos mezcla densidad química con suavizado y aquí no se puede separar.

> **Aviso para T-16a-2.** Esta medición tocó **todo** el conjunto, incluidos los espectros que acaben en el split de prueba. Es descriptiva y sin etiquetas, pero **no debe usarse para mover pisos ni cortes**: eso se hace sobre validación (D-15.2).

---

## 5. Hallazgos (se reportan, no se corrigieron)

| | Hallazgo | Alcance |
|---|---|---|
| **H-1** | El tamaño real es la mitad: 2 086 espectros, 1 915 compuestos | D-12 dice «4 183 espectros» |
| **H-2** | **8 pares de análisis** comparten el mismo espectro con InChIKey distinto | Ruido de etiqueta garantizado, y fuga entre splits aunque se parta por InChIKey |
| **H-3** | **8 archivos derivados tienen un punto con T = 0 que el original no tiene.** En 4, el derivado es el original **menos una constante** (p. ej. 0.0168–0.398 → 0–0.381); en los otros 4, los que vienen de `##XYPOINTS=`, es un primer punto espurio. MOD-04 recorta T = 0 a 10⁻⁶ (absorbancia 6) y **los acepta** | En **6** ese punto se queda con el 1.0 de la escala y todo lo demás queda por debajo de 0.39. En los otros 2 el cero cae fuera de la rejilla. De los 6, 3 tienen un original sano; **3 son la única copia que sobrevive de su análisis**, porque el original cayó por `##XYPOINTS=` |
| **H-4** | `##XYPOINTS=` no está en las etiquetas de datos de UT-03: 7 rechazos de espectros IR legítimos. MOD-04 tampoco lo reconoce | 7 archivos; los usuarios con el mismo conversor verían lo mismo |
| **H-5** | `.dx` no se admite. Es la extensión con que vienen los originales, 2 176 de 4 183 | No afecta al dataset; sí a un usuario de estos equipos. Decisión ya tomada en Requerimientos |
| **H-6** | 19 archivos con la mediana del vector normalizado > 0.5: poco contraste o línea base alta, con transmitancias de hasta 1.15 | Candidatos a revisión manual |
| **H-7** | 36 análisis con un `instrument` que no es IR | Campo mal llenado (`SUPUESTO`) |

Discrepancias en los documentos, sin tocar: `incremento-2.md` (sección 3 del contrato) sigue llamando SUPUESTO al 1024, aunque D-19 pide quitarlo; §10 dice que `datos/referencia/` va al repositorio y `.gitignore` lo excluye desde el incremento 1.

## 6. `indice.csv`

4 183 filas, una por archivo, sin etiquetas y sin split.

- **`archivo`** es la única columna añadida a las pedidas: el UUID. Sin ella el índice no tiene llave, porque `sample_id` se repite.
- `rango_medido_cm1` y `fraccion_relleno` van vacías en los rechazados: los calcula MOD-04.
- `n_puntos` es `##NPOINTS=`; en los que pasan, MOD-04 comprobó que es cierto.
- `veredicto` es la **primera** etapa en que se cae.
- `inchikey` es el estándar de RDKit.
- **No identifica los pares original/derivado.** Para deduplicar, T-16a-2 necesita `analysis_id` y el nombre original, que están en `meta_data.json`.
