# Incremento 1 (A) — Subir y validar el espectro

Resumen operativo para la implementación. **Fuentes (única verdad):** Requerimientos y Matriz **V3.1**, Diseño Modular **v2.0**, Diseño Detallado MOD-06 **v2.0**, Persistencia de Datos **v2.0**, Plan de Implementación **V3** (Pasos 3–8). El stack y las convenciones generales viven en `CLAUDE.md`. Ante cualquier duda o contradicción, manda el documento completo; **no inventes datos ni fechas**.

**Objetivo:** el usuario sube un `.jdx` o `.csv` y recibe «aceptado» o «rechazado con motivo».
**Cubre:** RF-01, RF-02 · HU-01, HU-02 · CA-01.1–01.3, CA-02.1–02.6 · RNF-01 (mensajes con motivo y acción), RNF-03, RNF-09.
**Módulos:** MOD-01 (mínima), MOD-02, MOD-03, UT-02, UT-03.
**Fuera de este incremento:** MOD-04 (procesar/normalizar), MOD-05 (gráfica), MOD-06 (identificación), MOD-07 (explicaciones), MOD-08 (PDF), UT-01 (catálogo de grupos).

---

## 0. Reglas de trabajo para esta implementación

1. **No implementes nada de MOD-04, MOD-05, MOD-06, MOD-07, MOD-08 ni UT-01.** Si una tarea parece necesitarlos, detente y pregunta.
2. **No agregues dependencias** de gráficas, machine learning ni PDF. Las decisiones D-1 (librería de gráficas), D-2 (lector compartido) y D-3 (librería de PDF) pertenecen a los incrementos 2 y 5.
3. **Sin base de datos.** Decisión aprobada en Persistencia v2.0: archivos de solo lectura + procesamiento en memoria.
4. **Nada «hardcodeado»:** todo parámetro se lee de UT-03 y todo mensaje de UT-02.
5. **Un commit por tarea** (riesgo del Paso 8). Las pruebas viven en `backend/pruebas/` (RNF-06).
6. Si una decisión aprobada cambia, regístralo: qué cambió, por qué y qué RF/HU/CA afecta.

## 1. Decisiones ya cerradas por el equipo

| # | Decisión | Consecuencia para el código |
|---|---|---|
| D-0 | **Solo `.jdx` y `.csv`.** `.dx` queda fuera del incremento (comparte formato con `.jdx`, se puede sumar después sin costo). | La lista de formatos vive en UT-03; el mensaje de rechazo se construye desde esa lista. Ya corregidos §6.1 y CA-01.3 en Requerimientos V3.1 y la tabla del Paso 6 del Plan. *Pendiente documental: §2 (flujo de uso), §4 (alcance, punto 1), **RF-01** y la fila RF-01 de la matriz §11.1 todavía nombran `.dx`; RF-01 es el que urge, porque hoy contradice a su propio CA-01.3. El glosario §6.3 sí debe conservar `.dx`: ahí define el formato JCAMP-DX en general.* |
| D-4 | **Botón «Analizar»:** al aceptar el archivo, la interfaz muestra que el documento fue aprobado y que «Analizar» está habilitado. **Presente y habilitado, sin acción** (RF-04 es del incremento 3). | CA-01.1 queda verificable: se comprueba el estado del botón, no que analice. |
| D-5 | **Contrato HTTP:** `POST /api/validar` (sección 5). | MOD-01 nunca llama a MOD-02/MOD-03 directamente; pasa por `backend/api/`. |
| D-6 | **Archivo de configuración: `parametros.json`, versionado.** Se renombra `parametros.ejemplo.json` → `parametros.json`. | El sufijo `.ejemplo` es convención de «plantilla para copiar» (como `.env.ejemplo`) y aquí engañaba: este archivo **es** la fuente operativa, no una plantilla. Sin variante `.ejemplo`. Va commiteado y `.gitignore` **no** debe ignorarlo (la antideriva depende de que esté versionado). Conservar la prueba que falla si aparece un segundo `parametros*.json`. `cargador.py` lee `parametros.json`. |
| D-7 | **Carpetas de paquetes Python del backend usan guion bajo, no guion.** `manejador-archivos` → `manejador_archivos`; en inc. 3, `motor-identificacion` → `motor_identificacion`. | Un guion no es identificador válido de Python: `import` sobre esa carpeta es error de sintaxis. Aplica **solo a carpetas que Python importa como paquete**. Las del frontend (`interfaz/`, `servicios/`, `visor-espectro/`) conservan el guion. Desviación justificada del Diseño Modular §10, permitida por su propia nota («los nombres anticipan los módulos») y por el checklist del Paso 9; se registra en la bitácora, no es cambio de arquitectura. |
| D-8 | **Datos de prueba fabricados en `datos/pruebas/` (commiteados); `backend/pruebas/` solo código (RNF-06).** | Coherente con Diseño Modular §10 (`datos/` es el hogar de datos estáticos) y deja `datos/pruebas/` junto a `datos/referencia/`. Se elimina la carpeta vacía `backend/pruebas/archivos/` y se alinea esa fila de `CLAUDE.md`. |
| D-9 | **`frontend/pruebas/` es carpeta nueva, para las pruebas JS (`node --test`).** | Única adición a la estructura del Diseño Modular §10, justificada: `backend/pruebas/` quedó solo para Python (D-8) y las pruebas de MOD-01 necesitan hogar propio, en paralelo. Se registra en la bitácora y en `CLAUDE.md`; amendar §10 del PDF queda a criterio del equipo. |

