"""Capa HTTP · orquestación de MOD-01 → MOD-02 → MOD-03 (T-07).

Uso habitual, desde la raíz del repositorio:

    uvicorn backend.api:crear_aplicacion --factory --reload

La interfaz queda en `http://127.0.0.1:8000/` y el endpoint del contrato D-5 en
`POST /api/validar`.

Dos piezas, a propósito:

- `aplicacion.py` encadena los módulos y sirve el frontend.
- `veredicto.py` es el **único** lugar donde un código se vuelve el mensaje de
  UT-02 que ve el usuario.
"""

from backend.api.aplicacion import (
    CAMPO_ARCHIVO,
    CARPETA_FRONTEND,
    CODIGO_FALLO_INTERNO,
    CODIGO_PETICION_INVALIDA,
    RUTA_ANALIZAR,
    RUTA_INTERFAZ,
    RUTA_LIBRERIAS,
    RUTA_PROCESAR,
    RUTA_REPORTE,
    RUTA_SERVICIOS,
    RUTA_VALIDAR,
    RUTA_VISOR,
    crear_aplicacion,
)
from backend.api.veredicto import aceptado, analizado, procesado, rechazado

__all__ = [
    "CAMPO_ARCHIVO",
    "CARPETA_FRONTEND",
    "CODIGO_FALLO_INTERNO",
    "CODIGO_PETICION_INVALIDA",
    "RUTA_ANALIZAR",
    "RUTA_INTERFAZ",
    "RUTA_LIBRERIAS",
    "RUTA_PROCESAR",
    "RUTA_REPORTE",
    "RUTA_SERVICIOS",
    "RUTA_VALIDAR",
    "RUTA_VISOR",
    "aceptado",
    "analizado",
    "crear_aplicacion",
    "procesado",
    "rechazado",
]
