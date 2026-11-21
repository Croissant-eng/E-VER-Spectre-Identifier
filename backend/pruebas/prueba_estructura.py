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

#: Carpetas que no son paquetes: cachés y archivos de apoyo de las pruebas.
IGNORADAS = {"__pycache__", ".pytest_cache", "archivos"}


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