## 2. Datos y persistencia (Paso 5 + Persistencia v2.0)

- **Temporal:** el contenido del archivo subido (solo en memoria, durante la petición) y el veredicto. Se descartan al terminar la petición (RNF-09).
- **Persistente:** únicamente el archivo de configuración de UT-03, de solo lectura. Ningún dato de usuario.
- **No se escribe nada a disco.**
- **Anti-deriva:** la regla vive en Requerimientos V3 §6.1; el **valor operativo vive solo en UT-03**. Nadie los copia al código.

## 3. UT-03 · parámetros confirmados

| Parámetro | Valor | Llave |
|---|---|---|
| Tamaño máximo | 5 MB = 5 242 880 bytes | `archivo.tamano_maximo_bytes` |
| Formatos | `.jdx`, `.csv` | `archivo.formatos_permitidos` |
| Puntos mínimos | 300 (CA-02.6) | `validacion.puntos_minimos` |
| Rango que debe cubrir | 1400–3700 cm⁻¹ | `validacion.rango_requerido_cm1` |
| Etiquetas JCAMP-DX obligatorias | `##TITLE=`, `##JCAMP-DX=`, `##XUNITS=`, `##YUNITS=`, `##END=` | `validacion.jcamp_etiquetas_obligatorias` |
| Etiqueta de datos (una de) | `##XYDATA=` o `##PEAK TABLE=` | `validacion.jcamp_etiquetas_datos_una_de` |

**Reglas que el JSON no puede expresar y MOD-03 debe aplicar:** `##TITLE=` tiene que estar en la **primera línea** y `##END=` en la **última**; no basta con que aparezcan en cualquier parte del archivo.

**Llaves obligatorias al arrancar en este incremento:** todo `archivo.*` y todo `validacion.*`. El bloque `motor` (umbral 0.6, pesos de fusión) está previsto para el incremento 3 y **no debe ser obligatorio** para que el backend levante hoy.

**El archivo ya existe en el repo** (D-6). Lo que falta es que deje de ser solo un documento y pase a ser la fuente que el código consulta: ningún módulo repite estos valores, y si el archivo cambia, el comportamiento cambia sin tocar código. Esa es la prueba de que sirve en la práctica.

## 4. UT-02 · mensajes

Cada mensaje lleva **motivo + acción** (RNF-01), sin detalles técnicos. El catálogo arranca con estos cuatro textos, que son los que **los criterios de aceptación verifican de forma literal**; los demás códigos se van creando conforme aparezcan las situaciones de error y límite durante la práctica.

| Situación | Texto exigido | CA |
|---|---|---|
| Formato no admitido | «Formato no soportado. Formatos admitidos: *lista leída de UT-03*» | CA-01.3 |
| Tamaño excedido | «El tamaño máximo permitido es de 5 MB» | CA-02.2 |
| Rango insuficiente | «Se requiere cubrir al menos 1400–3700 cm⁻¹» | CA-02.3 |
| Puntos insuficientes | «Mínimo 300 puntos» | CA-02.6 |

Con esos cuatro queda cubierta la redacción obligatoria. Quedan cuatro situaciones que sí necesitan **algún** mensaje, aunque su texto sea libre, porque los criterios exigen que se muestre el motivo: archivo que no es texto (binario), estructura inválida, configuración incompleta al arrancar y lectura interrumpida.

## 5. Contratos entre módulos (Plan V3) — sin código

