"""MOD-06, fusión de las dos vías y umbral de confianza (T-17).

Aquí se juntan la vía de reglas (T-15) y la del modelo (T-16) con la fórmula
del diseño de MOD-06:

    confianza = peso_reglas por score_regla + peso_ml por probabilidad_ml

Los dos pesos y el umbral vienen de UT-03 (D-15) y no se escriben aquí.

Cuándo se trabaja solo con reglas (D-16). Si no hay modelo, si su peso es
cero o si el modelo se entrenó con otra rejilla (D-19), la confianza es el
score de reglas tal cual y el resultado dice "modo": "reglas". El contrato no
cambia: evidencia.ml sigue presente y vale None.

Cómo se aplica el umbral (D-15, punto 4). Primero se saca el porcentaje entero,
redondeando la mitad hacia arriba, y ese entero se compara contra el umbral en
porcentaje. Así lo que se ve en pantalla y lo que se decidió salen del mismo
número: nunca se muestra un 60 % que el sistema diga que no llega al 60 %. El
precio, aceptado por el equipo, es que 0.595 cuenta como 60 %.

De dónde salen la región y el pico. Siempre de la vía de reglas. El modelo
dice si un grupo está, pero no sabe dónde está su pico.

Lo que no hace este módulo: no lee archivos, no carga el modelo (eso pasa al
arrancar la aplicación, fuera del motor, D-18) y no redacta textos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol, runtime_checkable

from backend.utilerias.catalogo import Catalogo
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.reglas import ErrorDelMotor, EspectroEntrada, evaluar

#: Los dos valores que puede tomar "modo" en la salida (D-16).
MODO_HIBRIDO: str = "hibrido"
MODO_REGLAS: str = "reglas"

#: Por qué el motor trabaja solo con reglas. Son para el registro del servidor,
#: no para el usuario: D-16 pide que la falta de modelo no se vea como error.
SIN_MODELO: str = "no hay modelo entrenado"
PESO_ML_EN_CERO: str = "el peso del modelo en UT-03 es cero"
REJILLA_DISTINTA: str = "el modelo se entrenó con otra rejilla"


@runtime_checkable
class ModeloML(Protocol):
    """Lo que la fusión necesita de la red neuronal de T-16.

    Se escribe como protocolo para que T-16c pueda conectar su modelo sin
    tocar este archivo. Lo único que se le pide es saber con cuántos puntos se
    entrenó (D-19) y devolver siete probabilidades en el orden canónico de
    UT-01 a partir de la ventana que se le pasa.
    """

    #: La N de la rejilla con la que se entrenó. Se compara con UT-03.
    puntos_rejilla: int

    def probabilidades(self, ventana: tuple[float, ...]) -> tuple[float, ...]:
        """Siete probabilidades entre 0 y 1, una por grupo."""
        ...


@dataclass(frozen=True)
class Deteccion:
    """Un grupo que pasó el umbral."""

    grupo: str
    confianza: float
    porcentaje: int
    region_cm1: tuple[float, float]
    pico_cm1: float | None
    evidencia_regla: float
    #: None cuando el motor trabajó solo con reglas.
    evidencia_ml: float | None


@dataclass(frozen=True)
class ResultadoMotor:
    """La salida de MOD-06 según su diseño (sección 5) con los añadidos de D-16."""

    detecciones: tuple[Deteccion, ...]
    umbral: float
    modo: str
    version_catalogo: str
    #: La confianza de los siete grupos, hayan pasado o no. No viaja al
    #: usuario; sirve para las pruebas y para la evidencia de RNF-08.
    confianzas: dict[str, float]

    @property
    def sin_detecciones(self) -> bool:
        return not self.detecciones

    def como_contrato(self) -> dict[str, Any]:
        """El diccionario que describe el diseño de MOD-06 en su sección 5."""
        return {
            "detecciones": [
                {
                    "grupo": d.grupo,
                    "confianza": d.confianza,
                    "porcentaje": d.porcentaje,
                    "region_cm1": list(d.region_cm1),
                    "pico_cm1": d.pico_cm1,
                    "evidencia": {"regla": d.evidencia_regla, "ml": d.evidencia_ml},
                }
                for d in self.detecciones
            ],
            "sin_detecciones": self.sin_detecciones,
            "umbral": self.umbral,
            "modo": self.modo,
        }


def porcentaje(fraccion: float) -> int:
    """La fracción como porcentaje entero, con la mitad redondeada hacia arriba.

    Se pasa por Decimal a partir del texto del número porque 0.595 por 100 da
    59.49999 en punto flotante, y entonces un 59.5 quedaría en 59.
    """
    return int((Decimal(repr(fraccion)) * 100).quantize(Decimal(1), ROUND_HALF_UP))


def motivo_para_solo_reglas(
    modelo: ModeloML | None, configuracion: Configuracion
) -> str | None:
    """Por qué no se puede usar el modelo, o None si sí se puede.

    Es la comprobación de arranque de D-19: un modelo entrenado con otra
    rejilla no se carga, porque daría números equivocados sin avisar.
    """
    motor = configuracion.motor
    if modelo is None:
        return SIN_MODELO
    if motor is None or motor.peso_ml == 0:
        return PESO_ML_EN_CERO
    if modelo.puntos_rejilla != configuracion.procesamiento.puntos_rejilla:
        return REJILLA_DISTINTA
    return None


def ventana_del_modelo(
    espectro: EspectroEntrada, configuracion: Configuracion
) -> tuple[float, ...]:
    """La parte del vector que ve el modelo.

    Es el rango que todo archivo válido tiene medido (UT-03, el mismo que exige
    MOD-03). Así los ceros de relleno nunca entran a la red, que de otro modo
    podría aprender la forma del relleno en lugar de la química (plan del
    incremento 3, sección 5).
    """
    minimo, maximo = configuracion.validacion.rango_requerido_cm1
    return tuple(
        valor
        for onda, valor in zip(espectro.eje_cm1, espectro.intensidad)
        if minimo <= onda <= maximo
    )


def _probabilidades(
    modelo: ModeloML, ventana: tuple[float, ...], cuantas: int
) -> tuple[float, ...]:
    salida = tuple(float(p) for p in modelo.probabilidades(ventana))
    if len(salida) != cuantas:
        raise ErrorDelMotor(
            f"el modelo devolvió {len(salida)} probabilidades y se esperaban {cuantas}"
        )
    if any(not 0 <= p <= 1 for p in salida):
        raise ErrorDelMotor("el modelo devolvió una probabilidad fuera de 0 a 1")
    return salida


def identificar(
    espectro: EspectroEntrada,
    modelo: ModeloML | None = None,
    catalogo: Catalogo | None = None,
    configuracion: Configuracion | None = None,
) -> ResultadoMotor:
    """Corre las dos vías, las junta y aplica el umbral.

    Args:
        espectro: el objeto del contrato de MOD-04 a MOD-06.
        modelo: la red de T-16 ya cargada, o None si no hay.
        catalogo: el de UT-01. Por omisión, el del repositorio.
        configuracion: la de UT-03. Por omisión, la del repositorio.

    Raises:
        ErrorDelMotor: si falta el bloque motor de UT-03, si el espectro no
            cumple el contrato o si el modelo responde algo que no sirve. La
            capa HTTP lo convierte en el mensaje genérico (CA-05.4).
    """
    parametros = configuracion if configuracion is not None else obtener_configuracion()
    if parametros.motor is None:
        raise ErrorDelMotor("faltan los parámetros del bloque «motor» de UT-03")
    datos = catalogo if catalogo is not None else obtener_catalogo()
    motor = parametros.motor

    reglas = evaluar(espectro, datos, parametros)

    usar_modelo = motivo_para_solo_reglas(modelo, parametros) is None
    if usar_modelo:
        assert modelo is not None
        probabilidades = _probabilidades(
            modelo, ventana_del_modelo(espectro, parametros), len(reglas.puntajes)
        )
    else:
        probabilidades = None

    umbral_en_porcentaje = porcentaje(motor.umbral_confianza)
    confianzas: dict[str, float] = {}
    candidatas: list[tuple[int, Deteccion]] = []

    for posicion, puntaje in enumerate(reglas.puntajes):
        if probabilidades is None:
            prob_ml = None
            confianza = puntaje.score
        else:
            prob_ml = probabilidades[posicion]
            confianza = motor.peso_reglas * puntaje.score + motor.peso_ml * prob_ml
        confianza = min(max(confianza, 0.0), 1.0)
        confianzas[puntaje.grupo] = confianza

        # Un grupo cuya región no se midió no se puede afirmar (T-15).
        if not puntaje.evaluable:
            continue
        en_porcentaje = porcentaje(confianza)
        if en_porcentaje < umbral_en_porcentaje:
            continue
        candidatas.append(
            (
                posicion,
                Deteccion(
                    grupo=puntaje.grupo,
                    confianza=confianza,
                    porcentaje=en_porcentaje,
                    region_cm1=puntaje.region_cm1,
                    pico_cm1=puntaje.pico_cm1,
                    evidencia_regla=puntaje.score,
                    evidencia_ml=prob_ml,
                ),
            )
        )

    # De mayor a menor confianza (RF-04). Si dos empatan, queda primero el que
    # va antes en el orden canónico, para que el resultado no dependa del azar.
    candidatas.sort(key=lambda par: (-par[1].confianza, par[0]))

    return ResultadoMotor(
        detecciones=tuple(deteccion for _, deteccion in candidatas),
        umbral=motor.umbral_confianza,
        modo=MODO_HIBRIDO if usar_modelo else MODO_REGLAS,
        version_catalogo=reglas.version_catalogo,
        confianzas=confianzas,
    )
