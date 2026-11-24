"""T-17: fusión de las dos vías y umbral del 60 %.

Casi todas estas pruebas usan confianzas simuladas. Se reemplaza la vía de
reglas por una que devuelve los scores que pide cada prueba, y cuando hace
falta un modelo se usa uno de mentira que devuelve probabilidades fijas. Así
se prueba la aritmética de la fusión sin depender de un espectro real ni de un
modelo entrenado, que todavía no existe.

Criterios que cubre: CA-05.3 (60 % aparece, 59 % no), CA-08.2 (máximo de 59 %
deja la lista vacía), D-15 (pesos en UT-03 que suman 1 y el umbral sobre el
porcentaje entero) y D-16 (con peso del modelo en cero o sin modelo, la
confianza es la de reglas y el contrato no cambia).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import (
    ErrorDeConfiguracion,
    cargar,
)
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.inferencia import fusion
from motor_identificacion.inferencia import (
    MODO_HIBRIDO,
    MODO_REGLAS,
    PESO_ML_EN_CERO,
    REJILLA_DISTINTA,
    SIN_MODELO,
    identificar,
    motivo_para_solo_reglas,
    porcentaje,
    ventana_del_modelo,
)
from motor_identificacion.reglas import ErrorDelMotor, Puntaje, ResultadoReglas

RAIZ = Path(__file__).resolve().parents[2]
RUTA_PARAMETROS = RAIZ / "backend" / "utilerias" / "configuracion" / "parametros.json"


class EspectroVacio:
    """Un espectro con la forma del contrato. Su contenido no importa aquí
    porque la vía de reglas está simulada, salvo en la prueba de la ventana."""

    def __init__(self) -> None:
        procesamiento = obtener_configuracion().procesamiento
        minimo, maximo = procesamiento.rango_rejilla_cm1
        puntos = procesamiento.puntos_rejilla
        paso = (maximo - minimo) / (puntos - 1)
        self.eje_cm1 = tuple(maximo - paso * i for i in range(puntos))
        self.intensidad = tuple(0.0 for _ in range(puntos))
        self.rango_medido_cm1 = (minimo, maximo)


class ModeloFijo:
    """Un modelo de mentira que siempre responde lo mismo."""

    def __init__(self, probabilidades: dict[str, float], puntos: int | None = None):
        self._probabilidades = probabilidades
        self.puntos_rejilla = (
            puntos if puntos is not None else obtener_configuracion().procesamiento.puntos_rejilla
        )
        self.ventanas: list[tuple[float, ...]] = []

    def probabilidades(self, ventana: tuple[float, ...]) -> tuple[float, ...]:
        self.ventanas.append(ventana)
        orden = obtener_catalogo().orden_canonico
        return tuple(self._probabilidades.get(grupo, 0.0) for grupo in orden)


def _reglas_simuladas(
    monkeypatch: pytest.MonkeyPatch,
    scores: dict[str, float],
    *,
    sin_medir: tuple[str, ...] = (),
) -> None:
    """Hace que la vía de reglas devuelva justo estos scores."""
    catalogo = obtener_catalogo()

    def evaluar_simulado(espectro, catalogo_recibido=None, configuracion=None):
        return ResultadoReglas(
            puntajes=tuple(
                Puntaje(
                    grupo=grupo.id,
                    score=scores.get(grupo.id, 0.0),
                    region_cm1=grupo.region_cm1,
                    pico_cm1=sum(grupo.region_cm1) / 2,
                    evaluable=grupo.id not in sin_medir,
                    ancho_cm1=None,
                    ajustes=(),
                )
                for grupo in catalogo.grupos
            ),
            version_catalogo=catalogo.version,
        )

    monkeypatch.setattr(fusion, "evaluar", evaluar_simulado)


def _con_pesos(peso_reglas: float, peso_ml: float, umbral: float | None = None):
    configuracion = obtener_configuracion()
    assert configuracion.motor is not None
    motor = replace(configuracion.motor, peso_reglas=peso_reglas, peso_ml=peso_ml)
    if umbral is not None:
        motor = replace(motor, umbral_confianza=umbral)
    return replace(configuracion, motor=motor)


def _ids(resultado) -> list[str]:
    return [d.grupo for d in resultado.detecciones]


# CA-05.3 y CA-08.2


def prueba_ca_05_3_el_sesenta_aparece_y_el_cincuenta_y_nueve_no(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.60, "GF-01": 0.59})

    resultado = identificar(EspectroVacio())

    assert _ids(resultado) == ["GF-05"]
    assert resultado.detecciones[0].porcentaje == 60


def prueba_ca_08_2_un_maximo_de_cincuenta_y_nueve_deja_la_lista_vacia(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.59, "GF-03": 0.30})

    resultado = identificar(EspectroVacio())

    assert resultado.detecciones == ()
    assert resultado.sin_detecciones is True
    assert resultado.como_contrato()["sin_detecciones"] is True
    assert resultado.como_contrato()["detecciones"] == []


def prueba_el_umbral_se_compara_sobre_el_porcentaje_redondeado(monkeypatch) -> None:
    """D-15: 0.595 se muestra como 60 % y por eso cuenta como detectado."""
    _reglas_simuladas(monkeypatch, {"GF-05": 0.595, "GF-01": 0.5949})

    resultado = identificar(EspectroVacio())

    assert _ids(resultado) == ["GF-05"]
    assert resultado.detecciones[0].porcentaje == 60


def prueba_el_porcentaje_redondea_la_mitad_hacia_arriba() -> None:
    assert porcentaje(0.595) == 60
    assert porcentaje(0.5949) == 59
    assert porcentaje(0.6) == 60
    assert porcentaje(0.0) == 0
    assert porcentaje(1.0) == 100
    assert porcentaje(0.005) == 1


def prueba_el_umbral_sale_de_ut03(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.70})

    assert _ids(identificar(EspectroVacio(), configuracion=_con_pesos(1, 0, 0.8))) == []
    assert _ids(identificar(EspectroVacio(), configuracion=_con_pesos(1, 0, 0.7))) == ["GF-05"]


# Orden


def prueba_las_detecciones_van_de_mayor_a_menor_confianza(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-01": 0.70, "GF-05": 0.95, "GF-07": 0.80})

    resultado = identificar(EspectroVacio())

    assert _ids(resultado) == ["GF-05", "GF-07", "GF-01"]


def prueba_con_empate_manda_el_orden_canonico(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-07": 0.80, "GF-02": 0.80, "GF-05": 0.80})

    for _ in range(3):
        assert _ids(identificar(EspectroVacio())) == ["GF-02", "GF-05", "GF-07"]


def prueba_un_grupo_sin_medir_no_se_reporta(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-01": 0.90, "GF-05": 0.90}, sin_medir=("GF-01",))

    assert _ids(identificar(EspectroVacio())) == ["GF-05"]


# D-16: solo reglas


def prueba_sin_modelo_la_confianza_es_exactamente_la_de_reglas(monkeypatch) -> None:
    scores = {"GF-01": 0.61, "GF-03": 0.8333, "GF-05": 0.97}
    _reglas_simuladas(monkeypatch, scores)

    resultado = identificar(EspectroVacio())

    assert resultado.modo == MODO_REGLAS
    for grupo, score in scores.items():
        assert resultado.confianzas[grupo] == score
    for deteccion in resultado.detecciones:
        assert deteccion.evidencia_ml is None
        assert deteccion.evidencia_regla == deteccion.confianza


def prueba_con_peso_del_modelo_en_cero_se_ignora_el_modelo(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.65})
    modelo = ModeloFijo({"GF-05": 0.0, "GF-01": 1.0})

    resultado = identificar(EspectroVacio(), modelo, configuracion=_con_pesos(1, 0))

    assert resultado.modo == MODO_REGLAS
    assert _ids(resultado) == ["GF-05"]
    assert resultado.confianzas["GF-05"] == 0.65
    assert modelo.ventanas == [], "con peso cero ni siquiera se le pregunta"


def prueba_el_contrato_no_cambia_entre_los_dos_modos(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.9})

    solo_reglas = identificar(EspectroVacio()).como_contrato()
    hibrido = identificar(EspectroVacio(), ModeloFijo({"GF-05": 0.9})).como_contrato()

    assert solo_reglas.keys() == hibrido.keys()
    assert solo_reglas["detecciones"][0].keys() == hibrido["detecciones"][0].keys()
    assert solo_reglas["detecciones"][0]["evidencia"]["ml"] is None
    assert hibrido["detecciones"][0]["evidencia"]["ml"] == 0.9
    assert solo_reglas["modo"] == MODO_REGLAS
    assert hibrido["modo"] == MODO_HIBRIDO


def prueba_los_motivos_para_trabajar_solo_con_reglas() -> None:
    configuracion = obtener_configuracion()
    otra_rejilla = configuracion.procesamiento.puntos_rejilla * 2

    assert motivo_para_solo_reglas(None, configuracion) == SIN_MODELO
    assert motivo_para_solo_reglas(ModeloFijo({}), _con_pesos(1, 0)) == PESO_ML_EN_CERO
    assert motivo_para_solo_reglas(ModeloFijo({}, otra_rejilla), configuracion) == REJILLA_DISTINTA
    assert motivo_para_solo_reglas(ModeloFijo({}), configuracion) is None


def prueba_un_modelo_de_otra_rejilla_no_se_usa(monkeypatch) -> None:
    """D-19: mejor solo reglas que números equivocados en silencio."""
    _reglas_simuladas(monkeypatch, {"GF-05": 0.7})
    otra = obtener_configuracion().procesamiento.puntos_rejilla + 1
    modelo = ModeloFijo({"GF-05": 0.0}, otra)

    resultado = identificar(EspectroVacio(), modelo)

    assert resultado.modo == MODO_REGLAS
    assert resultado.confianzas["GF-05"] == 0.7


# La fórmula


def prueba_la_formula_usa_los_pesos_de_ut03(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.8})
    modelo = ModeloFijo({"GF-05": 0.4})

    resultado = identificar(EspectroVacio(), modelo, configuracion=_con_pesos(0.25, 0.75))

    assert resultado.modo == MODO_HIBRIDO
    assert resultado.confianzas["GF-05"] == pytest.approx(0.25 * 0.8 + 0.75 * 0.4)


def prueba_si_las_vias_coinciden_sube_y_si_discrepan_baja(monkeypatch) -> None:
    """Lo que dice el diseño de MOD-06 en su sección 8."""
    _reglas_simuladas(monkeypatch, {"GF-05": 0.7})

    de_acuerdo = identificar(EspectroVacio(), ModeloFijo({"GF-05": 0.95}))
    en_desacuerdo = identificar(EspectroVacio(), ModeloFijo({"GF-05": 0.10}))

    assert de_acuerdo.confianzas["GF-05"] > 0.7
    assert en_desacuerdo.confianzas["GF-05"] < 0.7
    assert _ids(de_acuerdo) == ["GF-05"]
    assert _ids(en_desacuerdo) == []


def prueba_la_region_y_el_pico_salen_de_la_via_de_reglas(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.9})

    deteccion = identificar(EspectroVacio(), ModeloFijo({"GF-05": 0.9})).detecciones[0]
    grupo = obtener_catalogo().por_id("GF-05")

    assert deteccion.region_cm1 == grupo.region_cm1
    assert deteccion.pico_cm1 == sum(grupo.region_cm1) / 2


def prueba_el_modelo_solo_ve_la_ventana_medida() -> None:
    """Los ceros de relleno no entran a la red (plan del incremento 3, sección 5)."""
    espectro = EspectroVacio()
    configuracion = obtener_configuracion()
    minimo, maximo = configuracion.validacion.rango_requerido_cm1

    ventana = ventana_del_modelo(espectro, configuracion)
    esperados = [x for x in espectro.eje_cm1 if minimo <= x <= maximo]

    assert len(ventana) == len(esperados)
    assert 0 < len(ventana) < len(espectro.eje_cm1)


def prueba_un_modelo_que_responde_mal_es_fallo_del_motor(monkeypatch) -> None:
    _reglas_simuladas(monkeypatch, {"GF-05": 0.9})

    class Corto(ModeloFijo):
        def probabilidades(self, ventana):
            return (0.5, 0.5)

    class FueraDeRango(ModeloFijo):
        def probabilidades(self, ventana):
            return (1.5,) * 7

    for modelo in (Corto({}), FueraDeRango({})):
        with pytest.raises(ErrorDelMotor):
            identificar(EspectroVacio(), modelo)


def prueba_con_un_espectro_de_verdad_corre_de_punta_a_punta() -> None:
    """Sin simular nada: la vía de reglas real con un vector en ceros."""
    resultado = identificar(EspectroVacio())

    assert resultado.modo == MODO_REGLAS
    assert resultado.sin_detecciones is True
    assert set(resultado.confianzas) == set(obtener_catalogo().orden_canonico)


# UT-03 (D-15)


def _parametros_con(**cambios: Any) -> dict[str, Any]:
    datos = json.loads(RUTA_PARAMETROS.read_text(encoding="utf-8"))
    datos["motor"].update(cambios)
    return datos


def _cargar(tmp_path: Path, datos: dict[str, Any]):
    ruta = tmp_path / "parametros.json"
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return cargar(ruta)


def prueba_ut03_entrega_el_umbral_y_los_pesos() -> None:
    motor = obtener_configuracion().motor
    assert motor is not None
    assert motor.umbral_confianza == 0.6
    assert motor.peso_reglas + motor.peso_ml == pytest.approx(1)


@pytest.mark.parametrize(
    "cambios",
    [
        {"peso_reglas": 0.7, "peso_ml": 0.5},
        {"peso_reglas": 0.2, "peso_ml": 0.2},
        {"peso_reglas": -0.5, "peso_ml": 1.5},
        {"peso_reglas": "0.5"},
        {"umbral_confianza": 60},
        {"umbral_confianza": 0},
    ],
)
def prueba_ut03_no_arranca_con_pesos_o_umbral_incoherentes(tmp_path, cambios) -> None:
    with pytest.raises(ErrorDeConfiguracion):
        _cargar(tmp_path, _parametros_con(**cambios))


def prueba_ut03_acepta_pesos_que_suman_uno_con_decimales(tmp_path) -> None:
    motor = _cargar(tmp_path, _parametros_con(peso_reglas=0.7, peso_ml=0.3)).motor
    assert motor is not None
    assert (motor.peso_reglas, motor.peso_ml) == (0.7, 0.3)


def prueba_ut03_acepta_el_plan_b(tmp_path) -> None:
    motor = _cargar(tmp_path, _parametros_con(peso_reglas=1, peso_ml=0)).motor
    assert motor is not None
    assert motor.peso_ml == 0
