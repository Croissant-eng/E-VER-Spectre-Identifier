"""Generador de espectros sintéticos para las pruebas del incremento 1.

**Esto no es código de la aplicación.** Vive en `herramientas/` a propósito: es
una herramienta de preparación de datos de prueba. No lo importe ningún módulo
de `backend/`, y no se vuelva la base de MOD-04 sin revisarlo (sección 11 del
plan).

El incremento 1 solo valida **estructura, tamaño, puntos y rango**: nunca mira
química real. Por eso sus archivos de prueba son fabricados, sin una sola línea
de datos de NIST. Eso cubre todas las CA del incremento, evita el problema de
redistribución del repositorio público y deja que cualquiera corra las pruebas
sin descargar nada.

Los valores que importan —tamaño máximo y puntos mínimos— se leen de UT-03, no
se escriben aquí: si el equipo cambia el límite, los archivos de prueba lo
siguen.
"""

from __future__ import annotations

import struct
import zlib

#: Formato de cada par del CSV. Dos columnas: número de onda, intensidad.
_FORMATO_CSV = "{x:.4f},{y:.6f}"

#: Formato de ancho fijo, con el número de onda rellenado con ceros a la
#: izquierda («0400.0000»). Solo lo usa el archivo de tamaño exacto: con todas
#: las líneas del mismo largo, el relleno final es de unos pocos bytes en vez de
#: decenas de miles. Los ceros a la izquierda no estorban: sigue siendo un
#: número.
_FORMATO_CSV_FIJO = "{x:09.4f},{y:.6f}"


def _intensidad(indice: int, puntos: int) -> float:
    """Una curva suave y determinista, entre 0 y 1.

    No pretende parecerse a un espectro real: solo necesita ser un número
    plausible de transmitancia. La forma es determinista para que el archivo
    generado sea idéntico en cada corrida y git no vea cambios falsos.
    """
    fraccion = indice / max(puntos - 1, 1)
    # Dos «jorobas» mezcladas, sin usar módulos externos.
    joroba = 0.35 + 0.45 * abs(0.5 - fraccion) * 2
    rizo = 0.08 * ((indice * 7919) % 101) / 100
    return round(min(max(joroba + rizo, 0.01), 0.99), 6)


def _numeros_de_onda(puntos: int, desde: float, hasta: float) -> list[float]:
    if puntos < 2:
        raise ValueError("se necesitan al menos dos puntos")
    paso = (hasta - desde) / (puntos - 1)
    return [desde + indice * paso for indice in range(puntos)]


def csv_sintetico(puntos: int, desde: float, hasta: float) -> bytes:
    """Un CSV de dos columnas con `puntos` pares, de `desde` a `hasta` cm⁻¹."""
    lineas = [
        _FORMATO_CSV.format(x=x, y=_intensidad(indice, puntos))
        for indice, x in enumerate(_numeros_de_onda(puntos, desde, hasta))
    ]
    return ("\n".join(lineas) + "\n").encode("ascii")


