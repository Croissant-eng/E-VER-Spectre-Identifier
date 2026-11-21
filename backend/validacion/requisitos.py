"""MOD-03 · T-05 · ¿cumple los requisitos de puntos y rango?

**Lectura ligera:** contar los puntos y mirar el mínimo y el máximo del número
de onda, y compararlos con UT-03 (`validacion.puntos_minimos` y
`validacion.rango_requerido_cm1`). **No normaliza, no ordena y no convierte**:
eso es MOD-04, en el incremento 2.

Corre **después** de T-04 (`formato.py`): aquí se da por hecho que el archivo
ya es de verdad del formato que declara.

Cómo se obtienen los dos números en cada formato:

- **`.csv`** — se recorren **todas** las filas de datos, saltando el encabezado
  si lo hay. T-04 solo miraba las primeras, por eso un archivo con basura al
  final pasaba T-04: aquí se cae, porque ya no queda fila sin leer.
- **`.jdx`** — se leen `##NPOINTS=` (los puntos) y `##FIRSTX=` / `##LASTX=` (los
  extremos) del **encabezado**, que es texto ASCII. **El bloque de datos no se
  descomprime**: las formas DIF y SQZ de JCAMP-DX son trabajo de MOD-04
  (T-08/T-09). Si falta alguna de esas tres etiquetas, el archivo se **rechaza**
  —falla cerrado, igual que en T-04— en vez de adivinar.

Por eso **T-05 no necesita D-2**: nunca interpreta los datos, solo lee
etiquetas. D-2 («lector de espectro» compartido con MOD-04) sigue siendo
decisión del incremento 2, antes de T-08.

Dos cosas que este módulo **no** verifica, a propósito:

- Que `##NPOINTS=` diga la verdad. Comprobarlo exige descomprimir los datos, y
  eso es MOD-04. Si un archivo miente, lo descubre el incremento 2.
- Que el eje vaya de menor a mayor. El rango se saca del mínimo y el máximo de
  `##FIRSTX=` y `##LASTX=`, así que un eje descendente —que es lo normal en los
  archivos de NIST— se mide igual de bien. (Es también la razón por la que no se
  mira `##DELTAX=`: en un archivo real traía el signo equivocado.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.utilerias.configuracion import Configuracion
from backend.validacion.comun import (
    CAPA_ESTRUCTURA,
    CAPA_PUNTOS,
    CAPA_RANGO,
    EXTENSION_CSV,
    EXTENSION_JDX,
    Fallo,
    FilasCsv,
    coherencia,
    leer_csv,
)

#: Las tres etiquetas del encabezado de JCAMP-DX que dicen cuántos puntos hay y
#: qué tramo cubren. No son parámetros de negocio —no se eligen, las define el
#: formato— así que viven aquí y no en UT-03, igual que `##TITLE=` y `##END=`.
ETIQUETA_PUNTOS: str = "##NPOINTS="
ETIQUETA_PRIMERA_X: str = "##FIRSTX="
ETIQUETA_ULTIMA_X: str = "##LASTX="

#: Lo que separa un comentario del valor, dentro de una línea de etiqueta.
_COMENTARIO: str = "$$"


@dataclass(frozen=True)
class Medida:
    """Lo que hace falta para contestar las dos preguntas de T-05.

    Attributes:
        puntos: cuántos pares trae el espectro.
        onda_minima: el número de onda más bajo que cubre.
        onda_maxima: el más alto.
    """

    puntos: int
    onda_minima: float
    onda_maxima: float


def revisar(
    contenido: str, extension: str | None, parametros: Configuracion
) -> Fallo | None:
    """Mide el espectro y lo compara con los requisitos de UT-03."""
    if extension == EXTENSION_CSV:
        medido = _medir_csv(contenido)
    elif extension == EXTENSION_JDX:
        medido = _medir_jdx(contenido)
    else:
        return Fallo(
            CAPA_ESTRUCTURA,
            f"UT-03 admite «{extension}», pero MOD-03 todavía no sabe contar "
            "sus puntos ni medir su rango",
        )

    if isinstance(medido, Fallo):
        return medido
    return _comparar(medido, parametros)


# --------------------------------------------------------------------------- #
# Comparación con UT-03
# --------------------------------------------------------------------------- #


def _comparar(medida: Medida, parametros: Configuracion) -> Fallo | None:
    """Los puntos primero y el rango después, cada uno con su mensaje.

    El orden importa solo para un archivo que falle las dos cosas: se le dice
    lo de los puntos, que es lo más básico.
    """
    minimos = parametros.validacion.puntos_minimos
    if medida.puntos < minimos:
        return Fallo(
            CAPA_PUNTOS,
            f"el espectro trae {medida.puntos} puntos y UT-03 pide al menos "
            f"{minimos}",
        )

    requerido_minimo, requerido_maximo = parametros.validacion.rango_requerido_cm1
    if medida.onda_minima > requerido_minimo or medida.onda_maxima < requerido_maximo:
        return Fallo(
            CAPA_RANGO,
            f"el espectro cubre de {medida.onda_minima:g} a "
            f"{medida.onda_maxima:g} cm-1 y UT-03 pide cubrir de "
            f"{requerido_minimo:g} a {requerido_maximo:g}",
        )

    return None


# --------------------------------------------------------------------------- #
# CSV · se recorren todas las filas
# --------------------------------------------------------------------------- #


def _medir_csv(contenido: str) -> Medida | Fallo:
    """Cuenta los pares y toma el mínimo y el máximo de la primera columna."""
    leido = leer_csv(contenido)  # sin tope: todas las filas
    if isinstance(leido, Fallo):
        return leido
    assert isinstance(leido, FilasCsv)  # para quien lea el tipo

    # La coherencia de T-04 se aplica aquí a **todas** las filas, no solo a las
    # primeras: no es una regla nueva, es la misma sobre lo que ya está leído.
    # Sin esto, un número de onda negativo escondido al final torcería el
    # mínimo y el rango se mediría mal.
    fallo = coherencia(leido.pares)
    if fallo is not None:
        return fallo

    ondas = [onda for onda, _ in leido.pares]
    return Medida(len(leido.pares), min(ondas), max(ondas))


# --------------------------------------------------------------------------- #
# JCAMP-DX · se leen tres etiquetas del encabezado
# --------------------------------------------------------------------------- #


def _medir_jdx(contenido: str) -> Medida | Fallo:
    """Lee `##NPOINTS=`, `##FIRSTX=` y `##LASTX=`, sin tocar el bloque de datos."""
    crudos = {
        etiqueta: _valor_de_etiqueta(contenido, etiqueta)
        for etiqueta in (ETIQUETA_PUNTOS, ETIQUETA_PRIMERA_X, ETIQUETA_ULTIMA_X)
    }
    faltantes = [etiqueta for etiqueta, valor in crudos.items() if valor is None]
    if faltantes:
        return Fallo(
            CAPA_ESTRUCTURA,
            f"faltan etiquetas del encabezado: {', '.join(faltantes)}; sin "
            "ellas no se puede saber cuántos puntos trae ni qué rango cubre "
            "sin descomprimir los datos, y eso es trabajo de MOD-04",
        )

    puntos = _entero(crudos[ETIQUETA_PUNTOS], ETIQUETA_PUNTOS)
    if isinstance(puntos, Fallo):
        return puntos

    primera = _numero(crudos[ETIQUETA_PRIMERA_X], ETIQUETA_PRIMERA_X)
    if isinstance(primera, Fallo):
        return primera

    ultima = _numero(crudos[ETIQUETA_ULTIMA_X], ETIQUETA_ULTIMA_X)
    if isinstance(ultima, Fallo):
        return ultima

    if primera <= 0 or ultima <= 0:
        return Fallo(
            CAPA_ESTRUCTURA,
            f"{ETIQUETA_PRIMERA_X} y {ETIQUETA_ULTIMA_X} tienen que ser números "
            "de onda positivos",
        )

    # El eje puede ir de mayor a menor —así vienen los archivos de NIST— así que
    # el rango se saca del mínimo y el máximo, no del orden en que aparecen.
    return Medida(puntos, min(primera, ultima), max(primera, ultima))


def _valor_de_etiqueta(contenido: str, etiqueta: str) -> str | None:
    """El valor de una etiqueta del encabezado, sin su comentario.

    No distingue mayúsculas y tolera espacios y un comentario `$$` al final,
    que es como aparecen en los archivos reales.
    """
    for linea in contenido.splitlines():
        desnuda = linea.strip()
        if desnuda.upper().startswith(etiqueta):
            valor = desnuda[len(etiqueta) :]
            return valor.split(_COMENTARIO)[0].strip()
    return None


def _entero(crudo: str | None, etiqueta: str) -> int | Fallo:
    try:
        valor = int((crudo or "").strip())
    except ValueError:
        return Fallo(
            CAPA_ESTRUCTURA, f"{etiqueta} no trae un número entero de puntos"
        )
    if valor <= 0:
        return Fallo(CAPA_ESTRUCTURA, f"{etiqueta} tiene que ser mayor que cero")
    return valor


def _numero(crudo: str | None, etiqueta: str) -> float | Fallo:
    try:
        valor = float((crudo or "").strip())
    except ValueError:
        return Fallo(CAPA_ESTRUCTURA, f"{etiqueta} no trae un número")
    if not math.isfinite(valor):
        return Fallo(CAPA_ESTRUCTURA, f"{etiqueta} no trae un número utilizable")
    return valor
