# Propuesta para `incremento-3.md` v2.6 — arranque de T-16a

**Estado:** propuesta para revisión del equipo. No sustituye al plan; es el bloque a mezclar en v2.6 una vez aprobado.
**Fecha:** 24/11/2026
**Alcance:** lo que hay que cerrar antes de que alguien baje los 4 183 archivos, y la forma del entregable de T-16a.

---

## 0. Pre-vuelo — cuatro cosas antes de bajar un archivo

| # | Qué | Por qué ahora |
|---|---|---|
| 1 | **`.gitignore`: `motor-identificacion/modelo/*` con guion → guion bajo** | D-23.6 ya lo marcó «arréglalo ya, antes de T-16». Hoy los pesos se commitearían, contra D-18. Es una línea, y el día que T-16c produzca pesos ya será tarde |
| 2 | **Encabezado y §7: H8 sigue diciendo ABIERTO** | D-23 lo cierra el 24/11/2026, pero la línea 10 («T-14, T-15a y T-15b implementados. H8 sigue ABIERTO») y la fila H8 de §7 no se actualizaron. El plan se contradice consigo mismo en su propio encabezado |
| 3 | **§7 no lista T-15e** | D-23 lo crea y lo pone en paralelo con T-16a. Si no está en la tabla de reparto, no tiene responsable |
| 4 | **T-16b dice «bloqueada por el valor real de N (D-17)»** | N = 1024 es **D-19**. D-17 es el contrato HTTP. Errata |

---

## D-24 · Criterio de etiquetado por subestructura — **bloquea T-16a**

**Por qué existe esta decisión.** MOD-06 §7 y D-12 dicen que el etiquetado «se deriva de la estructura (SMILES) a un vector binario de 7 posiciones». Eso dice *de dónde* sale la etiqueta, no *cuándo vale 1*. Hoy ningún documento del proyecto define el criterio por grupo, y el «Terminado» de T-16a («etiquetado en el orden canónico») lo da por hecho. **Es el agujero más grande de T-16a**, y no es mecánico: hay al menos dos casos en los que la respuesta cambia lo que el modelo aprende y lo pone en desacuerdo con la vía de reglas.

**Qué hay que decidir, grupo por grupo** — el vector vale 1 cuando la molécula tiene **el enlace que produce la banda**, no cuando tiene el elemento:

- **GF-01 O–H.** Alcohol, fenol y ácido cuentan los tres (el catálogo los nombra). Decidir: un ácido carboxílico ¿activa GF-01 **y** GF-05? Sí por química, y hay que escribirlo, porque es el caso del ácido benzoico y ya está en la verdad de referencia de D-21.
- **GF-02 N–H.** Es **N–H**, no «nitrógeno». Una amina terciaria no activa GF-02. Una amida sí (tiene N–H si es primaria o secundaria; una amida terciaria, no). Nitro, nitrilo y azo no activan GF-02.
- **GF-03 C–H alifático (sp³).** Carbono sp³ con al menos un H. Un aromático totalmente sustituido sin cadenas no lo tiene — es el caso del ácido benzoico y la anilina de la tabla de D-21.
- **GF-04 C≡N.** Nitrilo. Decidir si se excluyen isonitrilos y cianatos, que no son el mismo enlace.
- **GF-05 C=O.** **Caso abierto n.º 1: la amida.** §4 del plan ya documenta que el C=O de amida (1630–1700) cae parcialmente **fuera** de la región de GF-05 (1670–1780), y que el efecto es una omisión de la vía de reglas. Si la amida se etiqueta GF-05 = 1, el CNN aprende a ver un C=O que **la vía de reglas no puede ver por diseño**, y en T-17 las dos vías discreparán de forma sistemática en una familia muy abundante en química de síntesis. Las dos salidas son defendibles —etiquetarla y aceptar la discrepancia, o excluir las amidas del entrenamiento y documentarlo— pero hay que elegir **antes** de entrenar, no al leer un F1 raro.
- **GF-06 C=C.** Alqueno, **no** aromático. El doble enlace de un anillo aromático no activa GF-06. Es exactamente la confusión que R-2 intenta deshacer; si la etiqueta la comete, no hay regla que la salve.
- **GF-07 anillo aromático.** **Caso abierto n.º 2: los heteroaromáticos.** El catálogo describe GF-07 por el par de bandas ~1600/~1500 más C–H aromático en 3000–3100 — eso es un **carbociclo** tipo benceno. Piridina, furano, tiofeno y pirazol son aromáticos pero no ponen sus bandas en el mismo sitio, y un aromático totalmente sustituido **no tiene C–H aromático**, que es justo lo que R-2 le exige a GF-07. Un laboratorio de síntesis produce heteroaromáticos a montones. Decidir: GF-07 = solo carbociclos aromáticos, o todos los aromáticos. Si es «todos», el grupo deja de corresponder a lo que el catálogo describe.

