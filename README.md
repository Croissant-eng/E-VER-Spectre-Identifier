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
| 1 (A) | Subir y validar | Completo |
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
motor_identificacion/  MOD-06 · zona aislada (reglas, modelo, inferencia)
datos/                 Catálogo de grupos, archivos de prueba y espectros de referencia
                       (no hay datos de usuarios)
herramientas/          Apoyo fuera de la aplicación: generar archivos de prueba, descargar espectros
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

### Levantar la aplicación

```bash
uvicorn backend.api:crear_aplicacion --factory --reload --port 8000
```

Y abrir **http://127.0.0.1:8000/**. Eso es todo: el mismo servidor sirve la interfaz y
atiende `POST /api/validar`, así que la página y el endpoint son del **mismo origen** y no
hace falta configurar nada más.

> Es `--factory` porque `backend/api` no expone una aplicación ya creada: crearla lee la
> configuración de UT-03, y eso no debe ocurrir por el solo hecho de importar el módulo. Si
> falta una llave obligatoria, **no arranca** y dice cuál falta.

### Frontend

No se abre `frontend/interfaz/index.html` con doble clic: el navegador no carga módulos de
JavaScript desde un archivo suelto y la llamada al servidor no tendría a quién preguntarle.
Se abre siempre por el servidor, en `http://127.0.0.1:8000/`.

### Pruebas

```bash
pytest
```

Un solo comando para todo: `pytest.ini` colecta `backend/pruebas/prueba_*.py` y esas
pruebas lanzan además las de JavaScript (`frontend/pruebas/*.test.js`) con `node --test`, el
corredor que ya viene dentro de Node —sin instalar nada ni compilar—. Si no hay Node
instalado, esas se saltan con un mensaje claro en vez de fallar.

Para una sola tarea:

```bash
pytest backend/pruebas/prueba_t07_integracion.py
```

## Configuración (UT-03)

Todos los parámetros operativos —tamaño máximo, formatos permitidos, puntos mínimos, rango
requerido y etiquetas JCAMP-DX— viven **únicamente** en
`backend/utilerias/configuracion/parametros.json`. Ningún módulo repite esos valores:
si el archivo cambia, el comportamiento cambia sin tocar código. Si al arrancar falta una llave
obligatoria, el backend **no arranca** y dice cuál falta.

## Cómo se trabaja
Una tarea del plan por vez (T-01, T-02…), con sus pruebas, y un commit por tarea con el ID en el mensaje.
Las reglas para Claude Code están en `CLAUDE.md`.

## Privacidad
Los archivos se procesan en memoria y se descartan al terminar; no se guarda nada del usuario (RNF-09).
