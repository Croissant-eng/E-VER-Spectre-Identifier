# D-21 · Medición de la línea base y de la fuerza de banda (T-15c)

Solo medición: el puntaje no cambió. Las 56 celdas (score, pico, ancho y ajustes)
son idénticas byte a byte antes y después de mover las tres constantes a UT-03.
**Nada de lo que se propone aquí está aplicado.**

```bash
python -m herramientas.medir_fuerza
```

La tabla de verdad es la de D-21. Los espectros pasan por el MOD-04 real.

## 1 · Causa B: el margen de línea base

**La ventana del motor no es ±200.** `_candidatos` pide los picos en la región
ya ensanchada por su escala y el margen se suma encima: para GF-01 son
350 + 200 = **±550**. Solo `cima_en` usa la ventana de la calibración de D-20.

| Margen | Ventana real GF-01 | Á. benzoico (sí) | 1-butanol (sí) | Ciclohexano (no) | Acetona (no) | Acetonitrilo (no) | Aciertos /56 |
|---|---|---|---|---|---|---|---|
| 50 | ±400 | 0.262 | 0.990 | 0.758 | 0.678 | 0.917 | 44 |
| 100 | ±450 | 0.262 | 0.990 | 0.811 | 0.678 | 0.917 | 44 |
| **200** | ±550 | 0.262 | 0.990 | 0.841 | 0.744 | 0.920 | **45** |
| 400 | ±750 | 0.262 | 0.990 | 0.892 | 0.750 | 0.929 | 44 |
| 600 | ±950 | 0.262 | 0.990 | 0.907 | 0.750 | 0.929 | 44 |
| 800 | ±1150 | 0.544 | 0.990 | 0.920 | 0.750 | 0.953 | 43 |
| 1000 | ±1350 | 0.555 | 0.990 | 0.920 | 0.750 | 0.956 | 43 |
| 1500 | ±1850 | 0.609 | 0.990 | 0.920 | 0.750 | 0.956 | 44 |
| 3600 | todo | 0.609 | 0.990 | 0.920 | 0.888 | 0.956 | 44 |

La base es el mínimo de la ventana: al ensancharla solo puede bajar, y sube a
verdaderos y falsos por igual. En el ácido benzoico el mínimo cae en 3419 cm⁻¹
(base 0.036), **dentro** de la región: esa parte de la hipótesis se cumple. Pero
aun con base 0 el levantamiento máximo posible es 0.045.

**El O–H del ácido benzoico no está en 3200–3550.** Media de intensidad:

| Tramo (cm⁻¹) | Á. benzoico | 1-butanol |
|---|---|---|
| 3400–3550 | 0.039 | 0.671 |
| 3200–3400 | 0.049 | 0.906 |
| 3100–3200 | 0.108 | 0.600 |
| 2500–2850 | 0.176 | 0.222 |

Escalar con el ancho de la región (k × 350) tampoco separa:

| k | Á. benzoico | Ciclohexano | Acetonitrilo |
|---|---|---|---|
| 1 | 0.262 | 0.892 | 0.929 |
| 2 | 0.448 | 0.920 | 0.952 |
| 3 | 0.555 | 0.920 | 0.956 |

El catálogo no declara el ancho de una banda, solo el de su región.

**El margen sí es definición de R-4.** Ancho al 80 % del ácido benzoico en la zona
de GF-03 (corte 160): 74.4 con margen 50, 88.2 con 100, **216.5 con 200**, 235.8
con 400, 244.6 con 1000. Con margen ≤ 100 R-4 dejaría pasar el hombro.

**Dónde se separa el O–H de ácido:** mediana de la intensidad en 2500–3300 (la
región `indicio` de GF-01). Presentes: 1-butanol 0.399, á. benzoico 0.171.
Ausentes: de 0.0055 a 0.029 (acetonitrilo). Separa ×5.9, con n = 2 presentes.

## 2 · Causa A: la fuerza

Altura = máximo en la región, escala 0–1. **`*` = presente según D-21.**

