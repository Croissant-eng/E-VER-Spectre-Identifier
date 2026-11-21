# E-VER Spectre Identifier

Aplicación web educativa que identifica grupos funcionales en espectros infrarrojos (IR).
Sube un `.jdx` o `.csv`, la app lo valida, lo normaliza, identifica 7 grupos funcionales con un
motor híbrido (reglas + IA), resalta los picos con una explicación y genera un reporte PDF.

- **Cliente:** Universidad Iberoamericana Campus León
- **Desarrollador:** E-VER (Electronic-Versions) — Sergio Uriel Bustamante Bustos, Julio Antonio Jiménez Jiménez
- **Materia:** Desarrollo de Aplicaciones y Servicios Virtuales

## Estado
| Incremento | Contenido | Estado |
|---|---|---|
| 1 (A) | Subir y validar | En curso |
| 2 (B) | Procesar y ver el espectro | Pendiente |
| 3 (C) | Identificar grupos funcionales | Pendiente |
| 4 (D) | Capa educativa | Pendiente |
| 5 (E) | Reporte PDF | Pendiente |

## Stack
Python + FastAPI (backend) · HTML/CSS/JS puro (frontend) · sin base de datos.

## Estructura
```
frontend/              Zona de presentación (MOD-01 interfaz, MOD-05 visor)
backend/               Zona de procesamiento (MOD-02, 03, 04, 07, 08 y utilerías UT-01/02/03)
motor-identificacion/  MOD-06 · zona aislada (reglas, modelo, inferencia)
datos/                 Catálogo de grupos (no hay datos de usuarios)
docs/                  Requerimientos, diseño, plan y bitácora
```

## Cómo levantar el proyecto

Requiere **Python 3.11 o superior** (probado en 3.14.5). Desde la raíz del repositorio:

```bash
# 1. Entorno virtual (una sola vez)
python -m venv .venv

# 2. Activarlo
.venv\Scripts\activate       # Windows (PowerShell o CMD)
source .venv/bin/activate      # macOS / Linux

# 3. Dependencias
pip install -r requirements.txt
```

### Backend

```bash
uvicorn backend.api.aplicacion:app --reload --port 8000
```

> El punto de entrada `backend/api/aplicacion.py` queda disponible al cerrar **T-07**
> (integración de punta a punta). Hasta entonces el backend no se levanta todavía: lo que
> sí se puede ejecutar son las pruebas.

### Frontend

`frontend/interfaz/index.html` se abre directo en el navegador (HTML/CSS/JS puro, sin
compilación ni servidor de desarrollo). Llega con **T-06**; necesita el backend arriba para
que la validación responda de verdad.

### Pruebas

```bash
pytest
```

Lee `pytest.ini`: colecta `backend/pruebas/prueba_*.py`. Para una sola tarea:

```bash
pytest backend/pruebas/prueba_ut03_configuracion.py
```

## Configuración (UT-03)

Todos los parámetros operativos —tamaño máximo, formatos permitidos, puntos mínimos, rango
requerido y etiquetas JCAMP-DX— viven **únicamente** en
`backend/utilerias/configuracion/parametros.ejemplo.json`. Ningún módulo repite esos valores:
si el archivo cambia, el comportamiento cambia sin tocar código. Si al arrancar falta una llave
obligatoria, el backend **no arranca** y dice cuál falta.

## Cómo se trabaja
Una tarea del plan por vez (T-01, T-02…), con sus pruebas, y un commit por tarea con el ID en el mensaje.
Las reglas para Claude Code están en `CLAUDE.md`.

## Privacidad
Los archivos se procesan en memoria y se descartan al terminar; no se guarda nada del usuario (RNF-09).
