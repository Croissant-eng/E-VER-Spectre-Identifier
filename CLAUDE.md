# CLAUDE.md · E-VER Spectre Identifier

Guía para Claude Code en este repositorio. Responde siempre en español.

## Qué es

Aplicación web responsiva (proyecto escolar, Univ. Iberoamericana León, equipo E-VER: Sergio Uriel Bustamante Bustos y Julio Antonio Jiménez Jiménez). El usuario sube un espectro IR y, en 3 pasos (cargar → «Analizar» → revisar/descargar), obtiene:

- la gráfica del espectro (eje 4000 → 400 cm⁻¹),
- los grupos funcionales detectados (lista cerrada GF-01…GF-07) con su confianza en %,
- el pico/región resaltado y una explicación educativa por grupo,
- el aviso «No se encontraron detecciones confiables» si nada llega al umbral (nunca inventar resultados),
- un reporte PDF descargable.

Fuera de alcance: RMN, molécula completa, cuantificación, cuentas/login, historial, imágenes del espectro, app nativa.

## Fuente de verdad

Los documentos viven en `docs/` y mandan sobre cualquier conversación previa:

1. **Requerimientos + Matriz V3.1** (principal: RF-01…09, RNF-01…09, HU-01…09, 30 CA).
2. Diseño Modular v2 · MOD-06 Diseño Detallado v2 · Persistencia de Datos v2.
3. Plan de Implementación V3.0 (tareas T-01…T-27) y `docs/plan_incrementos.md`.
4. **`docs/plan/incremento-<N>.md`**: resumen operativo del incremento en curso (tareas, contratos, pruebas, fixtures). Léelo antes de empezar. Hoy: `docs/plan/incremento-1.md`.

Si el código, el plan y la especificación se contradicen, **no lo resuelvas en el código**: detente y pregunta al equipo. No inventes datos ni fechas; lo no confirmado se marca **SUPUESTO**. Si una decisión aprobada cambia, regístrala: qué cambió, por qué y qué RF/HU/CA afecta.

## Stack (confirmado)

- Backend: **Python + FastAPI**. Frontend: **HTML/CSS/JS puro** (sin frameworks).
- **Sin base de datos** (Persistencia v2): archivos de solo lectura + procesamiento en memoria.
- Motor MOD-06: reglas + CNN 1D, inferencia en CPU, servicio/proceso aparte (incremento 3).

> SUPUESTO: versión de Python, framework de pruebas (p. ej. pytest) y gestor de dependencias; ningún documento los fija.

## Decisiones cerradas

| # | Decisión | Consecuencia |
|---|---|---|
| D-0 | **Solo `.jdx` y `.csv`.** `.dx` queda fuera por ahora. | La lista vive en UT-03; el mensaje de rechazo se arma desde esa lista. |
| D-4 | **Botón «Analizar»** presente y habilitado al aceptar el archivo, **sin acción** (RF-04 es del incremento 3). | CA-01.1 verifica el estado del botón, no que analice. |
| D-5 | **`POST /api/validar`**, `multipart/form-data`, campo `archivo`. **200** siempre que haya veredicto: `{"valido": true, "nombre", "bytes"}` o `{"valido": false, "codigo", "titulo", "mensaje", "accion"}`. **500** solo ante fallo interno, con mensaje genérico de UT-02. | Un rechazo es resultado de negocio, no error HTTP (nada de 400/413). MOD-01 pasa siempre por `backend/api/`. |
| D-6 | **El archivo de configuración ya existe** en `backend/utilerias/configuracion/` (con el nombre que tiene en el repo). | T-01 no lo crea: lo conecta. El archivo que carga el código debe ser el mismo del repo; si lleva sufijo `.ejemplo`, es porque **ese** es el que se carga, no una plantilla muerta junto a otra real. Al arrancar son obligatorias solo `archivo.*` y `validacion.*`; si falta una, el backend no arranca y da un error claro. El bloque `motor` es opcional hasta el incremento 3. Prueba de que sirve: cambiar `puntos_minimos` en el archivo cambia el comportamiento de MOD-03 sin tocar código. |

Pendientes (se deciden al llegar, pregunta antes de elegir): D-1 librería de gráficas (incr. 2, antes de T-12), D-2 lector compartido MOD-03/MOD-04 (incr. 2, antes de T-08), D-3 librería de PDF en memoria (incr. 5, antes de T-25).

