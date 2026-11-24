# Incremento 2 (B) — Procesar y ver el espectro

Plan de implementación del incremento 2. **Fuentes (única verdad):** Requerimientos y Matriz **V3.2**, Diseño Modular **v2.0**, Diseño Detallado MOD-06 **v2.0** (sección 5, el contrato de datos), Persistencia **v2.0**, Plan de Implementación **V3**. El stack y las convenciones generales viven en `CLAUDE.md`. Ante cualquier duda o contradicción, consulta el documento completo; **no inventes datos ni fechas** y marca `SUPUESTO` lo no confirmado.

**Objetivo:** el usuario sube un archivo válido y ve su espectro dibujado (eje 4000 → 400).
**Cubre:** RF-03, RF-09 · HU-03, HU-04 · CA-03.1–03.3, CA-04.1–04.3.
**Módulos nuevos:** MOD-04 (procesador de espectros), MOD-05 (visualizador). Más el lector compartido (D-2) y una librería de gráficas (D-1).
**Depende de:** incremento 1 cerrado (H5). MOD-02 y MOD-03 ya existen y están probados.
**Fuera de este incremento:** MOD-06 (identificación), MOD-07 (explicaciones), MOD-08 (PDF), UT-01 (catálogo).

---

## 0. Reglas de trabajo

1. **No implementes nada de MOD-06, MOD-07, MOD-08 ni UT-01.** Si una tarea parece necesitarlos, detente y pregunta.
2. **No toques MOD-01, MOD-02, MOD-03 ni UT-01/02/03** salvo lo que D-2 y el contrato exijan (promover `comun.py` al lector compartido; un código nuevo en UT-02 para la unidad no soportada; servir la gráfica desde MOD-01). Cualquier otro cambio a módulos cerrados se consulta.
3. **Nada «hardcodeado»:** parámetros desde UT-03; mensajes desde UT-02; el contrato de datos desde la sección 5 del diseño de MOD-06.
4. **Un commit por tarea.** Pruebas en `backend/pruebas/` (Python) y `frontend/pruebas/` (JS). **Pruebas sin red.**
5. **La cadena T-08 → T-09 → T-10 es estricta:** cada paso consume la salida del anterior. T-10 fija el contrato que MOD-05 y MOD-06 consumirán, así que no se cierra a la ligera.
6. Si una decisión aprobada cambia, regístralo: qué cambió, por qué y qué RF/HU/CA afecta.

## 1. Decisiones cerradas de este incremento

| # | Decisión | Consecuencia para el código |
|---|---|---|
| D-1 | **Librería de gráficas: Chart.js, vendorizada (no CDN), con `chartjs-plugin-annotation`.** | HTML/CSS/JS puro vía `<script>`, sin build. Eje invertido con `scales.x.reverse=true`; regiones y picos (inc. 4) con el plugin de anotaciones; responsiva de fábrica; `toBase64Image('image/png')` da el PNG para el PDF (inc. 5). Se copia al repo con la versión fijada; nada de red en pruebas. Alternativas descartadas: Plotly (~3 MB, de más), D3 (ejes/escala/resaltado a mano). |
| D-2 | **Lector de espectro compartido, acotado.** Solo lectura de bajo nivel común a MOD-03 y MOD-04: detección de formato, tokenización del CSV (separador, encabezado) y lectura de etiquetas de cabecera del `.jdx`. | Garantiza que MOD-03 (validación) y MOD-04 (parseo) vean **el mismo archivo** — si no, uno valida y el otro grafica distinto. La descompresión de XYDATA, la conversión numérica y la normalización se quedan en MOD-04; la validación se queda en MOD-03. Se promueve `backend/validacion/comun.py` al lector compartido. Ubicación sugerida: `backend/nucleo/` o un módulo propio (no sobrecargar UT-01/02/03). Decidir la ruta exacta al iniciar T-08. |
| D-10 | **La unidad de intensidad la valida MOD-04, no MOD-03.** | MOD-03 **lee y pasa** `##YUNITS=` (contrato §5) pero no la juzga. MOD-04, antes de convertir, verifica que sea **transmitancia o absorbancia** (§6.1); cualquier otra (reflectancia, índice de refracción) → rechazo con un **código nuevo de UT-02** (p. ej. `UNIDAD_NO_SOPORTADA`). Mantiene a MOD-03 ligero y pone el control donde se aplica la fórmula. El manifiesto de T-0R ya documenta que los dos espectros descartados llegarían hasta aquí. |

