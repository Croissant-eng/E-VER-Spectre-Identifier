"""MOD-06 · vía de reglas (T-15b).

Detecta picos sobre el vector normalizado y los compara con el catálogo de
UT-01. Devuelve un score en [0, 1] por grupo, con su región y su pico.

Uso:

    from motor_identificacion.reglas import evaluar

    resultado = evaluar(espectro)          # el objeto del contrato MOD-04
    resultado.por_id("GF-05").score
    resultado.por_id("GF-05").pico_cm1

Es la Fase 1 del diseño y, por sí sola, identifica de punta a punta: es el
plan B de D-16 ya construido. Determinista: la misma entrada da el mismo score
siempre.
"""

from motor_identificacion.reglas.evaluador import (
    BAJO_EL_PISO,
    FORMA_ANCHA,
    FORMA_ANGOSTA,
    INDICIO_SUMA,
    NO_EVALUABLE,
    R1_ANCHO_NO_ESPERADO,
    R2_FALTA_CONFIRMACION,
    R2_FALTA_PAR,
    R4_HOMBRO_ANCHO,
    R4_PICO_AGUDO,
    SIN_BANDA,
    SIN_PICO_RESUELTO,
    ErrorDelMotor,
    EspectroEntrada,
    Puntaje,
    ResultadoReglas,
    evaluar,
)
from motor_identificacion.reglas.picos import (
    Ancho,
    Pico,
    Rejilla,
)

__all__ = [
    "BAJO_EL_PISO",
    "FORMA_ANCHA",
    "FORMA_ANGOSTA",
    "INDICIO_SUMA",
    "NO_EVALUABLE",
    "R1_ANCHO_NO_ESPERADO",
    "R2_FALTA_CONFIRMACION",
    "R2_FALTA_PAR",
    "R4_HOMBRO_ANCHO",
    "R4_PICO_AGUDO",
    "SIN_BANDA",
    "SIN_PICO_RESUELTO",
    "Ancho",
    "ErrorDelMotor",
    "EspectroEntrada",
    "Pico",
    "Puntaje",
    "Rejilla",
    "ResultadoReglas",
    "evaluar",
]
