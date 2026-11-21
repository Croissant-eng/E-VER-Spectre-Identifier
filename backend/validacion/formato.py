"""MOD-03 · T-04 · ¿es de verdad este formato?

Las **cuatro capas** de T-04, en orden, cada una con su rechazo:

0. **Extensión** — tiene que estar en la lista de UT-03. Va primero a propósito:
   así un `.png` recibe el mensaje de formato (CA-01.3) y no el de «no es
   texto», que sería verdad pero no es lo que el usuario necesita oír.
1. **¿Es texto?** — bytes nulos, caracteres de control o marcas de reemplazo →
   rechazo inmediato. Es la defensa de RNF-03: nunca se interpreta binario.
2. **¿La estructura es la del formato declarado?** — `.jdx`: las etiquetas
   obligatorias de UT-03, con `##TITLE=` en la primera línea y `##END=` en la
   última, más una de las etiquetas de datos. `.csv`: las primeras filas
   parsean como pares numéricos, con separador coma o punto y coma y una fila
   de encabezado opcional, que es lo que admite Requerimientos §6.1.
3. **Coherencia mínima** — que haya datos y que los números de onda sean
   positivos y utilizables.

**Lo que no hace:** contar puntos ni mirar el rango (es T-05, `requisitos.py`),
normalizar o convertir (es MOD-04, incremento 2) y armar mensajes (es UT-02).
En particular **no se descifran las formas comprimidas de JCAMP-DX** (DIF,
SQZ): interpretarlas es trabajo de MOD-04 y aquí solo se mira si hay datos y si
el primer número de onda es plausible.

Ninguna entrada hace que este módulo levante una excepción (CA-02.4).
"""

from __future__ import annotations

import math
import re

from backend.utilerias.configuracion import Configuracion
from backend.validacion.comun import (
    CAPA_COHERENCIA,
    CAPA_ESTRUCTURA,
    CAPA_EXTENSION,
    CAPA_TAMANO,
    CAPA_TEXTO,
    EXTENSION_CSV,
    EXTENSION_JDX,
    SEPARADORES,
    Fallo,
    FilasCsv,
    coherencia,
    leer_csv,
)

#: Cuántas filas del `.csv` se revisan. La pregunta de T-04 es «¿tiene forma de
#: este formato?», y eso se contesta con las primeras filas; recorrer el archivo
#: completo es trabajo de T-05, que además tiene que contar.
FILAS_A_REVISAR: int = 10

#: Caracteres que no pueden aparecer en un archivo de texto: controles de C0 y
#: C1 (menos tabulador, salto de línea y retorno de carro), el de borrado y el
#: carácter de reemplazo con el que MOD-02 marcó los bytes inválidos.
_NO_ES_TEXTO = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�]")

#: Las dos etiquetas de JCAMP-DX cuya **posición** importa. La regla no se puede
#: escribir en el JSON de UT-03 (sección 3 del plan), así que vive aquí; los
#: textos siguen saliendo de la configuración.
_ETIQUETA_TITULO: str = "##TITLE="
_ETIQUETA_FIN: str = "##END="

#: Cómo empiezan las líneas que **no** son datos en un `.jdx`.
_PREFIJO_ETIQUETA: str = "##"
_PREFIJO_COMENTARIO: str = "$$"


def revisar(
    contenido: str,
    extension: str | None,
    parametros: Configuracion,
    *,
    tamano_correcto: bool = True,
) -> Fallo | None:
    """Corre las cuatro capas en orden y devuelve la primera que falle."""
    if not tamano_correcto:
        return Fallo(
            CAPA_TAMANO,
            "MOD-02 no confirmó el tamaño: no se revisa el contenido",
        )

    # --- Capa 0 · extensión ------------------------------------------------ #
    permitidos = parametros.archivo.formatos_permitidos
    if extension is None or extension not in permitidos:
        return Fallo(
            CAPA_EXTENSION,
            f"la extensión no está en la lista de UT-03 ({', '.join(permitidos)})",
        )

    # --- Capa 1 · ¿es texto? ----------------------------------------------- #
    if _NO_ES_TEXTO.search(contenido) is not None:
        return Fallo(CAPA_TEXTO, "el contenido trae bytes que no son texto imprimible")

    # --- Capas 2 y 3 · estructura y coherencia del formato declarado ------- #
    if extension == EXTENSION_JDX:
        return _revisar_jdx(contenido, parametros)
    if extension == EXTENSION_CSV:
        return _revisar_csv(contenido)

    return Fallo(
        CAPA_ESTRUCTURA,
        f"UT-03 admite «{extension}», pero MOD-03 todavía no sabe qué "
        "estructura esperar de ese formato",
    )


# --------------------------------------------------------------------------- #
# Capas 2 y 3 · CSV
# --------------------------------------------------------------------------- #


