"""Pruebas de T-15b · MOD-06, vía de reglas.

Cubren lo que el plan del incremento 3 le pide a T-15 (secciones 6, 8 y 9):
espectros sintéticos, las cuatro reglas de desempate sobre los espectros reales
de `datos/referencia/`, el relleno de ceros, el determinismo y la zona aislada.

**Todo corre sin red.** Si falta un espectro de referencia —esa carpeta está en
`.gitignore` porque los archivos son de Coblentz— la prueba se salta y dice cuál
falta y cómo bajarlo.

## Qué significa aquí «detectado»

La vía de reglas devuelve un **score**; quien decide si un grupo está es T-17,
con el umbral del 60 % y la fusión. Para poder afirmar algo, estas pruebas usan
el criterio de **D-16, plan B**: con `wML = 0` la confianza del motor **es** el
score de reglas, así que un grupo pasa la vía de reglas cuando su score alcanza
`umbral_confianza` de UT-03. El número no se escribe aquí: se lee de UT-03.

## Las que están marcadas como fallo conocido

Los siete `xfail(strict=True)` de T-15b se quitaron en T-15d, cuando el motor
acertó. Queda uno: CA-06.2 sobre una mezcla de O–H y N–H, que R-1 no cumple.

**El 56 de 56 no es una validación.** Los pisos de fuerza salieron de estos
mismos ocho espectros (D-22); lo que mide el motor de verdad es el subconjunto
de prueba congelado de RNF-08.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pytest

from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.reglas import (
    BAJO_EL_PISO,
    INDICIO_SUMA,
    NO_EVALUABLE,
    R1_ANCHO_NO_ESPERADO,
    R2_FALTA_CONFIRMACION,
    SIN_PICO_RESUELTO,
    R2_FALTA_PAR,
    R4_HOMBRO_ANCHO,
    R4_PICO_AGUDO,
    SIN_BANDA,
    ErrorDelMotor,
    Rejilla,
    evaluar,
)

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_REFERENCIA = RAIZ / "datos" / "referencia"

#: Los espectros de referencia se guardan en latin-1, como los lee el resto de
#: las pruebas de archivos reales.
CODIFICACION = "latin-1"

GRUPOS = ("GF-01", "GF-02", "GF-03", "GF-04", "GF-05", "GF-06", "GF-07")


# --------------------------------------------------------------------------- #
# Apoyo · el espectro del contrato, sin MOD-04
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class EspectroDePrueba:
    """Un espectro con la forma exacta del contrato MOD-04 → MOD-06.

    La vía de reglas declara su entrada como protocolo, así que no hace falta
    MOD-04 para probarla: es la frontera de la zona aislada, y esta clase la
    demuestra.
    """

    eje_cm1: tuple[float, ...]
    intensidad: tuple[float, ...]
    rango_medido_cm1: tuple[float, float]


def _eje() -> tuple[float, ...]:
    """La rejilla de UT-03, de mayor a menor número de onda."""
    procesamiento = obtener_configuracion().procesamiento
    minimo, maximo = procesamiento.rango_rejilla_cm1
    puntos = procesamiento.puntos_rejilla
    paso = (maximo - minimo) / (puntos - 1)
    return tuple(maximo - paso * i for i in range(puntos))


def _umbral() -> float:
    """El umbral de UT-03. Ver la nota del encabezado sobre D-16, plan B."""
    configuracion = obtener_configuracion()
    assert configuracion.motor is not None, "UT-03 debe traer el bloque motor"
    import json

    datos = json.loads(configuracion.ruta.read_text(encoding="utf-8"))
    return float(datos["motor"]["umbral_confianza"])


def espectro_sintetico(
    picos: tuple[tuple[float, float, float], ...],
    medido: tuple[float, float] | None = None,
) -> EspectroDePrueba:
    """Un espectro con bandas gaussianas en las posiciones que se le pidan.

    Cada pico es `(centro_cm1, altura, ancho_a_media_altura_cm1)`. Fuera del
    tramo medido la intensidad queda en 0, que es **relleno**, no absorbancia
    cero: así el sintético se parece a lo que MOD-04 entrega de verdad.
    """
    eje = _eje()
    medido_final = medido if medido is not None else (min(eje), max(eje))
    medido_min, medido_max = medido_final

    valores: list[float] = []
    for onda in eje:
        if not medido_min <= onda <= medido_max:
            valores.append(0.0)
            continue
        total = 0.0
        for centro, altura, ancho in picos:
            sigma = ancho / (2 * math.sqrt(2 * math.log(2)))
            total += altura * math.exp(-((onda - centro) ** 2) / (2 * sigma**2))
        valores.append(round(min(total, 1.0), 6))

    return EspectroDePrueba(
        eje_cm1=eje,
        intensidad=tuple(valores),
        rango_medido_cm1=medido_final,
    )


def _centro(grupo: str) -> float:
    minimo, maximo = obtener_catalogo().por_id(grupo).region_cm1
    return (minimo + maximo) / 2


def _acompanante(grupo: str, rol: str, cual: int = 0) -> float:
    region = obtener_catalogo().por_id(grupo).acompanantes_por_rol(rol)[cual]
    return (region.rango[0] + region.rango[1]) / 2


def _espectro_real(archivo: str):
    """Pasa un espectro de referencia por el pipeline real de MOD-04."""
    from backend.preprocesamiento import procesar

    ruta = CARPETA_REFERENCIA / archivo
    if not ruta.is_file():
        pytest.skip(
            f"falta {archivo} en datos/referencia; bájelo con "
            "«python -m herramientas.descargar_espectros_nist»"
        )

    resultado = procesar(ruta.name, ruta.read_text(encoding=CODIFICACION))
    if not resultado.valido:
        pytest.skip(
            f"MOD-04 rechaza {archivo} ({resultado.codigo}: {resultado.detalle}); "
            "no es un fallo de la vía de reglas"
        )
    return resultado.espectro


def _pasan(espectro) -> set[str]:
    """Los grupos cuyo score alcanza el umbral de UT-03."""
    umbral = _umbral()
    return {g: s for g, s in evaluar(espectro).scores().items() if s >= umbral}.keys()


# --------------------------------------------------------------------------- #
# Sintéticos
# --------------------------------------------------------------------------- #


def prueba_un_pico_en_la_region_de_gf05_lo_detecta_con_su_region() -> None:
    """Un pico de C=O y nada más: GF-05 con su región del catálogo."""
    region = obtener_catalogo().por_id("GF-05").region_cm1
    centro = (region[0] + region[1]) / 2

    resultado = evaluar(espectro_sintetico(((centro, 1.0, 20.0),)))
    gf05 = resultado.por_id("GF-05")

    assert gf05.score >= _umbral(), f"GF-05 quedó en {gf05.score:.2f}"
    assert gf05.region_cm1 == region
    assert gf05.pico_cm1 is not None
    assert region[0] <= gf05.pico_cm1 <= region[1]
    assert gf05.evaluable


def prueba_un_espectro_sin_picos_no_detecta_nada() -> None:
    """Sin bandas no hay nada que afirmar: todos los scores en cero."""
    resultado = evaluar(espectro_sintetico(()))

    for puntaje in resultado.puntajes:
        assert puntaje.score == 0.0, f"{puntaje.grupo} puntuó {puntaje.score}"
        assert puntaje.pico_cm1 is None
        assert {SIN_BANDA, NO_EVALUABLE, SIN_PICO_RESUELTO} & set(puntaje.ajustes), (
            f"{puntaje.grupo} no deja dicho por qué no hay banda: {puntaje.ajustes}"
        )


def prueba_el_score_decrece_con_la_distancia_al_rango() -> None:
    """MOD-06 §6: el score cae cuando el pico se aleja de la región."""
    region = obtener_catalogo().por_id("GF-05").region_cm1
    centro = (region[0] + region[1]) / 2
    ancho = region[1] - region[0]

    # Una banda lo bastante ancha para que su ladera deje señal en la región: el
    # piso se exige dentro (D-22.4), y una angosta de fuera ya puntúa cero.
    def score(posicion: float, ancho_banda: float) -> float:
        espectro = espectro_sintetico(((posicion, 1.0, ancho_banda),))
        return evaluar(espectro).por_id("GF-05").score

    assert score(centro, 60.0) > score(region[1] + ancho / 4, 60.0) > 0.0
    assert score(region[1] + ancho * 2, 60.0) == 0.0
    assert score(region[1] + ancho / 4, 20.0) == 0.0


#: De la banda más intensa posible a una ondulación.
ALTURAS = (1.0, 0.5, 0.2, 0.02, 0.001)


def prueba_un_pico_aislado_insignificante_puntua_menos_que_uno_fuerte() -> None:
    """MOD-06 §6. La versión de T-15b comparaba con `>=` y no probaba nada."""
    centro = _centro("GF-05")
    scores = [
        evaluar(espectro_sintetico(((centro, altura, 20.0),))).por_id("GF-05").score
        for altura in ALTURAS
    ]

    assert scores == sorted(scores, reverse=True), "el score nunca sube al debilitar"
    assert scores[-1] < _umbral() <= scores[0], f"no distingue fuerza: {scores}"


def prueba_entre_otras_bandas_el_score_baja_con_cada_debilitamiento() -> None:
    """La otra mitad: con más bandas en el espectro, cada paso baja de verdad."""
    centro = _centro("GF-05")
    otras = ((_centro("GF-04"), 0.05, 20.0), (_centro("GF-03"), 1.0, 20.0), (900.0, 0.1, 20.0))
    scores = [
        evaluar(espectro_sintetico(((centro, altura, 20.0), *otras))).por_id("GF-05").score
        for altura in ALTURAS
    ]

    # Estricto mientras haya banda; por debajo del piso ya no hay nada que bajar.
    assert scores[0] > scores[1] > scores[2] > 0.0, scores
    assert scores[3:] == [0.0, 0.0], scores


def prueba_es_determinista() -> None:
    """La misma entrada da el mismo score siempre."""
    espectro = espectro_sintetico(
        ((_centro("GF-05"), 1.0, 20.0), (_centro("GF-03"), 0.5, 15.0))
    )

    primero = evaluar(espectro).scores()
    for _ in range(3):
        assert evaluar(espectro).scores() == primero


def prueba_los_siete_grupos_siempre_vienen_en_el_orden_canonico() -> None:
    resultado = evaluar(espectro_sintetico(((_centro("GF-05"), 1.0, 20.0),)))

    assert tuple(p.grupo for p in resultado.puntajes) == obtener_catalogo().orden_canonico
    assert resultado.version_catalogo == obtener_catalogo().version


def prueba_el_score_siempre_cae_entre_cero_y_uno() -> None:
    espectro = espectro_sintetico(
        tuple((centro, 1.0, 30.0) for centro in (1715.0, 2900.0, 3400.0))
    )

    for puntaje in evaluar(espectro).puntajes:
        assert 0.0 <= puntaje.score <= 1.0


# --------------------------------------------------------------------------- #
# El relleno de ceros: «no evaluable» no es «ausente»
# --------------------------------------------------------------------------- #


def prueba_una_region_fuera_del_tramo_medido_queda_no_evaluable() -> None:
    """Un 0 de relleno dice «no se midió», no «no hay pico».

    El espectro mide solo la mitad alta del eje, así que las regiones de abajo
    —C=O, C=C, aromático— no se evaluaron. No son ausencias.
    """
    catalogo = obtener_catalogo()
    espectro = espectro_sintetico(
        ((_centro("GF-01"), 1.0, 300.0),), medido=(2000.0, 4000.0)
    )

    resultado = evaluar(espectro)
    for grupo in catalogo.grupos:
        puntaje = resultado.por_id(grupo.id)
        if grupo.region_cm1[0] < 2000.0:
            assert not puntaje.evaluable, f"{grupo.id} debería ser no evaluable"
            assert NO_EVALUABLE in puntaje.ajustes
            assert puntaje.score == 0.0
            assert puntaje.pico_cm1 is None
        else:
            assert puntaje.evaluable, f"{grupo.id} sí se midió"


def prueba_no_evaluable_se_distingue_de_ausente() -> None:
    """La diferencia que importa en el incremento 4."""
    region = obtener_catalogo().por_id("GF-05").region_cm1

    ausente = evaluar(espectro_sintetico(((_centro("GF-01"), 1.0, 300.0),)))
    no_medido = evaluar(
        espectro_sintetico(
            ((_centro("GF-01"), 1.0, 300.0),), medido=(region[1] + 100, 4000.0)
        )
    )

    assert ausente.por_id("GF-05").evaluable, "se midió: la ausencia es real"
    assert ausente.por_id("GF-05").score == 0.0
    assert NO_EVALUABLE not in ausente.por_id("GF-05").ajustes
    assert not no_medido.por_id("GF-05").evaluable
    assert NO_EVALUABLE in no_medido.por_id("GF-05").ajustes


# --------------------------------------------------------------------------- #
# R-1 · O–H y N–H, los dos, sin suprimir ninguno
# --------------------------------------------------------------------------- #


@pytest.mark.xfail(
    strict=True,
    reason="CA-06.2: R-1 juzga O–H y N–H con un solo ancho y deja a uno bajo el umbral",
)
def prueba_r1_detecta_oh_y_nh_a_la_vez() -> None:
    """CA-06.2: los dos **detectados** en un mismo espectro, no solo «sin cero».

    Mezcla de dos espectros reales, sumados en absorbancia normalizada: el O–H
    del 1-butanol y el N–H de la anilina.
    """
    butanol, anilina = _espectro_real(BUTANOL), _espectro_real(ANILINA)
    medido = (
        max(butanol.rango_medido_cm1[0], anilina.rango_medido_cm1[0]),
        min(butanol.rango_medido_cm1[1], anilina.rango_medido_cm1[1]),
    )
    suma = [a + b for a, b in zip(butanol.intensidad, anilina.intensidad)]
    dentro = [s for s, w in zip(suma, butanol.eje_cm1) if medido[0] <= w <= medido[1]]
    minimo, maximo = min(dentro), max(dentro)
    mezcla = EspectroDePrueba(
        eje_cm1=butanol.eje_cm1,
        intensidad=tuple(
            (s - minimo) / (maximo - minimo) if medido[0] <= w <= medido[1] else 0.0
            for s, w in zip(suma, butanol.eje_cm1)
        ),
        rango_medido_cm1=medido,
    )

    resultado = evaluar(mezcla)
    assert resultado.por_id("GF-01").score >= _umbral()
    assert resultado.por_id("GF-02").score >= _umbral()


def prueba_r1_ajusta_sin_dejar_en_cero_a_ninguno() -> None:
    """R-1 ajusta, no excluye. Es menos que CA-06.2, que se prueba arriba."""
    catalogo = obtener_catalogo()
    ancho_oh = catalogo.por_id("GF-01").region_cm1
    region_nh = catalogo.por_id("GF-02").region_cm1
    corte = obtener_configuracion().motor.ancho_media_altura_umbral_cm1  # type: ignore[union-attr]

    espectro = espectro_sintetico(
        (
            # O–H: ancha de verdad, más que el corte de R-1.
            ((ancho_oh[0] + ancho_oh[1]) / 2, 0.9, corte * 2),
            # N–H: angosta, dentro de la región de GF-02.
            (region_nh[1] - 20, 0.6, corte / 10),
        )
    )

    resultado = evaluar(espectro)
    gf01, gf02 = resultado.por_id("GF-01"), resultado.por_id("GF-02")

    assert gf01.score > 0.0, "R-1 no puede suprimir el O–H"
    assert gf02.score > 0.0, "R-1 no puede suprimir el N–H"


def prueba_r1_premia_la_banda_ancha_como_oh_y_la_angosta_como_nh() -> None:
    """El desempate es por ancho, el rasgo que el propio catálogo declara."""
    corte = obtener_configuracion().motor.ancho_media_altura_umbral_cm1  # type: ignore[union-attr]
    centro = _centro("GF-02")  # dentro del traslape 3300–3500

    ancha = evaluar(espectro_sintetico(((centro, 0.9, corte * 2),)))
    angosta = evaluar(espectro_sintetico(((centro, 0.9, corte / 10),)))

    assert ancha.por_id("GF-01").score > angosta.por_id("GF-01").score
    assert angosta.por_id("GF-02").score > ancha.por_id("GF-02").score


def prueba_r1_lee_la_forma_del_catalogo() -> None:
    """Guarda de la decisión: R-1 se activa desde `forma`, no desde una lista
    de IDs escrita en el motor. Si estas palabras cambian en el catálogo, R-1
    dejaría de aplicarse y hay que enterarse por una prueba roja."""
    from motor_identificacion.reglas import FORMA_ANCHA, FORMA_ANGOSTA

    catalogo = obtener_catalogo()
    assert catalogo.por_id("GF-01").forma == FORMA_ANCHA
    assert catalogo.por_id("GF-02").forma == FORMA_ANGOSTA


def prueba_r1_juzga_la_banda_mas_prominente_y_no_un_bache() -> None:
    """D-22: en la anilina ganaba un bache en 3226, de 301 cm⁻¹; su N–H mide 74."""
    gf01 = evaluar(_espectro_real(ANILINA)).por_id("GF-01")

    assert R1_ANCHO_NO_ESPERADO in gf01.ajustes
    assert 0.0 < gf01.score < _umbral(), "ajusta, no suprime"


# --------------------------------------------------------------------------- #
# R-2 · la banda acompañante es el desempate, no decoración
# --------------------------------------------------------------------------- #


def prueba_r2_sin_el_ch_de_alqueno_el_score_de_gf06_se_acota() -> None:
    """GF-06 exige su =C–H: sin él, no se reporta el alqueno."""
    centro = _centro("GF-06")
    acompanante = _acompanante("GF-06", "confirmacion")

    sin_confirmacion = evaluar(espectro_sintetico(((centro, 0.8, 30.0),)))
    con_confirmacion = evaluar(
        espectro_sintetico(((centro, 0.8, 30.0), (acompanante, 0.6, 30.0)))
    )

    gf06_sin = sin_confirmacion.por_id("GF-06")
    assert gf06_sin.score < _umbral()
    assert R2_FALTA_CONFIRMACION in gf06_sin.ajustes
    assert con_confirmacion.por_id("GF-06").score > gf06_sin.score


def prueba_r2_gf07_exige_el_par_completo_mas_el_ch_aromatico() -> None:
    """Las dos bandas del par **y** el C–H aromático. Falta una, no hay anillo."""
    centro = _centro("GF-07")
    par_alto = _acompanante("GF-07", "par", 0)
    par_bajo = _acompanante("GF-07", "par", 1)
    aromatico = _acompanante("GF-07", "confirmacion")
    banda = (centro, 0.7, 25.0)

    completo = evaluar(
        espectro_sintetico(
            (banda, (par_alto, 0.6, 20.0), (par_bajo, 0.6, 20.0), (aromatico, 0.5, 25.0))
        )
    ).por_id("GF-07")
    medio_par = evaluar(
        espectro_sintetico((banda, (par_alto, 0.6, 20.0), (aromatico, 0.5, 25.0)))
    ).por_id("GF-07")
    sin_aromatico = evaluar(
        espectro_sintetico((banda, (par_alto, 0.6, 20.0), (par_bajo, 0.6, 20.0)))
    ).por_id("GF-07")

    assert completo.score > medio_par.score
    assert medio_par.score < _umbral()
    assert R2_FALTA_PAR in medio_par.ajustes
    assert sin_aromatico.score < _umbral()
    assert R2_FALTA_CONFIRMACION in sin_aromatico.ajustes


def prueba_r2_el_par_usa_la_tolerancia_de_ut03() -> None:
    """Las bandas puntuales ~1600 y ~1500 se buscan con el margen de UT-03."""
    tolerancia = obtener_configuracion().motor.tolerancia_banda_puntual_cm1  # type: ignore[union-attr]
    centro = _centro("GF-07")
    par_alto = _acompanante("GF-07", "par", 0)
    par_bajo = _acompanante("GF-07", "par", 1)
    aromatico = _acompanante("GF-07", "confirmacion")

    def con_corrimiento(delta: float) -> float:
        return evaluar(
            espectro_sintetico(
                (
                    (centro, 0.7, 25.0),
                    (par_alto + delta, 0.6, 10.0),
                    (par_bajo, 0.6, 10.0),
                    (aromatico, 0.5, 25.0),
                )
            )
        ).por_id("GF-07").score

    assert con_corrimiento(tolerancia / 2) > 0.0
    assert con_corrimiento(tolerancia * 5) < con_corrimiento(0.0)


def prueba_r2_el_indicio_no_condiciona_la_deteccion() -> None:
    """D-20.4: la banda de ácidos de GF-01 es `indicio`, no `confirmacion`.

    Si condicionara, los alcoholes y fenoles quedarían penalizados por no tener
    la banda de ácido, que es justo lo que los distingue de un ácido.
    """
    corte = obtener_configuracion().motor.ancho_media_altura_umbral_cm1  # type: ignore[union-attr]
    indicio = obtener_catalogo().por_id("GF-01").acompanantes_por_rol("indicio")[0]

    sin_banda_de_acido = evaluar(
        espectro_sintetico(((_centro("GF-01"), 0.9, corte * 2),))
    ).por_id("GF-01")

    assert sin_banda_de_acido.score >= _umbral(), (
        "un alcohol sin banda de ácido debe poder afirmar O–H; el indicio no "
        f"condiciona (región del indicio: {indicio.rango})"
    )


def prueba_el_indicio_suma_en_el_acido_benzoico() -> None:
    """D-22.2: el O–H de un ácido se ve en el `indicio`, no en 3200–3550.

    Era el único falso negativo de la tabla (GF-01 en 0.26).
    """
    gf01 = evaluar(_espectro_real(ACIDO_BENZOICO)).por_id("GF-01")

    assert INDICIO_SUMA in gf01.ajustes
    assert gf01.score >= _umbral(), f"GF-01 quedó en {gf01.score:.2f}"
    assert gf01.pico_cm1 is None, "la evidencia no está en un pico de la región"


def prueba_el_indicio_es_neutro_cuando_falta(monkeypatch) -> None:
    """Asimétrico a propósito: quien no trae banda de ácido no pierde nada."""
    from motor_identificacion.reglas import evaluador

    espectros = {n: _espectro_real(n) for n in (BUTANOL, CICLOHEXANO, ACETONA, TOLUENO, ANILINA)}
    con = {n: evaluar(e).por_id("GF-01") for n, e in espectros.items()}
    monkeypatch.setattr(evaluador, "_aporte_indicio", lambda *_: 0.0)
    sin = {n: evaluar(e).por_id("GF-01") for n, e in espectros.items()}

    assert con == sin
    assert all(INDICIO_SUMA not in p.ajustes for p in con.values())
    # Y la suma misma deja el puntaje intacto cuando no hay qué sumar.
    for puntaje in con.values():
        assert evaluador._sumar_indicio(puntaje, 0.0) == puntaje


def prueba_el_indicio_tiene_que_alcanzar_el_piso_en_su_zona() -> None:
    """Una banda que no llena la zona no es una envolvente: no suma."""
    from motor_identificacion.reglas import evaluador

    motor = obtener_configuracion().motor
    assert motor is not None
    grupo = obtener_catalogo().por_id("GF-01")
    piso = motor.fuerza_minima_relativa["fuerte"].piso
    banda = (_acompanante("GF-01", "indicio"), piso * 1.2, motor.ancho_media_altura_umbral_cm1 * 1.1)
    espectro = espectro_sintetico((banda, (1000.0, 1.0, 20.0)))
    rejilla = Rejilla(
        espectro.eje_cm1, espectro.intensidad, espectro.rango_medido_cm1,
        motor.definicion_metodo.margen_linea_base_cm1,
    )
    assert evaluador._aporte_indicio(grupo, rejilla, motor) == 0.0


def prueba_el_indicio_nunca_resta(monkeypatch) -> None:
    from motor_identificacion.reglas import evaluador

    espectros = [_espectro_real(n) for n in TODOS]
    con = [evaluar(e).por_id("GF-01").score for e in espectros]
    monkeypatch.setattr(evaluador, "_aporte_indicio", lambda *_: 0.0)
    sin = [evaluar(e).por_id("GF-01").score for e in espectros]

    assert all(c >= s for c, s in zip(con, sin))
    assert any(c > s for c, s in zip(con, sin)), "el indicio no está sumando nada"


# --------------------------------------------------------------------------- #
# Pisos de fuerza (D-22.3 y D-22.4)
# --------------------------------------------------------------------------- #


def prueba_una_banda_bajo_el_piso_de_su_clase_no_puntua() -> None:
    """Justo debajo del piso no hay banda; justo encima, sí (clase fuerte)."""
    motor = obtener_configuracion().motor
    assert motor is not None
    piso = motor.fuerza_minima_relativa["fuerte"].piso
    centro = _centro("GF-05")

    bajo = evaluar(espectro_sintetico(((centro, piso * 0.95, 20.0),))).por_id("GF-05")
    sobre = evaluar(espectro_sintetico(((centro, piso * 1.05, 20.0),))).por_id("GF-05")

    assert bajo.score == 0.0 and BAJO_EL_PISO in bajo.ajustes
    assert sobre.score >= _umbral() and BAJO_EL_PISO not in sobre.ajustes


def prueba_el_piso_se_exige_dentro_de_la_region() -> None:
    """Un pico ajeno, por fuerte que sea, no acredita a la región vecina.

    Es lo que producía los GF-06 falsos: ganaban con 1684, 1614 y 1618.
    """
    for archivo in (ACIDO_BENZOICO, TOLUENO, ANILINA):
        gf06 = evaluar(_espectro_real(archivo)).por_id("GF-06")
        assert BAJO_EL_PISO in gf06.ajustes, archivo
        assert gf06.score == 0.0, archivo


def prueba_el_pico_de_fuera_sigue_valiendo_si_la_region_trae_senal() -> None:
    """D-22: no se prohíben del todo. El GF-03 de la acetona gana en 2969."""
    gf03 = evaluar(_espectro_real(ACETONA)).por_id("GF-03")
    assert gf03.score >= _umbral()
    assert gf03.pico_cm1 is not None and gf03.pico_cm1 > gf03.region_cm1[1]


def prueba_toda_intensidad_del_catalogo_tiene_piso() -> None:
    """Si alguien cambia la palabra en el catálogo, hay que enterarse aquí."""
    from motor_identificacion.reglas.evaluador import CLASE_DE_INTENSIDAD

    motor = obtener_configuracion().motor
    assert motor is not None
    clases = {g.id: CLASE_DE_INTENSIDAD[g.intensidad] for g in obtener_catalogo().grupos}
    assert clases == {
        "GF-01": "fuerte", "GF-05": "fuerte", "GF-06": "debil",
        "GF-02": "media", "GF-03": "media", "GF-04": "media", "GF-07": "media",
    }
    assert set(clases.values()) == set(motor.fuerza_minima_relativa)


# --------------------------------------------------------------------------- #
# Zona aislada y fallos
# --------------------------------------------------------------------------- #


def prueba_la_via_de_reglas_no_necesita_mod04_para_funcionar() -> None:
    """Zona aislada: la entrada es un protocolo de tres atributos numéricos."""
    espectro = espectro_sintetico(((_centro("GF-05"), 1.0, 20.0),))

    assert not hasattr(espectro, "nombre")
    assert not hasattr(espectro, "formato")
    assert evaluar(espectro).por_id("GF-05").score > 0.0


def prueba_sin_los_parametros_del_motor_no_arranca() -> None:
    """Sin los cortes de UT-03 no se puede aplicar R-1 ni R-2 ni R-4."""
    import dataclasses

    configuracion = dataclasses.replace(obtener_configuracion(), motor=None)

    with pytest.raises(ErrorDelMotor, match="motor"):
        evaluar(
            espectro_sintetico(((_centro("GF-05"), 1.0, 20.0),)),
            configuracion=configuracion,
        )


def prueba_un_espectro_que_no_cumple_el_contrato_se_rechaza() -> None:
    malos = [
        EspectroDePrueba(eje_cm1=(1.0, 2.0), intensidad=(0.1,), rango_medido_cm1=(1.0, 2.0)),
        EspectroDePrueba(eje_cm1=(1.0,), intensidad=(0.1,), rango_medido_cm1=(1.0, 1.0)),
    ]

    for espectro in malos:
        with pytest.raises(ErrorDelMotor, match="contrato"):
            evaluar(espectro)


def prueba_el_motor_no_sale_a_la_red() -> None:
    carpeta = RAIZ / "motor_identificacion"
    prohibidos = ["socket", "urllib", "http.client", "requests", "httpx", "urlopen"]

    for archivo in sorted(carpeta.rglob("*.py")):
        texto = archivo.read_text(encoding="utf-8")
        for nombre in prohibidos:
            assert nombre not in texto, (
                f"{archivo.name} menciona «{nombre}»: MOD-06 no sale a la red"
            )


def _modulos_importados(archivo: Path) -> set[str]:
    """Los módulos que un archivo importa de verdad, leídos del árbol sintáctico.

    Se lee el AST y no el texto porque los docstrings sí nombran cosas —el motor
    explica justamente por qué **no** importa de `herramientas/`— y lo que hay
    que vigilar es el código, no la prosa.
    """
    import ast

    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module)
    return modulos


def _archivos_del_motor() -> list[Path]:
    return sorted((RAIZ / "motor_identificacion").rglob("*.py"))


def prueba_el_motor_no_importa_de_herramientas() -> None:
    """La aplicación nunca importa de `herramientas/`, que es apoyo externo.

    `medir_anchos.py` hace cuentas parecidas, pero el motor tiene las suyas.
    """
    for archivo in _archivos_del_motor():
        for modulo in _modulos_importados(archivo):
            assert not modulo.startswith("herramientas"), (
                f"{archivo.name} importa «{modulo}»: el motor escribe su "
                "propia detección de picos"
            )


def prueba_el_motor_no_abre_archivos() -> None:
    """Zona aislada: el motor no abre archivos durante la inferencia."""
    import ast

    for archivo in _archivos_del_motor():
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
                assert nodo.func.id != "open", (
                    f"{archivo.name} abre un archivo: leer del disco es de "
                    "UT-01 y UT-03, no del motor"
                )


# --------------------------------------------------------------------------- #
# Espectros reales · R-3 y R-4, las regresiones obligatorias
# --------------------------------------------------------------------------- #

ACETONA = "67-64-1-IR.jdx"
ACIDO_BENZOICO = "65-85-0-IR.jdx"
CICLOHEXANO = "110-82-7-IR(Cyclohexane).jdx"
CICLOHEXENO = "110-83-8-IR(Cyclohexene).jdx"
TOLUENO = "108-88-3-IR(Toluene).jdx"
BENZONITRILO = "100-47-0-IR(Benzonitrile).jdx"
ACETONITRILO = "75-05-8-IR(Acetonitrile).jdx"
ANILINA = "62-53-3-IR.jdx"
BUTANOL = "71-36-3-IR(1-Butanol).jdx"

#: Los ocho de la tabla de verdad de D-21 (el benzonitrilo lo rechaza MOD-04).
TODOS = (
    CICLOHEXANO, ACETONA, ACIDO_BENZOICO, TOLUENO,
    CICLOHEXENO, ACETONITRILO, ANILINA, BUTANOL,
)


def prueba_r3_la_acetona_da_carbonilo_y_no_da_aromatico() -> None:
    """R-3 · la trampa del CCl₄, convertida en red de seguridad permanente.

    El archivo declara contaminación de CCl₄ en ~1550 cm⁻¹, que cae dentro de
    1450–1600 —la región de GF-07— y la acetona **no tiene anillo aromático**.
    Un «pico dentro del rango» ingenuo reportaría un aromático inexistente.
    """
    resultado = evaluar(_espectro_real(ACETONA))
    gf05, gf07 = resultado.por_id("GF-05"), resultado.por_id("GF-07")

    assert gf05.score >= _umbral(), f"C=O quedó en {gf05.score:.2f}"
    assert gf05.pico_cm1 is not None
    region = obtener_catalogo().por_id("GF-05").region_cm1
    assert region[0] <= gf05.pico_cm1 <= region[1], (
        "el plan pide que con la acetona detecte C=O dentro de su región"
    )
    assert gf07.score < _umbral(), (
        f"GF-07 quedó en {gf07.score:.2f}: el artefacto de CCl₄ se reportó como "
        "anillo aromático"
    )


def prueba_r4_el_acido_benzoico_no_tiene_ch_alifatico() -> None:
    """R-4 · el ácido benzoico no tiene carbonos sp³, y no debe reportar GF-03.

    Su envolvente ancha de O–H ocupa la zona del C–H alifático: afirmarlo ahí
    exige picos agudos y resueltos, no un hombro ancho.
    """
    gf03 = evaluar(_espectro_real(ACIDO_BENZOICO)).por_id("GF-03")

    assert gf03.score < _umbral(), f"GF-03 quedó en {gf03.score:.2f}"
    assert R4_HOMBRO_ANCHO in gf03.ajustes


def _con_motor(**cambios):
    """La configuración del repositorio con otros parámetros, solo en memoria."""
    import dataclasses

    base = obtener_configuracion()
    assert base.motor is not None
    return dataclasses.replace(base, motor=dataclasses.replace(base.motor, **cambios))


def prueba_r4_se_aplica_al_butanol_y_su_ch_pasa_el_corte() -> None:
    """El caso apretado de R-4, comprobado de verdad.

    El 1-butanol lleva envolvente ancha de O–H **y** C–H alifático. En T-15b el
    detector medía el C–H, no veía envolvente y la regla nunca se aplicaba: la
    prueba pasaba sin probar nada. Aquí se exige que R-4 **entre**, que el ancho
    al 80 % sea el de la calibración, y que con un corte menor reviente.
    """
    espectro = _espectro_real(BUTANOL)
    gf03 = evaluar(espectro).por_id("GF-03")
    assert R4_PICO_AGUDO in gf03.ajustes, f"R-4 no se aplicó: {gf03.ajustes}"
    assert gf03.score >= _umbral()

    motor = obtener_configuracion().motor
    assert motor is not None
    assert 118.3 <= motor.ancho_pico_agudo_max_cm1

    estricto = evaluar(espectro, configuracion=_con_motor(ancho_pico_agudo_max_cm1=100.0))
    assert R4_HOMBRO_ANCHO in estricto.por_id("GF-03").ajustes
    assert estricto.por_id("GF-03").score == 0.0


#: Los anchos de D-20 (docs/evidencia/d-20-anchos.md): compuesto, grupo, fracción.
ANCHOS_D20 = [
    pytest.param("71-36-3-IR(1-Butanol).jdx", "GF-01", "fraccion_r1", 408.9, id="butanol-r1"),
    pytest.param("62-53-3-IR.jdx", "GF-02", "fraccion_r1", 74.0, id="anilina-r1"),
    pytest.param("71-36-3-IR(1-Butanol).jdx", "GF-03", "fraccion_r4", 118.3, id="butanol-r4"),
    pytest.param("65-85-0-IR.jdx", "GF-03", "fraccion_r4", 216.5, id="benzoico-r4"),
    pytest.param("110-82-7-IR(Cyclohexane).jdx", "GF-03", "fraccion_r4", 12.6, id="ciclohexano-r4"),
]


@pytest.mark.parametrize(("archivo", "grupo", "fraccion", "esperado"), ANCHOS_D20)
def prueba_el_motor_mide_los_anchos_de_la_calibracion(
    archivo: str, grupo: str, fraccion: str, esperado: float
) -> None:
    """175 y 160 solo significan algo si el motor mide como se calibraron."""
    espectro = _espectro_real(archivo)
    motor = obtener_configuracion().motor
    assert motor is not None
    metodo = motor.definicion_metodo
    rejilla = Rejilla(
        espectro.eje_cm1, espectro.intensidad, espectro.rango_medido_cm1,
        metodo.margen_linea_base_cm1,
    )
    cima = rejilla.cima_en(*obtener_catalogo().por_id(grupo).region_cm1)
    ancho = rejilla.ancho(cima, getattr(metodo, fraccion)).cm1
    assert ancho == pytest.approx(esperado, abs=0.1)


def prueba_el_vecindario_no_depende_de_cuanto_se_busque() -> None:
    """Buscar picos más lejos no puede mover la línea base (T-15d, punto 3)."""
    espectro = _espectro_real(BUTANOL)
    motor = obtener_configuracion().motor
    assert motor is not None
    rejilla = Rejilla(
        espectro.eje_cm1, espectro.intensidad, espectro.rango_medido_cm1,
        motor.definicion_metodo.margen_linea_base_cm1,
    )
    region = obtener_catalogo().por_id("GF-03").region_cm1
    bases = {p.linea_base for p in rejilla.picos_en(*region, busqueda=500.0)}
    assert bases == {rejilla.linea_base(*region)}

    # Y por el camino que usa el puntaje, que es donde se desviaba.
    from motor_identificacion.reglas import evaluador

    for grupo in obtener_catalogo().grupos:
        candidatos = evaluador._candidatos(rejilla, grupo.region_cm1, motor)
        assert {c.pico.linea_base for c in candidatos} == {
            rejilla.linea_base(*grupo.region_cm1)
        }, grupo.id


def prueba_r4_no_ve_envolvente_donde_solo_hay_linea_base() -> None:
    """Una ondulación ancha de la línea base no es un O–H: no llega al piso."""
    for archivo in (CICLOHEXANO, TOLUENO, ACETONITRILO, ACETONA, CICLOHEXENO, ANILINA):
        ajustes = evaluar(_espectro_real(archivo)).por_id("GF-03").ajustes
        assert not {R4_PICO_AGUDO, R4_HOMBRO_ANCHO} & set(ajustes), archivo


def prueba_r4_mide_en_la_cima_de_la_region_y_no_en_un_satelite() -> None:
    """Un pico agudo justo fuera de la región no acredita a un hombro ancho.

    Con el vecindario ya unificado, el satélite 2835 del ácido benzoico mide
    90 cm⁻¹ y pasaría el corte; la cima de la región mide 216.5.
    """
    resultado = evaluar(_espectro_real(ACIDO_BENZOICO)).por_id("GF-03")
    assert R4_HOMBRO_ANCHO in resultado.ajustes
    assert resultado.score == 0.0


def prueba_r4_solo_se_aplica_dentro_de_la_envolvente_de_un_acido() -> None:
    """El ciclohexano no tiene O–H: R-4 no tiene por qué entrar."""
    gf03 = evaluar(_espectro_real(CICLOHEXANO)).por_id("GF-03")

    assert R4_HOMBRO_ANCHO not in gf03.ajustes
    assert gf03.score >= _umbral()


def prueba_r2_el_ciclohexeno_da_alqueno_y_el_tolueno_aromatico() -> None:
    """Los dos juntos son R-2: lo que los distingue es la banda acompañante."""
    ciclohexeno = evaluar(_espectro_real(CICLOHEXENO))
    tolueno = evaluar(_espectro_real(TOLUENO))

    assert ciclohexeno.por_id("GF-06").score >= _umbral(), "falta el alqueno"
    assert ciclohexeno.por_id("GF-07").score < _umbral(), "aromático inexistente"
    assert tolueno.por_id("GF-07").score >= _umbral(), "falta el aromático"


def prueba_el_acetonitrilo_da_nitrilo_sin_aromatico() -> None:
    resultado = evaluar(_espectro_real(ACETONITRILO))

    assert resultado.por_id("GF-04").score >= _umbral()
    assert resultado.por_id("GF-07").score < _umbral()


def prueba_la_anilina_da_nh() -> None:
    """El N–H angosto del lado de R-1."""
    assert evaluar(_espectro_real(ANILINA)).por_id("GF-02").score >= _umbral()


def prueba_el_butanol_da_oh_ancho() -> None:
    resultado = evaluar(_espectro_real(BUTANOL))

    assert resultado.por_id("GF-01").score >= _umbral()
    assert resultado.por_id("GF-01").ancho_cm1 is not None
    corte = obtener_configuracion().motor.ancho_media_altura_umbral_cm1  # type: ignore[union-attr]
    assert resultado.por_id("GF-01").ancho_cm1 >= corte, "el O–H debe salir ancho"


def prueba_los_espectros_reales_son_deterministas() -> None:
    espectro = _espectro_real(ACETONA)

    primero = evaluar(espectro).scores()
    assert evaluar(espectro).scores() == primero


# --------------------------------------------------------------------------- #
# El conjunto completo por compuesto
# --------------------------------------------------------------------------- #

#: Lo que cada espectro real debería dar, según la sección 9 del plan y la lista
#: de T-15b. Los marcados `xfail` fallan hoy: ver la nota del encabezado.
ESPERADOS = [
    pytest.param(CICLOHEXANO, {"GF-03"}, id="ciclohexano"),
    pytest.param(ACETONA, {"GF-03", "GF-05"}, id="acetona"),
    pytest.param(ACIDO_BENZOICO, {"GF-01", "GF-05", "GF-07"}, id="acido-benzoico"),
    pytest.param(TOLUENO, {"GF-03", "GF-07"}, id="tolueno"),
    pytest.param(CICLOHEXENO, {"GF-03", "GF-06"}, id="ciclohexeno"),
    pytest.param(BENZONITRILO, {"GF-04", "GF-07"}, id="benzonitrilo"),
    pytest.param(ACETONITRILO, {"GF-03", "GF-04"}, id="acetonitrilo"),
    pytest.param(ANILINA, {"GF-02", "GF-07"}, id="anilina"),
    pytest.param(BUTANOL, {"GF-01", "GF-03"}, id="1-butanol"),
]


@pytest.mark.parametrize(("archivo", "esperados"), ESPERADOS)
def prueba_el_conjunto_detectado_es_el_esperado(
    archivo: str, esperados: set[str]
) -> None:
    resultado = evaluar(_espectro_real(archivo))
    scores = resultado.scores()
    obtenidos = {g for g, s in scores.items() if s >= _umbral()}

    detalle = " ".join(f"{g}={scores[g]:.2f}" for g in GRUPOS)
    assert obtenidos == esperados, (
        f"{archivo}: se esperaba {sorted(esperados)} y se obtuvo "
        f"{sorted(obtenidos)} · scores: {detalle}"
    )


# --------------------------------------------------------------------------- #
# No-«hardcodeo»: ni regiones ni cortes escritos en el motor
# --------------------------------------------------------------------------- #


#: Los números que el motor **no** puede llevar escritos: las regiones de los
#: siete grupos y de los subtipos de C=O (son de UT-01), y los tres cortes y la
#: definición del método del bloque `motor` (son de UT-03).
NUMEROS_PROHIBIDOS = {
    3200, 3550, 2500, 3300, 3500, 2850, 2960, 2210, 2260, 1670, 1780,
    1620, 1680, 3020, 3100, 1450, 1600, 1500, 1715, 1720, 1735, 1740,
    1750, 1690, 1760, 1630, 1700,
    175, 160, 15,
    # La definición del método, que T-15c movió a UT-03 (D-21).
    0.5, 0.8, 200,
    # Los pisos de fuerza (D-22).
    0.10, 0.025, 0.029,
}


def prueba_el_motor_no_escribe_ni_regiones_ni_cortes() -> None:
    """Los números salen de UT-01 y de UT-03, nunca del código del motor.

    Se recorren las **constantes numéricas del árbol sintáctico**, no el texto:
    los docstrings citan los números del plan a propósito, para dejar dicho de
    dónde sale cada regla, y eso es documentación. Lo que no puede existir es un
    número *usado* por el código.
    """
    import ast

    hallazgos: list[str] = []
    for archivo in _archivos_del_motor():
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if (
                isinstance(nodo, ast.Constant)
                and isinstance(nodo.value, (int, float))
                and not isinstance(nodo.value, bool)
                and nodo.value in NUMEROS_PROHIBIDOS
            ):
                hallazgos.append(
                    f"{archivo.relative_to(RAIZ).as_posix()}:{nodo.lineno}: "
                    f"{nodo.value}"
                )

    assert not hallazgos, (
        "estos números deben pedirse a UT-01 o a UT-03:\n" + "\n".join(hallazgos)
    )
