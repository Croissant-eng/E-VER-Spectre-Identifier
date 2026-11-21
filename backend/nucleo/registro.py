"""Registro (logging) del backend.

Un solo lugar decide **cómo se nombran** los registros del proyecto, para que el
día que haya que silenciarlos o mandarlos a un archivo se haga en una línea.

**La regla que este módulo existe para sostener (RNF-09):** el registro guarda
*qué pasó*, nunca *qué traía el archivo*. Nombre, tamaño y resultado sí; el
contenido del espectro, jamás. Tampoco rutas de archivos temporales ni textos de
excepciones, que son los dos lugares por donde se suele escapar.

Este módulo **no instala manejadores ni cambia niveles**: configurar la salida es
trabajo del arranque de la aplicación (T-07, `backend/api/`). Así las pruebas
pueden capturar lo que se registra sin pelearse con una configuración global.
"""

from __future__ import annotations

import logging

#: Nombre del registro raíz del proyecto. Todos los módulos cuelgan de aquí, de
#: modo que `logging.getLogger(NOMBRE_RAIZ)` los alcanza a todos de una vez.
NOMBRE_RAIZ: str = "e-ver"


def obtener_registro(nombre: str) -> logging.Logger:
    """Devuelve el registro de un módulo, colgado del raíz del proyecto.

    Args:
        nombre: identificador corto del módulo, p. ej. ``"mod-02"``.

    Returns:
        El `logging.Logger` llamado ``e-ver.<nombre>``.
    """
    if not nombre or not nombre.strip():
        raise ValueError("el registro necesita un nombre de módulo")
    return logging.getLogger(f"{NOMBRE_RAIZ}.{nombre.strip()}")
