"""El embudo de Chemotion IR: MOD-03 y MOD-04 sobre los 4 183 (T-16a-1).

    python -m herramientas.dataset.embudo_chemotion

Escribe `datos/dataset/indice.csv` e imprime el embudo y las distribuciones.
Necesita RDKit (herramientas/dataset/requisitos.txt) y el conjunto descargado.

- Usa **los módulos de producción tal cual**: MOD-02 decodifica, MOD-03 valida,
  MOD-04 procesa. Aquí no se relee ni se convierte nada.
- Antes de contar comprueba que `backend/`, `motor_identificacion/` y
  `datos/catalogo/` estén idénticos a HEAD, e imprime ese hash: los números
  quedan atados a él.
- **No etiqueta y no construye split** (T-16a-2).
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from backend.manejador_archivos.receptor import recibir
from backend.nucleo.lector_espectro import nombre_de_etiqueta
from backend.preprocesamiento import procesar
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion.validador import validar
from herramientas.dataset.descargar_chemotion import DESTINO, META, RAIZ
from herramientas.dataset.estadistica import cuantil

INDICE = RAIZ / "datos" / "dataset" / "indice.csv"

#: Las del plan de T-16a-1 más `archivo`, la llave: `sample_id` se repite.
COLUMNAS = (
    "archivo",
    "sample_id",
    "cano_smiles",
    "inchikey",
    "instrument",
    "kind",
    "modo_medicion",
    "unidad_original",
    "rango_medido_cm1",
    "n_puntos",
    "fraccion_relleno",
    "veredicto",
)
PASA = "PASA"

ATR, TRANSMISION, DESCONOCIDO = "ATR", "transmision", "desconocido"

#: Las cabeceras donde un archivo puede declarar cómo se midió. `YUNITS` no
#: está a propósito: la unidad no es el modo. `TITLE` tampoco: es el nombre de
#: la muestra.
CABECERAS_DEL_MODO = (
    "SAMPLINGPROCEDURE",
    "SPECTROMETERDATASYSTEM",
    "DATAPROCESSING",
    "COMMENTS",
    "SAMPLEDESCRIPTION",
)
_ATR = re.compile(r"\bATR|attenuated total reflect", re.I)
_TRANSMISION = re.compile(r"\bKBr\b|\bpellet|\btransmission\b", re.I)

#: Carpetas cuyo estado define los números.
CARPETAS_ATADAS = ("backend", "motor_identificacion", "datos/catalogo")


# --------------------------------------------------------------------------- #
# Reglas (probadas en backend/pruebas/prueba_t16a1_embudo.py)
# --------------------------------------------------------------------------- #


def modo_medicion(instrumento: str | None, cabeceras: dict[str, str]) -> str:
    """ATR o transmisión solo si el archivo o su instrumento lo dicen."""
    texto = " | ".join(
        [instrumento or ""] + [cabeceras.get(c, "") for c in CABECERAS_DEL_MODO]
    )
    atr, transmision = bool(_ATR.search(texto)), bool(_TRANSMISION.search(texto))
    if atr == transmision:  # ninguno, o los dos a la vez
        return DESCONOCIDO
    return ATR if atr else TRANSMISION


def fraccion_relleno(eje_cm1, rango_medido_cm1) -> float:
    menor, mayor = rango_medido_cm1
    return sum(not menor <= onda <= mayor for onda in eje_cm1) / len(eje_cm1)


def etapa_del_embudo(smiles: bool, mod03: str | None, mod04: str | None) -> str:
    """La primera etapa en que se cae, en el orden del plan."""
    if not smiles:
        return "SMILES_NO_PARSEABLE"
    if mod03:
        return f"MOD-03:{mod03}"
    if mod04:
        return f"MOD-04:{mod04}"
    return PASA


# --------------------------------------------------------------------------- #
# Lectura del conjunto
# --------------------------------------------------------------------------- #


class _Subida:
    """Lo mínimo que MOD-02 pide de una subida."""

    def __init__(self, nombre: str, datos: bytes) -> None:
        self.filename = nombre
        self._flujo = io.BytesIO(datos)

    def read(self, cantidad: int = -1) -> bytes:
        return self._flujo.read(cantidad)

    def close(self) -> None:
        self._flujo.close()


def recibir_archivo(ruta: Path):
    """El archivo pasado por MOD-02, como en producción."""
    return asyncio.run(recibir(_Subida(ruta.name, ruta.read_bytes())))


def cabeceras_de(contenido: str) -> dict[str, str]:
    """Todas las etiquetas, con sus líneas de continuación. Gana la primera."""
    salida: dict[str, str] = {}
    actual: str | None = None
    for linea in contenido.splitlines():
        if linea.lstrip().startswith("##"):
            nombre, _, valor = linea.lstrip()[2:].partition("=")
            actual = nombre_de_etiqueta(nombre)
            if actual in salida:
                actual = None
                continue
            salida[actual] = valor.strip()
        elif actual in CABECERAS_DEL_MODO:
            salida[actual] += " " + linea.strip()
    return salida


def tipo_adjunto(nombre: str) -> str:
    """El papel del archivo según su nombre en Chemotion."""
    bajo = nombre.lower()
    for sufijo in (".edit.jdx", ".peak.jdx"):
        if bajo.endswith(sufijo):
            return sufijo
    return Path(bajo).suffix or "(sin)"


def adjuntos() -> list[dict]:
    """Un diccionario por archivo, en orden de UUID."""
    filas = []
    for analisis in json.loads((DESTINO / META).read_text(encoding="utf-8")):
        for conjunto in analisis["datasets"]:
            for adjunto in conjunto["attacments"]:
                filas.append(
                    {
                        "archivo": adjunto["identifier"].split("/")[-1],
                        "nombre_original": adjunto["filename"],
                        "analysis_id": analisis["analysis_id"],
                        "sample_id": analisis["sample_id"],
                        "cano_smiles": analisis["cano_smiles"],
                        "kind": analisis["kind"],
                        "instrument": conjunto["instrument"],
                        "content": analisis["content"] or "",
                    }
                )
    return sorted(filas, key=lambda f: f["archivo"])


def commit_atado() -> str:
    """El hash de HEAD, solo si el código que produce los números está limpio."""
    estado = subprocess.run(
        ["git", "status", "--porcelain", "--", *CARPETAS_ATADAS],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    # Las pruebas no producen números: pueden estar sin commitear.
    sucios = [x for x in estado.splitlines() if "backend/pruebas/" not in x]
    if sucios:
        raise SystemExit(
            "hay cambios sin commitear en lo que se mide:\n" + "\n".join(sucios)
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


# --------------------------------------------------------------------------- #
# El embudo
# --------------------------------------------------------------------------- #


def _quimica(smiles: str) -> tuple[bool, str]:
    """(¿parsea?, InChIKey). La clave puede faltar aunque el SMILES parsee."""
    from rdkit import Chem, RDLogger

    RDLogger.DisableLog("rdApp.*")
    if not smiles.strip():
        return False, ""
    molecula = Chem.MolFromSmiles(smiles)
    if molecula is None:
        return False, ""
    return True, Chem.MolToInchiKey(molecula) or ""


def evaluar_archivo(fila: dict, quimica: tuple[bool, str]) -> dict:
    """Completa la fila con lo que digan MOD-02, MOD-03 y MOD-04."""
    ruta = DESTINO / f"{fila['archivo']}.jdx"
    recepcion = recibir_archivo(ruta)
    contenido = recepcion.contenido or ""
    cab = cabeceras_de(contenido)

    mod03 = mod04 = None
    detalle = ""
    espectro = None
    if not recepcion.aceptado:
        mod03 = f"(MOD-02){recepcion.codigo}"
    else:
        try:
            v = validar(ruta.name, contenido, tamano_correcto=recepcion.tamano_correcto)
            if not v.valido:
                mod03, detalle = v.codigo, v.detalle
        except Exception as error:  # noqa: BLE001 - se cuenta, no se esconde
            mod03, detalle = "EXCEPCION", repr(error)[:120]
        if mod03 is None:
            try:
                r = procesar(ruta.name, contenido)
                if r.valido:
                    espectro = r.espectro
                else:
                    mod04, detalle = r.codigo, r.detalle
            except Exception as error:  # noqa: BLE001
                mod04, detalle = "EXCEPCION", repr(error)[:120]

    parsea, inchikey = quimica
    if not parsea:
        detalle = detalle or "RDKit no interpreta el SMILES"
    rango = relleno = ""
    if espectro is not None:
        rango = "{:g}-{:g}".format(*(round(x, 3) for x in espectro.rango_medido_cm1))
        relleno = round(
            fraccion_relleno(espectro.eje_cm1, espectro.rango_medido_cm1), 6
        )
    return fila | {
        "inchikey": inchikey,
        "modo_medicion": modo_medicion(fila["instrument"], cab),
        "unidad_original": cab.get("YUNITS", ""),
        "xunits": cab.get("XUNITS", ""),
        "rango_medido_cm1": rango,
        "n_puntos": cab.get("NPOINTS", ""),
        "fraccion_relleno": relleno,
        "veredicto": etapa_del_embudo(parsea, mod03, mod04),
        "parsea": parsea,
        "mod03": mod03,
        "mod04": mod04,
        "detalle": detalle,
        "espectro": espectro,
        "cabeceras": cab,
    }


def recorrer(filas: list[dict]) -> list[dict]:
    quimica = {s: _quimica(s) for s in {f["cano_smiles"] for f in filas}}
    salida = []
    for n, fila in enumerate(filas, start=1):
        salida.append(evaluar_archivo(fila, quimica[fila["cano_smiles"]]))
        if n % 500 == 0:
            print(f"  ... {n}", file=sys.stderr, flush=True)
    return salida


def escribir_indice(filas: list[dict]) -> None:
    with INDICE.open("w", encoding="utf-8", newline="") as flujo:
        escritor = csv.DictWriter(
            flujo, COLUMNAS, extrasaction="ignore", lineterminator="\n"
        )
        escritor.writeheader()
        for fila in filas:
            escritor.writerow(
                {c: ("" if fila[c] is None else fila[c]) for c in COLUMNAS}
            )


# --------------------------------------------------------------------------- #
# El reporte
# --------------------------------------------------------------------------- #


def _tabla(titulo: str, valores) -> None:
    conteo = Counter(valores)
    total = sum(conteo.values())
    print(f"\n### {titulo}  (n={total})")
    for clave, n in conteo.most_common():
        print(f"| {clave} | {n} | {100 * n / total:.2f} % |")


def _recuento(filas: list[dict]) -> str:
    return (
        f"{len(filas)} archivos, {len({f['analysis_id'] for f in filas})} análisis, "
        f"{len({f['sample_id'] for f in filas})} muestras, "
        f"{len({f['cano_smiles'] for f in filas})} SMILES, "
        f"{len({f['inchikey'] for f in filas if f['inchikey']})} InChIKey"
    )


def _tramo(r: float) -> str:
    for corte in (0.0, 0.01, 0.02, 0.05, 0.10, 0.20):
        if r <= corte:
            return f"<= {corte:.2f}"
    return "> 0.20"


def reportar(filas: list[dict]) -> None:
    pasan = [f for f in filas if f["veredicto"] == PASA]
    print("## Embudo")
    print("paquete:", _recuento(filas))
    resto = [f for f in filas if f["parsea"]]
    print("SMILES parseable:", _recuento(resto))
    resto = [f for f in resto if not f["mod03"]]
    print("pasan MOD-03:", _recuento(resto))
    resto = [f for f in resto if not f["mod04"]]
    print("pasan MOD-04:", _recuento(resto))
    assert len(resto) == len(pasan)

    caidos = [f for f in filas if f["veredicto"] != PASA]
    _tabla("veredicto", (f["veredicto"] for f in filas))
    _tabla("MOD-03 solo, sobre los 4183", (f["mod03"] for f in filas))
    _tabla(
        "MOD-04 solo, sobre los que pasan MOD-03",
        (f["mod04"] for f in filas if not f["mod03"]),
    )
    _tabla(
        "causa fina de los rechazos",
        ((f["veredicto"], " ".join(f["detalle"].split())[:150]) for f in caidos),
    )
    _tabla(
        "tipo de adjunto de los rechazos",
        ((f["veredicto"], tipo_adjunto(f["nombre_original"])) for f in caidos),
    )
    print(
        "\nSMILES distintos no parseables:",
        len({f["cano_smiles"] for f in filas if not f["parsea"]}),
        sorted({f["cano_smiles"] for f in filas if not f["parsea"]})[:30],
    )
    sin_clave = [f for f in filas if f["parsea"] and not f["inchikey"]]
    print(
        "parsean pero sin InChIKey:",
        len({f["cano_smiles"] for f in sin_clave}),
        "SMILES,",
        len(sin_clave),
        "archivos",
    )

    print("\n## Distribuciones")
    for nombre, grupo in (("los 4183", filas), ("pasan", pasan)):
        _tabla(
            f"tipo de adjunto ({nombre})",
            (tipo_adjunto(f["nombre_original"]) for f in grupo),
        )
        _tabla(f"instrument ({nombre})", (f["instrument"] for f in grupo))
        _tabla(f"kind ({nombre})", (f["kind"] for f in grupo))
        _tabla(f"YUNITS ({nombre})", (f["unidad_original"] for f in grupo))
        _tabla(f"modo_medicion ({nombre})", (f["modo_medicion"] for f in grupo))
    _tabla("YUNITS x veredicto", ((f["unidad_original"], f["veredicto"]) for f in filas))
    _tabla("XUNITS x veredicto", ((f["xunits"], f["veredicto"]) for f in filas))
    _tabla(
        "unidad efectiva que decidió MOD-04",
        (f["espectro"].unidad_original for f in pasan),
    )
    _tabla(
        "tipo x modo (pasan)",
        ((tipo_adjunto(f["nombre_original"]), f["modo_medicion"]) for f in pasan),
    )
    _tabla(
        "SAMPLING PROCEDURE",
        (f["cabeceras"].get("SAMPLINGPROCEDURE", "(ausente)") for f in filas),
    )

    por_analisis: dict[int, set[str]] = {}
    for f in pasan:
        por_analisis.setdefault(f["analysis_id"], set()).add(f["modo_medicion"])
    _tabla(
        "modo por análisis, juntando sus archivos (pasan)",
        ("+".join(sorted(m)) for m in por_analisis.values()),
    )
    desconocidos = [f for f in pasan if f["modo_medicion"] == DESCONOCIDO]
    _tabla(
        "desconocidos: qué dice el texto del autor (content) — NO usado",
        (
            "ATR"
            if _ATR.search(f["content"])
            else "KBr" if _TRANSMISION.search(f["content"]) else "nada"
            for f in desconocidos
        ),
    )
    _tabla(
        "desconocidos: kind ATR-FTIR — NO usado",
        ("ATR-FTIR" in f["kind"] for f in desconocidos),
    )
    _tabla(
        "modo x content (pasan)",
        (
            (f["modo_medicion"], "content:ATR" if _ATR.search(f["content"]) else
             "content:KBr" if _TRANSMISION.search(f["content"]) else "content:nada")
            for f in pasan
        ),
    )

    relleno = [f["fraccion_relleno"] for f in pasan]
    print("\n### fraccion_relleno (pasan), cuantiles")
    print(
        {
            q: round(cuantil(relleno, q), 4)
            for q in (0, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1)
        }
    )
    _tabla("fraccion_relleno por valor", relleno)
    _tabla("fraccion_relleno por tramo", (_tramo(r) for r in relleno))
    _tabla(
        "rango medido (pasan)",
        ("{:.0f}-{:.0f}".format(*f["espectro"].rango_medido_cm1) for f in pasan),
    )
    _tabla("n_puntos (pasan)", (f["n_puntos"] for f in pasan))


def main() -> None:
    logging.disable(logging.CRITICAL)
    sys.stdout.reconfigure(encoding="utf-8")
    print("commit:", commit_atado())
    print("N de la rejilla:", obtener_configuracion().procesamiento.puntos_rejilla)
    filas = recorrer(adjuntos())
    escribir_indice(filas)
    reportar(filas)


if __name__ == "__main__":
    main()
