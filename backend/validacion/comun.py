"""MOD-03 · piezas que comparten T-04 (formato) y T-05 (puntos y rango).

Aquí viven el **veredicto**, los nombres de las capas, la extensión y la
**lectura ligera de filas de un `.csv`**: separador, encabezado y pares de
números. Las dos tareas la necesitan —T-04 mira las primeras filas para saber
si el archivo tiene esta forma, T-05 las recorre todas para contar y medir— y
tenerla dos veces sería tener dos reglas que se separan con el tiempo.

Desde el incremento 2 la lectura de bajo nivel (extensión, separador,
encabezado y pares del CSV) vive en `backend/nucleo/lector_espectro.py`, que es
el lector compartido de D-2: así MOD-03 y MOD-04 leen el archivo de la misma
manera. Aquí se queda lo que es solo de MOD-03: las capas, el veredicto y la
forma en que una lectura fallida se vuelve un rechazo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.nucleo import lector_espectro
from backend.nucleo.lector_espectro import (
    COLUMNAS_CSV,
    EXTENSION_CSV,
    EXTENSION_JDX,
    SEPARADOR_COMA,
    SEPARADOR_PUNTO_Y_COMA,
    SEPARADORES,
    extension_de,
    par_de,
    separador_de,
)
from backend.utilerias import mensajes

# --------------------------------------------------------------------------- #
# Nombres de las capas · sirven para el registro y para las pruebas
# --------------------------------------------------------------------------- #

#: Freno de seguridad: MOD-02 no confirmó el tamaño (no debería ocurrir).
CAPA_TAMANO: str = "tamano"

#: T-04 · capa 0 · la extensión no está en la lista de UT-03.
CAPA_EXTENSION: str = "extension"

#: T-04 · capa 1 · el contenido no es texto.
CAPA_TEXTO: str = "texto"

#: T-04 · capa 2 · la estructura no es la del formato declarado.
CAPA_ESTRUCTURA: str = "estructura"

#: T-04 · capa 3 · la estructura está, pero los datos no son coherentes.
CAPA_COHERENCIA: str = "coherencia"

#: T-05 · el espectro trae menos puntos que el mínimo de UT-03 (CA-02.6).
CAPA_PUNTOS: str = "puntos"

#: T-05 · el espectro no cubre el rango requerido por UT-03 (CA-02.3).
CAPA_RANGO: str = "rango"

#: Qué código de UT-02 le corresponde a cada capa. Las capas 2 y 3 de T-04
#: comparten código: para el usuario, «la estructura no es la que el formato
#: necesita» cubre las dos, y el catálogo no se amplía sin que haga falta.
CODIGO_POR_CAPA: dict[str, str] = {
    CAPA_TAMANO: mensajes.TAMANO_EXCEDIDO,
    CAPA_EXTENSION: mensajes.FORMATO_NO_SOPORTADO,
    CAPA_TEXTO: mensajes.ARCHIVO_NO_ES_TEXTO,
    CAPA_ESTRUCTURA: mensajes.ESTRUCTURA_INVALIDA,
    CAPA_COHERENCIA: mensajes.ESTRUCTURA_INVALIDA,
    CAPA_PUNTOS: mensajes.PUNTOS_INSUFICIENTES,
    CAPA_RANGO: mensajes.RANGO_INSUFICIENTE,
}

# --------------------------------------------------------------------------- #
# Parámetros de implementación
#
# Ninguno es valor de negocio: los de UT-03 (tamaño, formatos, puntos mínimos,
# rango, etiquetas) se leen de la configuración. Estos solo dicen «cómo está
# escrito un archivo de dos columnas».
# --------------------------------------------------------------------------- #

#: Nombre anterior del separador, cuando solo se admitía la coma.
SEPARADOR_CSV: str = SEPARADOR_COMA

#: El piso de lo que puede llamarse espectro: con un solo punto no hay curva.
#: **No es el mínimo de UT-03** (eso lo aplica T-05, con su propio mensaje).
FILAS_MINIMAS: int = 2


# --------------------------------------------------------------------------- #
# Veredicto
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Veredicto:
    """Lo que MOD-03 entrega a la interfaz (contrato de la sección 5).

    Attributes:
        valido: ``True`` si el archivo pasó las revisiones que se pidieron.
        nombre: el nombre que entregó MOD-02, ya limpio.
        extension: la extensión reconocida (``".csv"``), o ``None`` si el nombre
            no traía ninguna.
        codigo: el código de UT-02 que explica el rechazo, o ``None``.
        capa: qué capa rechazó el archivo, para el registro y las pruebas.
        detalle: una línea para el equipo sobre qué falló. **No se le muestra
            al usuario** —él ve el mensaje de UT-02— y nunca incluye contenido
            del espectro, porque va al registro (RNF-09).
    """

    valido: bool
    nombre: str
    extension: str | None
    codigo: str | None = None
    capa: str | None = None
    detalle: str = ""

    def __post_init__(self) -> None:
        # Red de seguridad contra un error de programación.
        if self.valido and (self.codigo is not None or self.capa is not None):
            raise ValueError("un veredicto válido no trae código ni capa")
        if not self.valido and (self.codigo is None or self.capa is None):
            raise ValueError("un rechazo tiene que decir su código y su capa")


@dataclass(frozen=True)
class Fallo:
    """Resultado interno de una capa: qué falló y cómo contarlo al equipo."""

    capa: str
    detalle: str


# --------------------------------------------------------------------------- #
# Extensión
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Lectura ligera de un `.csv`
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FilasCsv:
    """Lo que salió de leer un `.csv`.

    Attributes:
        pares: los pares «número de onda, intensidad» leídos.
        separador: con qué separador se leyó.
        encabezado: si se saltó una fila de encabezado.
    """

    pares: tuple[tuple[float, float], ...]
    separador: str
    encabezado: bool


def leer_csv(contenido: str, *, maximo_filas: int | None = None) -> FilasCsv | Fallo:
    """Lee las filas de un `.csv` de dos columnas con el lector compartido (D-2).

    Se admite **una fila de encabezado** al principio, como permite
    Requerimientos §6.1. Si la lectura falla, el motivo queda como `Fallo` de
    la capa de estructura.

    Args:
        contenido: el archivo como texto.
        maximo_filas: cuántos pares leer como máximo. ``None`` lee todos, que es
            lo que necesita T-05 para contar; T-04 pasa un tope, porque para
            reconocer la forma del archivo alcanza con las primeras filas.

    Returns:
        Las `FilasCsv`, o el `Fallo` de la primera fila que no encaja.
    """
    try:
        tabla = lector_espectro.leer_tabla_csv(contenido, maximo_filas=maximo_filas)
    except lector_espectro.LecturaFallida as error:
        return Fallo(CAPA_ESTRUCTURA, str(error))
    return FilasCsv(tabla.pares, tabla.separador, bool(tabla.encabezado))


def coherencia(pares: tuple[tuple[float, float], ...]) -> Fallo | None:
    """Capa 3 · que haya datos suficientes y que los números sean utilizables.

    La usan las dos tareas con el mismo criterio: T-04 sobre las primeras filas
    y T-05 sobre todas, que para entonces ya están leídas. No es una regla
    nueva, es la misma aplicada a lo que cada tarea tiene en la mano.
    """
    if len(pares) < FILAS_MINIMAS:
        return Fallo(CAPA_COHERENCIA, "con una sola fila no hay espectro que revisar")

    for onda, intensidad in pares:
        if not math.isfinite(onda) or not math.isfinite(intensidad):
            return Fallo(
                CAPA_COHERENCIA,
                "alguno de los valores no es un número utilizable",
            )
        if onda <= 0:
            return Fallo(
                CAPA_COHERENCIA,
                "alguno de los números de onda no es positivo",
            )
    return None