## Arquitectura

Flujo: Usuario → MOD-01 → `api` → MOD-02 → MOD-03 → MOD-04 → MOD-06 (aislado) → MOD-07 → MOD-01/MOD-05. Reporte: MOD-08 → descarga.

| ID | Módulo | Responsabilidad | Carpeta |
|---|---|---|---|
| MOD-01 | Interfaz web | Flujo de 3 pasos, resultados, mensajes. Sin lógica de análisis. | `frontend/interfaz/` (+ `frontend/servicios/` para la API) |
| MOD-02 | Manejador de archivos | Recibe, aplica el tamaño leyendo por bloques, lee como texto sin ejecutar, descarta. | `backend/manejador-archivos/` |
| MOD-03 | Validador | Contenido real (no la extensión), estructura, ≥300 puntos, rango 1400–3700 cm⁻¹. Lectura ligera: no normaliza, no ordena, no convierte. | `backend/validacion/` |
| MOD-04 | Procesador de espectros | Parsea JCAMP-DX/CSV, ordena, %T → absorbancia, normaliza 0–1, remuestrea a rejilla fija. | `backend/preprocesamiento/` |
| MOD-05 | Visualizador | Gráfica con eje invertido; resalta regiones y picos con color y leyenda. | `frontend/visor-espectro/` |
| MOD-06 | Motor de identificación | Híbrido: conf = wR·regla + wML·ML; umbral; ordena; «sin detecciones». Solo recibe números. Única parte con IA. | `motor-identificacion/` |
| MOD-07 | Capa educativa | Explicación y región por grupo detectado, desde UT-01. | `backend/educativo/` |
| MOD-08 | Generador de reportes | PDF al vuelo, sin guardarlo en el servidor. | `backend/reportes/` |
| UT-01 | Catálogo de grupos | Fuente única de los 7 grupos y acceso de solo lectura al modelo. | `backend/utilerias/catalogo/` + `datos/catalogo/grupos.json` |
| UT-02 | Errores y mensajes | Código → título, texto (motivo) y acción. | `backend/utilerias/mensajes/` |
| UT-03 | Configuración | Única fuente operativa de los parámetros. | `backend/utilerias/configuracion/parametros.ejemplo.json` (nombre actual en el repo, ver D-6) |

Otras carpetas: `backend/api/` (orquestación y límites), `backend/nucleo/`, `backend/pruebas/` (todas las pruebas, RNF-06; `backend/pruebas/archivos/` para archivos de prueba), `motor-identificacion/{reglas,modelo,inferencia,pruebas}/`, `datos/referencia/` (espectros de prueba de NIST/SDBS, **nunca** datos de usuario), `docs/`.

> Ojo: Python no importa carpetas con guion (`manejador-archivos`, `visor-espectro`, `motor-identificacion`). Si eso bloquea una tarea, no las renombres: propón la alternativa y espera aprobación.

Contrato MOD-04 → MOD-06 (MOD-06 Diseño §5): vector de absorbancia 0–1 en rejilla fija + eje 4000→400. Salida: `{detecciones: [{grupo, confianza, region_cm1, pico_cm1, evidencia:{regla, ml}}], sin_detecciones, umbral}`. Plan B: wML = 0 (solo reglas) sin cambiar el contrato.

> SUPUESTO: tamaño de la rejilla (el diseño da N = 1024 solo como ejemplo). Se agrega a `parametros.json` en el incremento 2, no antes.

## Plan: 5 incrementos

| # | Objetivo | RF / HU | Módulos nuevos | Tareas | CA |
|---|---|---|---|---|---|
| 1 | Subir y validar | RF-01, RF-02 / HU-01, 02 | MOD-01 (mínima), MOD-02, MOD-03, UT-02, UT-03 | T-00…T-07 | CA-01.1–01.3, CA-02.1–02.6 |
| 2 | Procesar y ver espectro | RF-03, RF-09 / HU-03, 04 | MOD-04, MOD-05 | T-08…T-13 | CA-03.1–03.3, CA-04.1–04.3 |
| 3 | Identificar grupos | RF-04, RF-07 / HU-05, 08 | MOD-06, UT-01 | T-14…T-19 | CA-05.1–05.4, CA-08.1–08.3 |
| 4 | Capa educativa | RF-05, RF-06 / HU-06, 07 | MOD-07, MOD-05 (resaltado) | T-20…T-24 | CA-06.1–06.3, CA-07.1–07.3 |
| 5 | Reporte PDF | RF-08 / HU-09 | MOD-08 | T-25…T-27 | CA-09.1–09.3 |

