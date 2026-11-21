"""Pruebas de T-03 · MOD-02 Manejador de archivos.

Cubren las cinco pruebas que el plan del incremento 1 (sección 10) le asigna a
T-03 —**CA-01.2**, **CA-02.2** y las **tres de RNF-09**— más las condiciones de
«terminado» de la tarea: leer por bloques, no confiar en el tamaño que declara
el navegador, no escribir nada en disco, cerrar siempre la subida y registrar
solo nombre, tamaño y resultado.

**MOD-02 se prueba aislado, sin MOD-03.** Aquí no se valida formato, estructura,
puntos ni rango: eso es T-04/T-05. Varias pruebas de abajo existen justamente
para fijar esa frontera (un `.png`, un archivo vacío y un binario disfrazado los
**acepta** MOD-02, porque su tamaño está bien, y los rechaza MOD-03 después).

Tampoco se monta la API (es T-07): las subidas se construyen aquí con el mismo
`UploadFile` de FastAPI que recibirá el endpoint, y una de ellas pasa de 1 MB
para forzar el archivo temporal en disco que crea Starlette. Nada de esto toca
la red: el script de descarga de NIST no corre dentro de pytest.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import tempfile
from collections.abc import Callable
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Any

import pytest
from fastapi import UploadFile
from starlette.formparsers import MultiPartParser

from backend.manejador_archivos import (
    BLOQUE_BYTES,
    Recepcion,
    nombre_seguro,
    recibir,
)
from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion

#: Tamaño a partir del cual Starlette deja de guardar la subida en memoria y
#: crea un archivo temporal en disco. Se lee de Starlette, no se escribe aquí:
#: si mañana cambia su valor, las pruebas de RNF-09 siguen probando el umbral
#: de verdad.
SPOOL_MAXIMO: int = MultiPartParser.spool_max_size


# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


def _correr(corutina: Any) -> Recepcion:
    """Corre una corrutina sin depender de un plugin de asyncio.

    MOD-02 es asíncrono porque `UploadFile.read` lo es. No agregamos
    `pytest-asyncio` solo para esto: el incremento 1 no suma dependencias.
    """
    return asyncio.run(corutina)


def _subida(
    contenido: bytes,
    nombre: str | None = "espectro.csv",
    *,
    tamano_declarado: int | None = None,
) -> UploadFile:
    """Una subida igual a la que armaría FastAPI al recibir el formulario.

    `tamano_declarado` es el tamaño que **dice** el navegador: puede mentir, y
    MOD-02 no debe creerle (RNF-03).
    """
    almacen = SpooledTemporaryFile(max_size=SPOOL_MAXIMO)
    almacen.write(contenido)
    almacen.seek(0)
    return UploadFile(
        file=almacen,
        filename=nombre,
        size=tamano_declarado if tamano_declarado is not None else len(contenido),
    )


class _Espia:
    """Envuelve una subida para anotar cómo la leyó MOD-02.

    Guarda cuántos bytes salieron, de qué tamaño fue cada bloque pedido y si la
    subida quedó cerrada. Con `al_leer` se puede hacer fallar una lectura a la
    mitad (prueba de error de RNF-09).
    """

    def __init__(
        self,
        subida: UploadFile,
        al_leer: Callable[[_Espia], None] | None = None,
    ) -> None:
        self._subida = subida
        self._al_leer = al_leer
        self.filename = subida.filename
        self.bytes_leidos = 0
        self.bloques_pedidos: list[int] = []
        self.cerrada = False

    async def read(self, cantidad: int = -1) -> bytes:
        self.bloques_pedidos.append(cantidad)
        if self._al_leer is not None:
            self._al_leer(self)
        bloque = await self._subida.read(cantidad)
        self.bytes_leidos += len(bloque)
        return bloque

    async def close(self) -> None:
        self.cerrada = True
        await self._subida.close()


def _listado(carpeta: Path) -> list[str]:
    """Los nombres de archivo que hay en una carpeta, para el antes y después."""
    return sorted(p.name for p in carpeta.iterdir())


@pytest.fixture
def temporal_aislado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Manda los temporales del sistema a una carpeta vacía y solo nuestra.

    Así el «listado del directorio antes y después» que pide RNF-09 se puede
    mirar de verdad, sin confundirse con los temporales de otros programas.
    """
    carpeta = tmp_path / "temporales"
    carpeta.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(carpeta))
    return carpeta