- **UT-03 → MOD-02 / MOD-03:** los parámetros (tamaño máximo, formatos permitidos, puntos mínimos, rango, etiquetas).
- **MOD-02 → MOD-03:** el contenido del archivo **como texto** (UTF-8, BOM descartado con `utf-8-sig`; los bytes inválidos llegan como el carácter de reemplazo `U+FFFD` «�», por `errors="replace"`), su nombre y un indicador de «tamaño correcto»; o un **rechazo con código**. MOD-02 no juzga contenido: la capa «¿es texto?» de MOD-03 (T-04) debe tratar como binario tanto `\x00` como `U+FFFD`, que es donde ahora aparecen los bytes inválidos.
- **MOD-03 → MOD-01:** un **veredicto**: válido sí/no y, si no, motivo + código.
- **UT-02 → todos:** dado un código, devuelve **título, texto y acción sugerida**.
- **MOD-01 → usuario:** vista de «aceptado» o «rechazado con mensaje».

### Contrato HTTP (D-5)

- `POST /api/validar`, `multipart/form-data`, campo `archivo`.
- **200** siempre que el servidor pueda emitir un veredicto — un rechazo es un resultado de negocio, no un error de transporte:
  - aceptado → `{ "valido": true, "nombre": "acetona.jdx", "bytes": 307200 }`
  - rechazado → `{ "valido": false, "codigo": "...", "titulo": "...", "mensaje": "...", "accion": "..." }`
- **500** solo ante fallo interno, con mensaje genérico de UT-02 y sin detalles técnicos.
- El **límite de 5 MB lo aplica MOD-02 leyendo por bloques**, no la configuración de FastAPI ni la del servidor: si lo corta la infraestructura, CA-02.2 no prueba el código del equipo.
- La orquestación vive en `backend/api/`.

## 6. Estructura del repositorio

Ya creada conforme al Diseño Modular v2.0 §10. Carpetas de este incremento:

| Ruta | Contenido |
|---|---|
| `frontend/interfaz/` | MOD-01 · flujo y mensajes |
| `frontend/servicios/` | llamada a `/api/validar` |
| `frontend/pruebas/` | pruebas JS de MOD-01 (`node --test`) (D-9) |
| `backend/api/` | orquestación y límites |
| `backend/manejador_archivos/` | MOD-02 (guion bajo, D-7) |
| `backend/validacion/` | MOD-03 |
| `backend/utilerias/configuracion/` | UT-03 · archivo de parámetros (ya creado) |
| `backend/utilerias/mensajes/` | UT-02 |
| `backend/nucleo/` | infraestructura base: arranque de la app, logging, utilidades compartidas. Está en Diseño Modular §10; no es un MOD numerado ni tiene CA. En inc. 1 puede alojar el logging que pide T-03 o quedar mínimo. |
| `backend/pruebas/` | RNF-06 · solo código de prueba, sin datos (D-8) |
| `datos/pruebas/` | fixtures fabricados, commiteados (D-8) |
| `datos/referencia/` | espectros reales (en `.gitignore`; ver Licencias) |

**Verificación previa (T-00):** que el archivo de configuración exista y sea el que el código va a cargar (D-6), que `.gitignore` excluya cualquier archivo subido por el usuario, y que el README diga cómo levantar el backend y abrir el frontend.

## 7. Orden de trabajo y dependencias

| Orden | Tarea | Predecesora | Esfuerzo | Responsable (Paso 7) |
|---|---|---|---|---|
| 0 | T-00 verificación del repositorio | — | B | Tú (impl.) |
| 0 | T-0R conjunto de prueba real (∥ todo) | — | M | Compañero (revisor), Paso 8 |
| 1 | T-01 UT-03 | T-00 | B | Tú (impl.) · rev. compañero |
| 2 | T-02 UT-02 (∥ T-01) | T-00 | B | Tú (impl.) · rev. compañero |
| 3 | T-03 MOD-02 | **T-01** | M | Tú (impl.) · rev. compañero |
| 4 | T-04 MOD-03 contenido real | **T-02** (con contenido simulado) | M-A | Tú (impl.) · rev. compañero |
| 5 | T-05 MOD-03 puntos y rango | T-04 | M | Tú (impl.) · rev. compañero |
| 6 | T-06 MOD-01 (∥ T-03/04/05) | **T-02** (con veredictos simulados) | M | Tú (impl.) · rev. compañero |
| 7 | T-07 integración E2E | T-03 + T-05 + T-06 | M | Tú (impl.) · compañero: pruebas/evidencia |

> **Los fixtures fabricados deben estar antes de T-03**, no antes de T-04 como sugiere el riesgo del Paso 8: CA-01.2, CA-02.2 y las tres de RNF-09 ya son de T-03 y necesitan los archivos de 5 MB y ~3 MB. Son **sintéticos** (sección 11), así que Claude Code los genera en el segundo prompt, antes de arrancar T-03.

> **T-04 y T-06 dependen de T-02:** ni el validador ni la interfaz pueden emitir un rechazo sin el catálogo de mensajes. Si se escriben antes, los textos terminan quemados en el código y hay que refactorizar.