**Mitigación, la misma que T-20** (riesgo de contenido químico): los patrones se contrastan contra **dos fuentes** y los revisa **quien no los escribió**. Y se hereda la frontera de T-3R: **si hay duda química sobre una etiqueta, el compuesto se deja fuera en vez de adivinar** — con su motivo anotado en `indice.csv`, para que la merma por ambigüedad sea un número y no un misterio.

---

## Enmienda a D-13 · la puerta, frente a la tasa base

**El problema.** La puerta de D-13 es F1 ≥ 0.80 por grupo en GF-01, GF-04 y GF-05 sobre el subconjunto de prueba. En un conjunto de química de síntesis, dos de esos tres grupos quedan en extremos opuestos y **ambos extremos rompen la puerta**:

- `SUPUESTO` (a medir en T-16a): **GF-05 (C=O) será muy abundante** — ésteres, amidas, cetonas, grupos protectores. Si su tasa base es, digamos, 0.85, un predictor que diga «sí» **siempre** obtiene F1 ≈ 0.92 sin haber aprendido nada, y la puerta se pasa sola. Lo mismo, aún más marcado, con GF-03 y GF-07, que no están en la puerta pero sí en el informe.
- `SUPUESTO`: **GF-04 (C≡N) será raro.** Si quedan 2 o 3 positivos en el split de prueba, su F1 lo mueve un solo acierto y la puerta decide sobre ruido.

**Dos añadidos, ninguno cambia el número 0.80:**

1. **Se reporta siempre el F1 del predictor trivial** (constante positivo y constante negativo) junto al del modelo, por grupo. Un 0.92 que un predictor constante también alcanza queda a la vista en la misma tabla, en vez de leerse como éxito. Para los grupos de la puerta, **el modelo tiene que superar al trivial**, no solo al 0.80.
2. **Support mínimo para que la puerta sea decidible.** Se fija en T-16a un mínimo de positivos en el split de prueba por debajo del cual el F1 de ese grupo es **informativo, no decisorio**, y se dice así en `rnf-08.md`. Si GF-04 queda por debajo, la puerta no «falla» ni «pasa»: queda sin decidir, y esa es la entrada honesta a D-16 — distinta de «el modelo no aprendió».

---

## Enmienda a D-12 · cuál es el conjunto de prueba (hoy el plan dice dos cosas)

**La contradicción.** D-12 cierra que **A (núcleo curado NIST) se reserva para prueba y validación** y **B (Chemotion) es el entrenamiento**. Pero T-3R pide un **split 70/15/15 del conjunto** con `split-prueba.txt` congelado, y `indice.csv` lleva columna de split. No pueden ser las dos: el núcleo son ~14 espectros, y con eso no se sostiene un F1 por grupo ni se recalibran pesos.

**Propuesta:**

- **Chemotion se divide 70/15/15 por `InChIKey`**, no por archivo. El **15 % de prueba es el subconjunto independiente de RNF-08**, y lo es para **las dos vías** — que es lo que D-22.2 pidió cuando dijo que la exactitud fuera de muestra de la vía de reglas hoy es desconocida.
- **El 15 % de validación** recalibra pesos (D-15) y pisos, y es donde se mide todo lo intermedio.
- **El núcleo NIST deja de llamarse «prueba».** Pasa a ser lo que de verdad es: fixtures de regresión de T-15, y un **chequeo fuera de dominio** que se reporta aparte y **no decide la puerta** — ver el punto siguiente, que es la razón de peso.