def _con_tamano_maximo(bytes_maximos: int) -> Configuracion:
    """La configuración real, con otro tamaño máximo (sin tocar el archivo)."""
    configuracion = obtener_configuracion()
    return dataclasses.replace(
        configuracion,
        archivo=dataclasses.replace(
            configuracion.archivo, tamano_maximo_bytes=bytes_maximos
        ),
    )


def _maximo() -> int:
    return obtener_configuracion().archivo.tamano_maximo_bytes


# --------------------------------------------------------------------------- #
# CA-01.2 · CSV válido de exactamente el tamaño máximo → acepta
# --------------------------------------------------------------------------- #


def prueba_ca_01_2_acepta_el_csv_de_tamano_maximo_exacto(
    csv_tamano_maximo: Path,
) -> None:
    contenido = csv_tamano_maximo.read_bytes()
    assert len(contenido) == _maximo(), "el archivo de prueba no pesa el límite"

    recepcion = _correr(recibir(_subida(contenido, "espectro-maximo.csv")))

    assert recepcion.aceptado
    assert recepcion.tamano_correcto
    assert recepcion.codigo is None
    assert recepcion.bytes_leidos == len(contenido)
    assert recepcion.nombre == "espectro-maximo.csv"
    assert recepcion.contenido is not None
    assert len(recepcion.contenido) == len(contenido), (
        "el CSV es ASCII: un byte por carácter; si no coincide, se perdió algo "
        "al decodificar"
    )


def prueba_ca_01_2_el_limite_es_inclusivo_hasta_el_ultimo_byte(
    csv_tamano_maximo: Path, csv_un_byte_de_mas: Path
) -> None:
    """El borde exacto: el límite acepta, el límite más un byte rechaza."""
    en_el_limite = _correr(recibir(_subida(csv_tamano_maximo.read_bytes())))
    pasado_el_limite = _correr(recibir(_subida(csv_un_byte_de_mas.read_bytes())))

    assert en_el_limite.aceptado
    assert not pasado_el_limite.aceptado


# --------------------------------------------------------------------------- #
# CA-02.2 · un byte de más → rechaza con el mensaje de tamaño
# --------------------------------------------------------------------------- #


def prueba_ca_02_2_rechaza_el_archivo_de_un_byte_de_mas(
    csv_un_byte_de_mas: Path,
) -> None:
    contenido = csv_un_byte_de_mas.read_bytes()
    assert len(contenido) == _maximo() + 1

    recepcion = _correr(recibir(_subida(contenido, "espectro-grande.csv")))

    assert not recepcion.aceptado
    assert not recepcion.tamano_correcto
    assert recepcion.codigo == mensajes.TAMANO_EXCEDIDO
    assert recepcion.contenido is None, (
        "un rechazo no entrega contenido: MOD-03 no debe poder mirarlo"
    )


def prueba_ca_02_2_el_rechazo_trae_motivo_y_accion_de_ut02(
    csv_un_byte_de_mas: Path,
) -> None:
    """MOD-02 devuelve el código; el texto exigido lo pone UT-02 (RNF-01)."""
    recepcion = _correr(recibir(_subida(csv_un_byte_de_mas.read_bytes())))
    mensaje = mensajes.obtener(recepcion.codigo)

    assert "tamaño máximo permitido" in mensaje.texto
    assert mensaje.accion.strip()
    assert mensaje.titulo.strip()


# --------------------------------------------------------------------------- #
# RNF-09 · normal · subida de ~3 MB: el temporal de FastAPI no sobrevive
# --------------------------------------------------------------------------- #