**Cadena crítica:** T-03 → T-04 → T-05 → T-07, secuencial y no repartible. Mitigación del Paso 8: el compañero toma pruebas y evidencias y revisa cada tarea al cerrarla.

## 8. Tareas

Cada tarea termina cuando pasan las pruebas que se nombran en ella (detalle en la sección 10).

### T-00 · Verificación del repositorio
- **Objetivo:** confirmar el árbol de la sección 6 antes de codificar (primer riesgo del Paso 8).
- **Terminado:** rutas verificadas, `.gitignore` correcto, README con instrucciones de arranque.

### T-0R · Datos de prueba — `datos/pruebas/` (fabricado) y `datos/referencia/` (real)
- **Objetivo:** dejar listos los dos conjuntos de datos. Es trabajo de datos, no de código, y corre en paralelo a todo.
- **Fixtures fabricados — los que usan las pruebas del incremento 1:** archivos estructuralmente válidos **sin contenido de NIST**, porque el incremento 1 solo valida estructura, tamaño, puntos y rango. Los genera Claude Code (segundo prompt) y van commiteados en `datos/pruebas/`; los pesados (5 MB, ~3 MB) se generan en el arranque de las pruebas, no al repo (sección 11).
- **Espectros reales — para el incremento 2 en adelante:** **NIST Chemistry WebBook** (`webbook.nist.gov`). Identificadores: acetona `C67641`, ácido benzoico `C65850`, anilina `C62533`. **Ya descargados y verificados** (sección 11). Son de Coblentz, con copyright: en el repo público **no se versionan** — `datos/referencia/` va en `.gitignore` y se commitea un **script de descarga + manifiesto** que los reproduce (ver «Licencias»). SDBS no hace falta aquí; se reserva para el dataset del incremento 3.
- **Terminado:** `datos/pruebas/` commiteado con los fixtures y sus notas de CA; `datos/referencia/` en `.gitignore` con el script + manifiesto commiteados; las pruebas de T-03 corren sin descargar nada.

### T-01 · UT-03 Configuración — `backend/utilerias/configuracion/`
- **Objetivo:** que el archivo ya creado sea la **única fuente operativa** de los parámetros (sección 3). La tarea no es escribir el archivo, es conectarlo.
- **Terminado:** los demás módulos leen de aquí y ninguno repite los valores; al cargar se valida que las llaves obligatorias **estén todas y sean coherentes** y, si falta una, el backend **no arranca** y da un error claro. **Prueba de que sirve de verdad:** cambiar un valor en el archivo (p. ej. `puntos_minimos` a 500) cambia el comportamiento de MOD-03 sin tocar una línea de código.
- **Pruebas:** `UT-03 · configuración incompleta`.

### T-02 · UT-02 Mensajes — `backend/utilerias/mensajes/`
- **Objetivo:** traducir códigos a mensajes con **motivo y acción** (RNF-01).
- **Insumos:** los cuatro textos literales de la sección 4; el resto del catálogo se completa según aparezcan los casos.
- **Terminado:** cada código devuelve título, texto y acción; el mensaje de formato se arma desde la lista de UT-03, no escrito a mano.
- **Pruebas:** unitarias de catálogo (código → mensaje esperado).

### T-03 · MOD-02 Manejador de archivos — `backend/manejador_archivos/`
- **Objetivo:** recibir, aplicar el tamaño, leer como texto y descartar.
- Leer **por bloques** contando bytes; al pasar el límite de UT-03, cortar y rechazar **sin leer el resto**. No confiar en el tamaño que declara el navegador.
- Contenido **solo en memoria**; nunca escribir el archivo en disco.
- **Cerrar siempre** el archivo subido en un bloque que se ejecute con éxito o con error (`try/finally`): FastAPI crea un temporal en disco si la subida pasa de 1 MB.
- Los logs guardan **solo nombre, tamaño y resultado**, nunca el contenido del espectro.
- **Terminado:** entrega contenido o rechazo con código.
- **Pruebas:** CA-01.2, CA-02.2 y las **tres de RNF-09**.