---

## El punto que el plan no ha considerado: ATR vs transmisión

D-12 resolvió **gas vs condensada** y eso estaba bien. Pero dentro de «fase condensada» hay un segundo desfase de dominio que nadie ha mirado:

- Los ocho espectros de referencia son de **transmisión** (Coblentz, líquido neto, red de difracción).
- `SUPUESTO`, y es justo lo que la verificación 1 de D-12 debe comprobar: **Chemotion es mayoritariamente ATR**, que es como se caracteriza en un laboratorio de síntesis.

Importa por dos razones concretas:

1. **ATR y transmisión no reparten la intensidad igual.** En ATR la penetración crece con la longitud de onda, así que las bandas de número de onda bajo salen realzadas frente a las de número de onda alto. Los pisos `fuerza_minima_relativa` de D-22 son **fracciones de la banda más intensa del espectro** — y se calibraron sobre transmisión. En ATR, un O–H en 3300 pesa relativamente menos frente a un C=O en 1700 que en transmisión. **El riesgo concreto es que los pisos sub-detecten sistemáticamente GF-01, GF-02 y GF-03 en Chemotion**, y que eso se lea como «la vía de reglas no generaliza» cuando en realidad es una diferencia de modo de medida.
2. **Es el argumento decisivo para no usar el núcleo NIST como puerta.** Si se entrena en ATR y se mide la puerta en transmisión, el F1 bajo no dirá si el modelo aprendió. Al revés, el núcleo sirve **precisamente** para medir ese desfase — pero como segundo número, declarado.

**Qué cambia en la verificación 1 de D-12:** no basta con confirmar «es condensada». Hay que **registrar el modo de medida por espectro** (de `instrument`, y de las cabeceras del `.jdx` si lo declaran) y reportar el reparto. Si sale mezclado, se reporta como columna de `indice.csv`, no se descarta nada todavía.

---

## D-23 reserva 2 · cómo medirla en T-16a, y dónde no medirla

La reserva dice que el puntaje usa el resto del espectro como referencia de ruido y que eso no escala a espectros densos. T-15d lo midió en sintéticos: una banda ajena baja un O–H de 1.00 a 0.54.

**Se puede medir ya, sin etiquetas**, porque es una propiedad del espectro y del detector, no de la química:

1. **El estadístico de referencia que el propio puntaje calcula**, espectro por espectro. Es el número que se compara con los ocho de referencia; si en Chemotion está varias veces más alto, todos los scores salen deflactados por construcción, y eso se sabe antes de entrenar nada.
2. **Densidad espectral**: número de picos resueltos por espectro con el mismo detector de T-15, y su distribución frente a los ocho.
3. **La hipótesis del relleno, que es específica y nadie ha mirado.** Si Chemotion es ATR con corte cerca de 650 cm⁻¹, llega con relleno de ceros por debajo de ese corte, mientras que los ocho de referencia llegan con poco o ninguno. Si el estadístico de ruido se calcula sobre la rejilla completa, **el relleno lo diluye** y los scores se inflan — en dirección contraria al efecto de densidad. Medir la **fracción de relleno** por espectro y ver si el estadístico de ruido correlaciona con ella separa los dos efectos en vez de dejarlos sumados.

**Dónde NO medirla: en el split de prueba.** D-15.2 es una regla dura — el subconjunto de prueba se toca **una sola vez**, en T-16d. Toda medición intermedia, incluida la evaluación fuera de muestra de la vía de reglas, va sobre **validación** (o entrenamiento). Quemarlo aquí dejaría a RNF-08 sin número honesto y nadie fuera del equipo podría notarlo.

**Y una nota de versión:** T-15e corre en paralelo y va a tocar R-1, que es parte de cómo se puntúa. Cualquier medición de la vía de reglas sobre Chemotion tiene que registrar **el commit del motor** con el que se tomó, o no será comparable con la de después.

---