def _revisar_csv(contenido: str) -> Fallo | None:
    """Las primeras filas tienen que ser pares «número de onda, intensidad»."""
    leido = leer_csv(contenido, maximo_filas=FILAS_A_REVISAR)
    if isinstance(leido, Fallo):
        return leido
    assert isinstance(leido, FilasCsv)  # para quien lea el tipo
    return coherencia(leido.pares)


# --------------------------------------------------------------------------- #
# Capas 2 y 3 · JCAMP-DX (.jdx)
# --------------------------------------------------------------------------- #


def _revisar_jdx(contenido: str, parametros: Configuracion) -> Fallo | None:
    """Las etiquetas obligatorias de UT-03, sus posiciones y una de datos.

    Las líneas en blanco del final se ignoran: un editor de texto las agrega al
    guardar y eso no convierte el archivo en uno truncado.
    """
    lineas = [linea.strip() for linea in contenido.splitlines() if linea.strip()]
    if not lineas:
        return Fallo(CAPA_ESTRUCTURA, "el archivo no trae ni una línea")

    obligatorias = parametros.validacion.jcamp_etiquetas_obligatorias
    en_mayusculas = contenido.upper()
    faltantes = [
        etiqueta for etiqueta in obligatorias if etiqueta.upper() not in en_mayusculas
    ]
    if faltantes:
        return Fallo(
            CAPA_ESTRUCTURA,
            f"faltan etiquetas obligatorias de UT-03: {', '.join(faltantes)}",
        )

    # Las dos reglas de posición que el JSON no puede expresar. Solo se exigen
    # si UT-03 pide esas etiquetas: la configuración sigue mandando.
    if _enlistada(_ETIQUETA_TITULO, obligatorias) and not lineas[0].upper().startswith(
        _ETIQUETA_TITULO
    ):
        return Fallo(
            CAPA_ESTRUCTURA,
            f"{_ETIQUETA_TITULO} no abre el archivo, y tiene que ir en la "
            "primera línea",
        )

    if _enlistada(_ETIQUETA_FIN, obligatorias) and not lineas[-1].upper().startswith(
        _ETIQUETA_FIN
    ):
        return Fallo(
            CAPA_ESTRUCTURA, f"{_ETIQUETA_FIN} no cierra el archivo: parece cortado"
        )

    etiquetas_de_datos = parametros.validacion.jcamp_etiquetas_datos_una_de
    donde = _indice_de_datos(lineas, etiquetas_de_datos)
    if donde is None:
        return Fallo(
            CAPA_ESTRUCTURA,
            "falta la etiqueta de datos; UT-03 admite: "
            f"{', '.join(etiquetas_de_datos)}",
        )

    datos = [
        linea
        for linea in lineas[donde + 1 :]
        if not linea.startswith(_PREFIJO_ETIQUETA)
        and not linea.startswith(_PREFIJO_COMENTARIO)
    ]
    if not datos:
        return Fallo(
            CAPA_COHERENCIA,
            "no hay ni una línea de datos después de la etiqueta de datos",
        )

    return _primer_numero_de_onda_plausible(datos[0])


def _enlistada(etiqueta: str, etiquetas: tuple[str, ...]) -> bool:
    return any(etiqueta.upper() == otra.upper() for otra in etiquetas)


def _indice_de_datos(
    lineas: list[str], etiquetas_de_datos: tuple[str, ...]
) -> int | None:
    """En qué línea está la etiqueta que abre los datos (`##XYDATA=`, …)."""
    for indice, linea in enumerate(lineas):
        arriba = linea.upper()
        if any(arriba.startswith(etiqueta.upper()) for etiqueta in etiquetas_de_datos):
            return indice
    return None


def _primer_numero_de_onda_plausible(linea: str) -> Fallo | None:
    """Capa 3 del `.jdx` · el primer número de onda, si se puede leer.

    A propósito es poco: JCAMP-DX permite guardar los datos comprimidos (DIF,
    SQZ), y descifrar eso es trabajo de MOD-04 en el incremento 2. Si el primer
    campo no se lee como número, se deja pasar en vez de rechazar un archivo
    por no entenderlo; si sí se lee, tiene que ser un número de onda posible.
    """
    sin_separadores = linea
    for separador in SEPARADORES:
        sin_separadores = sin_separadores.replace(separador, " ")
    campos = sin_separadores.split()
    if not campos:  # pragma: no cover - las líneas vacías ya se filtraron
        return None

    try:
        onda = float(campos[0])
    except ValueError:
        return None

    if not math.isfinite(onda) or onda <= 0:
        return Fallo(
            CAPA_COHERENCIA,
            "el primer número de onda de los datos no es un valor posible",
        )
    return None
