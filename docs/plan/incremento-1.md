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
| D-6 | **El archivo de configuración ya está creado** (`backend/utilerias/configuracion/`, nombre tal como está en el repo). | T-01 **no lo crea: lo pone a trabajar.** Debe comprobar que UT-03 lo lee de verdad en ejecución y que el archivo que carga el código es el mismo que está en el repo. Si conserva el sufijo `.ejemplo`, que sea porque **ese** es el archivo que se carga, no una plantilla muerta junto a otra real. |

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
- **MOD-02 → MOD-03:** el contenido del archivo **como texto**, su nombre y un indicador de «tamaño correcto»; o un **rechazo con código**.
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
| `backend/api/` | orquestación y límites |
| `backend/manejador-archivos/` | MOD-02 |
| `backend/validacion/` | MOD-03 |
| `backend/utilerias/configuracion/` | UT-03 · archivo de parámetros (ya creado) |
| `backend/utilerias/mensajes/` | UT-02 |
| `backend/pruebas/` | RNF-06 |
| `datos/referencia/` | espectros de prueba (NO datos de usuario) |

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

> **T-0R va en paralelo desde el día uno** y debe estar cerrada **antes de T-04** (riesgo del Paso 8): sin espectros reales, T-04 y T-07 se prueban contra archivos inventados y las pruebas no dicen nada.

> **T-04 y T-06 dependen de T-02:** ni el validador ni la interfaz pueden emitir un rechazo sin el catálogo de mensajes. Si se escriben antes, los textos terminan quemados en el código y hay que refactorizar.

**Cadena crítica:** T-03 → T-04 → T-05 → T-07, secuencial y no repartible. Mitigación del Paso 8: el compañero toma pruebas y evidencias y revisa cada tarea al cerrarla.

## 8. Tareas

Cada tarea termina cuando pasan las pruebas que se nombran en ella (detalle en la sección 10).

### T-00 · Verificación del repositorio
- **Objetivo:** confirmar el árbol de la sección 6 antes de codificar (primer riesgo del Paso 8).
- **Terminado:** rutas verificadas, `.gitignore` correcto, README con instrucciones de arranque.

### T-0R · Conjunto de prueba real — `datos/referencia/`
- **Objetivo:** conseguir los espectros reales y derivar de ellos los casos límite y de error (sección 11). Es trabajo de datos, no de código, así que corre en paralelo a todo.
- **De dónde:** **NIST Chemistry WebBook** (`webbook.nist.gov`), gratuito y ya nombrado en los documentos. Se busca el compuesto por nombre o número CAS, se entra a su página de especie y se abre **«IR Spectrum»**; ahí está la descarga en formato JCAMP-DX. Identificadores de los dos espectros de referencia que piden CA-05.1 y CA-05.2: **acetona = `C67641`** (CAS 67-64-1) y **ácido benzoico = `C65850`** (CAS 65-85-0). SDBS (`sdbs.db.aist.go.jp`) no hace falta en este incremento: no publica URL por espectro y conviene reservarlo para el dataset del incremento 3.
- **Estado:** los tres espectros reales **ya están descargados y verificados** (registro en la sección 11). Falta derivar de ellos los seis archivos restantes; esa parte sí la puede hacer Claude Code, son transformaciones mecánicas.
- **Terminado:** los nueve archivos de la sección 11 están en `datos/referencia/`, cada uno con una nota de qué CA cubre y de dónde salió; revisados los términos de uso antes de versionarlos.

### T-01 · UT-03 Configuración — `backend/utilerias/configuracion/`
- **Objetivo:** que el archivo ya creado sea la **única fuente operativa** de los parámetros (sección 3). La tarea no es escribir el archivo, es conectarlo.
- **Terminado:** los demás módulos leen de aquí y ninguno repite los valores; al cargar se valida que las llaves obligatorias **estén todas y sean coherentes** y, si falta una, el backend **no arranca** y da un error claro. **Prueba de que sirve de verdad:** cambiar un valor en el archivo (p. ej. `puntos_minimos` a 500) cambia el comportamiento de MOD-03 sin tocar una línea de código.
- **Pruebas:** `UT-03 · configuración incompleta`.

