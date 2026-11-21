"""MOD-03 · Validador.

Responde dos preguntas distintas, en dos tareas distintas:

- **T-04** (`formato.py`): «¿el contenido es de verdad del formato que declara?»
- **T-05** (`requisitos.py`): «¿cumple los requisitos de puntos y rango?»

Uso habitual (la orquestación vive en `backend/api/`, T-07):

    from backend.validacion import validar

    veredicto = validar(recepcion.nombre, recepcion.contenido)
    if not veredicto.valido:
        ...  # veredicto.codigo se traduce con UT-02

Para probar una tarea aislada (sección 9 del plan) están `validar_formato` y
`validar_requisitos`. El reparto interno vive en `comun.py`, que no es el
«lector de espectro» de D-2: ese sigue siendo decisión del incremento 2.
"""

from backend.validacion.comun import (
    CAPA_COHERENCIA,
    CAPA_ESTRUCTURA,
    CAPA_EXTENSION,
    CAPA_PUNTOS,
    CAPA_RANGO,
    CAPA_TAMANO,
    CAPA_TEXTO,
    CODIGO_POR_CAPA,
    COLUMNAS_CSV,
    EXTENSION_CSV,
    EXTENSION_JDX,
    FILAS_MINIMAS,
    SEPARADOR_COMA,
    SEPARADOR_CSV,
    SEPARADOR_PUNTO_Y_COMA,
    SEPARADORES,
    FilasCsv,
    Veredicto,
    extension_de,
    leer_csv,
    separador_de,
)
from backend.validacion.formato import FILAS_A_REVISAR
from backend.validacion.requisitos import (
    ETIQUETA_PRIMERA_X,
    ETIQUETA_PUNTOS,
    ETIQUETA_ULTIMA_X,
    Medida,
)
from backend.validacion.validador import (
    validar,
    validar_formato,
    validar_requisitos,
)

__all__ = [
    "CAPA_COHERENCIA",
    "CAPA_ESTRUCTURA",
    "CAPA_EXTENSION",
    "CAPA_PUNTOS",
    "CAPA_RANGO",
    "CAPA_TAMANO",
    "CAPA_TEXTO",
    "CODIGO_POR_CAPA",
    "COLUMNAS_CSV",
    "ETIQUETA_PRIMERA_X",
    "ETIQUETA_PUNTOS",
    "ETIQUETA_ULTIMA_X",
    "EXTENSION_CSV",
    "EXTENSION_JDX",
    "FILAS_A_REVISAR",
    "FILAS_MINIMAS",
    "FilasCsv",
    "Medida",
    "SEPARADOR_COMA",
    "SEPARADOR_CSV",
    "SEPARADOR_PUNTO_Y_COMA",
    "SEPARADORES",
    "Veredicto",
    "extension_de",
    "leer_csv",
    "separador_de",
    "validar",
    "validar_formato",
    "validar_requisitos",
]