def prueba_rnf_09_normal_no_queda_temporal_tras_una_subida_de_tres_megas(
    csv_tres_megas: Path, temporal_aislado: Path
) -> None:
    contenido = csv_tres_megas.read_bytes()
    assert len(contenido) > SPOOL_MAXIMO, (
        "el archivo debe pasar de 1 MB; si no, Starlette lo deja en memoria y "
        "la prueba no demuestra nada"
    )

    assert _listado(temporal_aislado) == [], "la carpeta temporal no arrancó vacía"

    subida = _subida(contenido, "espectro-tres-megas.csv")
    antes = _listado(temporal_aislado)
    assert len(antes) == 1, (
        "FastAPI debía haber creado el temporal en disco al pasar de 1 MB; "
        f"listado: {antes}"
    )

    recepcion = _correr(recibir(subida))

    despues = _listado(temporal_aislado)
    assert recepcion.aceptado
    assert recepcion.bytes_leidos == len(contenido)
    assert despues == [], (
        "quedó un archivo del usuario en el directorio temporal (RNF-09); "
        f"antes: {antes} · después: {despues}"
    )


# --------------------------------------------------------------------------- #
# RNF-09 · error · falla a mitad de la lectura: también se limpia
# --------------------------------------------------------------------------- #


def prueba_rnf_09_error_el_temporal_se_borra_aunque_falle_la_lectura(
    csv_tres_megas: Path, temporal_aislado: Path
) -> None:
    def fallar_en_la_segunda_lectura(espia: _Espia) -> None:
        if len(espia.bloques_pedidos) == 2:
            raise OSError(5, "Input/output error")

    subida = _subida(csv_tres_megas.read_bytes(), "espectro-tres-megas.csv")
    espia = _Espia(subida, fallar_en_la_segunda_lectura)
    antes = _listado(temporal_aislado)
    assert len(antes) == 1

    recepcion = _correr(recibir(espia))
    despues = _listado(temporal_aislado)

    assert not recepcion.aceptado
    assert recepcion.codigo == mensajes.LECTURA_INTERRUMPIDA
    assert recepcion.contenido is None
    assert espia.cerrada, "la subida debe cerrarse en el bloque finally"
    assert despues == [], (
        "el temporal debe borrarse también cuando la lectura falla; "
        f"antes: {antes} · después: {despues}"
    )


def prueba_rnf_09_error_el_mensaje_no_filtra_detalles_tecnicos(
    csv_tres_megas: Path, temporal_aislado: Path
) -> None:
    def fallar(espia: _Espia) -> None:
        raise OSError(5, "Input/output error en C:/temp/upload-9f2a.tmp")

    espia = _Espia(_subida(csv_tres_megas.read_bytes()), fallar)
    recepcion = _correr(recibir(espia))
    mensaje = mensajes.obtener(recepcion.codigo)

    for fragmento in ("OSError", "Input/output", "C:/temp", ".tmp", "Traceback"):
        assert fragmento not in mensaje.texto
        assert fragmento not in mensaje.accion
    assert mensaje.accion.strip()


# --------------------------------------------------------------------------- #
# RNF-09 · límite · pasa el límite y declara menos: corta sin leer el resto
# --------------------------------------------------------------------------- #


def prueba_rnf_09_limite_corta_al_pasar_el_limite_sin_leer_el_resto(
    csv_tamano_maximo: Path, csv_tres_megas: Path, temporal_aislado: Path
) -> None:
    """El archivo pesa ~8 MB y declara 1 KB: MOD-02 no le cree y corta en seco.

    Es la prueba de que el límite lo aplica MOD-02 y no la infraestructura: si
    lo cortara el servidor, este caso ni llegaría al código del equipo.
    """
    contenido = csv_tamano_maximo.read_bytes() + csv_tres_megas.read_bytes()
    maximo = _maximo()
    assert len(contenido) > maximo + 1

    espia = _Espia(
        _subida(contenido, "espectro-que-miente.csv", tamano_declarado=1024)
    )
    antes = _listado(temporal_aislado)
    recepcion = _correr(recibir(espia))
    despues = _listado(temporal_aislado)

    assert not recepcion.aceptado
    assert recepcion.codigo == mensajes.TAMANO_EXCEDIDO
    assert espia.bytes_leidos == maximo + 1, (
        "basta un byte de más para saber que pasó el límite: no hay por qué "
        f"leer más (se leyeron {espia.bytes_leidos} de {len(contenido)})"
    )
    assert espia.bytes_leidos < len(contenido)
    assert espia.cerrada
    assert despues == [], f"antes: {antes} · después: {despues}"


# --------------------------------------------------------------------------- #
# Lectura por bloques y el tamaño que declara el navegador
# --------------------------------------------------------------------------- #


