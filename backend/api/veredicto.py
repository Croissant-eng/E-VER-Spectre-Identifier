"""Capa HTTP · el **único** lugar donde un código se vuelve un mensaje.

MOD-02 y MOD-03 devuelven **códigos** (`TAMANO_EXCEDIDO`, `PUNTOS_INSUFICIENTES`,
…) y nunca redactan nada. Aquí entran esos códigos por la misma puerta y salen
convertidos en el cuerpo que describe el contrato de la sección 5 del plan, con
el texto que pone UT-02.

Que la traducción viva en un solo lugar es lo que evita el problema clásico: el
mismo rechazo redactado distinto en dos pantallas, o con el texto escrito a mano
en el módulo que lo detectó. Una prueba de `backend/pruebas/` falla si
`mensajes.obtener` aparece en cualquier otro archivo de `backend/`.

Este módulo **no escribe ningún texto**: lo único que hay en el código son las
llaves del contrato. Si hace falta una redacción nueva, se agrega al catálogo de
UT-02, no aquí.
"""

from __future__ import annotations

from typing import Any

from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion


def aceptado(nombre: str, bytes_leidos: int) -> dict[str, Any]:
    """El cuerpo de una aceptación: `{valido, nombre, bytes}`.

    Args:
        nombre: el nombre ya limpio que entregó MOD-02. Es lo que la interfaz
            muestra (CA-01.1), así que sale tal cual.
        bytes_leidos: cuántos bytes contó MOD-02 de verdad, no lo que declaró
            el navegador.

    Returns:
        El cuerpo listo para responder. **No** lleva el contenido del espectro:
        se procesó en memoria y no sale del servidor (RNF-09).
    """
    return {"valido": True, "nombre": nombre, "bytes": bytes_leidos}


#: Decimales con que viajan el eje y la intensidad. Seis alcanzan de sobra
#: para la gráfica y dejan la respuesta en unas pocas decenas de kilobytes.
DECIMALES_ESPECTRO: int = 6


def procesado(nombre: str, espectro: Any) -> dict[str, Any]:
    """El cuerpo de `POST /api/procesar` cuando MOD-04 terminó (incremento 2).

    Lleva el espectro **normalizado** del contrato de MOD-06 §5: el eje de la
    rejilla fija de 4000 a 400 cm⁻¹ y la intensidad entre 0 y 1. No es el
    archivo ni sus valores originales, así que RNF-09 se sigue cumpliendo:
    lo que se subió no sale del servidor.

    Args:
        nombre: el nombre ya limpio que entregó MOD-02.
        espectro: el `EspectroProcesado` de MOD-04.
    """
    return {
        "valido": True,
        "nombre": nombre,
        "espectro": {
            "eje_cm1": [round(x, DECIMALES_ESPECTRO) for x in espectro.eje_cm1],
            "intensidad": [round(y, DECIMALES_ESPECTRO) for y in espectro.intensidad],
            "rango_medido_cm1": list(espectro.rango_medido_cm1),
            "unidad_original": espectro.unidad_original,
        },
    }


def rechazado(
    codigo: str, configuracion: Configuracion | None = None
) -> dict[str, Any]:
    """El cuerpo de un rechazo, con el motivo y la acción de UT-02 (RNF-01).

    Args:
        codigo: el código que devolvió MOD-02 o MOD-03.
        configuracion: los parámetros con los que UT-02 arma el texto —el
            tamaño máximo, el rango, los puntos mínimos—. La capa HTTP pasa la
            que leyó al arrancar; si es ``None``, UT-02 pide la de UT-03.

    Returns:
        El cuerpo listo para responder.

    Raises:
        CodigoDesconocido: si el código no está en el catálogo. Es un error del
            programa, no del usuario: quien llama lo trata como fallo interno y
            responde el mensaje genérico, sin mostrar el código inventado.
    """
    mensaje = mensajes.obtener(codigo, configuracion)
    return {
        "valido": False,
        "codigo": mensaje.codigo,
        "titulo": mensaje.titulo,
        "mensaje": mensaje.texto,
        "accion": mensaje.accion,
    }


#: Decimales con que viajan la confianza y las evidencias del análisis.
DECIMALES_CONFIANZA: int = 4


def _redondeado(valor: float | None) -> float | None:
    return None if valor is None else round(valor, DECIMALES_CONFIANZA)


def analizado(
    resultado: Any, catalogo: Any, configuracion: Configuracion | None = None
) -> dict[str, Any]:
    """El cuerpo de POST /api/analizar (incremento 3).

    Es la salida de MOD-06 de su diseño (sección 5) más dos cosas que la
    página necesita para mostrarla: el nombre de cada grupo, que sale de
    UT-01, y el aviso de UT-02 cuando no hubo detecciones (CA-08). El aviso
    viaja dentro del resultado con valido en True porque no es un error: el
    sistema analizó y está siendo honesto.

    Args:
        resultado: el ResultadoMotor de la fusión (T-17).
        catalogo: el de UT-01, para los nombres.
        configuracion: la de UT-03, para que el aviso nombre el umbral.
    """
    contrato = resultado.como_contrato()
    for deteccion in contrato["detecciones"]:
        deteccion["nombre"] = catalogo.por_id(deteccion["grupo"]).nombre
        deteccion["confianza"] = _redondeado(deteccion["confianza"])
        deteccion["evidencia"] = {
            clave: _redondeado(valor) for clave, valor in deteccion["evidencia"].items()
        }

    cuerpo: dict[str, Any] = {"valido": True, **contrato}
    if resultado.sin_detecciones:
        mensaje = mensajes.obtener(mensajes.SIN_DETECCIONES, configuracion)
        cuerpo["aviso"] = {
            "codigo": mensaje.codigo,
            "titulo": mensaje.titulo,
            "mensaje": mensaje.texto,
            "accion": mensaje.accion,
        }
    return cuerpo
