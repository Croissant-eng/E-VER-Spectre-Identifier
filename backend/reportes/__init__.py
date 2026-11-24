"""MOD-08, generador de reportes (incremento 5).

Uso:

    from backend.reportes import DatosDelReporte, generar_pdf

    pdf = generar_pdf(datos)   # bytes, armados en memoria
"""

from backend.reportes.generador import (
    AVISO_ORIENTATIVO,
    AVISO_SOLO_REGLAS,
    TITULO,
    DatosDelReporte,
    generar_pdf,
)

__all__ = [
    "AVISO_ORIENTATIVO",
    "AVISO_SOLO_REGLAS",
    "TITULO",
    "DatosDelReporte",
    "generar_pdf",
]