## 2. La unidad del CSV (D-11, cerrada)

Un `.jdx` declara su unidad en `##YUNITS=`; un **CSV no tiene esa etiqueta**. Regla fijada para que MOD-04 nunca convierta a ciegas:

1. Si el CSV trae **encabezado con la unidad** (`wavenumber,transmittance` o `…,absorbance`) → se usa esa (§6.1 ya admite encabezado).
2. Sin encabezado y **algún valor >1** → **transmitancia en %** (se divide entre 100 y se convierte con `A = −log₁₀(T)`).
3. Sin encabezado y **todos los valores en [0,1]** → **se rechaza** con un mensaje de UT-02 que pida nombrar la unidad en el encabezado.

El punto 3 es el único caso genuinamente ambiguo, y adivinar mal **invierte el espectro** (transmitancia y absorbancia son inversas: los picos se volverían valles), así que rechazar con instrucción clara es más seguro que un espectro falso silencioso. Necesita un **código nuevo de UT-02** para ese rechazo. Si el equipo prefiere otro trato para el caso [0,1], es un cambio de una línea.

## 3. Contratos de datos (del Plan V3 y del diseño de MOD-06 §5) — sin código

- **Lector compartido (D-2) → MOD-03 y MOD-04:** dado el texto, entrega la estructura de bajo nivel: formato, (para CSV) encabezado sí/no + separador + filas de campos, (para `.jdx`) las etiquetas de cabecera como diccionario. No convierte números ni descomprime.
- **MOD-03 → MOD-04:** el contenido ya validado (texto), su formato (`.jdx` o `.csv`) y la unidad declarada (`##YUNITS=` si es `.jdx`; para CSV, lo que resuelva la sección 2).
- **MOD-04 → MOD-05 y MOD-06 (contrato único, diseño MOD-06 §5):** el espectro **normalizado**: vector de intensidades **0–1 (absorbancia)** en una **rejilla fija** (p. ej. N = 1024) + el **eje de número de onda ordenado 4000 → 400 cm⁻¹**. Este contrato es la única fuente de verdad entre MOD-04 y el resto; cualquier diferencia de rango, rejilla o normalización rompe el modelo del incremento 3.
- **MOD-04 → UT-02:** código «sin señal analizable» (línea plana) y `UNIDAD_NO_SOPORTADA` → mensajes.
- **MOD-05 → MOD-01:** la gráfica lista para mostrarse; si no hay espectro válido, no dibuja nada y MOD-01 muestra el mensaje de error (CA-04.3).

## 4. Estructura — adiciones de este incremento

| Ruta | Contenido |
|---|---|
| `backend/preprocesamiento/` | MOD-04 (parseo, orden, conversión, normalización) |
| `backend/nucleo/` (o módulo propio) | lector de espectro compartido (D-2), promovido desde `comun.py` |
| `frontend/visor-espectro/` | MOD-05 (gráfica + eje invertido; el resaltado llega en inc. 4) |
| `frontend/vendor/` (o similar) | Chart.js y el plugin de anotaciones, vendorizados y con versión fijada (D-1) |

## 5. Orden de trabajo y dependencias

