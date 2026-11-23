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
