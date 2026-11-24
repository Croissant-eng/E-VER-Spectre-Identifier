"""Pruebas de T-09: ordenar los puntos y pasar transmitancia a absorbancia.

CA-03.1 pide que un espectro en transmitancia por ciento termine en
absorbancia. Aquí se revisa la conversión con valores conocidos, como dice la
matriz de pruebas: A tiene que ser menos el logaritmo en base 10 de T. La
parte de normalizar de 0 a 1 de ese mismo criterio se prueba en T-10.

CA-03.2 pide que un JCAMP-DX en orden descendente dé lo mismo que su
equivalente en orden ascendente.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from backend.preprocesamiento.conversion import (
    PORCENTAJE,
    UnidadSinDeclarar,
    a_absorbancia,
    ordenar,
    unidad_efectiva,
)
from backend.preprocesamiento.lector import (
    ABSORBANCIA,
    DESCONOCIDA,
    TRANSMITANCIA,
    leer,
)
from backend.preprocesamiento.procesador import procesar
from backend.utilerias import mensajes


def _leer(carpeta: Path, nombre: str):
    return leer(nombre, (carpeta / nombre).read_text(encoding="ascii"))


# CA-03.1


@pytest.mark.parametrize(
    ("porcentaje", "absorbancia"),
    [(100.0, 0.0), (10.0, 1.0), (1.0, 2.0), (50.0, -math.log10(0.5))],
)
def prueba_ca_03_1_valores_conocidos_de_transmitancia_en_porcentaje(
    porcentaje: float, absorbancia: float
) -> None:
    # Se agrega un 80 % para que la unidad se reconozca como porcentaje aunque
    # el valor probado sea pequeño.
    resultado = a_absorbancia([porcentaje, 80.0], TRANSMITANCIA)
    assert resultado[0] == pytest.approx(absorbancia)


def prueba_ca_03_1_el_csv_en_porcentaje_da_la_misma_absorbancia_que_en_fraccion(
    carpeta_fixtures: Path,
) -> None:
    en_porcentaje = _leer(carpeta_fixtures, "espectro-porcentaje.csv")
    en_fraccion = _leer(carpeta_fixtures, "espectro-valido.jdx")

    assert en_porcentaje.unidad == TRANSMITANCIA
    a = a_absorbancia([y for _, y in en_porcentaje.pares], en_porcentaje.unidad)
    b = a_absorbancia([y for _, y in en_fraccion.pares], en_fraccion.unidad)
    assert a == pytest.approx(b, abs=1e-6)
    for (_, t), absorbancia in zip(en_fraccion.pares, b):
        assert absorbancia == pytest.approx(-math.log10(t))


def prueba_la_absorbancia_no_se_convierte() -> None:
    assert a_absorbancia([0.1, 0.9, 1.7], ABSORBANCIA) == [0.1, 0.9, 1.7]


def prueba_una_transmitancia_de_cero_no_rompe_el_calculo() -> None:
    resultado = a_absorbancia([0.0, -0.01, 0.5], TRANSMITANCIA)
    assert all(math.isfinite(valor) for valor in resultado)


# D-11: la unidad de un CSV sin encabezado.


def prueba_d_11_sin_encabezado_y_algun_valor_mayor_que_1_es_porcentaje() -> None:
    assert unidad_efectiva([80.0, 95.0, 12.0], DESCONOCIDA) == PORCENTAJE
    assert unidad_efectiva([0.4, 1.2, 0.9], DESCONOCIDA) == PORCENTAJE


@pytest.mark.parametrize("valores", [[0.8, 0.9, 0.2], [0.05, 0.1, 0.9], [0.0, 1.0]])
def prueba_d_11_sin_encabezado_y_todo_entre_0_y_1_se_rechaza(valores) -> None:
    with pytest.raises(UnidadSinDeclarar):
        unidad_efectiva(valores, DESCONOCIDA)


def prueba_d_11_el_csv_ambiguo_llega_al_usuario_con_su_mensaje() -> None:
    texto = "\n".join(f"{400 + i * 4},{0.2 + (i % 7) / 10}" for i in range(901))
    resultado = procesar("ambiguo.csv", texto)
    assert not resultado.valido
    assert resultado.codigo == mensajes.UNIDAD_SIN_DECLARAR
    assert "encabezado" in mensajes.obtener(mensajes.UNIDAD_SIN_DECLARAR).accion


@pytest.mark.parametrize(
    ("encabezado", "esperada"),
    [("numero_de_onda,transmitancia", TRANSMITANCIA), ("wavenumber,absorbance", ABSORBANCIA)],
)
def prueba_d_11_con_encabezado_manda_el_encabezado(encabezado, esperada) -> None:
    texto = encabezado + "\n" + "\n".join(f"{400 + i * 4},{0.5}" for i in range(3))
    assert leer("x.csv", texto).unidad == esperada


# D-10: la unidad que no es transmitancia ni absorbancia.


@pytest.mark.parametrize("unidad", ["REFLECTANCE", "REFRACTIVE INDEX", "KUBELKA-MUNK"])
def prueba_d_10_una_unidad_no_soportada_se_rechaza_sin_convertir(
    carpeta_fixtures: Path, unidad: str
) -> None:
    texto = (carpeta_fixtures / "espectro-valido.jdx").read_text(encoding="ascii")
    lineas = [
        f"##YUNITS={unidad}" if linea.upper().startswith("##YUNITS=") else linea
        for linea in texto.splitlines()
    ]
    resultado = procesar("reflectancia.jdx", "\n".join(lineas) + "\n")
    assert not resultado.valido
    assert resultado.codigo == mensajes.UNIDAD_NO_SOPORTADA


# CA-03.2


def prueba_ca_03_2_descendente_y_ascendente_dan_lo_mismo(
    carpeta_fixtures: Path,
) -> None:
    ascendente = _leer(carpeta_fixtures, "espectro-valido.jdx")
    descendente = _leer(carpeta_fixtures, "espectro-descendente.jdx")
    assert descendente.pares[0][0] > descendente.pares[-1][0]

    assert ordenar(descendente.pares) == ordenar(ascendente.pares)


def prueba_ordenar_deja_el_eje_siempre_creciente() -> None:
    pares = [(3.0, 0.3), (1.0, 0.1), (2.0, 0.2), (2.0, 0.4)]

    resultado = ordenar(pares)

    assert resultado == [(1.0, 0.1), (2.0, pytest.approx(0.3)), (3.0, 0.3)]