| Orden | Tarea | Depende de | Notas |
|---|---|---|---|
| 0 | Cerrar D-2 (ruta del lector) y la sección 2 (unidad del CSV) | — | Antes de T-08/T-09 |
| 1 | Promover `comun.py` → lector compartido (D-2) | inc. 1 | Base de MOD-03 y MOD-04 |
| 2 | T-08 interpretar `.jdx` y `.csv` a pares | lector | Cadena estricta |
| 3 | T-09 ordenar + convertir T→A | T-08 | |
| 4 | T-10 normalizar 0–1 + remuestrear a rejilla fija | T-09 | **Fija el contrato §5** |
| 5 | T-11 línea plana → «sin señal analizable» | T-10 | |
| 6 | T-12 gráfica con eje invertido | T-10 (o vector simulado) | ∥ a T-08–T-11 |
| 7 | T-13 gráfica responsiva + caso sin gráfica | T-12 | Cierra H7 |

MOD-05 (T-12/T-13) puede arrancar en paralelo contra un vector simulado y conectarse al cerrar T-10.

## 6. Tareas

### T-08 · MOD-04 · interpretar `.jdx` y `.csv` a pares (número de onda, intensidad)
- **Objetivo:** un `.jdx` y un `.csv` del mismo espectro producen el mismo conjunto de pares.
- Usa el **lector compartido** (D-2) para la estructura; aquí se hace la conversión a números.
- **`.jdx`:** aplica `##XFACTOR=`/`##YFACTOR=` (si no están, 1); usa `##FIRSTX=`/`##LASTX=`/`##NPOINTS=` y **verifica que el número de puntos leídos coincida con `##NPOINTS=`**; soporta las formas comprimidas (DIF/SQZ) o rechaza con mensaje claro (UT-02), **nunca leer valores equivocados en silencio**. Deduce la dirección del eje por `##FIRSTX=` vs `##LASTX=`, **nunca por el signo de `##DELTAX=`** (en un archivo real venía equivocado — ver manifiesto de T-0R).
- **`.csv`:** separador coma o punto y coma, decimal según separador (ver inc. 1 §T-04); salta el encabezado.
- **Pruebas:** un `.jdx` real de NIST (datos comprimidos) se lee completo y el conteo coincide con `##NPOINTS=`; un `.jdx` con `##YFACTOR=`≠1 y su `.csv` equivalente dan los mismos valores.

### T-09 · MOD-04 · ordenar y convertir transmitancia a absorbancia
- **Objetivo:** ordenar los puntos y convertir T→A. Aquí entra la validación de unidad (D-10) y la convención del CSV (sección 2).
- Unidad: si es absorbancia, no convierte; si es transmitancia, `A = −log₁₀(T)` (con T en fracción; si viene en %, dividir entre 100 antes); si es otra, rechaza con `UNIDAD_NO_SOPORTADA`.
- **Pruebas:** CA-03.1 (conversión correcta), CA-03.2 (orden ascendente ≡ descendente dan lo mismo).

### T-10 · MOD-04 · normalizar 0–1 y remuestrear a la rejilla fija
- **Objetivo:** dejar todo espectro con el mismo tamaño, eje 4000 → 400 e intensidad 0–1. **Fija el contrato §5** que consumen MOD-05 y MOD-06.
- **Pruebas:** vector dentro de [0,1] con el número de puntos acordado; mismo eje de salida para entradas de distinta resolución.

### T-11 · MOD-04 · espectro sin señal analizable (línea plana)
- **Objetivo:** una intensidad constante no debe fallar; informa «sin señal analizable» (UT-02).
- **Pruebas:** CA-03.3 (no lanza excepción, da el mensaje).

### T-12 · MOD-05 · gráfica con eje invertido (4000 → 400)
- **Objetivo:** dibujar con Chart.js (D-1): número de onda en el eje horizontal de 4000 a 400, intensidad en el vertical.
- Prueba la **construcción de la configuración de Chart.js como función pura** (espectro → objeto de configuración: eje invertido, mapeo de datos), igual que el patrón de T-06; la verificación visual va por captura.
- **Pruebas:** CA-04.1 (ejes, unidades, eje invertido).

