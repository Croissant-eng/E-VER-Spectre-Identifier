"""Lector de espectro compartido por MOD-03 y MOD-04 (decisión D-2).

Aquí vive la lectura de bajo nivel que los dos módulos necesitan, para que los
dos vean exactamente el mismo archivo. Si cada uno tuviera su propia forma de
partir un CSV o de leer las etiquetas de un JCAMP-DX, podría pasar que MOD-03
aprobara un archivo y MOD-04 lo leyera de otra manera.

Lo que hace este módulo, y nada más:

1. Reconoce la extensión del archivo.
2. En un CSV, averigua el separador, salta el encabezado si lo hay y entrega
   las filas como pares de números, junto con el texto del encabezado.
3. En un JCAMP-DX, entrega las etiquetas del encabezado como diccionario, la
   forma del bloque de datos y las líneas de ese bloque, sin descomprimirlas.

Lo que no hace: no valida contra UT-03 (eso es de MOD-03), no descomprime ni
convierte la intensidad y no normaliza (eso es de MOD-04). Tampoco conoce los
mensajes de UT-02. Cuando algo no se puede leer levanta LecturaFallida con una
frase para el equipo, y cada módulo decide qué código le corresponde.

Nació de backend/validacion/comun.py, que tenía la lectura ligera del CSV de
MOD-03. Ese archivo sigue existiendo y ahora toma de aquí su lectura.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Los dos formatos que se saben leer. UT-03 decide cuáles se admiten.
EXTENSION_JDX: str = ".jdx"
EXTENSION_CSV: str = ".csv"

#: Los dos separadores que admiten los Requerimientos en su sección 6.1. La
#: coma va primero y gana los empates.
SEPARADOR_COMA: str = ","
SEPARADOR_PUNTO_Y_COMA: str = ";"
SEPARADORES: tuple[str, ...] = (SEPARADOR_COMA, SEPARADOR_PUNTO_Y_COMA)

#: Un par es número de onda e intensidad: dos columnas, ni una más.
COLUMNAS_CSV: int = 2

#: Lo que separa un comentario del valor en un JCAMP-DX.
COMENTARIO_JDX: str = "$$"

#: Las etiquetas que abren el bloque de datos de un JCAMP-DX.
ETIQUETAS_DE_DATOS: tuple[str, ...] = ("XYDATA", "PEAKTABLE")

# En los nombres de etiqueta el estándar ignora espacios, guiones, guiones
# bajos y diagonales, y no distingue mayúsculas.
_IGNORADO_EN_ETIQUETAS = re.compile(r"[\s\-_/]")


class LecturaFallida(Exception):
    """El archivo no tiene la forma que se esperaba.

    El texto es para el equipo y para el registro. Nunca lleva valores del
    espectro y nunca se le muestra al usuario.
    """


# Extensión


def extension_de(nombre: str | None) -> str | None:
    """La extensión del nombre, en minúsculas y con punto.

    Devuelve None cuando no hay extensión que valga: sin punto, con el punto al
    final o cuando el punto abre el nombre, como en un archivo oculto.
    """
    if not nombre:
        return None
    punto = nombre.rfind(".")
    if punto <= 0 or punto == len(nombre) - 1:
        return None
    return nombre[punto:].lower()


# CSV


@dataclass(frozen=True)
class TablaCsv:
    """Lo que sale de leer un CSV.

    pares trae número de onda e intensidad en el orden del archivo. encabezado
    es el texto de la fila de encabezado, o una cadena vacía si no la tenía.
    """

    pares: tuple[tuple[float, float], ...]
    separador: str
    encabezado: str


def separador_de(contenido: str) -> str:
    """Adivina con qué separador está escrito el CSV.

    Gana el separador que parta la primera fila con contenido en exactamente
    dos columnas. Si ninguno lo logra se devuelve la coma y la lectura falla con
    un motivo claro; si lo logran los dos, gana la coma. La primera fila sirve
    aunque sea el encabezado, porque usa el mismo separador que los datos.
    """
    primera = next((linea for linea in contenido.splitlines() if linea.strip()), "")
    for separador in SEPARADORES:
        if len(primera.split(separador)) == COLUMNAS_CSV:
            return separador
    return SEPARADOR_COMA


def par_de(campos: list[str], separador: str) -> tuple[float, float] | None:
    """El par de una fila, o None si la fila no es un par de números.

    Con punto y coma los campos pueden traer el decimal con coma, como exporta
    Excel en español, y se cambia por punto antes de leerlos.
    """
    if len(campos) != COLUMNAS_CSV:
        return None

    valores: list[float] = []
    for campo in campos:
        texto = campo.strip()
        if separador == SEPARADOR_PUNTO_Y_COMA:
            texto = texto.replace(SEPARADOR_COMA, ".")
        try:
            valores.append(float(texto))
        except ValueError:
            return None

    return valores[0], valores[1]


def leer_tabla_csv(contenido: str, *, maximo_filas: int | None = None) -> TablaCsv:
    """Lee las filas de un CSV de dos columnas.

    Se admite una fila de encabezado al principio, siempre que tenga dos
    columnas. Una segunda fila que no sea de números ya es un archivo que no
    tiene esta forma.

    Args:
        contenido: el archivo como texto.
        maximo_filas: cuántos pares leer como máximo. None los lee todos.

    Raises:
        LecturaFallida: si una fila no encaja o si no hay datos.
    """
    separador = separador_de(contenido)
    pares: list[tuple[float, float]] = []
    encabezado = ""
    hubo_encabezado = False

    for linea in contenido.splitlines():
        if not linea.strip():
            continue

        campos = linea.split(separador)
        par = par_de(campos, separador)

        if par is None:
            if not pares and not hubo_encabezado and len(campos) == COLUMNAS_CSV:
                hubo_encabezado = True
                encabezado = linea.strip()
                continue
            if len(campos) != COLUMNAS_CSV:
                raise LecturaFallida(
                    f"una fila no trae dos columnas separadas por «{separador}»"
                )
            raise LecturaFallida("una fila no trae un par de números")

        pares.append(par)
        if maximo_filas is not None and len(pares) >= maximo_filas:
            break

    if not pares:
        raise LecturaFallida("el archivo no trae ni una fila de datos")

    return TablaCsv(tuple(pares), separador, encabezado)


# JCAMP-DX


@dataclass(frozen=True)
class CabeceraJdx:
    """Las partes de un JCAMP-DX, sin interpretar los datos.

    etiquetas tiene los nombres sin espacios ni guiones y en mayúsculas, por
    ejemplo NPOINTS o XFACTOR. forma es lo que sigue a la etiqueta de datos,
    por ejemplo (X++(Y..Y)). lineas_de_datos son las líneas del bloque, sin
    comentarios.
    """

    etiquetas: dict[str, str]
    forma: str
    lineas_de_datos: tuple[str, ...]


def nombre_de_etiqueta(texto: str) -> str:
    """El nombre de una etiqueta en su forma comparable: NPOINTS, XFACTOR."""
    return _IGNORADO_EN_ETIQUETAS.sub("", texto.strip().lstrip("#").rstrip("=")).upper()


def leer_cabecera_jdx(contenido: str) -> CabeceraJdx:
    """Separa las etiquetas, la forma del bloque de datos y sus líneas.

    Si una etiqueta aparece dos veces se queda la primera.

    Raises:
        LecturaFallida: si no hay bloque de datos o si está vacío.
    """
    etiquetas: dict[str, str] = {}
    forma = ""
    lineas: list[str] = []
    dentro_de_datos = False

    for linea in contenido.splitlines():
        sin_comentario = linea.split(COMENTARIO_JDX, 1)[0].strip()
        if not sin_comentario:
            continue
        if sin_comentario.startswith("##"):
            if dentro_de_datos:
                break
            nombre, _, valor = sin_comentario[2:].partition("=")
            nombre = nombre_de_etiqueta(nombre)
            if nombre in ETIQUETAS_DE_DATOS:
                forma = valor.strip()
                dentro_de_datos = True
                continue
            etiquetas.setdefault(nombre, valor.strip())
            continue
        if dentro_de_datos:
            lineas.append(sin_comentario)

    if not dentro_de_datos or not lineas:
        raise LecturaFallida("no se encontró el bloque de datos")
    return CabeceraJdx(etiquetas, forma, tuple(lineas))


def valor_de_etiqueta(contenido: str, etiqueta: str) -> str | None:
    """El valor de una sola etiqueta del encabezado, sin su comentario.

    Es la lectura ligera que usa MOD-03: no necesita que exista el bloque de
    datos y se detiene en la primera coincidencia. La etiqueta puede venir
    como ##NPOINTS= o como NPOINTS.
    """
    buscada = nombre_de_etiqueta(etiqueta)
    for linea in contenido.splitlines():
        desnuda = linea.strip()
        if not desnuda.startswith("##"):
            continue
        nombre, igual, valor = desnuda[2:].partition("=")
        if igual and nombre_de_etiqueta(nombre) == buscada:
            return valor.split(COMENTARIO_JDX)[0].strip()
    return None