Orden del incremento 1: T-00 → T-01 ∥ T-02 → T-03 (necesita T-01) · T-04 y T-06 (necesitan **T-02**) → T-05 → T-07. **T-0R** (espectros reales de NIST/SDBS en `datos/referencia/`) corre en paralelo desde el inicio y debe cerrarse **antes de T-04**. El detalle está en `docs/plan/incremento-1.md`.

## Reglas de trabajo

1. **Explica el enfoque antes de codificar.** Para cada tarea: qué archivos tocas, qué RF/CA atiende y qué prueba lo demuestra. Espera el visto bueno.
2. **Solo el incremento en curso.** Hoy: no implementes nada de MOD-04, MOD-05, MOD-06, MOD-07, MOD-08 ni UT-01. Si una tarea parece necesitarlos, detente y pregunta.
3. **No agregues dependencias** de gráficas, machine learning ni PDF hasta que se cierren D-1 y D-3. No cambies la arquitectura ni el alcance sin preguntar.
4. **Sin base de datos.**
5. **Nada «hardcodeado»:** todo parámetro sale de UT-03 y todo mensaje de UT-02. Nada de 5 MB, 300, 1400–3700, 0.6 ni textos de error escritos en otros módulos. Las regiones de los grupos salen de UT-01.
6. **Procesar en memoria (RNF-09).** Nunca escribir el archivo del usuario a disco. El límite de 5 MB lo aplica **MOD-02 leyendo por bloques** (no FastAPI ni el servidor) y corta sin leer el resto. Cerrar siempre el archivo subido en `try/finally` (FastAPI crea un temporal arriba de 1 MB). Logs solo con nombre, tamaño y resultado, nunca el contenido. El PDF se genera y entrega sin guardarse.
7. **Seguridad (RNF-03):** el archivo es solo datos; rechazar binario; JCAMP-DX válido exige `##TITLE=` en la **primera** línea y `##END=` en la **última**.
8. **Mensajes vía UT-02** con motivo y acción, sin detalles técnicos. Cuatro textos son literales porque los CA los verifican:
   - CA-01.3: «Formato no soportado. Formatos admitidos: *lista leída de UT-03*»
   - CA-02.2: «El tamaño máximo permitido es de 5 MB»
   - CA-02.3: «Se requiere cubrir al menos 1400–3700 cm⁻¹»
   - CA-02.6: «Mínimo 300 puntos»
9. **Una prueba por cada CA**, en `backend/pruebas/`, nombrada con su ID (p. ej. `test_CA_02_6_...`); cada módulo con caso normal, límite y error (RNF-06). No afirmes que una prueba pasó si no se ejecutó. Los fixtures van en `datos/referencia/`: se parte de espectros **reales** y solo se fabrica lo que no existe en la naturaleza (tamaño al byte exacto, truncado, binario disfrazado). Revisar licencias de NIST/SDBS antes de versionarlos.
10. **Un commit por tarea** con su ID: `T-01: descripción`. Agrega archivos por nombre (no `git add .`); `.env` y cualquier archivo subido por el usuario en `.gitignore`.
    > SUPUESTO: la guía del profesor pide además `tipo(RF-XX): descripción`; se pueden combinar como `T-03: feat(RF-01) leer archivo en memoria`. Confirmar con el equipo.
11. **Rama por incremento** (`incremento-N`) y **tag al cerrarlo** (`v0.N.0`, p. ej. `v0.2.0`).
    > SUPUESTO: que el incremento 1 lleve `v0.1.0`.
12. **Regresión antes de cerrar:** ejecutar todas las pruebas, incluidas las de incrementos anteriores; si algo se rompe, proponer la corrección sin aplicarla hasta que el equipo autorice.
13. **Documentos en `docs/`;** al cerrar un incremento, actualizar README, matriz de trazabilidad, bitácora de IA y `docs/plan_incrementos.md`.