def csv_de_tamano_exacto(
    bytes_objetivo: int, desde: float, hasta: float, *, puntos_minimos: int
) -> bytes:
    """Un CSV válido que pesa **exactamente** `bytes_objetivo`.

    Es lo único que no puede existir «en la naturaleza»: un espectro de un
    tamaño al byte. Se arma con tantos pares como quepan y se rellena la última
    intensidad con decimales de más —sigue siendo un número válido— hasta dar
    el tamaño exacto.

    Args:
        bytes_objetivo: tamaño final del archivo, en bytes.
        desde: primer número de onda.
        hasta: último número de onda.
        puntos_minimos: cantidad de pares por debajo de la cual el archivo no
            serviría para la prueba (se toma de UT-03).

    Raises:
        ValueError: si el tamaño pedido no alcanza para los puntos mínimos.
    """
    largo_linea = len(_FORMATO_CSV_FIJO.format(x=hasta, y=0.123456)) + 1
    puntos = max(bytes_objetivo // largo_linea, puntos_minimos)

    # Se arma dejando la última línea para el final: ahí va el relleno.
    while True:
        ondas = _numeros_de_onda(puntos, desde, hasta)
        cuerpo = "\n".join(
            _FORMATO_CSV_FIJO.format(x=x, y=_intensidad(indice, puntos))
            for indice, x in enumerate(ondas[:-1])
        )
        cuerpo = (cuerpo + "\n").encode("ascii") if cuerpo else b""
        ultima = _FORMATO_CSV_FIJO.format(x=ondas[-1], y=_intensidad(puntos - 1, puntos))
        faltan = bytes_objetivo - len(cuerpo) - len(ultima.encode("ascii")) - 1

        if faltan >= 0:
            break
        puntos -= 1
        if puntos < puntos_minimos:
            raise ValueError(
                f"{bytes_objetivo} bytes no alcanzan para {puntos_minimos} pares"
            )

    # El relleno son decimales extra de la última intensidad: el par sigue
    # siendo «número, número».
    archivo = cuerpo + (ultima + "0" * faltan + "\n").encode("ascii")

    if len(archivo) != bytes_objetivo:  # pragma: no cover - red de seguridad
        raise AssertionError(
            f"se pidieron {bytes_objetivo} bytes y salieron {len(archivo)}"
        )
    if puntos < puntos_minimos:  # pragma: no cover - red de seguridad
        raise AssertionError(f"quedaron {puntos} pares, menos que el mínimo")
    return archivo


def jdx_sintetico(
    titulo: str,
    puntos: int,
    desde: float,
    hasta: float,
    *,
    nota: str = "",
    con_end: bool = True,
) -> bytes:
    """Un `.jdx` con las etiquetas obligatorias y pares bajo `##XYDATA=`.

    `##TITLE=` queda en la primera línea y `##END=` en la última, como exige
    MOD-03. Con `con_end=False` se obtiene el archivo truncado de CA-02.4.

    La nota se escribe como comentario `$$`, que es parte del formato
    JCAMP-DX, así que el archivo sigue siendo válido.
    """
    lineas = [
        f"##TITLE={titulo}",
        "##JCAMP-DX=4.24",
        "##DATA TYPE=INFRARED SPECTRUM",
    ]
    if nota:
        lineas.append(f"$$ {nota}")
    lineas += [
        "##ORIGIN=E-VER Spectre Identifier (archivo fabricado para pruebas)",
        "##OWNER=PUBLIC DOMAIN",
        "##XUNITS=1/CM",
        "##YUNITS=TRANSMITTANCE",
        "##XFACTOR=1",
        "##YFACTOR=1",
        f"##FIRSTX={desde:.4f}",
        f"##LASTX={hasta:.4f}",
        f"##NPOINTS={puntos}",
        "##XYDATA=(XY..XY)",
    ]
    lineas += [
        f"{x:.4f} {_intensidad(indice, puntos):.6f}"
        for indice, x in enumerate(_numeros_de_onda(puntos, desde, hasta))
    ]
    if con_end:
        lineas.append("##END=")
    return ("\n".join(lineas) + "\n").encode("ascii")


def png_minimo() -> bytes:
    """Un PNG válido de 1×1 píxel, armado a mano.

    Sirve para CA-01.3: un formato que la aplicación no admite. Se fabrica con
    la biblioteca estándar para no agregar dependencias de imágenes.
    """

    def trozo(tipo: bytes, datos: bytes) -> bytes:
        crc = zlib.crc32(tipo + datos) & 0xFFFFFFFF
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", crc)

    firma = b"\x89PNG\r\n\x1a\n"
    # 1×1, 8 bits, escala de grises.
    cabecera = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    pixeles = zlib.compress(b"\x00\x00")
    return firma + trozo(b"IHDR", cabecera) + trozo(b"IDAT", pixeles) + trozo(b"IEND", b"")


def binario_disfrazado() -> bytes:
    """Bytes binarios con la cabecera «MZ», para renombrarlos a `.csv`.

    Sirve para CA-02.5: la aplicación debe rechazarlo **por su contenido**, sin
    confiar en la extensión. **No es un ejecutable:** son bytes nulos y un
    relleno determinista detrás de la cabecera, sin cabecera PE válida ni una
    sola instrucción. No puede ejecutarse ni en Windows ni en ningún otro
    sistema; lo único que importa para la prueba es que traiga bytes nulos y no
    imprimibles.
    """
    relleno = bytes((indice * 37 + 11) % 256 for indice in range(512))
    return b"MZ" + b"\x00" * 60 + relleno