### T-13 · MOD-05 + MOD-01 · gráfica responsiva y caso sin gráfica
- **Objetivo:** la gráfica se ajusta a 360 px sin desplazamiento horizontal; un archivo inválido no deja una gráfica vacía, sino el mensaje de error.
- **Pruebas:** CA-04.2 (360 px, medido como en T-06 — ancho/contenido/desborda, no por impresión), CA-04.3 (archivo inválido → mensaje, no gráfica vacía).

## 7. Pruebas del incremento

| ID | Tipo | Entrada / condición | Resultado esperado | Nivel |
|---|---|---|---|---|
| CA-03.1 | Normal | Espectro válido en transmitancia (%) | Convierte a absorbancia y normaliza 0–1 | Unitaria (MOD-04) |
| CA-03.2 | Límite | `.jdx` con onda descendente (4000→400) | Resultado idéntico al del equivalente ascendente | Unitaria (MOD-04) |
| CA-03.3 | Error | Intensidad constante (línea plana) | «Sin señal analizable», sin excepción | Unitaria (MOD-04/UT-02) |
| CA-04.1 | Normal | Espectro válido | Gráfica con eje 4000→400 e intensidad vertical | Integración / visual |
| CA-04.2 | Límite | Espectro a 360 px | Sin desplazamiento horizontal, ejes legibles (medido) | Manual/medición |
| CA-04.3 | Error | Archivo que no pasó validación | Mensaje de error, no gráfica vacía | E2E |
| (unidad) | Error | `.jdx` en reflectancia / índice de refracción | `UNIDAD_NO_SOPORTADA`, sin convertir | Unitaria (MOD-04) |
| (T-08) | Normal | `.jdx` real de NIST (comprimido) | Se lee completo; conteo = `##NPOINTS=` | Integración (MOD-04) |
| (T-08) | Límite | `.jdx` con `##YFACTOR=`≠1 y su `.csv` | Los dos dan los mismos valores | Unitaria (MOD-04) |

## 8. Datos de prueba

Este incremento **sí usa los espectros reales** (el incremento 1 solo fabricados). Se reproducen con `descargar_espectros_nist.py` + `espectros_nist.json` (T-0R, incremento 1), locales y fuera del repo (copyright Coblentz). Para la prueba de equivalencia de T-08 hace falta el **mismo compuesto en `.jdx` y en `.csv`** (el `.csv` se genera del `.jdx` con el script suelto, fuera de la app). Para los casos de normalización/eje, fixtures sintéticos en `datos/pruebas/` siguen sirviendo (estructura, no química). Un fixture en reflectancia (uno de los descartados de T-0R) prueba `UNIDAD_NO_SOPORTADA`.

## 9. Hitos

**H6** — MOD-04 procesa y normaliza: CA-03.1–03.3 en verde, contrato §5 fijado. → **H7** — gráfica visible y responsiva: CA-04.1–04.3; **incremento 2 demostrable** (subir un válido y ver su espectro dibujado).

## 10. Decisiones abiertas que hereda el incremento 3

- **Umbral y pesos de fusión** (0.6; wR/wML) ya están en UT-03; se recalibran con validación.
- **Dataset de SDBS/NIST para entrenar MOD-06** (riesgo abierto): conseguir y etiquetar, reservar un subconjunto de prueba independiente (RNF-08). Faltan espectros con **C≡N (GF-04)** y **C=C (GF-06)**, que ningún compuesto de T-0R cubre.
- **Plan B del motor:** si el CNN no alcanza F1 ≥ 0.80 a tiempo, entregar con `wML = 0` (solo reglas) sin cambiar el contrato.

## 11. Registro de lo implementado

Esta sección se agregó al terminar el incremento. Dice cómo quedaron las decisiones de arriba en el código y qué se resolvió por el camino. Lo marcado como SUPUESTO falta que el equipo lo confirme.

**D-2, ruta del lector.** El lector compartido quedó en `backend/nucleo/lector_espectro.py`. Tiene la extensión, el separador, el encabezado y los pares del CSV, y las etiquetas y el bloque de datos del JCAMP-DX. `backend/validacion/comun.py` sigue existiendo para MOD-03, pero ahora toma su lectura de ahí, igual que `backend/preprocesamiento/lector.py`. Una prueba revisa que los dos módulos saquen los mismos pares del mismo archivo.

