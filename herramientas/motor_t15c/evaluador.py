# Congelado en T-15c: ver herramientas/motor_t15c/__init__.py. No editar.
"""MOD-06 · vía de reglas · puntaje por grupo (T-15b).

Qué hace: por cada uno de los siete grupos del catálogo, busca su banda en el
espectro normalizado y devuelve un **score en [0, 1]** con su región y, si la
encontró, la posición del pico. Aplica las cuatro reglas de desempate de la
sección 6 del plan.

Qué **no** hace, a propósito: no decide si un grupo «está» (el umbral del 60 %
es de T-17), no ordena la lista (T-18), no redacta nada (T-20) y no sabe que
existe un modelo (T-16).

## Cómo se forma el score

    score = f_posicion × f_forma × f_agudeza × min(evidencias requeridas)

- **f_posicion** cae con la distancia al rango, y la escala con la que cae sale
  de la propia región del catálogo (o de la tolerancia de UT-03, para las
  bandas de rango puntual). No hay ninguna distancia escrita aquí.
- **f_forma** es R-1: compara el ancho medido con lo que el catálogo declara en
  `forma`, contra el corte de UT-03.
- **f_agudeza** es R-4.
- **las evidencias requeridas** son la de la banda principal más las de cada
  región acompañante con rol `confirmacion` o `par`, que es R-2. Se combinan
  con un **mínimo**, no con un producto: el score lo manda el eslabón más
  débil de la cadena, y así tres evidencias buenas no se castigan entre ellas.

## Las reglas nunca excluyen

Las cuatro son **ajuste de score**. Son etiquetas múltiples: un espectro puede
traer O–H y N–H a la vez (CA-06.2), y cada grupo se puntúa con su propia mejor
banda candidata. Un desempate que eligiera ganador entre los dos rompería ese
criterio de aceptación. Lo que sí pasa es que, cuando falta una evidencia que
una regla **exige**, el score se va cerca de cero: el grupo sigue en la lista
con su número, pero no alcanza ningún umbral razonable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from backend.utilerias.catalogo import Catalogo, GrupoFuncional
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import Configuracion, ParametrosMotor
from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.motor_t15c.picos import (
    Pico,
    Rejilla,
)

#: Los valores de `forma` del catálogo que R-1 sabe interpretar. El desempate de
#: R-1 es «por ancho de banda, el rasgo que el propio catálogo usa», así que la
#: regla se activa desde el dato y no desde una lista de IDs escrita aquí. Una
#: prueba comprueba que GF-01 siga declarándose «ancha» y GF-02 «angosta»: si
#: alguien cambia esas palabras en el catálogo, R-1 dejaría de aplicarse y hay
#: que enterarse por una prueba roja, no por un resultado raro.
FORMA_ANCHA = "ancha"
FORMA_ANGOSTA = "angosta"

#: Códigos de los ajustes que se aplicaron. Son para las pruebas y el registro
#: interno, **no** son texto para el usuario: la redacción es T-19 y T-20.
NO_EVALUABLE = "no-evaluable"
SIN_BANDA = "sin-banda"
SIN_PICO_RESUELTO = "sin-pico-resuelto"
R1_ANCHO_NO_ESPERADO = "R-1:ancho-no-esperado"
R2_FALTA_CONFIRMACION = "R-2:falta-confirmacion"
R2_FALTA_PAR = "R-2:falta-par"
R4_HOMBRO_ANCHO = "R-4:hombro-ancho"
R4_PICO_AGUDO = "R-4:pico-agudo"


class ErrorDelMotor(Exception):
    """El motor no puede evaluar con lo que recibió.

    Es un fallo interno (CA-05.4), no un rechazo de negocio: el usuario ve el
    mensaje genérico de UT-02 y nunca este detalle.
    """


@runtime_checkable
class EspectroEntrada(Protocol):
    """Lo único que la vía de reglas necesita del contrato MOD-04 → MOD-06.

    Se declara como protocolo y no se importa el tipo de MOD-04 a propósito:
    así el motor no depende del procesador, solo de la forma de los datos. Es
    la frontera de la zona aislada, escrita en el código.
    """

    eje_cm1: tuple[float, ...]
    intensidad: tuple[float, ...]
    rango_medido_cm1: tuple[float, float]


@dataclass(frozen=True)
class Puntaje:
    """Lo que la vía de reglas entrega por cada grupo."""

    grupo: str
    score: float
    region_cm1: tuple[float, float]
    #: Posición del pico, o `None` cuando la banda no tiene un máximo resuelto
    #: dentro de la región. El contrato lo prevé: un grupo puede puntuar sin
    #: posición exacta de pico (CA-06.3).
    pico_cm1: float | None
    #: `False` cuando la región del grupo cae fuera del tramo medido. No es lo
    #: mismo que «ausente», y la diferencia importa en el incremento 4.
    evaluable: bool
    ancho_cm1: float | None
    ajustes: tuple[str, ...]


@dataclass(frozen=True)
class ResultadoReglas:
    """Los siete puntajes, en el orden canónico de UT-01."""

    puntajes: tuple[Puntaje, ...]
    version_catalogo: str

    def por_id(self, grupo: str) -> Puntaje:
        for puntaje in self.puntajes:
            if puntaje.grupo == grupo:
                return puntaje
        raise ErrorDelMotor(f"la vía de reglas no puntuó «{grupo}»")

    def scores(self) -> dict[str, float]:
        return {p.grupo: p.score for p in self.puntajes}


# --------------------------------------------------------------------------- #
# Candidatos
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Candidato:
    pico: Pico | None
    resuelto: bool
    f_posicion: float
    evidencia: float
    ancho_r1: float | None
    ancho_r4: float | None


def _evidencia(
    rejilla: Rejilla,
    pico: Pico | None,
    forma: str,
    region: tuple[float, float],
) -> float:
    """Cuánta señal hay en la banda, medida **según la forma que se espera**.

    No se puede medir igual una envolvente ancha y un pico agudo, y el catálogo
    ya dice cuál es cuál:

    - Una banda que el catálogo declara **ancha** —el O–H de GF-01— se mide por
      cuánto **levanta toda su región** sobre la línea base local. Su
      prominencia topográfica es engañosamente pequeña (una envolvente de 400
      cm⁻¹ casi no tiene valles: se ve como una ladera, no como un pico), y su
      altura máxima es engañosamente grande (cualquier pico angosto que caiga
      ahí la alcanza). El promedio de la región es lo que solo una banda ancha
      de verdad consigue mover.
    - Cualquier otra se mide por su **prominencia topográfica**, que es lo que
      distingue una banda de un bache montado en la ladera de otra.

    Esto es consumir el catálogo para lo que está: el plan dice que el desempate
    se hace «por el rasgo que el propio catálogo usa».
    """
    if pico is None:
        return 0.0
    if forma.strip().lower() == FORMA_ANCHA:
        fuerza = max(rejilla.promedio_en(*region) - pico.linea_base, 0.0)
    else:
        fuerza = max(pico.prominencia, 0.0)
    divisor = fuerza + rejilla.escala_prominencia
    return 0.0 if divisor <= 0 else fuerza / divisor


def _escala(grupo_region: tuple[float, float], motor: ParametrosMotor) -> float:
    """Con qué margen se busca la banda y con qué rapidez cae el score fuera.

    Para una región normal, su propio ancho: una banda que cae a una anchura de
    distancia de su región ya no es esa banda. Para una banda de rango puntual
    —las dos del par de GF-07, que el plan escribe como «~1600» y «~1500»— la
    escala es la tolerancia de UT-03, porque un punto no tiene ancho propio.
    """
    minimo, maximo = grupo_region
    ancho = maximo - minimo
    return ancho if ancho > 0 else motor.tolerancia_banda_puntual_cm1


def _candidatos(
    rejilla: Rejilla,
    region: tuple[float, float],
    motor: ParametrosMotor,
    forma: str = "",
) -> tuple[_Candidato, ...]:
    """Las bandas que podrían ser la de esta región, con su penalización."""
    minimo, maximo = region
    escala = _escala(region, motor)
    metodo = motor.definicion_metodo

    encontrados: list[_Candidato] = []
    for pico in rejilla.picos_en(minimo - escala, maximo + escala):
        if pico.cm1 > maximo:
            distancia = pico.cm1 - maximo
        elif pico.cm1 < minimo:
            distancia = minimo - pico.cm1
        else:
            distancia = 0.0
        encontrados.append(
            _Candidato(
                pico=pico,
                resuelto=True,
                f_posicion=max(0.0, 1.0 - distancia / escala),
                evidencia=_evidencia(rejilla, pico, forma, region),
                ancho_r1=rejilla.ancho(pico, metodo.fraccion_r1).cm1,
                ancho_r4=rejilla.ancho(pico, metodo.fraccion_r4).cm1,
            )
        )

    # Sin máximo resuelto dentro de la ventana, la región puede seguir llevando
    # señal: es el hombro de una banda cuya cima quedó fuera. Puntúa, pero sin
    # posición de pico.
    if not encontrados:
        cima = rejilla.cima_en(minimo, maximo)
        if cima is not None:
            encontrados.append(
                _Candidato(
                    pico=cima,
                    resuelto=False,
                    f_posicion=1.0,
                    evidencia=_evidencia(rejilla, cima, forma, region),
                    ancho_r1=rejilla.ancho(cima, metodo.fraccion_r1).cm1,
                    ancho_r4=rejilla.ancho(cima, metodo.fraccion_r4).cm1,
                )
            )

    return tuple(encontrados)


# --------------------------------------------------------------------------- #
# Las reglas
# --------------------------------------------------------------------------- #


def _f_forma_r1(
    grupo: GrupoFuncional, candidato: _Candidato, motor: ParametrosMotor
) -> tuple[float, tuple[str, ...]]:
    """R-1 · O–H ancho contra N–H angosto, traslapados en 3300–3500.

    Ajusta, no excluye: los dos grupos se puntúan por separado y cada uno se
    queda con la banda candidata que mejor le cuadra, así que un espectro con
    O–H y N–H detecta los dos. Lo que hace la regla es que la banda ancha
    puntúe mejor como O–H y la angosta mejor como N–H.
    """
    forma = (grupo.forma or "").strip().lower()
    ancho = candidato.ancho_r1
    if ancho is None or forma not in {FORMA_ANCHA, FORMA_ANGOSTA}:
        return 1.0, ()

    corte = motor.ancho_media_altura_umbral_cm1
    if forma == FORMA_ANCHA:
        if ancho >= corte:
            return 1.0, ()
        return min(1.0, ancho / corte), (R1_ANCHO_NO_ESPERADO,)

    if ancho <= corte:
        return 1.0, ()
    return min(1.0, corte / ancho), (R1_ANCHO_NO_ESPERADO,)


def _hay_envolvente_ancha(
    rejilla: Rejilla, catalogo: Catalogo, motor: ParametrosMotor
) -> tuple[float, float] | None:
    """La región `indicio` que trae una banda ancha, si hay alguna.

    El rol `indicio` no condiciona la detección de su propio grupo —la banda de
    ácidos de GF-01 no debe penalizar a los alcoholes y fenoles, que es justo lo
    que los distingue—, pero **R-4 lo consume**: es lo que dice que estamos
    dentro de la envolvente ancha de un ácido.
    """
    for grupo in catalogo.grupos:
        for region in grupo.acompanantes_por_rol("indicio"):
            if not rejilla.contiene(*region.rango):
                continue
            cima = rejilla.cima_en(*region.rango)
            if cima is None:
                continue
            ancho = rejilla.ancho(cima, motor.definicion_metodo.fraccion_r1).cm1
            if ancho >= motor.ancho_media_altura_umbral_cm1:
                return region.rango
    return None


def _f_agudeza_r4(
    grupo: GrupoFuncional,
    candidato: _Candidato,
    envolvente: tuple[float, float] | None,
    motor: ParametrosMotor,
) -> tuple[float, tuple[str, ...]]:
    """R-4 · dentro de una envolvente ancha de O–H, exigir picos agudos.

    El caso es el ácido benzoico: su envolvente de O–H ocupa la zona del C–H
    alifático, y el ácido benzoico **no tiene** C–H alifático. Afirmarlo ahí
    exige un pico agudo y resuelto, no un hombro ancho — que es exactamente el
    rasgo que el catálogo le asigna a GF-03.

    La regla solo se aplica a un grupo cuya región cae **dentro** de la
    envolvente, y nunca al grupo dueño de la banda de ácidos: eso sale de las
    regiones del catálogo, no de una lista de IDs.

    Cuando el pico no es agudo, la exigencia **no se cumple** y la evidencia de
    ese grupo dentro de la envolvente se considera ausente. Es el mismo trato
    que R-2 le da a una banda de confirmación que falta.
    """
    if envolvente is None or candidato.ancho_r4 is None:
        return 1.0, ()

    minimo, maximo = grupo.region_cm1
    envolvente_min, envolvente_max = envolvente
    dentro = envolvente_min <= minimo and maximo <= envolvente_max
    if not dentro or grupo.acompanantes_por_rol("indicio"):
        return 1.0, ()

    if candidato.ancho_r4 <= motor.ancho_pico_agudo_max_cm1:
        return 1.0, (R4_PICO_AGUDO,)
    return 0.0, (R4_HOMBRO_ANCHO,)


def _evidencias_requeridas(
    grupo: GrupoFuncional, rejilla: Rejilla, motor: ParametrosMotor
) -> tuple[list[float], tuple[str, ...]]:
    """R-2 · las bandas acompañantes que el grupo exige.

    `confirmacion` es lo que de verdad distingue a GF-06 de GF-07: sin su =C–H
    o sin su C–H aromático, el score se va cerca de cero en vez de reportar el
    grupo. `par` son las dos bandas puntuales del anillo, cada una con la
    tolerancia de UT-03; se exigen las dos, así que manda la más débil.
    """
    evidencias: list[float] = []
    ajustes: list[str] = []

    for region in grupo.acompanantes_por_rol("confirmacion"):
        candidatos = _candidatos(rejilla, region.rango, motor)
        evidencia = max((c.evidencia for c in candidatos), default=0.0)
        evidencias.append(evidencia)
        if evidencia == 0.0:
            ajustes.append(R2_FALTA_CONFIRMACION)

    par = grupo.acompanantes_por_rol("par")
    if par:
        del_par: list[float] = []
        for region in par:
            candidatos = _candidatos(rejilla, region.rango, motor)
            del_par.append(max((c.evidencia for c in candidatos), default=0.0))
        evidencias.append(min(del_par))
        if min(del_par) == 0.0:
            ajustes.append(R2_FALTA_PAR)

    return evidencias, tuple(ajustes)


# --------------------------------------------------------------------------- #
# Evaluación
# --------------------------------------------------------------------------- #


def _puntuar_grupo(
    grupo: GrupoFuncional,
    rejilla: Rejilla,
    envolvente: tuple[float, float] | None,
    motor: ParametrosMotor,
) -> Puntaje:
    region = grupo.region_cm1

    # El relleno de ceros: fuera del tramo medido la intensidad vale 0, y ese 0
    # es «no se midió», no «no hay pico». El grupo queda no evaluable.
    if not rejilla.contiene(*region):
        return Puntaje(
            grupo=grupo.id,
            score=0.0,
            region_cm1=region,
            pico_cm1=None,
            evaluable=False,
            ancho_cm1=None,
            ajustes=(NO_EVALUABLE,),
        )

    requeridas, ajustes_r2 = _evidencias_requeridas(grupo, rejilla, motor)
    candidatos = _candidatos(rejilla, region, motor, grupo.forma or "")

    if not candidatos:
        return Puntaje(
            grupo=grupo.id,
            score=0.0,
            region_cm1=region,
            pico_cm1=None,
            evaluable=True,
            ancho_cm1=None,
            ajustes=(SIN_BANDA,) + ajustes_r2,
        )

    mejor: Puntaje | None = None
    for candidato in candidatos:
        f_forma, ajustes_r1 = _f_forma_r1(grupo, candidato, motor)
        f_agudeza, ajustes_r4 = _f_agudeza_r4(grupo, candidato, envolvente, motor)
        score = (
            candidato.f_posicion
            * f_forma
            * f_agudeza
            * min([candidato.evidencia, *requeridas])
        )
        ajustes = ajustes_r1 + ajustes_r2 + ajustes_r4
        if not candidato.resuelto:
            ajustes = (SIN_PICO_RESUELTO,) + ajustes

        puntaje = Puntaje(
            grupo=grupo.id,
            score=min(max(score, 0.0), 1.0),
            region_cm1=region,
            pico_cm1=(
                candidato.pico.cm1
                if candidato.resuelto and candidato.pico is not None
                else None
            ),
            evaluable=True,
            ancho_cm1=candidato.ancho_r1,
            ajustes=ajustes,
        )
        # Determinista con empates: solo gana quien supera estrictamente, así
        # que el primer candidato de la rejilla —el de mayor número de onda—
        # conserva el puesto.
        if mejor is None or puntaje.score > mejor.score:
            mejor = puntaje

    assert mejor is not None
    return mejor


def evaluar(
    espectro: EspectroEntrada,
    catalogo: Catalogo | None = None,
    configuracion: Configuracion | None = None,
) -> ResultadoReglas:
    """Puntúa los siete grupos del catálogo sobre un espectro ya normalizado.

    Args:
        espectro: el objeto del contrato MOD-04 → MOD-06. Solo se leen
            `eje_cm1`, `intensidad` y `rango_medido_cm1`.
        catalogo: el catálogo de UT-01. Por omisión, el del repositorio.
        configuracion: los parámetros de UT-03. Por omisión, los del
            repositorio. Los dos argumentos existen para las pruebas.

    Returns:
        Los siete puntajes en el orden canónico del catálogo.

    Raises:
        ErrorDelMotor: si faltan los parámetros del bloque `motor` de UT-03 o
            si el espectro no tiene la forma del contrato.
    """
    parametros = configuracion if configuracion is not None else obtener_configuracion()
    if parametros.motor is None:
        raise ErrorDelMotor(
            "faltan los parámetros del bloque «motor» de UT-03: la vía de "
            "reglas no puede aplicar R-1 ni R-2 ni R-4 sin sus cortes"
        )
    datos = catalogo if catalogo is not None else obtener_catalogo()

    try:
        rejilla = Rejilla(
            eje_cm1=tuple(espectro.eje_cm1),
            intensidad=tuple(espectro.intensidad),
            rango_medido_cm1=tuple(espectro.rango_medido_cm1),  # type: ignore[arg-type]
            margen_linea_base_cm1=(
                parametros.motor.definicion_metodo.margen_linea_base_cm1
            ),
        )
    except (AttributeError, TypeError, ValueError) as error:
        raise ErrorDelMotor(
            f"el espectro no cumple el contrato MOD-04 → MOD-06: {error}"
        ) from error

    envolvente = _hay_envolvente_ancha(rejilla, datos, parametros.motor)

    return ResultadoReglas(
        puntajes=tuple(
            _puntuar_grupo(grupo, rejilla, envolvente, parametros.motor)
            for grupo in datos.grupos
        ),
        version_catalogo=datos.version,
    )
