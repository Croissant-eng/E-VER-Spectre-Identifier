"""Descarga (o verifica) los espectros reales de NIST Chemistry WebBook.

Los tres espectros reales del proyecto son de la **Coblentz Society** y llevan
copyright: commitearlos en un repositorio público sería redistribuirlos. Por eso
`datos/referencia/` está en `.gitignore` y lo que se versiona es este par
—script + manifiesto— que los reproduce.

Uso, desde la raíz del repositorio:

    python -m herramientas.descargar_espectros_nist --verificar   # los de disco
    python -m herramientas.descargar_espectros_nist              # descarga los que falten
    python -m herramientas.descargar_espectros_nist --forzar     # vuelve a bajarlos

El manifiesto (`espectros_nist.json`) guarda el `sha256` de cada archivo, así
que la verificación es byte a byte. Si NIST vuelve a digitalizar un espectro, el
`sha256` dejará de coincidir: el script lo dice en vez de callarse, y entonces
hay que decidir a mano si se acepta la versión nueva y se actualiza el
manifiesto.

Un compuesto puede tener varios espectros IR en el WebBook, y el índice que los
distingue no se adivina: para el ácido benzoico, el índice 3 trae uno
parecidísimo al elegido (3345 puntos contra 3364). El manifiesto guarda el
índice de cada uno —acetona 3, ácido benzoico 4, anilina 2, verificados contra
el sitio— y el script lo prueba primero; si NIST reordena los espectros, sondea
los demás índices como respaldo y se queda con el que coincide.

**Esto no es código de la aplicación**: vive en `herramientas/` y ningún módulo
de `backend/` lo importa. Solo usa la biblioteca estándar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MANIFIESTO = Path(__file__).resolve().parent / "espectros_nist.json"

#: Punto de descarga de JCAMP-DX del WebBook.
URL_BASE = "https://webbook.nist.gov/cgi/cbook.cgi"

#: Cuántos índices probar por compuesto antes de rendirse.
INDICES_A_PROBAR = 8

#: Pausa entre peticiones, para no castigar al servidor de NIST.
PAUSA_SEGUNDOS = 1.0

#: Identificación genérica: no lleva datos de nadie.
AGENTE = "E-VER-Spectre-Identifier/1.0 (proyecto academico; descarga de fixtures)"


def _sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def _etiqueta(texto: str, llave: str) -> str | None:
    encontrada = re.search(rf"^##{re.escape(llave)}=(.*)$", texto, re.MULTILINE)
    return encontrada.group(1).strip() if encontrada else None


def _parece_jcamp(datos: bytes) -> bool:
    return datos.lstrip().startswith(b"##TITLE=")


def _coincide_el_contenido(datos: bytes, espectro: dict) -> tuple[bool, str]:
    """¿Este archivo es el espectro que describe el manifiesto?

    Primero por `sha256`, que es exacto. Si no coincide, se comparan los datos
    que identifican al espectro elegido (puntos y extremos del eje), para poder
    decir «es el mismo espectro pero los bytes cambiaron» en lugar de un «no
    coincide» a secas.
    """
    if _sha256(datos) == espectro["sha256"]:
        return True, "sha256 idéntico"

    texto = datos.decode("latin-1")
    puntos = _etiqueta(texto, "NPOINTS")
    primero = _etiqueta(texto, "FIRSTX")
    ultimo = _etiqueta(texto, "LASTX")
    try:
        mismo = (
            int(puntos or -1) == espectro["puntos"]
            and abs(float(primero or 0) - espectro["primer_x"]) < 0.01
            and abs(float(ultimo or 0) - espectro["ultimo_x"]) < 0.01
        )
    except ValueError:
        mismo = False

    if mismo:
        return False, (
            f"mismos puntos y extremos ({puntos} puntos, {primero}–{ultimo}) "
            "pero distintos bytes: NIST pudo re-digitalizarlo"
        )
    return False, f"otro espectro ({puntos} puntos, {primero}–{ultimo})"


def _descargar(id_nist: str, tipo: str, indice: int) -> bytes:
    parametros = urllib.parse.urlencode(
        {"JCAMP": id_nist, "Index": indice, "Type": tipo}
    )
    peticion = urllib.request.Request(
        f"{URL_BASE}?{parametros}", headers={"User-Agent": AGENTE}
    )
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        return respuesta.read()


def verificar(carpeta: Path, espectros: list[dict]) -> int:
    """Compara los archivos que ya están en disco contra el manifiesto."""
    problemas = 0
    for espectro in espectros:
        ruta = carpeta / espectro["archivo"]
        if not ruta.is_file():
            print(f"  FALTA    {espectro['archivo']} ({espectro['compuesto']})")
            problemas += 1
            continue

        datos = ruta.read_bytes()
        coincide, detalle = _coincide_el_contenido(datos, espectro)
        if coincide:
            print(
                f"  OK       {espectro['archivo']:<16} {espectro['compuesto']:<16} "
                f"{len(datos):>6} bytes · {espectro['puntos']} puntos"
            )
        else:
            print(f"  DISTINTO {espectro['archivo']:<16} {detalle}")
            problemas += 1
    return problemas


def descargar_faltantes(carpeta: Path, espectros: list[dict], forzar: bool) -> int:
    """Baja de NIST los espectros que no estén en disco."""
    problemas = 0
    carpeta.mkdir(parents=True, exist_ok=True)

    for espectro in espectros:
        ruta = carpeta / espectro["archivo"]
        if ruta.is_file() and not forzar:
            print(f"  YA ESTÁ  {espectro['archivo']}")
            continue

        print(f"  buscando {espectro['compuesto']} ({espectro['id_nist']})…")
        encontrado = False
        ultimo_detalle = "no se probó ningún índice"

        # El índice conocido va primero; los demás quedan como respaldo por si
        # NIST reordena los espectros de un compuesto.
        conocido = espectro.get("indice")
        por_probar = [conocido] if conocido is not None else []
        por_probar += [i for i in range(INDICES_A_PROBAR) if i != conocido]

        for indice in por_probar:
            try:
                datos = _descargar(espectro["id_nist"], espectro["tipo"], indice)
            except (urllib.error.URLError, TimeoutError) as error:
                ultimo_detalle = f"no se pudo descargar: {error}"
                break

            if not _parece_jcamp(datos):
                ultimo_detalle = f"el índice {indice} no devolvió un JCAMP-DX"
                time.sleep(PAUSA_SEGUNDOS)
                continue

            coincide, detalle = _coincide_el_contenido(datos, espectro)
            if coincide:
                ruta.write_bytes(datos)
                print(f"  OK       índice {indice} → {espectro['archivo']} ({detalle})")
                encontrado = True
                break

            ultimo_detalle = f"índice {indice}: {detalle}"
            time.sleep(PAUSA_SEGUNDOS)

        if not encontrado:
            print(f"  SIN SUERTE {espectro['archivo']}: {ultimo_detalle}")
            print(
                "             Bájelo a mano: busque el CAS en webbook.nist.gov, "
                "abra «IR Spectrum» y descargue el JCAMP-DX del espectro que "
                "describe el manifiesto."
            )
            problemas += 1
    return problemas


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--verificar",
        action="store_true",
        help="solo compara los archivos de disco con el manifiesto, sin descargar",
    )
    analizador.add_argument(
        "--forzar",
        action="store_true",
        help="vuelve a descargar incluso si el archivo ya está",
    )
    analizador.add_argument(
        "--carpeta",
        type=Path,
        help="carpeta destino (por omisión, la del manifiesto)",
    )
    argumentos = analizador.parse_args()

    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    espectros = manifiesto["espectros"]
    carpeta = argumentos.carpeta or RAIZ / manifiesto["carpeta_destino"]

    print(f"Manifiesto: {MANIFIESTO.name} · {len(espectros)} espectros")
    print(f"Carpeta:    {carpeta}")
    print(f"Licencia:   {manifiesto['_licencia']}")
    print()

    if argumentos.verificar:
        problemas = verificar(carpeta, espectros)
    else:
        problemas = descargar_faltantes(carpeta, espectros, argumentos.forzar)
        print()
        problemas += verificar(carpeta, espectros)

    print()
    if problemas:
        print(f"{problemas} problema(s). Revise el detalle de arriba.")
        return 1
    print("Todo coincide con el manifiesto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
