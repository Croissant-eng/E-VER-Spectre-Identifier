"""Pruebas de T-05 · MOD-03 Validador (puntos y rango).

Cubren las tres pruebas que el plan del incremento 1 (sección 10) le asigna a
T-05 —**CA-02.1**, **CA-02.3** y **CA-02.6**— con los fixtures de
`datos/pruebas/`, y las dos condiciones que la tarea agrega:

- el `.csv` se recorre **completo** (T-04 solo miraba las primeras diez filas,
  por eso un archivo con basura al final pasaba T-04 y aquí no);
- el `.jdx` se mide leyendo `##NPOINTS=`, `##FIRSTX=` y `##LASTX=` del
  encabezado, **sin descomprimir** el bloque de datos, y si falta alguna de las
  tres el archivo se rechaza (falla cerrado).

Los dos valores con los que se compara —puntos mínimos y rango requerido— se
leen de UT-03: hay pruebas que los cambian y comprueban que el comportamiento
cambia sin tocar código.

**MOD-03 se prueba aislado, sin MOD-02 real** (sección 9) y sin montar la API
(es T-07). Nada de esto toca la red.
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

import pytest

from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion import (
    CAPA_COHERENCIA,
    CAPA_ESTRUCTURA,
    CAPA_PUNTOS,
    CAPA_RANGO,
    CAPA_TEXTO,
    ETIQUETA_PRIMERA_X,
    ETIQUETA_PUNTOS,
    ETIQUETA_ULTIMA_X,
    Veredicto,
    validar,
    validar_requisitos,
)
from herramientas.generador_espectros import csv_sintetico, jdx_sintetico

# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #

#: El rango que usan los fixtures válidos, más amplio que el requerido.
DESDE, HASTA = 400.0, 4000.0


def _texto(ruta: Path) -> str:
    """Lee un fixture igual que lo entregaría MOD-02: texto, sin BOM."""
    return ruta.read_bytes().decode("utf-8-sig", errors="replace")


def _puntos_minimos() -> int:
    return obtener_configuracion().validacion.puntos_minimos


def _rango_requerido() -> tuple[float, float]:
    return obtener_configuracion().validacion.rango_requerido_cm1


def _con_puntos_minimos(puntos: int) -> Configuracion:
    configuracion = obtener_configuracion()
    return dataclasses.replace(
        configuracion,
        validacion=dataclasses.replace(
            configuracion.validacion, puntos_minimos=puntos
        ),
    )


def _con_rango(minimo: float, maximo: float) -> Configuracion:
    configuracion = obtener_configuracion()
    return dataclasses.replace(
        configuracion,
        validacion=dataclasses.replace(
            configuracion.validacion, rango_requerido_cm1=(minimo, maximo)
        ),
    )


def _csv(puntos: int, desde: float = DESDE, hasta: float = HASTA, **extra: object) -> str:
    return csv_sintetico(puntos, desde, hasta, **extra).decode("ascii")  # type: ignore[arg-type]


def _jdx(puntos: int, desde: float = DESDE, hasta: float = HASTA) -> str:
    return jdx_sintetico("ESPECTRO DE PRUEBA", puntos, desde, hasta).decode("ascii")


# --------------------------------------------------------------------------- #
# CA-02.1 · CSV de 900 puntos y rango 400–4000 → válido
# --------------------------------------------------------------------------- #


def prueba_ca_02_1_el_csv_normal_cumple_los_requisitos(
    carpeta_fixtures: Path,
) -> None:
    archivo = "espectro-valido-900-puntos.csv"

    veredicto = validar_requisitos(archivo, _texto(carpeta_fixtures / archivo))

    assert veredicto.valido, veredicto.detalle
    assert veredicto.codigo is None


def prueba_ca_02_1_el_csv_normal_pasa_todo_mod_03(carpeta_fixtures: Path) -> None:
    """El camino completo: formato (T-04) y requisitos (T-05) de corrido."""
    archivo = "espectro-valido-900-puntos.csv"

    veredicto = validar(archivo, _texto(carpeta_fixtures / archivo))

    assert veredicto.valido, veredicto.detalle


@pytest.mark.parametrize(
    "archivo",
    [
        "espectro-valido.jdx",
        "espectro-con-encabezado.csv",
        "espectro-punto-y-coma.csv",
        "espectro-puntos-minimos.csv",
    ],
)
def prueba_los_demas_fixtures_validos_tambien_cumplen(
    carpeta_fixtures: Path, archivo: str
) -> None:
    veredicto = validar(archivo, _texto(carpeta_fixtures / archivo))

    assert veredicto.valido, veredicto.detalle


# --------------------------------------------------------------------------- #
# CA-02.6 · 300 puntos válido, 299 rechazado con «Mínimo 300 puntos»
# --------------------------------------------------------------------------- #


def prueba_ca_02_6_el_minimo_exacto_se_acepta(carpeta_fixtures: Path) -> None:
    archivo = "espectro-puntos-minimos.csv"

    veredicto = validar_requisitos(archivo, _texto(carpeta_fixtures / archivo))

    assert veredicto.valido, veredicto.detalle


def prueba_ca_02_6_un_punto_menos_se_rechaza(carpeta_fixtures: Path) -> None:
    archivo = "espectro-un-punto-menos.csv"

    veredicto = validar_requisitos(archivo, _texto(carpeta_fixtures / archivo))

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.PUNTOS_INSUFICIENTES
    assert veredicto.capa == CAPA_PUNTOS


def prueba_ca_02_6_el_mensaje_es_el_que_exige_el_criterio(
    carpeta_fixtures: Path,
) -> None:
    """«Mínimo 300 puntos», con el número leído de UT-03."""
    veredicto = validar_requisitos(
        "espectro-un-punto-menos.csv",
        _texto(carpeta_fixtures / "espectro-un-punto-menos.csv"),
    )
    mensaje = mensajes.obtener(veredicto.codigo)

    assert mensaje.texto == f"Mínimo {_puntos_minimos()} puntos"
    assert mensaje.accion.strip()


def prueba_ca_02_6_el_borde_esta_en_el_punto_exacto() -> None:
    """Uno menos rechaza, el mínimo justo acepta: el límite es inclusivo."""
    minimos = _puntos_minimos()

    assert not validar_requisitos("e.csv", _csv(minimos - 1)).valido
    assert validar_requisitos("e.csv", _csv(minimos)).valido


# --------------------------------------------------------------------------- #
# CA-02.3 · rango corto → «Se requiere cubrir al menos 1400–3700 cm⁻¹»
# --------------------------------------------------------------------------- #


def prueba_ca_02_3_el_rango_corto_se_rechaza(carpeta_fixtures: Path) -> None:
    archivo = "espectro-rango-corto.csv"

    veredicto = validar_requisitos(archivo, _texto(carpeta_fixtures / archivo))

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.RANGO_INSUFICIENTE
    assert veredicto.capa == CAPA_RANGO


def prueba_ca_02_3_el_mensaje_es_el_que_exige_el_criterio(
    carpeta_fixtures: Path,
) -> None:
    """«Se requiere cubrir al menos 1400–3700 cm⁻¹», con el rango de UT-03."""
    veredicto = validar_requisitos(
        "espectro-rango-corto.csv",
        _texto(carpeta_fixtures / "espectro-rango-corto.csv"),
    )
    mensaje = mensajes.obtener(veredicto.codigo)
    minimo, maximo = _rango_requerido()

    assert mensaje.texto == (
        f"Se requiere cubrir al menos {minimo:g}–{maximo:g} cm⁻¹"
    )
    assert mensaje.accion.strip()


def prueba_ca_02_3_cubrir_el_rango_exacto_alcanza() -> None:
    """«Cubrir al menos» incluye los extremos justos."""
    minimo, maximo = _rango_requerido()

    veredicto = validar_requisitos("e.csv", _csv(_puntos_minimos(), minimo, maximo))

    assert veredicto.valido, veredicto.detalle


@pytest.mark.parametrize(
    ("caso", "desde", "hasta"),
    [
        ("le falta por abajo", 1500.0, 4000.0),
        ("le falta por arriba", 400.0, 3600.0),
        ("le falta por los dos lados", 1500.0, 3600.0),
    ],
)
def prueba_ca_02_3_cualquier_lado_que_falte_rechaza(
    caso: str, desde: float, hasta: float
) -> None:
    veredicto = validar_requisitos("e.csv", _csv(900, desde, hasta))

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.RANGO_INSUFICIENTE, caso


# --------------------------------------------------------------------------- #
# Los dos valores salen de UT-03
# --------------------------------------------------------------------------- #


def prueba_los_puntos_minimos_salen_de_ut03(carpeta_fixtures: Path) -> None:
    """Subir el mínimo en el archivo de parámetros rechaza lo que antes pasaba."""
    archivo = "espectro-valido-900-puntos.csv"
    contenido = _texto(carpeta_fixtures / archivo)

    assert validar_requisitos(archivo, contenido).valido

    exigente = validar_requisitos(
        archivo, contenido, configuracion=_con_puntos_minimos(1000)
    )
    assert not exigente.valido
    assert exigente.codigo == mensajes.PUNTOS_INSUFICIENTES


def prueba_el_rango_requerido_sale_de_ut03(carpeta_fixtures: Path) -> None:
    """Y al revés: con un rango más corto, el fixture de rango corto alcanza."""
    archivo = "espectro-rango-corto.csv"
    contenido = _texto(carpeta_fixtures / archivo)

    assert not validar_requisitos(archivo, contenido).valido

    permisivo = validar_requisitos(
        archivo, contenido, configuracion=_con_rango(1500.0, 3600.0)
    )
    assert permisivo.valido, permisivo.detalle


def prueba_los_puntos_se_revisan_antes_que_el_rango() -> None:
    """Un archivo que falla las dos cosas oye primero lo de los puntos."""
    veredicto = validar_requisitos("e.csv", _csv(10, 1500.0, 3600.0))

    assert veredicto.codigo == mensajes.PUNTOS_INSUFICIENTES


# --------------------------------------------------------------------------- #
# CSV · se recorren TODAS las filas, no solo las primeras
# --------------------------------------------------------------------------- #


def prueba_el_csv_se_recorre_completo() -> None:
    """La diferencia con T-04: la basura del final ya no se escapa.

    T-04 mira las primeras diez filas para reconocer la forma del archivo, así
    que un CSV con pares al principio y basura al final pasaba. T-05 tiene que
    contar, y contando se topa con ella.
    """
    from backend.validacion import validar_formato

    contenido = _csv(900) + "esto no es un par de numeros\n"

    assert validar_formato("e.csv", contenido).valido, (
        "T-04 solo mira las primeras filas: este archivo le parece bien"
    )

    veredicto = validar_requisitos("e.csv", contenido)
    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA


def prueba_el_conteo_no_incluye_el_encabezado() -> None:
    """Una fila de encabezado no es un punto del espectro."""
    minimos = _puntos_minimos()
    encabezado = ("numero_de_onda", "transmitancia")

    justos = _csv(minimos, encabezado=encabezado)
    uno_menos = _csv(minimos - 1, encabezado=encabezado)

    assert validar_requisitos("e.csv", justos).valido
    rechazado = validar_requisitos("e.csv", uno_menos)
    assert not rechazado.valido
    assert rechazado.codigo == mensajes.PUNTOS_INSUFICIENTES


def prueba_el_csv_de_punto_y_coma_se_mide_igual() -> None:
    """El separador de §6.1 no cambia el conteo ni el rango."""
    contenido = _csv(900, separador=";", decimal_coma=True)

    assert validar_requisitos("e.csv", contenido).valido


def prueba_un_numero_de_onda_negativo_escondido_al_final_se_rechaza() -> None:
    """Si pasara, torcería el mínimo y el rango se mediría mal."""
    contenido = _csv(900) + "-50.0,0.5\n"

    veredicto = validar_requisitos("e.csv", contenido)

    assert not veredicto.valido
    assert veredicto.capa == CAPA_COHERENCIA


def prueba_el_csv_del_tamano_maximo_se_mide_completo(
    csv_tamano_maximo: Path,
) -> None:
    """El archivo de CA-01.2 tiene cientos de miles de filas: se cuentan todas."""
    veredicto = validar_requisitos("maximo.csv", _texto(csv_tamano_maximo))

    assert veredicto.valido, veredicto.detalle


# --------------------------------------------------------------------------- #
# `.jdx` · se lee el encabezado, no se descomprime nada
# --------------------------------------------------------------------------- #


def prueba_el_jdx_se_mide_con_las_etiquetas_del_encabezado(
    carpeta_fixtures: Path,
) -> None:
    archivo = "espectro-valido.jdx"

    veredicto = validar_requisitos(archivo, _texto(carpeta_fixtures / archivo))

    assert veredicto.valido, veredicto.detalle


def prueba_el_jdx_con_pocos_puntos_se_rechaza() -> None:
    contenido = _jdx(_puntos_minimos() - 1)

    veredicto = validar_requisitos("e.jdx", contenido)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.PUNTOS_INSUFICIENTES


def prueba_el_jdx_con_rango_corto_se_rechaza() -> None:
    contenido = _jdx(900, 1500.0, 3700.0)

    veredicto = validar_requisitos("e.jdx", contenido)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.RANGO_INSUFICIENTE


def prueba_el_jdx_con_el_eje_al_reves_se_mide_igual() -> None:
    """Los archivos de NIST bajan de 4000 a 400: el rango sale del mín y el máx.

    Es también la razón de no mirar `##DELTAX=`: en un archivo real traía el
    signo equivocado (trampa 1 de la sección 11 del plan).
    """
    contenido = _jdx(900).replace(
        f"{ETIQUETA_PRIMERA_X}400.0000", f"{ETIQUETA_PRIMERA_X}4000.0000"
    ).replace(f"{ETIQUETA_ULTIMA_X}4000.0000", f"{ETIQUETA_ULTIMA_X}400.0000")

    assert f"{ETIQUETA_PRIMERA_X}4000" in contenido, "la prueba debía invertir el eje"
    assert validar_requisitos("e.jdx", contenido).valido


@pytest.mark.parametrize(
    "etiqueta", [ETIQUETA_PUNTOS, ETIQUETA_PRIMERA_X, ETIQUETA_ULTIMA_X]
)
def prueba_si_falta_una_etiqueta_del_encabezado_falla_cerrado(etiqueta: str) -> None:
    """Sin ellas habría que descomprimir los datos, y eso es de MOD-04."""
    contenido = "\n".join(
        linea for linea in _jdx(900).splitlines() if not linea.startswith(etiqueta)
    )

    veredicto = validar_requisitos("e.jdx", contenido)

    assert not veredicto.valido, etiqueta
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA
    assert veredicto.capa == CAPA_ESTRUCTURA
    assert etiqueta in veredicto.detalle


def prueba_el_bloque_de_datos_no_se_descomprime() -> None:
    """Un bloque comprimido (DIF/SQZ) no impide medir: se lee el encabezado.

    Descifrarlo es trabajo de MOD-04 en el incremento 2; aquí ni se intenta.
    """
    contenido = _jdx(900)
    cabeza, _, _ = contenido.partition("##XYDATA=")
    comprimido = (
        cabeza + "##XYDATA=(X++(Y..Y))\n400.0 J80K75j12%%\nL99M88\n##END=\n"
    )

    veredicto = validar_requisitos("e.jdx", comprimido)

    assert veredicto.valido, veredicto.detalle


@pytest.mark.parametrize(
    ("caso", "reemplazo"),
    [
        ("puntos que no son número", f"{ETIQUETA_PUNTOS}muchos"),
        ("puntos en cero", f"{ETIQUETA_PUNTOS}0"),
        ("puntos negativos", f"{ETIQUETA_PUNTOS}-900"),
        ("puntos con decimales", f"{ETIQUETA_PUNTOS}900.5"),
    ],
)
def prueba_un_npoints_ilegible_falla_cerrado(caso: str, reemplazo: str) -> None:
    contenido = _jdx(900).replace(f"{ETIQUETA_PUNTOS}900", reemplazo)

    veredicto = validar_requisitos("e.jdx", contenido)

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA, caso


@pytest.mark.parametrize(
    ("caso", "reemplazo"),
    [
        ("primera X que no es número", f"{ETIQUETA_PRIMERA_X}inicio"),
        ("primera X en cero", f"{ETIQUETA_PRIMERA_X}0"),
        ("primera X negativa", f"{ETIQUETA_PRIMERA_X}-400"),
    ],
)
def prueba_un_firstx_ilegible_falla_cerrado(caso: str, reemplazo: str) -> None:
    contenido = _jdx(900).replace(f"{ETIQUETA_PRIMERA_X}400.0000", reemplazo)

    veredicto = validar_requisitos("e.jdx", contenido)

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA, caso


def prueba_las_etiquetas_se_leen_sin_importar_mayusculas_ni_comentarios() -> None:
    """Así vienen los archivos reales: `$$` de comentario y a veces minúsculas."""
    contenido = (
        _jdx(900)
        .replace(f"{ETIQUETA_PUNTOS}900", f"{ETIQUETA_PUNTOS.lower()}900  $$ nota")
        .replace(f"{ETIQUETA_ULTIMA_X}4000.0000", f"{ETIQUETA_ULTIMA_X}4000.0 $$ cm-1")
    )

    assert validar_requisitos("e.jdx", contenido).valido


# --------------------------------------------------------------------------- #
# Orden entre T-04 y T-05, y robustez
# --------------------------------------------------------------------------- #


def prueba_el_formato_se_revisa_antes_que_los_requisitos(
    carpeta_fixtures: Path,
) -> None:
    """No se cuentan los puntos de algo que no es un espectro."""
    binario = validar(
        "binario-disfrazado.csv",
        _texto(carpeta_fixtures / "binario-disfrazado.csv"),
    )
    imagen = validar("imagen.png", _texto(carpeta_fixtures / "imagen.png"))

    assert binario.capa == CAPA_TEXTO
    assert imagen.codigo == mensajes.FORMATO_NO_SOPORTADO


def prueba_el_camino_completo_llega_a_los_requisitos(carpeta_fixtures: Path) -> None:
    """Y cuando el formato está bien, el veredicto final es el de T-05."""
    pocos = validar(
        "espectro-un-punto-menos.csv",
        _texto(carpeta_fixtures / "espectro-un-punto-menos.csv"),
    )
    corto = validar(
        "espectro-rango-corto.csv",
        _texto(carpeta_fixtures / "espectro-rango-corto.csv"),
    )

    assert pocos.codigo == mensajes.PUNTOS_INSUFICIENTES
    assert corto.codigo == mensajes.RANGO_INSUFICIENTE


def prueba_un_formato_que_mod_03_no_sabe_medir_falla_cerrado() -> None:
    """Igual que en T-04: si UT-03 admite algo que aquí no se sabe medir, no pasa."""
    configuracion = dataclasses.replace(
        obtener_configuracion(),
        archivo=dataclasses.replace(
            obtener_configuracion().archivo, formatos_permitidos=(".txt",)
        ),
    )

    veredicto = validar_requisitos("e.txt", _csv(900), configuracion=configuracion)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA


ARCHIVOS_HOSTILES = (
    "",
    "\n\n\n",
    "   \t  \n",
    "no soy un espectro",
    ",",
    "400.0\n",
    "##TITLE=\n",
    "##NPOINTS=\n",
    f"{ETIQUETA_PUNTOS}900\n",
    "400.0,0.80\n" * 2,
    "e" * 10000,
)


@pytest.mark.parametrize("contenido", ARCHIVOS_HOSTILES)
@pytest.mark.parametrize("nombre", ["espectro.csv", "espectro.jdx"])
def prueba_ninguna_entrada_hace_estallar_a_t05(nombre: str, contenido: str) -> None:
    """Misma robustez que T-04: siempre sale un veredicto (CA-02.4)."""
    veredicto = validar_requisitos(nombre, contenido)

    assert isinstance(veredicto, Veredicto)
    if not veredicto.valido:
        assert veredicto.codigo in mensajes.codigos()


def prueba_todo_rechazo_se_puede_traducir_con_ut02() -> None:
    casos = (_csv(10), _csv(900, 1500.0, 3600.0), "basura\n", _jdx(10))
    for contenido in casos:
        for nombre in ("e.csv", "e.jdx"):
            veredicto = validar_requisitos(nombre, contenido)
            if veredicto.valido:
                continue
            mensaje = mensajes.obtener(veredicto.codigo)
            assert mensaje.texto.strip()
            assert mensaje.accion.strip()


# --------------------------------------------------------------------------- #
# Registros
# --------------------------------------------------------------------------- #


def prueba_el_registro_dice_la_capa_y_no_el_contenido(
    caplog: pytest.LogCaptureFixture, carpeta_fixtures: Path
) -> None:
    contenido = _texto(carpeta_fixtures / "espectro-un-punto-menos.csv")

    with caplog.at_level(logging.INFO):
        veredicto = validar_requisitos("acetona.csv", contenido)

    registrado = "\n".join(r.getMessage() for r in caplog.records)

    assert not veredicto.valido
    assert "acetona.csv" in registrado
    assert mensajes.PUNTOS_INSUFICIENTES in registrado
    assert CAPA_PUNTOS in registrado
    assert "0.8" not in registrado, "el contenido nunca va al registro (RNF-09)"