### T-02 · UT-02 Mensajes — `backend/utilerias/mensajes/`
- **Objetivo:** traducir códigos a mensajes con **motivo y acción** (RNF-01).
- **Insumos:** los cuatro textos literales de la sección 4; el resto del catálogo se completa según aparezcan los casos.
- **Terminado:** cada código devuelve título, texto y acción; el mensaje de formato se arma desde la lista de UT-03, no escrito a mano.
- **Pruebas:** unitarias de catálogo (código → mensaje esperado).

### T-03 · MOD-02 Manejador de archivos — `backend/manejador-archivos/`
- **Objetivo:** recibir, aplicar el tamaño, leer como texto y descartar.
- Leer **por bloques** contando bytes; al pasar el límite de UT-03, cortar y rechazar **sin leer el resto**. No confiar en el tamaño que declara el navegador.
- Contenido **solo en memoria**; nunca escribir el archivo en disco.
- **Cerrar siempre** el archivo subido en un bloque que se ejecute con éxito o con error (`try/finally`): FastAPI crea un temporal en disco si la subida pasa de 1 MB.
- Los logs guardan **solo nombre, tamaño y resultado**, nunca el contenido del espectro.
- **Terminado:** entrega contenido o rechazo con código.
- **Pruebas:** CA-01.2, CA-02.2 y las **tres de RNF-09**.

### T-04 · MOD-03 Validador (contenido real) — `backend/validacion/`
- **Objetivo:** confirmar que el contenido **es de verdad** del formato, sin confiar en la extensión. Tres capas, cada una con su rechazo:
  1. **¿Es texto?** Bytes nulos o no imprimibles → rechazo inmediato (defensa RNF-03: nunca interpretamos binario).
  2. **¿La estructura coincide con el formato declarado?** `.jdx`: etiquetas obligatorias de UT-03, con `##TITLE=` en la primera línea y `##END=` en la última, más una de las etiquetas de datos. `.csv`: las primeras filas parsean como pares numéricos (número de onda, intensidad) separados por coma.
  3. **¿Coherencia mínima?** Número razonable de filas y valores plausibles (número de onda positivo).
- **Separación clave:** aquí se responde «¿es de verdad este formato?»; «¿cumple los requisitos?» es T-05.
- **Pruebas:** CA-01.3, CA-02.4, CA-02.5.

### T-05 · MOD-03 Validador (puntos y rango)
- **Objetivo:** **lectura ligera**: contar puntos y mirar mínimo/máximo del número de onda. **No normaliza, no ordena, no convierte** (eso es MOD-04, incremento 2).
- **Pruebas:** CA-02.1, CA-02.3, CA-02.6.

### T-06 · MOD-01 Interfaz mínima — `frontend/interfaz/`
- **Objetivo:** subir el archivo y mostrar el veredicto (HTML/CSS/JS puro), contra veredictos simulados mientras avanzan T-03/04/05.
- Al aceptar: muestra el **nombre del archivo**, el aviso de documento aprobado y el botón **«Analizar» habilitado y sin acción** (D-4).
- Al rechazar: muestra el mensaje con **motivo y acción**, sin detalles técnicos.
- Que el diseño no rompa a 360 px (adelanto de RNF-05; la prueba formal es del incremento 2).
- **Pruebas:** vista correcta según veredicto simulado; CA-01.1 en integración.

### T-07 · Integración MOD-01 → `api` → MOD-02 → MOD-03
- **Objetivo:** cerrar el flujo de punta a punta con el contrato de la sección 5.
- **Terminado:** todas las pruebas de la sección 10 pasan y la evidencia queda guardada.

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

## 11. Archivos de prueba a preparar antes de T-04 y T-07

Riesgo del Paso 8: «falta de espectros `.jdx`/`.csv` reales». **Se parte de espectros reales descargados de NIST o SDBS** y de ellos se derivan los casos límite y de error; solo se fabrica lo que no puede existir en la naturaleza (un tamaño al byte exacto, un archivo truncado, un binario disfrazado). Trabajar con archivos inventados de principio a fin haría que las pruebas pasen sin demostrar nada: los `.jdx` reales de NIST traen datos comprimidos y factores de escala que un archivo hecho a mano no tiene.

Van en `datos/referencia/`, cada uno con nota de origen y del CA que cubre (T-0R).