### T-04 · MOD-03 Validador (contenido real) — `backend/validacion/`
- **Objetivo:** confirmar que el contenido **es de verdad** del formato. La extensión se revisa, pero no se confía solo en ella. Cuatro capas, cada una con su rechazo:
  0. **¿La extensión está permitida?** `.jdx` o `.csv` (lista de UT-03). Si no (`.png`, etc.) → **E-FORMATO-NO-SOPORTADO** (CA-01.3). Va **antes** que «¿es texto?» para que un `.png` dé el mensaje de formato, no el de binario.
  1. **¿Es texto?** Bytes nulos, no imprimibles, o el carácter de reemplazo `U+FFFD` «�» (donde MOD-02 dejó los bytes inválidos; ver contrato §5) → rechazo inmediato (defensa RNF-03: nunca interpretamos binario).
  2. **¿La estructura coincide con el formato declarado?** `.jdx`: etiquetas obligatorias de UT-03, con `##TITLE=` en la primera línea y `##END=` en la última, más una de las etiquetas de datos. `.csv`: las primeras filas de datos parsean como pares numéricos (número de onda, intensidad), con separador **coma o punto y coma** y una **fila de encabezado opcional** no numérica — ambas cosas las exige **Requerimientos §6.1**, así que rechazar un encabezado válido es un incumplimiento. Con separador `;` los campos pueden traer decimal con coma (Excel en español, `400,0;0,805`); con separador `,` el decimal es punto. (La conversión numérica real es de MOD-04; aquí solo se confirma que *parece* pares numéricos.)
  3. **¿Coherencia mínima?** Número razonable de filas y valores plausibles (número de onda positivo).
- **Separación clave:** aquí se responde «¿es de verdad este formato?»; «¿cumple los requisitos?» es T-05.
- **Pruebas:** CA-01.3, CA-02.4, CA-02.5.

### T-05 · MOD-03 Validador (puntos y rango)
- **Objetivo:** **lectura ligera**: contar puntos y mirar mínimo/máximo del número de onda, contra `validacion.puntos_minimos` (300) y `validacion.rango_requerido_cm1` (1400–3700). **No normaliza, no ordena, no convierte** (eso es MOD-04, incremento 2).
- **CSV:** recorre **todas** las filas de datos (T-04 solo miró las primeras diez, por eso hoy pasa un CSV con basura al final); cuenta pares y toma min/máx de la primera columna; salta el encabezado si lo hay.
- **`.jdx`:** lee `##NPOINTS=` (puntos) y `##FIRSTX=`/`##LASTX=` (rango) del **encabezado** — texto ASCII, **no se descomprime el bloque XYDATA** (eso es MOD-04). Si faltan esas etiquetas, **falla cerrado** (igual que la decisión de fail-closed de T-04). Por eso **T-05 no necesita D-2**: D-2 sigue siendo decisión del incremento 2, antes de T-08.
- **Mensajes literales:** «Mínimo 300 puntos» (CA-02.6) y «Se requiere cubrir al menos 1400–3700 cm⁻¹» (CA-02.3).
- **Pruebas:** CA-02.1, CA-02.3, CA-02.6 (fixtures CSV: `espectro-un-punto-menos.csv`, `espectro-puntos-minimos.csv`, `espectro-rango-corto.csv`).

### T-06 · MOD-01 Interfaz mínima — `frontend/interfaz/`
- **Objetivo:** subir el archivo y mostrar el veredicto (HTML/CSS/JS puro), contra veredictos simulados mientras avanzan T-03/04/05.
- Al aceptar: muestra el **nombre del archivo**, el aviso de documento aprobado y el botón **«Analizar» habilitado y sin acción** (D-4).
- Al rechazar: muestra el mensaje con **motivo y acción**, sin detalles técnicos.
- Que el diseño no rompa a 360 px (adelanto de RNF-05; la prueba formal es del incremento 2).
- **Pruebas:** vista correcta según veredicto simulado; CA-01.1 en integración.

### T-07 · Integración MOD-01 → `api` → MOD-02 → MOD-03
- **Objetivo:** montar `POST /api/validar` en `backend/api/` y encadenar MOD-02 → MOD-03 (ya listos y probados aislados; **no se tocan**). `api/` es un orquestador delgado.
- **Veredicto en un solo lugar:** MOD-02 y MOD-03 devuelven un **código**; `api/` lo traduce con UT-02 al veredicto del contrato §5 (`{valido:false, codigo, titulo, mensaje, accion}`), en un único punto.
- **Códigos de estado:** 200 siempre que pueda emitir veredicto (un rechazo es resultado de negocio); 500 solo ante fallo interno, con el **mensaje genérico de UT-02** (el pendiente de §5) y **sin detalles técnicos**.
- **Límite:** lo sigue aplicando MOD-02 leyendo por bloques, **no** FastAPI ni el servidor (si lo corta la infraestructura, CA-02.2 deja de probar el código).
- **Arranque:** falla ruidoso si UT-03 está incompleta (`CONFIGURACION_INCOMPLETA`), como pide T-01.
- **Mismo origen:** sirve el frontend como archivos estáticos para que `fetch("/api/validar")` no cruce orígenes.
- **Opcional:** servir a la vista los formatos permitidos y el tamaño máximo desde UT-03 (sin `accept` en el selector, para que un `.png` siga siendo elegible y dé el mensaje de CA-01.3).
- **Terminado:** CA-01.1 de punta a punta (sube el `.jdx` válido → nombre + «Analizar» habilitado) y el resto de la sección 10 en integración; con eso cierra **H5** y el incremento es demostrable. La prueba automatizada usa el `.jdx` fabricado de `datos/pruebas/`; la captura de evidencia puede usar el acetona local.

