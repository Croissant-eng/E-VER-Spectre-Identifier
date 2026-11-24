"""Revisión de lo que llega a POST /api/reporte (incremento 5).

La página manda en JSON:

    nombre: el nombre del archivo que se analizó, tal como lo devolvió MOD-02.
    espectro: el mismo objeto que mandó a /api/analizar.
    grafica_png: la gráfica resaltada, como data URL de una imagen PNG.
    zona_horaria_min: lo que da getTimezoneOffset() en el navegador, para
        escribir la fecha en la hora de quien analizó. Es opcional.

El espectro se revisa con la misma función que /api/analizar y el servidor
vuelve a correr el motor y MOD-07 con él. Así los grupos, las confianzas y las
explicaciones del PDF no dependen de lo que diga la página: salen del mismo
cálculo que se mostró en pantalla. Lo único que se toma tal cual es la imagen,
y antes se comprueba que de verdad sea un PNG.

Si algo no cuadra se devuelve None y la ruta responde REPORTE_INVALIDO.
"""

from __future__ import annotations

import base64
import binascii
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.api.entrada_analisis import EspectroRecibido, espectro_desde
from backend.utilerias.configuracion import Configuracion

#: Los primeros ocho bytes de todo archivo PNG.
FIRMA_PNG: bytes = b"\x89PNG\r\n\x1a\n"
PREFIJO_PNG: str = "data:image/png;base64,"

#: Largo máximo del nombre que se escribe en el reporte.
LARGO_MAXIMO_NOMBRE: int = 255

#: El desfase horario más grande que existe, en minutos (UTC+14 y UTC-12).
DESFASE_MAXIMO_MIN: int = 14 * 60


@dataclass(frozen=True)
class PeticionDeReporte:
    nombre: str
    espectro: EspectroRecibido
    imagen_png: bytes = field(repr=False)
    fecha_hora: datetime
    zona: str


def _nombre(valor: Any) -> str | None:
    """El nombre sin caracteres de control y con un largo razonable."""
    if not isinstance(valor, str):
        return None
    limpio = "".join(c for c in valor if unicodedata.category(c)[0] != "C").strip()
    if not limpio or len(limpio) > LARGO_MAXIMO_NOMBRE:
        return None
    return limpio


def _imagen(valor: Any, limite_bytes: int) -> bytes | None:
    if not isinstance(valor, str) or not valor.startswith(PREFIJO_PNG):
        return None
    codificada = valor[len(PREFIJO_PNG):]
    # Se revisa el largo antes de decodificar para no gastar memoria de más.
    if len(codificada) > limite_bytes * 4 // 3 + 4:
        return None
    try:
        imagen = base64.b64decode(codificada, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(imagen) > limite_bytes or not imagen.startswith(FIRMA_PNG):
        return None
    return imagen


def _hora_local(valor: Any, ahora: datetime) -> tuple[datetime, str] | None:
    """La hora de quien analizó y su zona escrita como UTC-06:00."""
    if valor is None:
        desfase = 0
    elif isinstance(valor, bool) or not isinstance(valor, int):
        return None
    else:
        desfase = valor
    if abs(desfase) > DESFASE_MAXIMO_MIN:
        return None
    # getTimezoneOffset() es positivo al oeste de Greenwich: México da 360.
    local = ahora - timedelta(minutes=desfase)
    horas, minutos = divmod(abs(desfase), 60)
    signo = "-" if desfase > 0 else "+"
    return local, f"UTC{signo}{horas:02d}:{minutos:02d}"


def peticion_desde(
    cuerpo: Any, configuracion: Configuracion, ahora: datetime | None = None
) -> PeticionDeReporte | None:
    """La petición ya revisada, o None si no tiene la forma esperada.

    La imagen no puede pasar del tamaño máximo de archivo de UT-03: es el
    mismo límite que ya cuida todo lo que sube al servidor.
    """
    if not isinstance(cuerpo, dict):
        return None
    nombre = _nombre(cuerpo.get("nombre"))
    espectro = espectro_desde(cuerpo.get("espectro"), configuracion)
    imagen = _imagen(cuerpo.get("grafica_png"), configuracion.archivo.tamano_maximo_bytes)
    momento = ahora if ahora is not None else datetime.now(timezone.utc)
    hora = _hora_local(cuerpo.get("zona_horaria_min"), momento)
    if nombre is None or espectro is None or imagen is None or hora is None:
        return None
    return PeticionDeReporte(nombre, espectro, imagen, hora[0], hora[1])
