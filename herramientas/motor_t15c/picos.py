# Congelado en T-15c: ver herramientas/motor_t15c/__init__.py. No editar.
"""MOD-06 · vía de reglas · detección de picos y medición de anchos (T-15b).

Trabaja **solo con números**: el eje, el vector de intensidades y el tramo
medido. No conoce archivos, ni nombres, ni unidades.

Es la detección **propia del motor**. `herramientas/medir_anchos.py` hace
cuentas parecidas, pero es apoyo de desarrollo fuera de la aplicación y este
módulo no importa de ahí: la aplicación nunca importa de `herramientas/`.

Dos cosas que conviene tener presentes al leer:

1. **El eje baja.** Va de 4000 a 400 cm⁻¹, así que un índice que crece es un
   número de onda que baja. Por eso «hacia la izquierda» (más cm⁻¹) es
   `paso = -1`.
2. **Fuera del tramo medido la intensidad vale 0 por relleno, y ese 0 no es
   absorbancia cero.** Todo lo de aquí se queda dentro de `rango_medido_cm1`;
   quien decide qué hacer cuando una región se sale es el evaluador.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class Pico:
    """Un máximo local del espectro, con lo que hace falta para puntuarlo.

    Lleva **dos** medidas de cuánto sobresale, y no son intercambiables:

    - `linea_base` es el mínimo del vecindario de la región. La normalización de
      MOD-04 es global (el mínimo de todo el espectro va a 0), así que una banda
      que se asienta sobre señal de fondo necesita su propia base. **Es la base
      con la que se miden los anchos.**
    - `prominencia` es la prominencia topográfica: cuánto sobresale el pico por
      encima del **mayor de sus dos valles vecinos**. **Es la medida de cuánta
      señal hay**, y es la que distingue una banda de verdad de un bache
      montado sobre la ladera de otra banda. La altura sobre el mínimo de la
      región no sirve para eso: un bache diminuto en lo alto de una envolvente
      ancha queda altísimo sobre el mínimo regional.
    """

    indice: int
    cm1: float
    altura: float
    linea_base: float
    prominencia: float

    @property
    def altura_sobre_base(self) -> float:
        """Altura sobre la base regional. Es la escala de los anchos."""
        return self.altura - self.linea_base


@dataclass(frozen=True)
class Ancho:
    """El ancho de una banda a una fracción de su altura."""

    cm1: float
    #: True si la caminata se agotó sin cruzar el nivel. El ancho devuelto es
    #: entonces una cota inferior, no una medición.
    saturado: bool


class Rejilla:
    """El espectro ya normalizado, con las cuentas que la vía de reglas repite.

    Se construye una vez por análisis: el tramo medido, el ruido de fondo y los
    máximos locales se calculan aquí y se reutilizan para los siete grupos.
    """

    def __init__(
        self,
        eje_cm1: tuple[float, ...],
        intensidad: tuple[float, ...],
        rango_medido_cm1: tuple[float, float],
        margen_linea_base_cm1: float,
    ) -> None:
        if len(eje_cm1) != len(intensidad):
            raise ValueError("el eje y la intensidad deben tener el mismo largo")
        if len(eje_cm1) < 3:
            raise ValueError("hacen falta al menos tres puntos para buscar un pico")

        self.eje = eje_cm1
        self.intensidad = intensidad
        self.medido = rango_medido_cm1
        self.margen_linea_base = margen_linea_base_cm1

        medido_min, medido_max = rango_medido_cm1
        dentro = [
            i for i, onda in enumerate(eje_cm1) if medido_min <= onda <= medido_max
        ]
        if not dentro:
            raise ValueError("el tramo medido no toca la rejilla")
        self.primero, self.ultimo = min(dentro), max(dentro)

        self.ruido = self._ruido()
        self.maximos = self._maximos_locales()
        self.prominencias = {i: self._prominencia(i) for i in self.maximos}
        self.escala_prominencia = self._escala_prominencia()

    # ------------------------------------------------------------------ #
    # Cálculos de una vez
    # ------------------------------------------------------------------ #

    def _ruido(self) -> float:
        """Ruido de fondo, como la mediana del salto entre puntos vecinos.

        Es una estimación robusta: las bandas de verdad aportan saltos grandes,
        pero son una minoría de los puntos, así que la mediana se queda con el
        temblor del fondo. Un espectro sintético perfecto da 0, y entonces
        cualquier pico real tiene relación señal/ruido infinita, que es lo
        correcto.
        """
        saltos = [
            abs(self.intensidad[i + 1] - self.intensidad[i])
            for i in range(self.primero, self.ultimo)
        ]
        return median(saltos) if saltos else 0.0

    def _maximos_locales(self) -> tuple[int, ...]:
        """Los índices que son máximo local dentro del tramo medido.

        Estricto por la izquierda y permisivo por la derecha, para que una
        meseta de puntos iguales cuente **una** vez y no ninguna.
        """
        return tuple(
            i
            for i in range(self.primero + 1, self.ultimo)
            if self.intensidad[i] > self.intensidad[i - 1]
            and self.intensidad[i] >= self.intensidad[i + 1]
        )

    def _prominencia(self, indice: int) -> float:
        """Prominencia topográfica del máximo: su altura sobre el mayor valle.

        Se camina a los dos lados mientras la señal no suba por encima del
        propio pico, guardando el mínimo alcanzado. Esos son sus dos valles; el
        **mayor** de los dos es el nivel desde el que el pico de verdad
        sobresale, igual que la prominencia de una montaña se mide desde el
        collado más alto que la une a una montaña mayor.

        Es lo que separa una banda de un bache: un bache montado en la ladera
        de una envolvente ancha tiene un valle vecino casi a su misma altura, y
        su prominencia sale diminuta aunque su altura absoluta sea grande.
        """
        altura = self.intensidad[indice]

        valle_izquierdo = altura
        posicion = indice - 1
        while posicion >= self.primero and self.intensidad[posicion] <= altura:
            valle_izquierdo = min(valle_izquierdo, self.intensidad[posicion])
            posicion -= 1

        valle_derecho = altura
        posicion = indice + 1
        while posicion <= self.ultimo and self.intensidad[posicion] <= altura:
            valle_derecho = min(valle_derecho, self.intensidad[posicion])
            posicion += 1

        return altura - max(valle_izquierdo, valle_derecho)

    def _escala_prominencia(self) -> float:
        """La prominencia típica de este espectro, como vara de medir.

        Es la mediana de las prominencias de sus máximos locales, **quitando la
        banda más intensa**: la mayoría de los máximos son temblor del fondo,
        así que esa mediana describe «un bache cualquiera de este archivo». Una
        banda de verdad sobresale varias veces esa vara, y una banda débil de
        verdad —el C=C de un alqueno— también.

        Se quita la más intensa porque la vara mide el **desorden**, no la
        señal: en un espectro con una sola banda —un sintético de prueba— la
        mediana sería esa banda y se estaría comparando consigo misma. Sin
        ningún otro máximo, la vara es el ruido.

        Sale del espectro y no de un número escrito aquí: así el mismo código
        sirve con un archivo limpio y con uno cargado, sin recalibrar.
        """
        valores = sorted(p for p in self.prominencias.values() if p > 0)
        if len(valores) <= 1:
            return self.ruido
        return max(median(valores[:-1]), self.ruido)

    # ------------------------------------------------------------------ #
    # Consultas por región
    # ------------------------------------------------------------------ #

    def contiene(self, desde: float, hasta: float) -> bool:
        """¿El tramo medido cubre por completo esa región?"""
        medido_min, medido_max = self.medido
        return medido_min <= desde and hasta <= medido_max

    def indices_en(self, desde: float, hasta: float) -> tuple[int, ...]:
        """Los índices medidos cuyo número de onda cae en [desde, hasta]."""
        return tuple(
            i
            for i in range(self.primero, self.ultimo + 1)
            if desde <= self.eje[i] <= hasta
        )

    def linea_base(self, desde: float, hasta: float) -> float:
        """El mínimo del vecindario de una región, como base local.

        El vecindario es la región estirada por el margen de UT-03
        (`motor.definicion_metodo`) a cada lado y recortada al tramo medido.

        Ojo: el margen se suma a la región **que se recibe**. `_candidatos` pasa
        la región ya ensanchada por su escala, así que ahí la ventana real es
        región ± (escala + margen), más ancha que la de la calibración de D-20,
        que fue región ± margen (hallazgo de T-15c, docs/evidencia/d-21-fuerza.md).
        """
        indices = self.indices_en(
            desde - self.margen_linea_base, hasta + self.margen_linea_base
        )
        if not indices:
            indices = self.indices_en(desde, hasta)
        if not indices:
            return 0.0
        return min(self.intensidad[i] for i in indices)

    def promedio_en(self, desde: float, hasta: float) -> float:
        """La intensidad media de una región.

        Es la medida que corresponde a una banda **ancha**: una envolvente
        levanta toda su región, mientras que un pico angosto dentro de la misma
        región apenas mueve el promedio. Un máximo alto no basta para afirmar
        una banda ancha, y esto es lo que lo distingue.
        """
        indices = self.indices_en(desde, hasta)
        if not indices:
            return 0.0
        return sum(self.intensidad[i] for i in indices) / len(indices)

    def picos_en(self, desde: float, hasta: float) -> tuple[Pico, ...]:
        """Los máximos locales de una región, con su línea base ya puesta."""
        base = self.linea_base(desde, hasta)
        return tuple(
            Pico(
                indice=i,
                cm1=self.eje[i],
                altura=self.intensidad[i],
                linea_base=base,
                prominencia=self.prominencias[i],
            )
            for i in self.maximos
            if desde <= self.eje[i] <= hasta
        )

    def cima_en(self, desde: float, hasta: float) -> Pico | None:
        """El punto más alto de una región, sea máximo local o no.

        Sirve para las bandas cuya cima queda fuera de la región y dentro de
        ella solo se ve el hombro: el grupo puede puntuar, pero sin posición de
        pico (`pico_cm1` nulo, que el contrato ya prevé).
        """
        indices = self.indices_en(desde, hasta)
        if not indices:
            return None
        base = self.linea_base(desde, hasta)
        cima = max(indices, key=lambda i: self.intensidad[i])
        # Un hombro no tiene valles propios: su «prominencia» es cuánto cae la
        # señal de ahí a los bordes de la región. En una ladera monótona eso es
        # poco, y por eso un hombro puntúa bajo sin necesidad de una regla
        # aparte.
        bordes = max(self.intensidad[min(indices)], self.intensidad[max(indices)])
        return Pico(
            indice=cima,
            cm1=self.eje[cima],
            altura=self.intensidad[cima],
            linea_base=base,
            prominencia=max(self.intensidad[cima] - bordes, 0.0),
        )

    # ------------------------------------------------------------------ #
    # Ancho
    # ------------------------------------------------------------------ #

    def ancho(self, pico: Pico, fraccion: float) -> Ancho:
        """Ancho de la banda del pico a `fraccion` de su altura.

        Camina a los dos lados hasta que la señal baja del nivel y **interpola**
        el cruce: el paso de la rejilla es de unos 3.5 cm⁻¹ y sin interpolar el
        ancho vendría cuantizado en múltiplos de eso.
        """
        nivel = pico.linea_base + pico.altura_sobre_base * fraccion
        alto, saturado_alto = self._cruce(pico.indice, -1, nivel)
        bajo, saturado_bajo = self._cruce(pico.indice, +1, nivel)
        return Ancho(cm1=alto - bajo, saturado=saturado_alto or saturado_bajo)

    def _cruce(self, inicio: int, paso: int, nivel: float) -> tuple[float, bool]:
        indice = inicio
        while self.primero <= indice + paso <= self.ultimo:
            siguiente = indice + paso
            if self.intensidad[siguiente] <= nivel:
                anterior, posterior = (
                    self.intensidad[indice],
                    self.intensidad[siguiente],
                )
                amplitud = anterior - posterior
                fraccion = 0.0 if amplitud == 0 else (anterior - nivel) / amplitud
                return (
                    self.eje[indice]
                    + (self.eje[siguiente] - self.eje[indice]) * fraccion,
                    False,
                )
            indice = siguiente
        return self.eje[indice], True

    # ------------------------------------------------------------------ #
    # Evidencia
    # ------------------------------------------------------------------ #

    def evidencia(self, pico: Pico | None) -> float:
        """Cuánta señal hay en ese pico, de 0 a 1.

        `prominencia / (prominencia + vara)`, con la vara del propio espectro:
        una curva que satura en 1, escrita de la forma que no divide entre cero.
        Sin pico, 0. Pico del tamaño de un bache cualquiera, 0.5. Pico diez
        veces esa vara, 0.91.

        No hay ningún corte elegido: el único valor de referencia es «este pico
        es como los demás baches de este archivo», que sale del archivo.
        """
        if pico is None:
            return 0.0
        prominencia = max(pico.prominencia, 0.0)
        divisor = prominencia + self.escala_prominencia
        return 0.0 if divisor <= 0 else prominencia / divisor
