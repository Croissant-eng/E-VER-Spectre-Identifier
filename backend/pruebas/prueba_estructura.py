"""Pruebas de estructura del repositorio (T-00) y de la decisión D-7.

D-7: las carpetas que Python importa como paquete usan **guion bajo**. Un guion
no es identificador válido, así que `import backend.manejador-archivos` es un
error de sintaxis, no un error en tiempo de ejecución: no hay forma de
importarla ni de rodearla. Esta prueba falla si el guion vuelve.

Solo mira el backend. Las carpetas del frontend (`interfaz/`, `servicios/`,
`visor-espectro/`) conservan el guion a propósito: nadie las importa.
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"

#: Carpetas que no son paquetes: solo cachés de herramientas. D-8 quitó
#: `backend/pruebas/archivos/`: los datos de prueba viven en `datos/pruebas/` y
#: `backend/pruebas/` queda solo para código (RNF-06).
IGNORADAS = {"__pycache__", ".pytest_cache"}


def prueba_las_carpetas_del_backend_son_importables_como_paquete() -> None:
    """D-7: cada carpeta del backend debe poder escribirse en un `import`."""
    invalidas: list[str] = []

    for carpeta in sorted(p for p in BACKEND.rglob("*") if p.is_dir()):
        if any(parte in IGNORADAS for parte in carpeta.relative_to(RAIZ).parts):
            continue
        if not carpeta.name.isidentifier():
            invalidas.append(carpeta.relative_to(RAIZ).as_posix())

    assert not invalidas, (
        "estas carpetas del backend no se pueden importar en Python; "
        f"use guion bajo (D-7): {invalidas}"
    )


def prueba_mod_02_vive_en_la_carpeta_con_guion_bajo() -> None:
    """La carpeta de MOD-02 que nombran el plan (§6) y CLAUDE.md."""
    assert (BACKEND / "manejador_archivos").is_dir()
    assert not (BACKEND / "manejador-archivos").exists(), (
        "quedó la carpeta vieja con guion: el renombre de D-7 está a medias"
    )


def prueba_las_pruebas_solo_guardan_codigo() -> None:
    """D-8: `backend/pruebas/` es código; los datos de prueba viven en `datos/`.

    Tener dos lugares para lo mismo invita a que alguien commitee ahí un
    espectro —o un archivo de megabytes— y la sección 11 del plan dice justo lo
    contrario.
    """
    assert not (BACKEND / "pruebas" / "archivos").exists(), (
        "D-8 quitó backend/pruebas/archivos/: los archivos de prueba van en "
        "datos/pruebas/"
    )

    intrusos = [
        p.relative_to(RAIZ).as_posix()
        for p in (BACKEND / "pruebas").rglob("*")
        if p.is_file()
        and p.suffix != ".py"
        and "__pycache__" not in p.relative_to(RAIZ).parts
    ]

    assert not intrusos, (
        "estos archivos no son código y no deberían vivir en backend/pruebas/; "
        f"su lugar es datos/pruebas/: {intrusos}"
    )


def prueba_los_datos_de_prueba_viven_en_datos() -> None:
    """La otra mitad de D-8: la carpeta de fixtures existe y está poblada."""
    carpeta = RAIZ / "datos" / "pruebas"
    assert carpeta.is_dir(), f"faltan los archivos de prueba en {carpeta}"
    assert any(carpeta.iterdir()), f"{carpeta} está vacía"