## 9. Qué puede probarse aislado (Paso 3 del Plan V3)

- **UT-03:** leer cada parámetro y obtener el valor esperado; configuración incompleta → error de arranque.
- **UT-02:** dado un código → el mensaje esperado (motivo + acción).
- **MOD-02:** con archivos de prueba (válido / >5 MB / vacío) → contenido o rechazo por tamaño. **Sin MOD-03 real.**
- **MOD-03:** con contenido **simulado** (válido / extensión mentirosa / estructura rota / 299 vs 300 puntos / rango corto) → veredicto correcto. **Sin MOD-02 real.**
- **MOD-01:** con un veredicto **simulado** → la vista correcta.

## 10. Pruebas del incremento

| ID | Tipo | Entrada / condición | Resultado esperado | Nivel | Tarea | Evidencia |
|---|---|---|---|---|---|---|
| CA-01.1 | Normal | `.jdx` válido (~300 KB) | Acepta, muestra el nombre y «Analizar» queda habilitado | E2E | T-07 | Captura + archivo + registro |
| CA-01.2 | Límite | CSV válido de exactamente 5 242 880 bytes | Acepta | Unitaria (MOD-02) | T-03 | Resultado + archivo |
| CA-01.3 | Error | `.png` u otro formato no admitido | Rechaza con el mensaje de formato de UT-02 | Unitaria + E2E | T-04 | Captura + archivo |
| CA-02.1 | Normal | CSV de 2 columnas, 900 puntos, rango 400–4000 | Marca «válido» y continúa | Unitaria (MOD-03) | T-05 | Resultado + entrada |
| CA-02.2 | Límite | Archivo de 5 242 881 bytes | Rechaza «el tamaño máximo permitido es de 5 MB» | Unitaria (MOD-02/03) | T-03 | Resultado + archivo |
| CA-02.3 | Límite | Espectro que solo cubre 1500–3700 cm⁻¹ | Rechaza «se requiere cubrir al menos 1400–3700 cm⁻¹» | Unitaria (MOD-03/UT-03) | T-05 | Resultado + entrada |
| CA-02.4 | Error | Archivo vacío (0 bytes) o `.jdx` truncado (sin `##END=`/`##XYDATA=`) | Muestra el motivo; no se detiene de forma abrupta y atiende la siguiente petición | Unitaria (MOD-03/UT-02) | T-04 | Captura + entrada |
| CA-02.5 | Error | Ejecutable renombrado a `.csv` (binario) | Rechaza **por su contenido**; no lo ejecuta ni lo almacena | Unitaria / seguridad | T-04 | Resultado + entrada |
| CA-02.6 | Límite | Espectro con 299 vs 300 puntos | 300 → válido; 299 → rechazo «mínimo 300 puntos» | Unitaria (MOD-03) | T-05 | Resultado + entrada |
| UT-03 | Error | Configuración sin una llave obligatoria | Error de configuración claro; **no arranca en silencio** | Unitaria (UT-03) | T-01 | Registro del error |
| RNF-09 | Normal | CSV válido de ~3 MB (>1 MB, fuerza el temporal de FastAPI) | Al terminar la petición no queda ningún archivo del usuario en el directorio temporal | Integración (MOD-02) | T-03 | Listado del directorio antes y después |
| RNF-09 | Error | Error simulado a mitad de la lectura (mock) | Mensaje claro (UT-02) y el temporal **también** se elimina | Unitaria con mock | T-03 | Registro + listado del directorio |
| RNF-09 | Límite | 5 MB + 1 byte que declara un tamaño menor | Rechaza al pasar el límite, sin leer el resto y sin dejar temporal | Unitaria (MOD-02) | T-03 | Resultado + listado del directorio |

## 11. Archivos de prueba a preparar antes de T-03

El incremento 1 **solo valida estructura, tamaño, puntos y rango** — nunca mira química real. Por eso sus fixtures son **fabricados**: archivos estructuralmente válidos (etiquetas correctas, conteo de puntos correcto), **sin contenido de NIST**. Esto cumple todas las CA del incremento, evita el problema de licencia del repo público y deja que el revisor corra las pruebas sin descargar nada.

