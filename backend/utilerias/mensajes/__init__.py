"""UT-02 · Errores y mensajes.

Uso habitual:

    from backend.utilerias import mensajes

    mensaje = mensajes.obtener(mensajes.FORMATO_NO_SOPORTADO)
    mensaje.titulo, mensaje.texto, mensaje.accion
"""

from backend.utilerias.mensajes.catalogo import (
    ANALISIS_FALLIDO,
    ARCHIVO_NO_ES_TEXTO,
    CONFIGURACION_INCOMPLETA,
    DATOS_ILEGIBLES,
    ESPECTRO_INVALIDO,
    ESTRUCTURA_INVALIDA,
    FALLO_INTERNO,
    FORMATO_NO_SOPORTADO,
    LECTURA_INTERRUMPIDA,
    PUNTOS_INSUFICIENTES,
    RANGO_INSUFICIENTE,
    SIN_DETECCIONES,
    SIN_SENAL,
    TAMANO_EXCEDIDO,
    UNIDAD_NO_SOPORTADA,
    UNIDAD_SIN_DECLARAR,
    CodigoDesconocido,
    Mensaje,
    codigos,
    obtener,
)

__all__ = [
    "ANALISIS_FALLIDO",
    "ARCHIVO_NO_ES_TEXTO",
    "CONFIGURACION_INCOMPLETA",
    "DATOS_ILEGIBLES",
    "ESPECTRO_INVALIDO",
    "ESTRUCTURA_INVALIDA",
    "FALLO_INTERNO",
    "FORMATO_NO_SOPORTADO",
    "LECTURA_INTERRUMPIDA",
    "PUNTOS_INSUFICIENTES",
    "RANGO_INSUFICIENTE",
    "SIN_DETECCIONES",
    "SIN_SENAL",
    "TAMANO_EXCEDIDO",
    "UNIDAD_NO_SOPORTADA",
    "UNIDAD_SIN_DECLARAR",
    "CodigoDesconocido",
    "Mensaje",
    "codigos",
    "obtener",
]