def prueba_lee_por_bloques_y_no_de_un_solo_golpe(csv_tres_megas: Path) -> None:
    espia = _Espia(_subida(csv_tres_megas.read_bytes()))
    recepcion = _correr(recibir(espia))

    assert recepcion.aceptado
    assert len(espia.bloques_pedidos) > 1, "se leyó todo de un golpe"
    assert max(espia.bloques_pedidos) <= BLOQUE_BYTES
    assert -1 not in espia.bloques_pedidos, (
        "read(-1) lee el archivo completo de una vez: eso es justo lo que "
        "RNF-03 pide evitar"
    )


def prueba_no_cree_el_tamano_declarado_cuando_miente_a_lo_grande(
    csv_tamano_maximo: Path,
) -> None:
    """Declara pasarse del límite, pero cabe: se acepta por lo que pesa."""
    recepcion = _correr(
        recibir(
            _subida(
                csv_tamano_maximo.read_bytes(),
                tamano_declarado=_maximo() * 10,
            )
        )
    )

    assert recepcion.aceptado
    assert recepcion.bytes_leidos == _maximo()


def prueba_una_subida_sin_tamano_declarado_funciona_igual() -> None:
    """`UploadFile.size` puede venir en `None`: MOD-02 no lo consulta."""
    subida = UploadFile(file=SpooledTemporaryFile(), filename="espectro.csv")
    subida.file.write(b"400.0,0.5\n")
    subida.file.seek(0)

    recepcion = _correr(recibir(subida))

    assert recepcion.aceptado
    assert recepcion.bytes_leidos == 10


# --------------------------------------------------------------------------- #
# El límite se lee de UT-03
# --------------------------------------------------------------------------- #


def prueba_el_limite_sale_de_ut03_y_cambiarlo_cambia_el_comportamiento() -> None:
    """La prueba de que UT-03 sirve de verdad, aplicada a MOD-02 (T-01)."""
    contenido = b"400.0,0.5\n" * 50  # 500 bytes

    apretado = _correr(
        recibir(_subida(contenido), configuracion=_con_tamano_maximo(200))
    )
    holgado = _correr(
        recibir(_subida(contenido), configuracion=_con_tamano_maximo(5000))
    )

    assert not apretado.aceptado
    assert apretado.codigo == mensajes.TAMANO_EXCEDIDO
    assert holgado.aceptado
    assert holgado.bytes_leidos == len(contenido)


# --------------------------------------------------------------------------- #
# La frontera con MOD-03: MOD-02 no juzga el contenido
# --------------------------------------------------------------------------- #


def prueba_el_archivo_vacio_se_entrega_vacio_no_se_rechaza(
    carpeta_fixtures: Path,
) -> None:
    """CA-02.4 es de MOD-03 (T-04): para MOD-02, 0 bytes es un tamaño correcto."""
    recepcion = _correr(
        recibir(_subida((carpeta_fixtures / "archivo-vacio.csv").read_bytes()))
    )

    assert recepcion.aceptado
    assert recepcion.tamano_correcto
    assert recepcion.contenido == ""
    assert recepcion.bytes_leidos == 0


def prueba_el_formato_no_lo_decide_mod_02(carpeta_fixtures: Path) -> None:
    """CA-01.3 es de MOD-03 (T-04): un `.png` pequeño pasa el filtro de tamaño."""
    recepcion = _correr(
        recibir(_subida((carpeta_fixtures / "imagen.png").read_bytes(), "imagen.png"))
    )

    assert recepcion.aceptado, (
        "MOD-02 solo aplica el tamaño; el formato lo rechaza MOD-03 en T-04"
    )


def prueba_el_binario_llega_como_texto_para_que_mod_03_lo_rechace(
    carpeta_fixtures: Path,
) -> None:
    """CA-02.5 es de MOD-03, y necesita ver los bytes nulos en el texto."""
    recepcion = _correr(
        recibir(
            _subida(
                (carpeta_fixtures / "binario-disfrazado.csv").read_bytes(),
                "ejecutable.csv",
            )
        )
    )

    assert recepcion.aceptado
    assert recepcion.contenido is not None
    assert "\x00" in recepcion.contenido, (
        "MOD-03 reconoce el binario por sus bytes nulos: MOD-02 no debe "
        "borrarlos al decodificar"
    )


