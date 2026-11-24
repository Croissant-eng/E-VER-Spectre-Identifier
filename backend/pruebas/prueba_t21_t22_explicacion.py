"""T-21 y T-22: MOD-07 explica cada grupo detectado.

CA-07.1: la explicación del C=O en 1715 cm⁻¹ trae la región característica,
la posición observada, el rasgo (pico intenso y agudo) y por qué corresponde.
CA-07.2: la del N–H en la zona que comparte con O–H dice por qué es N–H.
CA-07.3: un grupo sin plantilla sale con «Explicación no disponible», se
registra el error y los demás grupos se muestran igual.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.api import RUTA_ANALIZAR, crear_aplicacion
from backend.api import aplicacion as capa_http
from backend.educativo import explicar, rasgo_de
from backend.utilerias import mensajes
from backend.utilerias.catalogo import RUTA_PLANTILLAS, cargar_plantillas, obtener_plantillas
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.inferencia import Deteccion, ResultadoMotor


def _region_en_texto(grupo: str) -> tuple[str, str]:
    menor, mayor = obtener_catalogo().por_id(grupo).region_cm1
    return str(round(menor)), str(round(mayor))


# CA-07.1


def prueba_ca_07_1_el_carbonilo_trae_las_cuatro_partes() -> None:
    explicacion = explicar("GF-05", 1715.0)
    menor, mayor = _region_en_texto("GF-05")

    assert explicacion.disponible
    assert menor in explicacion.region and mayor in explicacion.region
    assert "1715" in explicacion.posicion
    assert "pico intenso y agudo" in explicacion.rasgo
    assert "carbonilo" in explicacion.por_que


def prueba_la_region_sale_del_catalogo_y_no_de_la_plantilla() -> None:
    catalogo = obtener_catalogo()
    otro = replace(catalogo.por_id("GF-05"), region_cm1=(1600.0, 1800.0))
    grupos = tuple(otro if g.id == "GF-05" else g for g in catalogo.grupos)
    cambiado = replace(catalogo, grupos=grupos)

    assert "1600" in explicar("GF-05", 1715.0, catalogo=cambiado).region


def prueba_todos_los_grupos_tienen_un_rasgo_que_se_puede_decir() -> None:
    for grupo in obtener_catalogo().grupos:
        assert rasgo_de(grupo)


def prueba_la_marca_de_confirmacion_se_llena_con_el_catalogo() -> None:
    explicacion = explicar("GF-06", 1650.0)
    confirmacion = obtener_catalogo().por_id("GF-06").acompanantes_por_rol("confirmacion")[0]

    assert "{" not in explicacion.por_que
    assert str(round(confirmacion.rango[0])) in explicacion.por_que


def prueba_sin_posicion_de_pico_lo_dice_y_no_inventa_un_numero() -> None:
    """Prepara CA-06.3: la gráfica resalta la región completa."""
    explicacion = explicar("GF-05", None)

    assert explicacion.disponible
    assert "región completa" in explicacion.posicion
    assert not re.search(r"\d", explicacion.posicion)


# CA-07.2


def prueba_ca_07_2_el_nh_dice_por_que_no_es_oh() -> None:
    explicacion = explicar("GF-02", 3400.0)

    assert explicacion.distincion is not None
    assert "N–H y no a O–H" in explicacion.distincion
    assert "angosta" in explicacion.distincion


def prueba_la_distincion_solo_sale_si_el_pico_cae_en_la_region_del_vecino() -> None:
    menor, _ = obtener_catalogo().por_id("GF-01").region_cm1

    assert explicar("GF-02", menor - 1).distincion is None


# CA-07.3


def _sin_plantilla(tmp_path, grupo: str):
    datos = json.loads(RUTA_PLANTILLAS.read_text(encoding="utf-8"))
    datos["plantillas"] = [p for p in datos["plantillas"] if p["grupo"] != grupo]
    ruta = tmp_path / "plantillas.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return cargar_plantillas(ruta)


def prueba_ca_07_3_sin_plantilla_no_hay_explicacion_inventada(tmp_path) -> None:
    explicacion = explicar("GF-07", 1500.0, plantillas=_sin_plantilla(tmp_path, "GF-07"))

    assert explicacion.disponible is False
    assert explicacion.por_que == ""


def _resultado(*grupos: str) -> ResultadoMotor:
    catalogo = obtener_catalogo()
    detecciones = tuple(
        Deteccion(
            grupo=g,
            confianza=0.9 - i * 0.1,
            porcentaje=90 - i * 10,
            region_cm1=catalogo.por_id(g).region_cm1,
            pico_cm1=sum(catalogo.por_id(g).region_cm1) / 2,
            evidencia_regla=0.9 - i * 0.1,
            evidencia_ml=None,
        )
        for i, g in enumerate(grupos)
    )
    return ResultadoMotor(detecciones, 0.6, "reglas", catalogo.version, {})


def _espectro() -> dict:
    procesamiento = obtener_configuracion().procesamiento
    minimo, maximo = procesamiento.rango_rejilla_cm1
    puntos = procesamiento.puntos_rejilla
    paso = (maximo - minimo) / (puntos - 1)
    return {
        "eje_cm1": [round(maximo - paso * i, 6) for i in range(puntos)],
        "intensidad": [0.0] * puntos,
        "rango_medido_cm1": [minimo, maximo],
    }


def prueba_ca_07_3_de_punta_a_punta(tmp_path, monkeypatch, caplog) -> None:
    monkeypatch.setattr(capa_http, "identificar", lambda *a, **k: _resultado("GF-05", "GF-07"))
    monkeypatch.setattr(capa_http, "obtener_plantillas", lambda: _sin_plantilla(tmp_path, "GF-07"))

    with caplog.at_level(logging.ERROR):
        with TestClient(crear_aplicacion()) as cliente:
            datos = cliente.post(RUTA_ANALIZAR, json=_espectro()).json()

    por_grupo = {d["grupo"]: d for d in datos["detecciones"]}
    assert list(por_grupo) == ["GF-05", "GF-07"], "el grupo sin plantilla sigue en la lista"
    assert por_grupo["GF-05"]["explicacion"]["disponible"] is True
    assert por_grupo["GF-07"]["explicacion"]["disponible"] is False
    assert por_grupo["GF-07"]["explicacion"]["titulo"] == "Explicación no disponible"
    assert any(
        mensajes.EXPLICACION_NO_DISPONIBLE in r.getMessage() and "GF-07" in r.getMessage()
        for r in caplog.records
    )


def prueba_si_explicar_un_grupo_falla_los_demas_siguen(monkeypatch) -> None:
    monkeypatch.setattr(capa_http, "identificar", lambda *a, **k: _resultado("GF-05", "GF-01"))
    original = capa_http.explicar

    def falla_en_oh(grupo, *args, **kwargs):
        if grupo == "GF-01":
            raise RuntimeError("falla de prueba")
        return original(grupo, *args, **kwargs)

    monkeypatch.setattr(capa_http, "explicar", falla_en_oh)
    with TestClient(crear_aplicacion()) as cliente:
        respuesta = cliente.post(RUTA_ANALIZAR, json=_espectro())

    datos = respuesta.json()
    assert respuesta.status_code == 200
    assert datos["detecciones"][0]["explicacion"]["disponible"] is True
    assert datos["detecciones"][1]["explicacion"]["disponible"] is False


def prueba_la_ruta_explica_cada_grupo_detectado(monkeypatch) -> None:
    monkeypatch.setattr(capa_http, "identificar", lambda *a, **k: _resultado("GF-05"))
    with TestClient(crear_aplicacion()) as cliente:
        deteccion = cliente.post(RUTA_ANALIZAR, json=_espectro()).json()["detecciones"][0]

    explicacion = deteccion["explicacion"]
    assert set(explicacion) == {"disponible", "region", "posicion", "rasgo", "por_que", "distincion"}
    assert "pico intenso y agudo" in explicacion["rasgo"]
