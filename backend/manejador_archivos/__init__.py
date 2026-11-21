"""MOD-02 · Manejador de archivos.

Recibe la subida, le aplica el tamaño máximo de UT-03 y la entrega como texto a
MOD-03, o devuelve un rechazo con código de UT-02.

Uso habitual (la orquestación vive en `backend/api/`, T-07):

    from backend.manejador_archivos import recibir

    recepcion = await recibir(archivo)
    if recepcion.aceptado:
        ...  # recepcion.contenido va a MOD-03
    else:
        ...  # recepcion.codigo se traduce con UT-02
"""

from backend.manejador_archivos.receptor import (
    BLOQUE_BYTES,
    CODIFICACION,
    LARGO_MAXIMO_NOMBRE,
    NOMBRE_DESCONOCIDO,
    ArchivoSubido,
    Recepcion,
    nombre_seguro,
    recibir,
)

__all__ = [
    "BLOQUE_BYTES",
    "CODIFICACION",
    "LARGO_MAXIMO_NOMBRE",
    "NOMBRE_DESCONOCIDO",
    "ArchivoSubido",
    "Recepcion",
    "nombre_seguro",
    "recibir",
]