def prueba_el_bom_de_windows_no_estorba_a_mod_03() -> None:
    """Con BOM, `##TITLE=` dejaría de estar al principio de la primera línea."""
    recepcion = _correr(
        recibir(_subida("\ufeff##TITLE=PRUEBA\n##END=\n".encode("utf-8"), "e.jdx"))
    )

    assert recepcion.aceptado
    assert recepcion.contenido is not None
    assert recepcion.contenido.startswith("##TITLE=")


# --------------------------------------------------------------------------- #
# Cierre y limpieza
# --------------------------------------------------------------------------- #


def prueba_siempre_cierra_la_subida(
    csv_tamano_maximo: Path, csv_un_byte_de_mas: Path
) -> None:
    aceptada = _Espia(_subida(csv_tamano_maximo.read_bytes()))
    rechazada = _Espia(_subida(csv_un_byte_de_mas.read_bytes()))

    _correr(recibir(aceptada))
    _correr(recibir(rechazada))

    assert aceptada.cerrada, "se cerró en el camino feliz"
    assert rechazada.cerrada, "y también cuando hubo rechazo"


def prueba_no_escribe_nada_en_disco(temporal_aislado: Path) -> None:
    """Lo que cabe en memoria no toca el disco (RNF-09)."""
    recepcion = _correr(recibir(_subida(b"400.0,0.5\n500.0,0.6\n")))

    assert recepcion.aceptado
    assert _listado(temporal_aislado) == []


# --------------------------------------------------------------------------- #
# Nombre del archivo
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("declarado", "esperado"),
    [
        ("acetona.jdx", "acetona.jdx"),
        ("../../etc/passwd.csv", "passwd.csv"),
        ("..\\..\\Windows\\system32\\espectro.csv", "espectro.csv"),
        ("espectro\n##TITLE=falso.csv", "espectro_##TITLE=falso.csv"),
        ("  espectro.csv  ", "espectro.csv"),
        ("", "(sin nombre)"),
        (None, "(sin nombre)"),
    ],
)
def prueba_el_nombre_llega_limpio(declarado: str | None, esperado: str) -> None:
    """El nombre lo escribe el navegador: no se usa tal cual (RNF-03).

    Se queda solo el nombre del archivo —sin rutas— y sin saltos de línea, que
    son los que permitirían inventar una línea falsa en el registro.
    """
    assert nombre_seguro(declarado) == esperado


def prueba_el_nombre_largo_conserva_la_extension() -> None:
    """MOD-03 necesita la extensión para CA-01.3; el resto se recorta."""
    limpio = nombre_seguro("e" * 500 + ".jdx")

    assert limpio.endswith(".jdx")
    assert len(limpio) < 500


def prueba_la_recepcion_entrega_el_nombre_ya_limpio() -> None:
    recepcion = _correr(recibir(_subida(b"400.0,0.5\n", "../../espectro.csv")))

    assert recepcion.nombre == "espectro.csv"


# --------------------------------------------------------------------------- #
# Registros
# --------------------------------------------------------------------------- #


def prueba_los_registros_guardan_nombre_tamano_y_resultado_y_nada_mas(
    caplog: pytest.LogCaptureFixture,
) -> None:
    contenido = b"400.0,0.512345\n500.0,0.698765\n"

    with caplog.at_level(logging.INFO):
        recepcion = _correr(recibir(_subida(contenido, "acetona.csv")))

    registrado = "\n".join(r.getMessage() for r in caplog.records)

    assert recepcion.aceptado
    assert caplog.records, "MOD-02 debe registrar la recepción"
    assert "acetona.csv" in registrado
    assert str(len(contenido)) in registrado
    assert "0.512345" not in registrado, (
        "el contenido del espectro nunca va al registro (RNF-09)"
    )
    assert "400.0" not in registrado


def prueba_el_registro_del_rechazo_dice_el_codigo(
    csv_un_byte_de_mas: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        recepcion = _correr(
            recibir(_subida(csv_un_byte_de_mas.read_bytes(), "grande.csv"))
        )

    registrado = "\n".join(r.getMessage() for r in caplog.records)

    assert not recepcion.aceptado
    assert mensajes.TAMANO_EXCEDIDO in registrado
    assert "grande.csv" in registrado
