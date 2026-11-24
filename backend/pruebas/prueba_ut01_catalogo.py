"""Pruebas de T-14 · UT-01 Catálogo de los 7 grupos funcionales.

Cubren las pruebas que el plan del incremento 3 le pide a T-14 (secciones 8 y 9):

- **Cobertura:** los 7 grupos existen, en el orden canónico, y a ninguno le falta
  región ni rasgo.
- **Los números son los del plan:** la tabla de abajo repite la sección 4 del
  plan del incremento 3. Es el único lugar del repositorio, además del catálogo,
  donde estos números vuelven a escribirse: si alguien cambia un rango en el
  JSON por descuido, esta prueba revienta.
- **No-«hardcodeo»:** ningún número de región aparece fuera del catálogo.
- **Catálogo incompleto o corrupto al cargar → error claro**, sin arrancar en
  silencio (mismo patrón que UT-03 en T-01).
- **Solo lectura:** lo que entrega UT-01 no se puede modificar.
- **Sin red:** el lector solo abre un archivo local.

El orden canónico GF-01 … GF-07 es el que usará el vector de etiquetas de T-16.
Queda fijado una sola vez, en el catálogo; aquí solo se verifica.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from pathlib import Path
from typing import Any

import pytest

from backend.utilerias.catalogo import (
    BANDAS_DEL_PAR,
    GRUPOS_ESPERADOS,
    NOMBRE_ARCHIVO,
    PATRON_ARCHIVO,
    ROLES_VALIDOS,
    RUTA_CATALOGO,
    ErrorDeCatalogo,
    cargar,
    obtener,
    recargar,
)

RAIZ = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# La tabla de la sección 4 del plan del incremento 3
# (Requerimientos V3.2 §6.2 + MOD-06 §4)
# --------------------------------------------------------------------------- #

#: id -> (región principal, regiones acompañantes como (mín, máx, rol))
ESPERADO: dict[
    str, tuple[tuple[float, float], tuple[tuple[float, float, str], ...]]
] = {
    "GF-01": ((3200.0, 3550.0), ((2500.0, 3300.0, "indicio"),)),
    "GF-02": ((3300.0, 3500.0), ()),
    "GF-03": ((2850.0, 2960.0), ()),
    "GF-04": ((2210.0, 2260.0), ()),
    "GF-05": ((1670.0, 1780.0), ()),
    "GF-06": ((1620.0, 1680.0), ((3020.0, 3100.0, "confirmacion"),)),
    "GF-07": (
        (1450.0, 1600.0),
        (
            (1600.0, 1600.0, "par"),
            (1500.0, 1500.0, "par"),
            (3000.0, 3100.0, "confirmacion"),
        ),
    ),
}

ORDEN_CANONICO_DEL_PLAN = (
    "GF-01",
    "GF-02",
    "GF-03",
    "GF-04",
    "GF-05",
    "GF-06",
    "GF-07",
)

#: Los **cinco** subtipos informativos de C=O de la sección 4 v1.7 del plan
#: (MOD-06 §4). La versión 1.0 del plan citaba solo tres, abreviados: era un
#: error del documento, corregido el 23/11/2026 (D-20.5).
SUBTIPOS_DE_GF05 = (
    ("cetona", (1715.0, 1715.0)),
    ("aldehído", (1720.0, 1740.0)),
    ("éster", (1735.0, 1750.0)),
    ("ácido carboxílico", (1690.0, 1760.0)),
    ("amida", (1630.0, 1700.0)),
)

#: El enlace o vibración de cada grupo, de la columna que la sección 4 v1.7
#: añadió. Solo GF-07 se verifica aquí: su valor venía de MOD-06 §4 y el plan lo
#: omitía (D-20, correcciones menores).
ENLACE_DE_GF07 = "estiramiento del anillo"


# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


def _datos_del_repositorio() -> dict[str, Any]:
    """El contenido del archivo real, para derivar de él los casos de error."""
    return json.loads(RUTA_CATALOGO.read_text(encoding="utf-8"))


def _escribir(carpeta: Path, datos: Any) -> Path:
    ruta = carpeta / NOMBRE_ARCHIVO
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def _grupo_de(datos: dict[str, Any], identificador: str) -> dict[str, Any]:
    for grupo in datos["grupos"]:
        if grupo["id"] == identificador:
            return grupo
    raise AssertionError(f"el archivo real no trae {identificador}")


# --------------------------------------------------------------------------- #
# El archivo del repositorio es el que el código carga
# --------------------------------------------------------------------------- #


def prueba_el_archivo_que_carga_el_codigo_es_el_del_repositorio() -> None:
    assert RUTA_CATALOGO.is_file(), f"no existe {RUTA_CATALOGO}"
    assert RUTA_CATALOGO.parent == RAIZ / "datos" / "catalogo"
    assert RUTA_CATALOGO.name == NOMBRE_ARCHIVO
    assert cargar().ruta == RUTA_CATALOGO


def prueba_solo_hay_un_archivo_de_catalogo() -> None:
    """Si aparece un segundo `grupos*.json`, uno de los dos deja de ser la
    fuente única y la decisión hay que volverla a tomar (persistencia v2)."""
    candidatos = sorted(p.name for p in RUTA_CATALOGO.parent.glob(PATRON_ARCHIVO))

    assert candidatos == [NOMBRE_ARCHIVO], (
        f"el catálogo debe ser un solo archivo; se encontraron: {candidatos}"
    )


def prueba_el_catalogo_declara_su_version() -> None:
    catalogo = cargar()
    assert catalogo.version, "el catálogo debe declarar su «version»"
    assert isinstance(catalogo.version, str)


# --------------------------------------------------------------------------- #
# Cobertura: los 7 grupos, en orden, sin faltarles región ni rasgo
# --------------------------------------------------------------------------- #


def prueba_estan_los_siete_grupos() -> None:
    catalogo = cargar()

    assert len(catalogo.grupos) == GRUPOS_ESPERADOS == 7, (
        "RF-04 pide siete grupos funcionales; el catálogo trae "
        f"{len(catalogo.grupos)}"
    )
    assert tuple(g.id for g in catalogo.grupos) == ORDEN_CANONICO_DEL_PLAN


def prueba_el_orden_canonico_es_el_del_plan() -> None:
    """El orden del vector de etiquetas de T-16. Si se reordena, el modelo
    acierta con las etiquetas cruzadas y nadie lo nota."""
    catalogo = cargar()

    assert catalogo.orden_canonico == ORDEN_CANONICO_DEL_PLAN
    assert tuple(g.id for g in catalogo.grupos) == catalogo.orden_canonico
    for posicion, identificador in enumerate(ORDEN_CANONICO_DEL_PLAN):
        assert catalogo.indice_de(identificador) == posicion


def prueba_ningun_grupo_queda_sin_region_ni_sin_rasgo() -> None:
    catalogo = cargar()

    for grupo in catalogo.grupos:
        minimo, maximo = grupo.region_cm1
        assert minimo > 0 and maximo > 0, f"{grupo.id}: región no positiva"
        assert minimo < maximo, f"{grupo.id}: región invertida o de ancho cero"

        assert grupo.nombre.strip(), f"{grupo.id}: sin nombre"
        assert grupo.enlace_vibracion.strip(), f"{grupo.id}: sin enlace/vibración"
        assert grupo.pista.strip(), f"{grupo.id}: sin pista"
        assert grupo.intensidad.strip() or (grupo.forma or "").strip(), (
            f"{grupo.id}: sin ningún rasgo (ni intensidad ni forma)"
        )


def prueba_los_rangos_son_los_de_la_seccion_4_del_plan() -> None:
    catalogo = cargar()

    for identificador, (region, acompanantes) in ESPERADO.items():
        grupo = catalogo.por_id(identificador)
        assert grupo.region_cm1 == region, (
            f"{identificador}: la región del catálogo no es la del plan"
        )
        reales = tuple(
            (r.rango[0], r.rango[1], r.rol) for r in grupo.regiones_acompanantes
        )
        assert reales == acompanantes, (
            f"{identificador}: las regiones acompañantes no son las del plan"
        )


# --------------------------------------------------------------------------- #
# Las regiones acompañantes son el desempate de R-2, no decoración
# --------------------------------------------------------------------------- #


def prueba_gf06_exige_su_ch_de_alqueno() -> None:
    """R-2: GF-06 necesita su =C–H acompañante."""
    acompanantes = cargar().por_id("GF-06").regiones_acompanantes

    assert len(acompanantes) == 1
    assert acompanantes[0].rol == "confirmacion"
    assert acompanantes[0].rango == (3020.0, 3100.0)


def prueba_gf07_exige_el_par_mas_el_ch_aromatico() -> None:
    """R-2: GF-07 necesita el par de bandas **más** el C–H aromático."""
    grupo = cargar().por_id("GF-07")

    par = [r.rango for r in grupo.acompanantes_por_rol("par")]
    confirmacion = [r.rango for r in grupo.acompanantes_por_rol("confirmacion")]

    assert par == [(1600.0, 1600.0), (1500.0, 1500.0)], (
        "GF-07 necesita las dos bandas del par (~1600 y ~1500)"
    )
    assert confirmacion == [(3000.0, 3100.0)], (
        "GF-07 necesita además el C–H aromático"
    )


def prueba_el_enlace_vibracion_de_gf07_es_el_de_mod06() -> None:
    """D-20: el plan omitía esta columna; el valor viene de MOD-06 §4."""
    assert cargar().por_id("GF-07").enlace_vibracion == ENLACE_DE_GF07


def prueba_un_par_son_exactamente_dos_bandas() -> None:
    """D-20.1: la condición que el equipo añadió al aprobar la decisión 1."""
    for grupo in cargar().grupos:
        pares = grupo.acompanantes_por_rol("par")
        assert len(pares) in (0, BANDAS_DEL_PAR), (
            f"{grupo.id} declara {len(pares)} banda(s) con rol «par»"
        )


@pytest.mark.parametrize("cuantas", [1, 3])
def prueba_un_par_incompleto_o_de_mas_no_carga(tmp_path: Path, cuantas: int) -> None:
    """El caso que motivó la condición: si un dedazo deja una sola banda del par,
    R-2 se debilita en silencio y hoy nada lo detectaría. Debe fallar al cargar.
    """
    datos = _datos_del_repositorio()
    grupo = _grupo_de(datos, "GF-07")
    par = [r for r in grupo["regiones_acompanantes"] if r["rol"] == "par"]
    resto = [r for r in grupo["regiones_acompanantes"] if r["rol"] != "par"]
    grupo["regiones_acompanantes"] = (par * 3)[:cuantas] + resto

    with pytest.raises(ErrorDeCatalogo, match="par"):
        cargar(_escribir(tmp_path, datos))


def prueba_gf01_trae_la_banda_de_acidos() -> None:
    acompanantes = cargar().por_id("GF-01").regiones_acompanantes

    assert len(acompanantes) == 1
    assert acompanantes[0].rango == (2500.0, 3300.0)
    assert acompanantes[0].rol == "indicio", (
        "la banda de ácidos señala un subtipo; no condiciona la detección de O–H"
    )


def prueba_los_roles_estan_en_el_vocabulario_cerrado() -> None:
    """`rol` es un valor de una lista cerrada: T-15 lo lee sin interpretar texto
    libre."""
    for grupo in cargar().grupos:
        for region in grupo.regiones_acompanantes:
            assert region.rol in ROLES_VALIDOS, (
                f"{grupo.id}: rol desconocido {region.rol!r}; "
                f"los válidos son {sorted(ROLES_VALIDOS)}"
            )


def prueba_los_grupos_sin_banda_acompanante_no_inventan_ninguna() -> None:
    """La sección 4 del plan solo le da acompañante a GF-01, GF-06 y GF-07."""
    for grupo in cargar().grupos:
        if grupo.id in {"GF-01", "GF-06", "GF-07"}:
            assert grupo.regiones_acompanantes
        else:
            assert grupo.regiones_acompanantes == (), (
                f"{grupo.id}: el plan no le da región acompañante"
            )


# --------------------------------------------------------------------------- #
# Subtipos: solo GF-05, y son informativos
# --------------------------------------------------------------------------- #


def prueba_solo_gf05_trae_subtipos() -> None:
    for grupo in cargar().grupos:
        if grupo.id == "GF-05":
            assert grupo.subtipos, "GF-05 lleva los subtipos de C=O"
        else:
            assert grupo.subtipos == (), (
                f"{grupo.id}: el plan solo le da subtipos a GF-05"
            )


def prueba_los_subtipos_de_gf05_son_los_del_plan() -> None:
    subtipos = cargar().por_id("GF-05").subtipos

    assert tuple((s.nombre, s.region_cm1) for s in subtipos) == SUBTIPOS_DE_GF05


# --------------------------------------------------------------------------- #
# T-14 no escribe textos de explicación (son T-20, incremento 4)
# --------------------------------------------------------------------------- #


def prueba_las_pistas_son_pistas_y_no_explicaciones() -> None:
    """Frontera de T-14: el catálogo no trae la capa educativa.

    Una pista es una frase corta que ayuda a desempatar; una explicación
    educativa es de T-20. El límite operativo es la longitud.
    """
    for grupo in cargar().grupos:
        assert len(grupo.pista) <= 200, (
            f"{grupo.id}: la pista parece un texto de explicación "
            f"({len(grupo.pista)} caracteres); los textos son T-20"
        )


def _llaves_de(valor: Any) -> set[str]:
    """Todas las llaves del JSON, a cualquier profundidad."""
    if isinstance(valor, dict):
        llaves = set(valor)
        for interior in valor.values():
            llaves |= _llaves_de(interior)
        return llaves
    if isinstance(valor, list):
        llaves: set[str] = set()
        for interior in valor:
            llaves |= _llaves_de(interior)
        return llaves
    return set()


def prueba_el_catalogo_no_trae_llaves_de_explicacion() -> None:
    """Ni plantillas ni textos educativos: eso llega en el incremento 4.

    Se miran las **llaves**, no el texto del archivo: una nota que diga «esto es
    para las explicaciones del incremento 4» es documentación legítima; un campo
    llamado `explicacion` sería T-20 metido aquí.
    """
    prohibidas = ["explicacion", "explicación", "plantilla", "educativo", "texto"]

    for llave in _llaves_de(_datos_del_repositorio()):
        for prohibida in prohibidas:
            assert prohibida not in llave.lower(), (
                f"la llave «{llave}» no va en el catálogo: los textos son T-20 "
                "(incremento 4)"
            )


# --------------------------------------------------------------------------- #
# Catálogo incompleto o corrupto → error claro, no arranca en silencio
# --------------------------------------------------------------------------- #


def prueba_el_archivo_no_existe(tmp_path: Path) -> None:
    with pytest.raises(ErrorDeCatalogo, match="no se encontró"):
        cargar(tmp_path / NOMBRE_ARCHIVO)


def prueba_el_archivo_no_es_json_valido(tmp_path: Path) -> None:
    ruta = tmp_path / NOMBRE_ARCHIVO
    ruta.write_text("{ esto no es json", encoding="utf-8")

    with pytest.raises(ErrorDeCatalogo, match="no es JSON válido"):
        cargar(ruta)


def prueba_el_json_no_es_un_objeto(tmp_path: Path) -> None:
    with pytest.raises(ErrorDeCatalogo, match="objeto JSON"):
        cargar(_escribir(tmp_path, ["GF-01"]))


@pytest.mark.parametrize("llave", ["version", "orden_canonico", "grupos"])
def prueba_falta_una_llave_de_la_raiz(tmp_path: Path, llave: str) -> None:
    datos = _datos_del_repositorio()
    del datos[llave]

    with pytest.raises(ErrorDeCatalogo) as excepcion:
        cargar(_escribir(tmp_path, datos))

    mensaje = str(excepcion.value)
    assert llave in mensaje
    assert "UT-01" in mensaje


def prueba_falta_un_grupo_completo(tmp_path: Path) -> None:
    """El caso que más importa: que el catálogo llegue con seis grupos."""
    datos = _datos_del_repositorio()
    datos["grupos"] = [g for g in datos["grupos"] if g["id"] != "GF-04"]

    with pytest.raises(ErrorDeCatalogo) as excepcion:
        cargar(_escribir(tmp_path, datos))

    assert "GF-04" in str(excepcion.value)


def prueba_falta_el_ultimo_grupo(tmp_path: Path) -> None:
    """Quitar el último no rompe la numeración consecutiva: se detecta por el
    conteo contra el orden canónico."""
    datos = _datos_del_repositorio()
    datos["grupos"] = datos["grupos"][:-1]

    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


def prueba_sobra_un_grupo(tmp_path: Path) -> None:
    datos = _datos_del_repositorio()
    extra = copy.deepcopy(datos["grupos"][0])
    extra["id"] = "GF-08"
    datos["grupos"].append(extra)

    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


def prueba_los_grupos_vienen_desordenados(tmp_path: Path) -> None:
    """El orden del vector de etiquetas de T-16 no se negocia."""
    datos = _datos_del_repositorio()
    datos["grupos"][0], datos["grupos"][1] = datos["grupos"][1], datos["grupos"][0]

    with pytest.raises(ErrorDeCatalogo, match="orden"):
        cargar(_escribir(tmp_path, datos))


def prueba_el_orden_canonico_no_coincide_con_los_grupos(tmp_path: Path) -> None:
    datos = _datos_del_repositorio()
    datos["orden_canonico"] = list(reversed(datos["orden_canonico"]))

    with pytest.raises(ErrorDeCatalogo, match="orden"):
        cargar(_escribir(tmp_path, datos))


def prueba_un_identificador_repetido(tmp_path: Path) -> None:
    datos = _datos_del_repositorio()
    datos["grupos"][1]["id"] = datos["grupos"][0]["id"]

    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


@pytest.mark.parametrize(
    "llave",
    ["nombre", "enlace_vibracion", "region_cm1", "intensidad", "pista"],
)
def prueba_a_un_grupo_le_falta_un_campo_obligatorio(
    tmp_path: Path, llave: str
) -> None:
    datos = _datos_del_repositorio()
    del _grupo_de(datos, "GF-05")[llave]

    with pytest.raises(ErrorDeCatalogo) as excepcion:
        cargar(_escribir(tmp_path, datos))

    mensaje = str(excepcion.value)
    assert llave in mensaje
    assert "GF-05" in mensaje


@pytest.mark.parametrize("llave", ["regiones_acompanantes", "subtipos", "forma"])
def prueba_a_un_grupo_le_falta_un_campo_que_puede_ir_vacio(
    tmp_path: Path, llave: str
) -> None:
    """Vacío sí; ausente no. Una llave que falta es un catálogo a medio escribir,
    y quien lo lea no debe tener que adivinar si el dato no existe o se perdió."""
    datos = _datos_del_repositorio()
    del _grupo_de(datos, "GF-02")[llave]

    with pytest.raises(ErrorDeCatalogo) as excepcion:
        cargar(_escribir(tmp_path, datos))

    assert llave in str(excepcion.value)


@pytest.mark.parametrize(
    ("llave", "valor"),
    [
        ("nombre", ""),
        ("nombre", "   "),
        ("pista", ""),
        ("intensidad", ""),
        ("enlace_vibracion", ""),
        ("region_cm1", [1670]),
        ("region_cm1", [1670, 1780, 1800]),
        ("region_cm1", [1780, 1670]),
        ("region_cm1", [1670, 1670]),
        ("region_cm1", [-1670, 1780]),
        ("region_cm1", ["1670", "1780"]),
        ("region_cm1", [True, 1780]),
        ("forma", ""),
        ("forma", 7),
        ("regiones_acompanantes", {}),
        ("subtipos", "ninguno"),
        ("id", "GF-99"),
        ("id", ""),
    ],
)
def prueba_un_valor_incoherente_y_no_arranca(
    tmp_path: Path, llave: str, valor: Any
) -> None:
    datos = _datos_del_repositorio()
    _grupo_de(datos, "GF-05")[llave] = valor

    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


@pytest.mark.parametrize(
    "acompanante",
    [
        {"rango": [3020, 3100]},
        {"rol": "confirmacion"},
        {"rango": [3020, 3100], "rol": "decoracion"},
        {"rango": [3020, 3100], "rol": ""},
        {"rango": [3100, 3020], "rol": "confirmacion"},
        {"rango": [3020], "rol": "confirmacion"},
        {"rango": "3020-3100", "rol": "confirmacion"},
        "3020-3100",
    ],
)
def prueba_una_region_acompanante_incoherente(
    tmp_path: Path, acompanante: Any
) -> None:
    datos = _datos_del_repositorio()
    _grupo_de(datos, "GF-06")["regiones_acompanantes"] = [acompanante]

    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


@pytest.mark.parametrize(
    "subtipo",
    [
        {"nombre": "cetona"},
        {"region_cm1": [1715, 1715]},
        {"nombre": "", "region_cm1": [1715, 1715]},
        {"nombre": "cetona", "region_cm1": [1750, 1735]},
        {"nombre": "cetona", "region_cm1": [0, 1715]},
        "cetona",
    ],
)
def prueba_un_subtipo_incoherente(tmp_path: Path, subtipo: Any) -> None:
    datos = _datos_del_repositorio()
    _grupo_de(datos, "GF-05")["subtipos"] = [subtipo]

    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


def prueba_el_mensaje_de_error_dice_que_hacer(tmp_path: Path) -> None:
    """No es un mensaje para el usuario final, pero quien arranque el backend
    tiene que saber qué archivo mirar y qué hacer."""
    datos = _datos_del_repositorio()
    del datos["grupos"]

    with pytest.raises(ErrorDeCatalogo) as excepcion:
        cargar(_escribir(tmp_path, datos))

    mensaje = str(excepcion.value)
    assert "UT-01" in mensaje
    assert NOMBRE_ARCHIVO in mensaje
    assert "catálogo" in mensaje.lower()


# --------------------------------------------------------------------------- #
# Solo lectura y carga única
# --------------------------------------------------------------------------- #


def prueba_el_catalogo_es_de_solo_lectura() -> None:
    catalogo = cargar()
    grupo = catalogo.por_id("GF-05")

    with pytest.raises(dataclasses.FrozenInstanceError):
        grupo.region_cm1 = (0.0, 1.0)  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        catalogo.version = "0"  # type: ignore[misc]

    assert isinstance(catalogo.grupos, tuple)
    assert isinstance(grupo.region_cm1, tuple)
    assert isinstance(grupo.regiones_acompanantes, tuple)
    assert isinstance(grupo.subtipos, tuple)


def prueba_obtener_carga_una_vez_y_recargar_la_reemplaza(tmp_path: Path) -> None:
    primero = obtener()
    assert obtener() is primero, "UT-01 debe cargar el catálogo una sola vez"

    datos = _datos_del_repositorio()
    datos["version"] = "9.9.9-de-prueba"
    otro = recargar(_escribir(tmp_path, datos))

    assert otro.version == "9.9.9-de-prueba"
    assert obtener() is otro

    restaurado = recargar()
    assert restaurado.ruta == RUTA_CATALOGO
    assert restaurado.version == primero.version


def prueba_por_id_rechaza_un_grupo_desconocido() -> None:
    with pytest.raises(ErrorDeCatalogo, match="GF-42"):
        cargar().por_id("GF-42")

    with pytest.raises(ErrorDeCatalogo, match="GF-42"):
        cargar().indice_de("GF-42")


# --------------------------------------------------------------------------- #
# Sin red
# --------------------------------------------------------------------------- #


def prueba_el_lector_no_sale_a_la_red() -> None:
    """UT-01 lee un archivo local del repositorio y nada más."""
    carpeta = RAIZ / "backend" / "utilerias" / "catalogo"
    prohibidos = ["socket", "urllib", "http.client", "requests", "httpx", "urlopen"]

    for archivo in sorted(carpeta.rglob("*.py")):
        texto = archivo.read_text(encoding="utf-8")
        for nombre in prohibidos:
            assert nombre not in texto, (
                f"{archivo.name} menciona «{nombre}»: UT-01 no sale a la red"
            )


# --------------------------------------------------------------------------- #
# No-«hardcodeo»: ningún número de región fuera del catálogo
# --------------------------------------------------------------------------- #

#: Todos los números de la sección 4 del plan, más los de los subtipos de C=O.
#: Si uno de estos aparece en el código de la aplicación, alguien dejó de pedirle
#: los datos a UT-01 (regla 2 de la sección 3 del plan del incremento 3).
VALORES_PROHIBIDOS = [
    r"\b3200\b",
    r"\b3550\b",
    r"\b2500\b",
    r"\b3300\b",
    r"\b3500\b",
    r"\b2850\b",
    r"\b2960\b",
    r"\b2210\b",
    r"\b2260\b",
    r"\b1670\b",
    r"\b1780\b",
    r"\b1620\b",
    r"\b1680\b",
    r"\b3020\b",
    r"\b3100\b",
    r"\b1450\b",
    r"\b1600\b",
    r"\b1500\b",
    r"\b1715\b",
    r"\b1720\b",
    r"\b1735\b",
    r"\b1740\b",
    r"\b1750\b",
    r"\b1690\b",
    r"\b1760\b",
    r"\b1630\b",
    r"\b1700\b",
]

#: El código de la aplicación. `herramientas/` queda fuera a propósito: son
#: utilidades de desarrollo (capturas, descargas) con milisegundos y píxeles que
#: coinciden por casualidad con números de onda.
CARPETAS_REVISADAS = [
    (RAIZ / "backend", "*.py"),
    (RAIZ / "motor_identificacion", "*.py"),
    (RAIZ / "frontend" / "interfaz", "*.js"),
    (RAIZ / "frontend" / "servicios", "*.js"),
    (RAIZ / "frontend" / "visor-espectro", "*.js"),
]

#: Exentas: las pruebas (que sí repiten los números para verificarlos) y la
#: carpeta del catálogo.
EXENTAS = {
    RAIZ / "backend" / "pruebas",
    RAIZ / "frontend" / "pruebas",
    RAIZ / "datos" / "catalogo",
}


def prueba_ningun_numero_de_region_aparece_fuera_del_catalogo() -> None:
    # T-15a renombró la carpeta de MOD-06 (D-7). Si la vieja con guion vuelve a
    # aparecer, el recorrido de arriba dejaría de mirar el motor **sin avisar**,
    # y esta prueba pasaría en verde vigilando una carpeta vacía.
    assert not (RAIZ / "motor-identificacion").exists(), (
        "volvió la carpeta con guion: el renombre de D-7 está a medias y esta "
        "prueba estaría revisando la carpeta equivocada"
    )

    hallazgos: list[str] = []

    for carpeta, patron in CARPETAS_REVISADAS:
        if not carpeta.is_dir():
            continue
        for archivo in sorted(carpeta.rglob(patron)):
            if any(exenta in archivo.parents for exenta in EXENTAS):
                continue
            texto = archivo.read_text(encoding="utf-8")
            for numero, linea in enumerate(texto.splitlines(), start=1):
                if any(re.search(p, linea) for p in VALORES_PROHIBIDOS):
                    relativa = archivo.relative_to(RAIZ).as_posix()
                    hallazgos.append(f"{relativa}:{numero}: {linea.strip()}")

    assert not hallazgos, (
        "estos números de región deben pedirse a UT-01, no escribirse en el "
        "código:\n" + "\n".join(hallazgos)
    )


def prueba_el_catalogo_es_el_unico_json_con_los_rangos() -> None:
    """UT-03 guarda parámetros; UT-01 guarda los rangos de los grupos. Ninguno
    de los dos repite lo del otro."""
    from backend.utilerias.configuracion import RUTA_PARAMETROS

    texto = RUTA_PARAMETROS.read_text(encoding="utf-8")
    repetidos = [p for p in VALORES_PROHIBIDOS if re.search(p, texto)]

    assert not repetidos, (
        f"el archivo de parámetros de UT-03 repite rangos del catálogo: {repetidos}"
    )