**D-10.** MOD-04 rechaza con `UNIDAD_NO_SOPORTADA` cualquier `##YUNITS=` que no sea transmitancia ni absorbancia.

**D-11.** El código nuevo de UT-02 para el CSV ambiguo se llama `UNIDAD_SIN_DECLARAR` y le pide a la persona agregar un encabezado con la unidad. Consecuencia: `espectro-valido-900-puntos.csv` y `espectro-punto-y-coma.csv`, que no traen encabezado y tienen todos sus valores entre 0 y 1, pasan la validación de MOD-03 pero MOD-04 los rechaza por esta regla. Las pruebas de MOD-04 usan `espectro-con-encabezado.csv` y la línea plana ahora trae encabezado.

**Ruta nueva, `POST /api/procesar`.** El plan no decía cómo llega el espectro a la página. Se agregó una ruta aparte que recibe el mismo archivo, lo pasa por MOD-02, MOD-03 y MOD-04 y devuelve `{valido, nombre, espectro}`, donde `espectro` trae `eje_cm1`, `intensidad`, `rango_medido_cm1` y `unidad_original`. Así el contrato D-5 de `/api/validar` no cambia. Como el archivo no se guarda (RNF-09), la página lo manda dos veces. Si el equipo prefiere que `/api/validar` devuelva también el espectro, el cambio es pequeño, pero toca el contrato cerrado del incremento 1.

**D-1.** Chart.js 4.4.7 y chartjs-plugin-annotation 3.1.0 quedaron en `frontend/vendor/` con su licencia y su huella SHA-256 en `frontend/vendor/LEEME.md`. La configuración de la gráfica es una función pura en `frontend/visor-espectro/configuracion.js`, probada con `node --test`. El complemento de anotaciones queda registrado y vacío para el incremento 4. La prueba de MOD-01 que busca direcciones de internet en el frontend ahora se salta `frontend/vendor/`, porque los comentarios de licencia traen la dirección del proyecto.

**Contrato de la sección 3.** La rejilla tiene 1024 puntos y va de 4000 a 400 cm⁻¹. Los dos valores viven en UT-03, en `procesamiento.puntos_rejilla` y `procesamiento.rango_rejilla_cm1`. El 1024 salió del ejemplo del diseño de MOD-06 y al principio quedó como SUPUESTO. El equipo lo cerró como la decisión D-19 del plan del incremento 3: son unos 3.5 cm⁻¹ por punto, que va con la resolución de los espectros reales, y es potencia de dos, cómoda para la red. Desde que se entrena el modelo (T-16c) ya no se cambia, porque un N distinto deja inservibles los pesos entrenados.

**Otros SUPUESTOS de MOD-04.**
- Una transmitancia declarada en el encabezado con algún valor mayor que 1.5 se toma como porcentaje.
- Una transmitancia de cero o negativa se sube a una millonésima antes del logaritmo.
- Fuera del tramo que midió el archivo, la rejilla queda en cero y la respuesta dice cuál fue el tramo medido. La gráfica solo dibuja ese tramo.

**Evidencia.** `python -m herramientas.capturar_grafica` sube los archivos contra la aplicación real, revisa el DOM antes de fotografiar y mide el ancho a 360 px. Las capturas quedan en `docs/evidencia/t-12-*` y `t-13-*`. Resultado: `ancho=345 contenido=345 desborda=no`; el marco es de 360 y la barra de desplazamiento vertical ocupa el resto.

**Pendiente.** La prueba de T-08 con un `.jdx` real de NIST se salta cuando el archivo no está en `datos/referencia/`. Desde la nube no se pudo descargar; hay que correrla en una computadora del equipo después de `python -m herramientas.descargar_espectros_nist`. Las dos pruebas de RNF-09 de MOD-02 sobre el archivo temporal fallan en Linux desde el incremento 1; no se tocaron.