| Archivo | Origen | Para |
|---|---|---|
| `.jdx` válido de ~300 KB | **ya descargado**: `67-64-1-IR.jdx` (acetona) | CA-01.1 |
| CSV de 2 columnas, 900 puntos, 400–4000 | convertido de uno de los tres `.jdx` reales | CA-02.1 |
| CSV válido de **exactamente 5 242 880 bytes**, ≥300 puntos, que cubra 1400–3700 | real + relleno de puntos hasta el tamaño exacto | CA-01.2 |
| Archivo de 5 242 881 bytes | el anterior + 1 byte | CA-02.2 |
| Espectro recortado a 1500–3700 | recorte de uno real | CA-02.3 |
| Par de espectros con 299 y 300 puntos | recortes de uno real | CA-02.6 |
| CSV válido de ~3 MB | real o relleno de uno real | pruebas RNF-09 |
| Archivo de 0 bytes y `.jdx` truncado (sin `##END=`) | fabricados a partir de uno real | CA-02.4 |
| Binario renombrado a `.csv`, y un `.png` sin renombrar | fabricados | CA-02.5 y CA-01.3 |

> Conviene bajar el **mismo compuesto en `.jdx` y en `.csv`**: sirve para este incremento y es exactamente lo que pide T-08 en el incremento 2 (que ambos produzcan los mismos pares).

### Fase del espectro: elegir bien o el archivo no sirve

NIST publica espectros en **fase gas** y en **fase condensada** (líquido o sólido), y no son intercambiables: la recomendación estándar es no comparar un espectro de fase gas con uno de fase líquida. Para este proyecto importa de forma concreta:

- **Ácido benzoico (CA-05.2):** bajar el de **fase condensada**. La banda ancha e intensa de O–H que describe el catálogo (GF-01) viene de los puentes de hidrógeno, que en fase gas prácticamente desaparecen. Con el espectro de fase gas, el espectro no se parece a lo que dice la tabla de correlación.
- **Acetona (CA-05.1):** el C=O se desplaza unos cm⁻¹ entre fases. Anotar en la nota de origen del archivo cuál se usó, para que el día que el motor dé un número raro se sepa contra qué se está midiendo.

Anoten la fase junto al origen de cada archivo. En el incremento 1 no cambia el resultado de ninguna prueba —aquí solo se valida estructura, puntos y rango—, pero estos mismos archivos son los que van a usar en el incremento 3 contra CA-05.1 y CA-05.2, y ahí sí decide.

### Cómo generar el CSV

Los espectros se bajan en `.jdx`; el `.csv` se obtiene convirtiendo uno de ellos con un **script suelto, fuera de la aplicación**. Interpretar JCAMP-DX y convertirlo a pares de números es trabajo de MOD-04 y pertenece al incremento 2: ese script es una herramienta para preparar fixtures y **no debe quedar dentro del código del incremento 1** ni convertirse después en la base de MOD-04 sin revisarlo.

### Espectros reales ya elegidos (registro de T-0R)

Los tres cubren lo que el incremento necesita; de ellos se derivan los seis archivos restantes. Todos de NIST Chemistry WebBook, en `##YUNITS=TRANSMITTANCE` y con factores de escala en 1.

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

### Licencias

Las páginas de NIST llevan la nota «Data compilation copyright by the U.S. Secretary of Commerce on behalf of the U.S.A.». Para uso académico no hay problema; revisar antes de versionar los archivos en un repositorio público (riesgo abierto n.º 4 de Requerimientos V3.1).

> **Licencias:** antes de versionar espectros de NIST/SDBS, revisar sus términos de uso (riesgo abierto n.º 4 de Requerimientos V3).

## 12. Hitos

**H1** cimientos probados en unidad (T-00, T-01, T-02) → **H2** MOD-02 recibe y descarta sin residuos, pruebas RNF-09 en verde (T-03) → **H3** validación completa: CA-01.3 y CA-02.1–02.6 (T-04, T-05) → **H4** la UI muestra el veredicto (T-06) → **H5** flujo de punta a punta: CA-01.1 + CA-02 completo (T-07, incremento demostrable).

> H2 no se cierra hasta que pasen las tres pruebas RNF-09 de T-03.
> H3 no se abre hasta que T-0R esté cerrada: sin espectros reales no hay con qué probar.

## 13. Qué no cubre este incremento aunque aparezca en «Cubre»

**RNF-01** se atiende aquí en su parte verificable por código: cada rechazo muestra motivo y acción (sección 4) y el flujo no pasa de los pasos previstos. Su verificación formal del Paso 6 —prueba de usabilidad con 3 a 5 estudiantes de química— **no** es parte del incremento 1; queda para cuando exista el flujo completo. No marquen RNF-01 como cerrado al terminar H5.
