"""MOD-07, capa educativa (incremento 4).

Uso:

    from backend.educativo import explicar

    explicacion = explicar(grupo, pico_cm1)
    explicacion.region, explicacion.posicion, explicacion.rasgo, explicacion.por_que
"""

from backend.educativo.explicador import (
    Explicacion,
    VocabularioDesconocido,
    explicar,
    rasgo_de,
)

__all__ = ["Explicacion", "VocabularioDesconocido", "explicar", "rasgo_de"]
