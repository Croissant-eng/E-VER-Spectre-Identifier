"""MOD-08, el reporte en PDF (T-25, T-26 y T-27).

Arma el PDF con ReportLab (decisión D-3, elegida por el equipo el 24/11/2026)
y lo arma completo en memoria: se escribe en un BytesIO y se devuelve como
bytes, sin tocar el disco (RNF-09). El servidor no guarda el reporte.

Lo que lleva, según CA-09.1:

1. El nombre del archivo y la fecha y hora del análisis.
2. La gráfica con las regiones resaltadas, tal como la dibujó la página
   (T-26).
3. Cada grupo con su confianza y su explicación de MOD-07.
4. El aviso de que el resultado es orientativo (RF-08).

Si no hubo detecciones, el reporte lo dice con el aviso de UT-02 (CA-09.2).
Si el motor trabajó solo con reglas, también lo dice, como dejó pedido D-16.

Los datos llegan ya armados en el mismo diccionario que la página recibe de
/api/analizar, así que el reporte no puede decir algo distinto de lo que se
vio en pantalla. Este módulo no redacta mensajes de error.

Para que se vean bien símbolos como C≡N o cm⁻¹ se usa la fuente DejaVu, que
viene en backend/reportes/fuentes con su licencia libre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

CARPETA_FUENTES = Path(__file__).resolve().parent / "fuentes"
FUENTE = "DejaVuSans"
FUENTE_NEGRITA = "DejaVuSans-Bold"

#: Los textos fijos del reporte. Son parte del documento, no mensajes de
#: error, por eso viven aquí y no en UT-02.
TITULO = "Reporte de análisis infrarrojo"
AUTOR = "E-VER Spectre Identifier"
SECCION_GRAFICA = "Espectro con las regiones resaltadas"
SECCION_GRUPOS = "Grupos funcionales detectados"
AVISO_ORIENTATIVO = (
    "Este resultado es orientativo. La aplicación identifica grupos funcionales "
    "a partir de reglas y, cuando está disponible, de un modelo entrenado; no "
    "identifica la molécula completa ni sustituye la interpretación de una "
    "persona con formación en química."
)
AVISO_SOLO_REGLAS = (
    "Este análisis se hizo solo con la vía de reglas, sin el modelo entrenado."
)
MODO_REGLAS = "reglas"

#: El espacio máximo de la gráfica en la hoja. Se escala conservando su
#: proporción hasta caber en los dos, así una imagen muy alta no se sale de la
#: página.
ANCHO_GRAFICA = 17 * cm
ALTO_MAXIMO_GRAFICA = 12 * cm

_fuentes_listas = False


def _registrar_fuentes() -> None:
    global _fuentes_listas
    if _fuentes_listas:
        return
    pdfmetrics.registerFont(TTFont(FUENTE, str(CARPETA_FUENTES / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(
        TTFont(FUENTE_NEGRITA, str(CARPETA_FUENTES / "DejaVuSans-Bold.ttf"))
    )
    pdfmetrics.registerFontFamily(
        FUENTE, normal=FUENTE, bold=FUENTE_NEGRITA, italic=FUENTE, boldItalic=FUENTE_NEGRITA
    )
    _fuentes_listas = True


@dataclass(frozen=True)
class DatosDelReporte:
    """Todo lo que lleva un reporte."""

    nombre_archivo: str
    #: Ya en la hora de quien analizó, con su desfase escrito aparte.
    fecha_hora: datetime
    zona: str
    #: El cuerpo de /api/analizar, con detecciones, explicaciones y aviso.
    analisis: dict[str, Any]
    imagen_png: bytes = field(repr=False)


def _estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName=FUENTE, fontSize=10, leading=14)
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base, fontName=FUENTE_NEGRITA, fontSize=18, leading=22, spaceAfter=6
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base, fontName=FUENTE_NEGRITA, fontSize=13, leading=17,
            spaceBefore=12, spaceAfter=4,
        ),
        "grupo": ParagraphStyle(
            "grupo", parent=base, fontName=FUENTE_NEGRITA, fontSize=11, leading=15, spaceBefore=8
        ),
        "texto": base,
        "suave": ParagraphStyle("suave", parent=base, textColor=colors.HexColor("#556070")),
        "aviso": ParagraphStyle(
            "aviso", parent=base, textColor=colors.HexColor("#7a4b00"), spaceBefore=14
        ),
    }


def _p(texto: str, estilo: ParagraphStyle) -> Paragraph:
    """Un párrafo con el texto escapado.

    Paragraph de ReportLab interpreta un poco de marcado. El nombre del
    archivo lo eligió quien lo subió, así que todo texto se escapa para que no
    pueda romper el PDF ni meterle formato.
    """
    return Paragraph(escape(texto), estilo)


def _grafica(imagen_png: bytes, estilos) -> list:
    """T-26: la gráfica tal como la dibujó la página, con su resaltado."""
    ancho, alto = ImageReader(BytesIO(imagen_png)).getSize()
    escala = min(ANCHO_GRAFICA / ancho, ALTO_MAXIMO_GRAFICA / alto)
    return [
        Paragraph(SECCION_GRAFICA, estilos["subtitulo"]),
        Image(BytesIO(imagen_png), width=ancho * escala, height=alto * escala),
    ]


def _grupos(analisis: dict[str, Any], estilos) -> list:
    partes: list = [Paragraph(SECCION_GRUPOS, estilos["subtitulo"])]

    if analisis.get("sin_detecciones"):
        # CA-09.2: el reporte dice explícitamente que no hubo detecciones.
        aviso = analisis.get("aviso") or {}
        for clave, estilo in (("titulo", "grupo"), ("mensaje", "texto"), ("accion", "texto")):
            if aviso.get(clave):
                partes.append(_p(aviso[clave], estilos[estilo]))
        return partes

    for deteccion in analisis.get("detecciones", []):
        partes.append(
            _p(f"{deteccion['nombre']}: {deteccion['porcentaje']} % de confianza", estilos["grupo"])
        )
        explicacion = deteccion.get("explicacion") or {}
        if explicacion.get("disponible"):
            for clave in ("region", "posicion", "rasgo", "por_que", "distincion"):
                if explicacion.get(clave):
                    partes.append(_p(explicacion[clave], estilos["texto"]))
        else:
            # CA-07.3 llevado al reporte: el grupo se queda con su aviso.
            for clave in ("titulo", "mensaje"):
                if explicacion.get(clave):
                    partes.append(_p(explicacion[clave], estilos["suave"]))
        partes.append(Spacer(1, 4))
    return partes


def generar_pdf(datos: DatosDelReporte) -> bytes:
    """El PDF del reporte, como bytes. Nunca se escribe en disco."""
    _registrar_fuentes()
    estilos = _estilos()
    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=TITULO,
        author=AUTOR,
    )

    fecha = datos.fecha_hora.strftime("%d/%m/%Y a las %H:%M")
    partes: list = [
        Paragraph(TITULO, estilos["titulo"]),
        _p(f"Archivo: {datos.nombre_archivo}", estilos["texto"]),
        _p(f"Fecha y hora del análisis: {fecha} ({datos.zona})", estilos["texto"]),
    ]
    partes += _grafica(datos.imagen_png, estilos)
    partes += _grupos(datos.analisis, estilos)
    if datos.analisis.get("modo") == MODO_REGLAS:
        partes.append(_p(AVISO_SOLO_REGLAS, estilos["aviso"]))
    partes.append(_p(AVISO_ORIENTATIVO, estilos["aviso"]))

    documento.build(partes)
    return salida.getvalue()
