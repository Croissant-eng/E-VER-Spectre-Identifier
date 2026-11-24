"""MOD-06, inferencia: la fusión de las dos vías y el umbral (T-17).

Uso:

    from motor_identificacion.inferencia import identificar

    resultado = identificar(espectro)              # solo reglas
    resultado = identificar(espectro, modelo)      # reglas y modelo
    resultado.como_contrato()                      # el JSON de MOD-06
"""

from motor_identificacion.inferencia.fusion import (
    MODO_HIBRIDO,
    MODO_REGLAS,
    PESO_ML_EN_CERO,
    REJILLA_DISTINTA,
    SIN_MODELO,
    Deteccion,
    ModeloML,
    ResultadoMotor,
    identificar,
    motivo_para_solo_reglas,
    porcentaje,
    ventana_del_modelo,
)

__all__ = [
    "MODO_HIBRIDO",
    "MODO_REGLAS",
    "PESO_ML_EN_CERO",
    "REJILLA_DISTINTA",
    "SIN_MODELO",
    "Deteccion",
    "ModeloML",
    "ResultadoMotor",
    "identificar",
    "motivo_para_solo_reglas",
    "porcentaje",
    "ventana_del_modelo",
]
