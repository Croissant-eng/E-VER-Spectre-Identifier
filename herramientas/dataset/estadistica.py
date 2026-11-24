"""Lo mínimo de estadística descriptiva, sin dependencias."""

from __future__ import annotations

from math import sqrt


def cuantil(valores, q: float) -> float:
    """Cuantil con interpolación lineal."""
    v = sorted(valores)
    posicion = (len(v) - 1) * q
    i = int(posicion)
    if i + 1 >= len(v):
        return float(v[-1])
    return v[i] + (v[i + 1] - v[i]) * (posicion - i)


def rangos(valores) -> list[float]:
    """Rangos con empates promediados."""
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    salida = [0.0] * len(valores)
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        for k in range(i, j + 1):
            salida[orden[k]] = (i + j) / 2 + 1
        i = j + 1
    return salida


def pearson(a, b) -> float | None:
    """Correlación lineal, o None si una variable es constante."""
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = sqrt(sum((x - ma) ** 2 for x in a))
    sb = sqrt(sum((y - mb) ** 2 for y in b))
    if sa == 0 or sb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def spearman(a, b) -> float | None:
    """Correlación de rangos, o None si una variable es constante."""
    return pearson(rangos(a), rangos(b))


def percentil_de(valor: float, poblacion) -> float:
    """Qué porcentaje de la población queda en o por debajo del valor."""
    return 100.0 * sum(p <= valor for p in poblacion) / len(poblacion)
