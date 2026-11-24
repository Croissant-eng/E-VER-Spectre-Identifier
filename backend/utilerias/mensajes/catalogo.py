"""UT-02 · Errores y mensajes · catálogo de códigos.

Traduce un **código** a un mensaje con **motivo y acción** (RNF-01). El usuario
nunca ve detalles técnicos: ni rutas, ni nombres de módulos, ni excepciones.

Los cuatro primeros códigos llevan el texto que los criterios de aceptación
verifican **de forma literal** (sección 4 del plan del incremento 1). Esos
textos nombran valores —el tamaño máximo, el rango requerido, los puntos
mínimos— que **no se escriben aquí**: se piden a UT-03 al armar el mensaje. Así
el texto cumple la letra del criterio y, si mañana el archivo de parámetros
sube el tamaño máximo, el mensaje lo dice sin tocar una línea de código.

Los otros cuatro códigos cubren las situaciones que sí necesitan *algún*
mensaje, aunque su redacción sea libre: archivo que no es texto, estructura
inválida, configuración incompleta al arrancar y lectura interrumpida. El
noveno, `FALLO_INTERNO`, es el **mensaje genérico** que la sección 5 deja
pendiente para el 500 del endpoint (T-07).

El catálogo se completa conforme aparezcan más situaciones; hoy no se inventan
códigos que ninguna tarea del incremento 1 use todavía.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion

# --------------------------------------------------------------------------- #
# Códigos
# --------------------------------------------------------------------------- #

#: La extensión del archivo no está en la lista de UT-03 (CA-01.3).
FORMATO_NO_SOPORTADO = "FORMATO_NO_SOPORTADO"

#: El archivo pasa del tamaño máximo de UT-03 (CA-02.2).
TAMANO_EXCEDIDO = "TAMANO_EXCEDIDO"

#: El espectro no cubre el rango requerido por UT-03 (CA-02.3).
RANGO_INSUFICIENTE = "RANGO_INSUFICIENTE"

#: El espectro trae menos puntos que el mínimo de UT-03 (CA-02.6).
PUNTOS_INSUFICIENTES = "PUNTOS_INSUFICIENTES"

#: El contenido no es texto: bytes nulos o no imprimibles (CA-02.5, RNF-03).
ARCHIVO_NO_ES_TEXTO = "ARCHIVO_NO_ES_TEXTO"

#: El contenido es texto, pero no tiene la estructura del formato (CA-02.4).
ESTRUCTURA_INVALIDA = "ESTRUCTURA_INVALIDA"

#: Falta una llave obligatoria de UT-03 y el servicio no puede operar.
CONFIGURACION_INCOMPLETA = "CONFIGURACION_INCOMPLETA"

#: La lectura del archivo se interrumpió antes de terminar (pruebas RNF-09).
LECTURA_INTERRUMPIDA = "LECTURA_INTERRUMPIDA"

#: Algo falló por dentro y no se pudo emitir veredicto. Es el **mensaje
#: genérico** que la sección 5 del plan deja pendiente para el 500 de
#: `POST /api/validar` (T-07): dice qué pasó y qué hacer, y nunca por qué, que
#: es justo lo que no debe salir del servidor.
FALLO_INTERNO = "FALLO_INTERNO"

#: El archivo pasó la validación, pero sus datos no se pudieron leer con
#: seguridad en MOD-04: compresión que no se reconoce, unidades que no son las
#: de un espectro infrarrojo o un número de puntos que no cuadra (T-08).
DATOS_ILEGIBLES = "DATOS_ILEGIBLES"

#: La intensidad del espectro es constante, una línea plana, y no hay nada que
#: analizar (T-11, CA-03.3).
SIN_SENAL = "SIN_SENAL"

#: La intensidad viene en una unidad que no es transmitancia ni absorbancia,
#: por ejemplo reflectancia (D-10).
UNIDAD_NO_SOPORTADA = "UNIDAD_NO_SOPORTADA"

#: Un CSV sin encabezado con todos sus valores entre 0 y 1: puede ser
#: transmitancia en fracción o absorbancia, y adivinar mal invierte el
#: espectro, así que se pide nombrar la unidad (D-11).
UNIDAD_SIN_DECLARAR = "UNIDAD_SIN_DECLARAR"

#: Incremento 3. Lo que llegó a POST /api/analizar no tiene la forma del
#: espectro procesado: otra longitud, otro eje o valores fuera de 0 a 1. Se
#: rechaza antes de llegar al motor (D-17).
ESPECTRO_INVALIDO = "ESPECTRO_INVALIDO"

#: Incremento 3. El motor falló por dentro al analizar (CA-05.4). El texto es
#: el que pide el criterio, palabra por palabra.
ANALISIS_FALLIDO = "ANALISIS_FALLIDO"

#: Incremento 3. Ningún grupo alcanzó el umbral (CA-08). No es un error: viaja
#: dentro del resultado del análisis como aviso, nunca como rechazo.
SIN_DETECCIONES = "SIN_DETECCIONES"


class CodigoDesconocido(Exception):
    """Se pidió un código que no está en el catálogo.

    Es un error del programa, no del usuario: significa que algún módulo inventó
    un código en vez de agregarlo aquí.
    """


@dataclass(frozen=True)
class Mensaje:
    """Lo que la interfaz necesita para explicar un rechazo."""

    codigo: str
    titulo: str
    texto: str
    accion: str


# --------------------------------------------------------------------------- #
# Piezas que se leen de UT-03
# --------------------------------------------------------------------------- #

_BYTES_POR_MEGABYTE = 1024 * 1024

#: Guion largo y «centímetros a la menos uno», tal como los escribe el plan.
def _porcentaje_del_umbral(configuracion: Configuracion) -> int:
    """El umbral de UT-03 en porcentaje entero, para nombrarlo en el aviso."""
    motor = configuracion.motor
    if motor is None:
        raise ValueError("UT-03 no trae el bloque motor con el umbral")
    return round(motor.umbral_confianza * 100)


_GUION = "–"
_CM_MENOS_UNO = "cm⁻¹"


def _formatos(configuracion: Configuracion) -> str:
    return ", ".join(configuracion.archivo.formatos_permitidos)


def _tamano_maximo(configuracion: Configuracion) -> str:
    megabytes = configuracion.archivo.tamano_maximo_bytes / _BYTES_POR_MEGABYTE
    if megabytes == int(megabytes):
        return f"{int(megabytes)} MB"
    return f"{megabytes:.2f}".rstrip("0").rstrip(".") + " MB"


def _rango(configuracion: Configuracion) -> str:
    minimo, maximo = configuracion.validacion.rango_requerido_cm1
    return f"{minimo:g}{_GUION}{maximo:g} {_CM_MENOS_UNO}"


def _puntos_minimos(configuracion: Configuracion) -> str:
    return f"{configuracion.validacion.puntos_minimos:d}"


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Entrada:
    titulo: str
    texto: Callable[[Configuracion], str]
    accion: Callable[[Configuracion], str]


_CATALOGO: dict[str, _Entrada] = {
    # --- Textos exigidos de forma literal (sección 4) --------------------- #
    FORMATO_NO_SOPORTADO: _Entrada(
        titulo="Formato no admitido",
        texto=lambda c: f"Formato no soportado. Formatos admitidos: {_formatos(c)}",
        accion=lambda c: (
            "Exporte el espectro en uno de los formatos admitidos y vuelva a "
            "subirlo."
        ),
    ),
    TAMANO_EXCEDIDO: _Entrada(
        titulo="El archivo es demasiado grande",
        # CA-02.2 cita este texto en minúscula dentro de la oración; la
        # redacción exigida es la de la sección 4.
        texto=lambda c: f"El tamaño máximo permitido es de {_tamano_maximo(c)}",
        accion=lambda c: (
            "Suba un espectro más pequeño o recórtelo al rango que necesita "
            "analizar."
        ),
    ),
    RANGO_INSUFICIENTE: _Entrada(
        titulo="El espectro no cubre el rango necesario",
        texto=lambda c: f"Se requiere cubrir al menos {_rango(c)}",
        accion=lambda c: (
            "Vuelva a exportar el espectro con el rango completo y súbalo de "
            "nuevo."
        ),
    ),
    PUNTOS_INSUFICIENTES: _Entrada(
        titulo="El espectro tiene muy pocos puntos",
        texto=lambda c: f"Mínimo {_puntos_minimos(c)} puntos",
        accion=lambda c: (
            "Exporte el espectro con mayor resolución, de modo que incluya más "
            "puntos."
        ),
    ),
    # --- Situaciones con redacción libre (sección 4) ----------------------- #
    ARCHIVO_NO_ES_TEXTO: _Entrada(
        titulo="El archivo no es un espectro",
        texto=lambda c: (
            "El contenido del archivo no es texto, así que no puede ser un "
            "espectro infrarrojo."
        ),
        accion=lambda c: (
            "Revise que subió el archivo correcto, guardado en alguno de los "
            f"formatos admitidos ({_formatos(c)}), y vuelva a intentarlo."
        ),
    ),
    ESTRUCTURA_INVALIDA: _Entrada(
        titulo="El archivo está incompleto o no tiene la estructura esperada",
        texto=lambda c: (
            "El archivo es de texto, pero no contiene un espectro con la "
            "estructura que el formato necesita."
        ),
        accion=lambda c: (
            "Vuelva a exportar el espectro completo desde el programa que lo "
            "generó y súbalo de nuevo."
        ),
    ),
    CONFIGURACION_INCOMPLETA: _Entrada(
        titulo="El servicio no está disponible por ahora",
        texto=lambda c: (
            "La aplicación no pudo iniciar con su configuración, así que no "
            "puede validar espectros en este momento."
        ),
        accion=lambda c: (
            "Avise al equipo del proyecto e intente de nuevo más tarde."
        ),
    ),
    LECTURA_INTERRUMPIDA: _Entrada(
        titulo="La subida no se completó",
        texto=lambda c: (
            "La lectura del archivo se interrumpió antes de terminar, así que "
            "no se pudo revisar el espectro."
        ),
        accion=lambda c: "Vuelva a subir el archivo.",
    ),
    # El genérico de la sección 5: sirve para cualquier fallo interno, así que
    # no nombra ninguna causa. Si nombrara una, estaría contando por dentro qué
    # se rompió, que es exactamente lo que no debe salir.
    FALLO_INTERNO: _Entrada(
        titulo="No se pudo revisar el archivo",
        texto=lambda c: (
            "Ocurrió un problema al revisar el archivo y no se pudo entregar "
            "un resultado."
        ),
        accion=lambda c: (
            "Vuelva a intentarlo en un momento; si sigue ocurriendo, avise al "
            "equipo del proyecto."
        ),
    ),
    # Incremento 2, lectura completa en MOD-04 (T-08).
    DATOS_ILEGIBLES: _Entrada(
        titulo="No se pudieron leer los datos del espectro",
        texto=lambda c: (
            "El archivo tiene la estructura correcta, pero sus datos vienen en "
            "una forma o en unas unidades que la aplicación no reconoce."
        ),
        accion=lambda c: (
            "Exporte el espectro otra vez, en número de onda y con la "
            "intensidad en transmitancia o absorbancia, y vuelva a subirlo."
        ),
    ),
    # Incremento 2, línea plana (T-11). CA-03.3 pide decir que no hay señal
    # analizable.
    SIN_SENAL: _Entrada(
        titulo="Sin señal analizable",
        texto=lambda c: (
            "El espectro no contiene señal analizable: su intensidad es la "
            "misma en todos los puntos."
        ),
        accion=lambda c: (
            "Revise que exportó la medición correcta y que el equipo registró "
            "la muestra, y vuelva a subir el archivo."
        ),
    ),
    # Incremento 2, unidad de la intensidad (D-10 y D-11).
    UNIDAD_NO_SOPORTADA: _Entrada(
        titulo="Unidad de intensidad no admitida",
        texto=lambda c: (
            "La intensidad del espectro no viene en transmitancia ni en "
            "absorbancia, que son las dos unidades que la aplicación sabe "
            "analizar."
        ),
        accion=lambda c: (
            "Exporte el espectro en transmitancia o en absorbancia y vuelva a "
            "subirlo."
        ),
    ),
    UNIDAD_SIN_DECLARAR: _Entrada(
        titulo="No se sabe en qué unidad viene la intensidad",
        texto=lambda c: (
            "El archivo no tiene encabezado y todos sus valores están entre 0 "
            "y 1, así que pueden ser transmitancia o absorbancia. Tomar una "
            "por otra invertiría el espectro."
        ),
        accion=lambda c: (
            "Agregue una primera fila de encabezado que nombre la unidad, por "
            "ejemplo «numero_de_onda,transmitancia» o "
            "«numero_de_onda,absorbancia», y vuelva a subir el archivo."
        ),
    ),
    # Incremento 3: el análisis (D-17, CA-05.4 y CA-08).
    ESPECTRO_INVALIDO: _Entrada(
        titulo="El espectro no se puede analizar",
        texto=lambda c: (
            "Los datos que llegaron para el análisis no tienen la forma del "
            "espectro procesado."
        ),
        accion=lambda c: (
            "Vuelva a subir el archivo para que se procese de nuevo y después "
            "pulse «Analizar»."
        ),
    ),
    ANALISIS_FALLIDO: _Entrada(
        titulo="Análisis no completado",
        texto=lambda c: "No fue posible completar el análisis; intenta de nuevo.",
        accion=lambda c: (
            "Pulse «Analizar» otra vez; su archivo sigue cargado y no hace falta "
            "volver a subirlo."
        ),
    ),
    SIN_DETECCIONES: _Entrada(
        titulo="No se encontraron detecciones confiables",
        texto=lambda c: (
            "Ningún grupo funcional alcanzó el "
            f"{_porcentaje_del_umbral(c)} % de confianza que se necesita para "
            "reportarlo."
        ),
        accion=lambda c: (
            "Revise la calidad del espectro, por ejemplo el ruido, la línea base "
            "o el tramo medido, y vuelva a analizarlo."
        ),
    ),
}


# --------------------------------------------------------------------------- #
# Consulta
# --------------------------------------------------------------------------- #


def obtener(codigo: str, configuracion: Configuracion | None = None) -> Mensaje:
    """Devuelve el mensaje de un código, con su motivo y su acción.

    Args:
        codigo: una de las constantes de este módulo.
        configuracion: los parámetros con los que se arma el texto. Si es
            ``None`` se usan los de UT-03. El parámetro existe para las pruebas.

    Returns:
        El mensaje listo para mostrarse.

    Raises:
        CodigoDesconocido: si el código no está en el catálogo.
    """
    entrada = _CATALOGO.get(codigo)
    if entrada is None:
        raise CodigoDesconocido(
            f"UT-02: el código «{codigo}» no está en el catálogo. "
            "Agréguelo a backend/utilerias/mensajes antes de usarlo."
        )

    parametros = configuracion if configuracion is not None else obtener_configuracion()

    return Mensaje(
        codigo=codigo,
        titulo=entrada.titulo,
        texto=entrada.texto(parametros),
        accion=entrada.accion(parametros),
    )


def codigos() -> tuple[str, ...]:
    """Los códigos que el catálogo conoce hoy."""
    return tuple(_CATALOGO)
