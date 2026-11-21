"""Infraestructura base del backend (Diseño Modular v2.0 §10).

No es un MOD numerado ni tiene criterios de aceptación propios: aquí viven las
piezas que todos los módulos comparten. En el incremento 1 solo contiene el
registro (logging) que pide T-03.

Uso habitual:

    from backend.nucleo import obtener_registro

    _registro = obtener_registro("mod-02")
"""

from backend.nucleo.registro import NOMBRE_RAIZ, obtener_registro

__all__ = ["NOMBRE_RAIZ", "obtener_registro"]