Van commiteados en `datos/pruebas/`, cada uno con nota del CA que cubre. **Excepción:** los archivos grandes (5 MB, ~3 MB) **no** se commitean —no metan binarios de megabytes al historial de git— sino que se generan en el arranque de las pruebas.

| Archivo (fabricado) | Cómo | Para |
|---|---|---|
| `.jdx` válido pequeño | etiquetas mínimas correctas + `##XYDATA=` con puntos sintéticos | CA-01.1 |
| CSV de 2 columnas, 900 puntos, 400–4000 | números sintéticos | CA-02.1 |
| CSV de exactamente 5 242 880 bytes, ≥300 puntos, 1400–3700 | sintético; **generado en el arranque de pruebas**, no commiteado | CA-01.2 |
| Archivo de 5 242 881 bytes | el anterior + 1 byte; generado en pruebas | CA-02.2 |
| CSV recortado a 1500–3700 | sintético | CA-02.3 |
| Par de CSV con 299 y 300 puntos | sintético | CA-02.6 |
| CSV de ~3 MB | sintético; generado en pruebas | RNF-09 |
| Archivo de 0 bytes y `.jdx` truncado (sin `##END=`) | fabricados | CA-02.4 |
| Binario renombrado a `.csv`, y un `.png` | fabricados | CA-02.5 y CA-01.3 |

> Conviene bajar el **mismo compuesto en `.jdx` y en `.csv`**: sirve para este incremento y es exactamente lo que pide T-08 en el incremento 2 (que ambos produzcan los mismos pares).

### Fase del espectro: elegir bien o el archivo no sirve

NIST publica espectros en **fase gas** y en **fase condensada** (líquido o sólido), y no son intercambiables: la recomendación estándar es no comparar un espectro de fase gas con uno de fase líquida. Para este proyecto importa de forma concreta:

- **Ácido benzoico (CA-05.2):** bajar el de **fase condensada**. La banda ancha e intensa de O–H que describe el catálogo (GF-01) viene de los puentes de hidrógeno, que en fase gas prácticamente desaparecen. Con el espectro de fase gas, el espectro no se parece a lo que dice la tabla de correlación.
- **Acetona (CA-05.1):** el C=O se desplaza unos cm⁻¹ entre fases. Anotar en la nota de origen del archivo cuál se usó, para que el día que el motor dé un número raro se sepa contra qué se está midiendo.

Anoten la fase junto al origen de cada archivo. En el incremento 1 no cambia el resultado de ninguna prueba —aquí solo se valida estructura, puntos y rango—, pero estos mismos archivos son los que van a usar en el incremento 3 contra CA-05.1 y CA-05.2, y ahí sí decide.

### El CSV de un espectro real (para el incremento 2, no para el 1)

Los fixtures del incremento 1 son sintéticos (arriba). Cuando en el incremento 2 haga falta el `.csv` de un espectro **real** —para T-08, que verifica que `.jdx` y `.csv` del mismo compuesto den los mismos pares— se obtiene convirtiendo uno de los `.jdx` descargados con un **script suelto, fuera de la aplicación**. Interpretar JCAMP-DX es trabajo de MOD-04: ese script es solo una herramienta de fixtures y **no debe quedar dentro del código** ni volverse la base de MOD-04 sin revisarlo.

### Espectros reales ya elegidos (registro de T-0R)

Material para el incremento 2 en adelante (no para los fixtures del incremento 1, que son sintéticos). Todos de NIST Chemistry WebBook, Coblentz, en `##YUNITS=TRANSMITTANCE` y con factores de escala en 1. **Los tres llevan copyright de Coblentz**, así que no se commitean en el repo público (ver «Licencias»).

| Archivo | Compuesto | Espectro elegido | Rango · puntos | Por qué |
|---|---|---|---|---|
| `67-64-1-IR.jdx` | Acetona | Coblentz · SOLUTION (10 % CCl₄ 4000–1330, CS₂ 1330–600) · Beckman IR-7 · 4 cm⁻¹ | 598.7–3983.5 · 5216 | Fase condensada; cubre hasta 4000 como el eje de la gráfica. No hay espectro de líquido puro disponible. |
| `65-85-0-IR.jdx` | Ácido benzoico | Coblentz · SOLID (SPLIT MULL) · DOW KBr · 2 cm⁻¹ | 453–3816 · 3364 | Sólido en transmisión. El «split mull» evita que las bandas C–H del nujol contaminen 2850–2960 (GF-03). |
| `62-53-3-IR.jdx` | Anilina | Coblentz · LIQUID (NEAT) · Beckman IR-7 · 4 cm⁻¹ | 600–3952.4 · 4158 | Líquido puro; muestra los dos picos N–H de amina primaria (GF-02). |

