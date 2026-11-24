"""Descarga y verifica Chemotion IR (D-12 opción B, T-16a-1).

    python -m herramientas.dataset.descargar_chemotion              # baja y extrae
    python -m herramientas.dataset.descargar_chemotion --verificar  # solo lo de disco

Deja en `datos/dataset/espectros/` (fuera de Git, ver datos/dataset/ORIGEN.md)
los 4 183 archivos y `meta_data.json`. En el paquete los archivos son UUID sin
extensión: aquí se guardan como `<uuid>.jdx`, **con los bytes intactos**.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "datos" / "dataset" / "espectros"
META = "meta_data.json"

URL = (
    "https://radar4chem.radar-service.eu/radar-backend/archives/"
    "OGoEQGlsZGElrgst/versions/1/content"
)
BYTES = 47_502_336
SHA256 = "37fec9f65a3dc07ff9e4b876090392f22b66d1a49139444b00926fbe6906bcaa"
ARCHIVOS = 4183

#: Los md5 que el propio paquete declara en su `manifest-md5.txt`.
MD5 = {
    "dataset/JCAMP-DX Files/IR_data.tar.xz": "7651fbdbce6c99a1880521f75b6da4ca",
    "dataset/meta_data.json": "31d9b064fe2a979f9b7d94bae5d3bb68",
}
_UUID = re.compile(r"exp/([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})")


def _bajar() -> bytes:
    with urllib.request.urlopen(URL, timeout=300) as respuesta:
        datos = respuesta.read(BYTES + 1)
    if len(datos) != BYTES or hashlib.sha256(datos).hexdigest() != SHA256:
        raise SystemExit("el paquete descargado no es el que se verificó el 24/11/2026")
    return datos


def _miembro(bolsa: tarfile.TarFile, sufijo: str) -> bytes:
    for m in bolsa.getmembers():
        if m.isfile() and m.name.endswith("/data/" + sufijo):
            datos = bolsa.extractfile(m).read()
            if hashlib.md5(datos).hexdigest() != MD5[sufijo]:
                raise SystemExit(f"el md5 de {sufijo} no coincide")
            return datos
    raise SystemExit(f"el paquete no trae {sufijo}")


def descargar() -> None:
    bolsa = tarfile.open(fileobj=io.BytesIO(_bajar()))
    meta = _miembro(bolsa, "dataset/meta_data.json")
    interior = tarfile.open(
        fileobj=io.BytesIO(_miembro(bolsa, "dataset/JCAMP-DX Files/IR_data.tar.xz"))
    )
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / META).write_bytes(meta)
    for m in interior:
        if m.isdir():
            continue
        # Solo un UUID puede convertirse en ruta: nada del paquete decide dónde
        # se escribe.
        nombre = _UUID.fullmatch(m.name)
        if not (m.isfile() and nombre):
            raise SystemExit(f"entrada inesperada en el paquete: {m.name!r}")
        (DESTINO / f"{nombre[1]}.jdx").write_bytes(interior.extractfile(m).read())


def verificar() -> None:
    jdx = {p.stem for p in DESTINO.glob("*.jdx")}
    if len(jdx) != ARCHIVOS:
        raise SystemExit(f"hay {len(jdx)} .jdx y deben ser {ARCHIVOS}: NO CUADRA")
    crudo = (DESTINO / META).read_bytes()
    if hashlib.md5(crudo).hexdigest() != MD5["dataset/" + META]:
        raise SystemExit("meta_data.json no es el del paquete")
    declarados = [
        adjunto["identifier"].split("/")[-1]
        for analisis in json.loads(crudo)
        for conjunto in analisis["datasets"]
        for adjunto in conjunto["attacments"]  # sic: así viene en el paquete
    ]
    if len(declarados) != len(set(declarados)) or set(declarados) != jdx:
        raise SystemExit("los archivos y meta_data.json no se corresponden 1 a 1")
    sin_titulo = [
        p.name for p in DESTINO.glob("*.jdx") if b"##TITLE" not in p.read_bytes()[:200]
    ]
    print(
        f"{len(jdx)} archivos, correspondencia 1 a 1 con {META}; "
        f"sin ##TITLE= al inicio: {len(sin_titulo)}"
    )


if __name__ == "__main__":
    if "--verificar" not in sys.argv:
        descargar()
    verificar()