| Compuesto | GF-01 | GF-02 | GF-03 | GF-04 | GF-05 | GF-06 | GF-07 |
|---|---|---|---|---|---|---|---|
| ciclohexano | 0.0180 | 0.0180 | 1.0000* | 0.0043 | 0.0068 | 0.0078 | 0.2143 |
| acetona | 0.0205 | 0.0205 | 0.0298* | 0.0072 | 1.0000* | 0.0360 | 0.0688 |
| ácido benzoico | 0.0748* | 0.0452 | 0.2318 | 0.0476 | 1.0000* | 0.6734 | 0.3514* |
| tolueno | 0.0073 | 0.0073 | 0.3227* | 0.0021 | 0.0226 | 0.0533 | 0.5678* |
| ciclohexeno | 0.0213 | 0.0205 | 1.0000* | 0.0082 | 0.0250 | 0.0838* | 0.1798 |
| acetonitrilo | 0.0524 | 0.0164 | 0.1760* | 0.4855* | 0.0082 | 0.0192 | 1.0000 |
| anilina | 0.1887 | 0.1887* | 0.0085 | 0.0034 | 0.0300 | 0.5348 | 1.0000* |
| 1-butanol | 0.9473* | 0.9473 | 1.0000* | 0.0103 | 0.0417 | 0.0591 | 0.6774 |

| Clase | Presentes | Ausentes | ¿Separa? |
|---|---|---|---|
| fuerte | 0.0748–1.0000 (n=4) | 0.0068–0.1887 (n=12) | **No** |
| media | 0.0298–1.0000 (n=11) | 0.0021–1.0000 (n=21) | **No** |
| media/débil | 0.0838 (**n=1**) | 0.0078–0.6734 (n=7) | **No** |

Ninguna clase separa con la altura. Con prominencia topográfica **en la región**
separa solo la débil: 0.0766 contra un máximo ausente de 0.0112 (×6.8, n=1).
El 0.0748 del ácido benzoico es la ladera en 3201 cm⁻¹, no una banda.

Un piso no tiene que separarlo todo, solo quitar lo que hoy pasa de 0.60.
Intervalo en el que cada piso quita los mismos falsos sin perder presentes:

| Clase | Intervalo | Media geométrica | Quita | No quita |
|---|---|---|---|---|
| fuerte, altura | (0.0524, 0.0748] | 0.063 | 5 de 6 | anilina/GF-01 (0.1887) |
| media, altura | (0.0205, 0.0298] | 0.025 | 1 de 1 | — |
| débil, altura | (0.0533, 0.0838] | — | 1 de 3 | benzoico y anilina/GF-06 |
| débil, prominencia en región | (0.0000, 0.0766] | 0.029 (contra 0.0112) | 3 de 3 | — |

Simulación **fuera del motor** (score actual y además fuerza ≥ piso):

| Pisos | Aciertos /56 | Conjuntos /8 |
|---|---|---|
| sin pisos (hoy) | 45 | 1 |
| altura 0.063 / 0.025 / 0.070 | 52 | 6 |
| altura 0.063 / 0.025 + prominencia 0.029 en la débil | 54 | 6 |

Los pisos salen de los mismos 8 espectros con que se evalúan: son cifras
optimistas, no una validación. El piso débil descansa en **un dato**
(ciclohexeno) y el medio en un solo contraste, dentro de la acetona.

## 3 · Lo que la medición descubrió además

- **Causa C.** Los tres GF-06 falsos ganan con un pico **fuera** de 1620–1680:
  benzoico 1684 (su C=O), tolueno 1614 y anilina 1618 (el anillo). La búsqueda se
  extiende un ancho de región a cada lado. Igual ciclohexeno/GF-05, que gana con
  el C=C en 1656. No se puede prohibir sin más: el GF-03 **verdadero** de la
  acetona gana con 2969, 9 cm⁻¹ fuera.
- **Anilina/GF-01.** Gana un bache en 3226 cuyo ancho (301) pasa R-1 porque se
  funde con el N–H vecino. El N–H real mide 74. Ningún piso lo arregla.
- **R-4 no llega a aplicarse al 1-butanol.** El detector de envolvente toma el
  punto más alto de 2500–3300, que es su C–H (ancho menor que 175), y concluye
  que no hay envolvente. Su GF-03 = 0.99 no prueba el corte de 160.
- **El score no baja con la debilidad** en un espectro de una sola banda: alturas
  1.0, 0.1 y 0.001 dan las tres 1.0.
