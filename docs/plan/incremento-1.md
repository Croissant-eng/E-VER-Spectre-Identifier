# Incremento 1 (A) — Subir y validar el espectro

Resumen operativo del Plan de Implementación V2 (Pasos 3, 4, 6 y 7). Ante cualquier duda, manda el plan completo.

**Objetivo:** el usuario sube un `.jdx` o `.csv` y recibe «aceptado» o «rechazado con motivo».
**Cubre:** RF-01, RF-02 · HU-01, HU-02 · CA-01.1–01.3, CA-02.1–02.6 · RNF-03, RNF-09.
**Fuera de este incremento:** procesar/normalizar, gráfica, identificación, explicaciones, PDF.

## Parámetros confirmados (viven en UT-03)
| Parámetro | Valor |
|---|---|
| Tamaño máximo | 5 MB |
| Formatos | `.jdx`, `.csv` |
| Puntos mínimos | 300 (CA-02.6) |
| Rango que debe cubrir | 1400–3700 cm⁻¹ |
| Etiquetas JCAMP-DX mínimas | `##TITLE=` (primera línea), `##JCAMP-DX=`, `##XUNITS=`, `##YUNITS=`, `##XYDATA=` o `##PEAK TABLE=`, `##END=` (última línea) |

## Orden de trabajo
1. **T-01 ∥ T-02** — UT-03 y UT-02 (sin dependencias).
2. **T-03** — MOD-02 (necesita T-01).
3. **T-04 → T-05** — MOD-03 (puede empezar con contenido simulado).
4. **T-06** — MOD-01, en paralelo a T-03/04/05, contra veredictos simulados.
5. **T-07** — integración de punta a punta.

## Tareas
### T-01 · UT-03 Configuración — `backend/utilerias/configuracion/`
- **Objetivo:** concentrar los parámetros en un solo lugar (partir de `parametros.ejemplo.json`).
- **Terminado:** los demás módulos leen de aquí; si falta un parámetro, el backend no arranca y da un error claro.

### T-02 · UT-02 Mensajes — `backend/utilerias/mensajes/`
- **Objetivo:** traducir códigos a mensajes con motivo y acción.
- **Rechazos a cubrir:** formato no soportado, tamaño excedido, no es texto, estructura inválida, puntos insuficientes, fuera de rango.
- **Terminado:** cada código devuelve su mensaje.

### T-03 · MOD-02 Manejador de archivos — `backend/manejador-archivos/`
- **Objetivo:** recibir, aplicar el tamaño, leer como texto y descartar.
- Leer **por bloques** contando bytes; al pasar 5 MB, cortar y rechazar sin leer el resto.
- Contenido **solo en memoria**; nunca escribir el archivo en disco.
- **Cerrar siempre** el archivo subido (try/finally): FastAPI crea un temporal en disco si pasa de 1 MB.
- Los logs guardan solo nombre, tamaño y resultado.
- **Terminado:** pruebas RNF-09 en verde.

### T-04 · MOD-03 Validador (contenido real) — `backend/validacion/`
- **Objetivo:** confirmar que el contenido es de verdad del formato, sin confiar en la extensión.
- Rechazar binario (bytes nulos / no imprimibles).
- `.jdx`: exigir la lista mínima de etiquetas. `.csv`: pares numéricos separados por coma.
- **Terminado:** CA-02.4, CA-02.5 y CA-01.3.

### T-05 · MOD-03 Validador (puntos y rango)
- **Objetivo:** lectura **ligera**: contar puntos y ver mínimo/máximo del número de onda. No normaliza (eso es MOD-04).
- **Terminado:** CA-02.1, CA-02.3, CA-02.6.

### T-06 · MOD-01 Interfaz mínima — `frontend/interfaz/`
- **Objetivo:** subir el archivo y mostrar el veredicto (HTML/CSS/JS puro).
- **Terminado:** muestra «aceptado» o «rechazado con mensaje» según el veredicto.

### T-07 · Integración MOD-01 → MOD-02 → MOD-03
- **Terminado:** todos los casos de abajo pasan de punta a punta.

## Pruebas del incremento
| ID | Tipo | Entrada | Resultado esperado |
|---|---|---|---|
| CA-01.1 | Normal | `.jdx` válido (~300 KB) | Acepta, muestra el nombre y habilita «Analizar» |
| CA-01.2 | Límite | CSV válido de exactamente 5 MB | Acepta |
| CA-01.3 | Error | `.png` u otro formato | Rechaza «Formato no soportado. Admitidos: .jdx, .csv» |
| CA-02.1 | Normal | CSV 2 columnas, 900 puntos, 400–4000 | Válido |
| CA-02.2 | Límite | 5 MB + 1 byte | Rechaza «el tamaño máximo es 5 MB» |
| CA-02.3 | Límite | Espectro que solo cubre 1500–3700 | Rechaza «se requiere cubrir al menos 1400–3700 cm⁻¹» |
| CA-02.4 | Error | Archivo vacío o `.jdx` truncado (sin `##END=`/`##XYDATA=`) | Motivo del error; no se detiene abruptamente |
| CA-02.5 | Error | Ejecutable renombrado a `.csv` | Rechaza por contenido; no lo ejecuta ni guarda |
| CA-02.6 | Límite | 299 vs 300 puntos | 300 válido; 299 rechazo «mínimo 300 puntos» |
| UT-03 | Error | Configuración sin un parámetro | Error de configuración claro; no arranca en silencio |
| RNF-09 | Normal | CSV válido de ~3 MB | No queda ningún archivo en el directorio temporal |
| RNF-09 | Error | Error simulado a mitad de la lectura | Mensaje claro y el temporal se elimina |
| RNF-09 | Límite | 5 MB + 1 byte que declara un tamaño menor | Rechaza al pasar el límite, sin temporal |

## Hitos
H1 cimientos (T-01, T-02) → H2 recibe y descarta sin residuos (T-03) → H3 validación completa (T-04, T-05)
→ H4 la UI muestra el veredicto (T-06) → H5 flujo de punta a punta (T-07).