**Descartados, y por qué importa conservarlos:**

- Ácido benzoico de PNNL/Johnson — `##YUNITS=Reflectance` (reflectancia difusa con esfera integradora).
- Etanol de PNNL/Myers — `##YUNITS=dispersion index`, `##YLABEL=Real refractive index`: no es un espectro de absorción sino el índice de refracción real.

Guardarlos aparte como **casos de error reales**: §6.1 solo admite transmitancia o absorbancia, pero ningún CA valida la unidad, así que hoy ambos pasarían MOD-03 y llegarían a MOD-04. Ver la nota de abajo.

**Etanol: no se bajó.** La única opción condensada que quedaba era una solución al 10 %, donde parte del O–H queda sin asociar y aparece un pico angosto de O–H libre cerca de 3640 cm⁻¹ junto a la banda ancha. Aportaba poco: su C–H alifático ya está en la acetona. Los grupos que siguen sin espectro son **GF-04 (C≡N)** y **GF-06 (C=C)**; se resuelven al armar el dataset del incremento 3, no aquí.

### Dos trampas encontradas en los archivos reales

1. **`##DELTAX=` puede traer el signo equivocado.** En `65-85-0-IR.jdx` dice `+1`, pero el eje baja de 3816 a 453; según la especificación debería ser −1. **MOD-04 debe deducir la dirección comparando `##FIRSTX=` contra `##LASTX=`, nunca por el signo de DELTAX** (T-08/T-09, CA-03.2).
2. **Contaminación de solvente en la acetona.** El archivo declara `$$SPECTRAL CONTAMINATION DUE TO CCl4 AROUND 1550, AND CS2 AROUND 855 CM^-1`. Los 1550 cm⁻¹ caen dentro de 1450–1600, que es **GF-07 (anillo aromático)**, y la acetona no tiene anillo. No rompe CA-05.1 —solo exige detectar C=O— pero explica de antemano un posible falso positivo en el incremento 3.

### Decisión abierta para el equipo: validar `##YUNITS=`

En cuatro descargas reales aparecieron tres unidades distintas: transmitancia, reflectancia e índice de refracción. §6.1 declara que solo se admiten transmitancia y absorbancia, pero RF-02 no la menciona y ningún CA la cubre. Propuesta a discutir: añadir la lista de unidades admitidas a UT-03 y la verificación a MOD-03, con su propio mensaje en UT-02. **Es un cambio de alcance: requiere aprobación del equipo antes de implementarse, no lo metan por cuenta propia en el incremento 1.**

### Licencias (repo público)

Los tres espectros reales son de la **Coblentz Society** y llevan copyright («Collection © copyright by the U.S. Secretary of Commerce… All rights reserved»; el ácido benzoico, «© 1988 by Coblentz Society Inc.»). Usarlos para estudiar es uso académico sin problema; **commitearlos en un repo público es redistribuirlos**, y eso es justo lo que el riesgo abierto n.º 4 de Requerimientos V3.1 manda revisar.

**Decisión del equipo (repo público):** los `.jdx` reales **no se versionan**. `datos/referencia/` queda en `.gitignore`; en su lugar se commitea un **script de descarga + manifiesto** (compuesto, CAS, ID de NIST, espectro elegido) para que cualquiera los reproduzca. Los **fixtures sintéticos** del incremento 1 sí se commitean: no contienen datos de NIST. Esto no es consejo legal, es la vía que evita el problema de redistribución de raíz.

## 12. Hitos

**H1** cimientos probados en unidad (T-00, T-01, T-02) → **H2** MOD-02 recibe y descarta sin residuos, pruebas RNF-09 en verde (T-03) → **H3** validación completa: CA-01.3 y CA-02.1–02.6 (T-04, T-05) → **H4** la UI muestra el veredicto (T-06) → **H5** flujo de punta a punta: CA-01.1 + CA-02 completo (T-07, incremento demostrable).

> H2 no se cierra hasta que pasen las tres pruebas RNF-09 de T-03.
> H3 necesita los fixtures fabricados listos (sección 11), no los espectros reales: el incremento 1 valida estructura, no química.

## 13. Qué no cubre este incremento aunque aparezca en «Cubre»

**RNF-01** se atiende aquí en su parte verificable por código: cada rechazo muestra motivo y acción (sección 4) y el flujo no pasa de los pasos previstos. Su verificación formal del Paso 6 —prueba de usabilidad con 3 a 5 estudiantes de química— **no** es parte del incremento 1; queda para cuando exista el flujo completo. No marquen RNF-01 como cerrado al terminar H5.
