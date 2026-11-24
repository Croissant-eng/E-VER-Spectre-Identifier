"""UT-01 · Catálogo de grupos funcionales.

Fuente única de los 7 grupos y de sus rangos, en solo lectura. Nadie lee
`datos/catalogo/grupos.json` por su cuenta: todos piden los datos aquí.

Uso habitual:

    from backend.utilerias.catalogo import obtener as obtener_catalogo

    catalogo = obtener_catalogo()
    catalogo.por_id("GF-05").region_cm1      # la región principal, (mín, máx)
    catalogo.orden_canonico                  # el orden del vector de T-16
    catalogo.indice_de("GF-05")              # su posición en ese vector
"""

from backend.utilerias.catalogo.lector import (
    BANDAS_DEL_PAR,
    CARPETA,
    GRUPOS_ESPERADOS,
    NOMBRE_ARCHIVO,
    PATRON_ARCHIVO,
    ROLES_VALIDOS,
    RUTA_CATALOGO,
    Catalogo,
    ErrorDeCatalogo,
    GrupoFuncional,
    RegionAcompanante,
    SubtipoDeGrupo,
    cargar,
    obtener,
    recargar,
)

__all__ = [
    "BANDAS_DEL_PAR",
    "CARPETA",
    "GRUPOS_ESPERADOS",
    "NOMBRE_ARCHIVO",
    "PATRON_ARCHIVO",
    "ROLES_VALIDOS",
    "RUTA_CATALOGO",
    "Catalogo",
    "ErrorDeCatalogo",
    "GrupoFuncional",
    "RegionAcompanante",
    "SubtipoDeGrupo",
    "cargar",
    "obtener",
    "recargar",
]