## T-16a · partes y «Terminado» propuestos

**Bloqueada por:** D-12 (cerrada), **D-24** (abierta), y las dos enmiendas de arriba.

**Partes:**

1. **Descarga y verificación de integridad** del paquete (4 183 `.jdx` + `meta_data.json`), con su DOI y licencia anotados junto al directorio.
2. **El embudo**, con causa por archivo. No es un número, es una tabla:

   | Etapa | Quedan | Se caen | Motivo |
   |---|---|---|---|
   | Archivos en el paquete | 4 183 | — | — |
   | Con `cano_smiles` presente y parseable | | | |
   | Pasan MOD-03 (estructura, puntos ≥ 300, rango 1400–3700, tamaño) | | | código de rechazo |
   | Pasan MOD-04 (unidad admitida, eje deducible, señal presente) | | | `UNIDAD_NO_SOPORTADA`, `UNIDAD_SIN_DECLARAR`, `DATOS_ILEGIBLES`, `SIN_SENAL` |
   | Con etiqueta derivable sin ambigüedad (D-24) | | | motivo químico |
   | Compuestos únicos tras deduplicar por `InChIKey` | | | — |
   | Tras excluir los que coinciden con el núcleo curado | | | manda el núcleo (D-12) |

   El desglose de `UNIDAD_*` es además **el argumento que le faltaba a la decisión abierta de `##YUNITS=`** (§12): si una fracción apreciable de un conjunto publicado de 4 183 espectros reales declara una unidad no admitida, la discusión deja de ser sobre un archivo de estireno.
3. **Support por grupo**, en **cuatro** cortes: a nivel espectro y a nivel compuesto, y por split. Más la **tasa base** de cada grupo, que es lo que alimenta la enmienda de D-13.
4. **Matriz de co-ocurrencia 7 × 7.** El plan ya teme las correlaciones falsas («si todos sus nitrilos son aromáticos, el motor aprenderá que un nitrilo implica un anillo») pero nunca pide el número que las revela. En un conjunto de síntesis es muy probable que GF-04 venga casi siempre acompañado de GF-07. Si es así, hay que saberlo **antes** de entrenar, porque condiciona si el núcleo curado necesita el `acetonitrile` de la prioridad 1 para romperla.
5. **El split 70/15/15 por `InChIKey`**, con `split-prueba.txt` congelado y su suma de verificación.
6. **Las tres mediciones de la reserva 2**, sobre validación.

**`indice.csv` — el esquema de D-12 fue escrito para NIST y no encaja con Chemotion.** Chemotion no trae CAS; trae `sample_id` y `cano_smiles`. Columnas propuestas: `sample_id`, `cano_smiles`, `inchikey`, `instrument`, `kind`, `modo_medicion` (ATR / transmisión / desconocido), `rango_medido_cm1`, `n_puntos`, `unidad_original`, `fraccion_relleno`, `veredicto_pipeline` (pasó o código de rechazo), las **7 etiquetas** en orden canónico, y `split`.

**Terminado:**

- D-24 cerrada y aplicada, con la revisión cruzada hecha.
- El embudo completo, con causa por archivo, en `docs/evidencia/t-16a-embudo.md`.
- `indice.csv` y `split-prueba.txt` versionados; **los espectros no**.
- Support, tasa base y matriz de co-ocurrencia escritos.
- Las tres mediciones de la reserva 2, con el commit del motor anotado.
- El modo de medida reportado (verificación 1 de D-12, ampliada).

**Fronteras:** T-16a **no entrena nada** y **no toca `split-prueba.txt`** más que para congelarlo. La evaluación fuera de muestra de la vía de reglas se hace sobre **validación**, y su número no se presenta como RNF-08.

**Una nota de orden:** T-16a es el **primer consumidor real** de MOD-03 y MOD-04 fuera de la app, así que la regla de T-16b («el entrenamiento importa la normalización real de MOD-04, no una copia») empieza a aplicar **aquí**, no en T-16b. Si T-16a procesa los 4 183 con una copia, la prueba de paridad de T-16b llegará tarde a comprobar algo que ya se usó.
