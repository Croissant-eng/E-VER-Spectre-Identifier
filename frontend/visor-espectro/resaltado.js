/**
 * MOD-05, el resaltado de los grupos sobre la gráfica (T-23 y T-24).
 *
 * Funciones puras: reciben los grupos que la persona eligió y devuelven las
 * anotaciones para el complemento de Chart.js (D-1) y la leyenda. No tocan el
 * DOM ni la librería, así que se prueban con node --test.
 *
 * Lo que pide cada criterio:
 *
 * CA-06.1: al elegir un grupo se resalta su región y se marca su pico.
 * CA-06.2: si se eligen varios, cada uno lleva su color y aparece en la
 *   leyenda. Las regiones de O–H y N–H se enciman, así que el relleno es
 *   transparente y la línea del pico lleva el color pleno del grupo.
 * CA-06.3: si el motor no dio la posición del pico, se resalta la región
 *   completa con borde y la leyenda lo dice, en lugar de dejar la gráfica
 *   sin marca.
 *
 * La región y el pico llegan del servidor (vía de reglas). Aquí no se
 * escribe ningún número de onda.
 */

/**
 * Un color por grupo, en el orden canónico. Son siete tonos que se distinguen
 * entre sí también con daltonismo común (paleta de Okabe e Ito, más un gris).
 */
export const COLORES_GRUPO = {
  "GF-01": [213, 94, 0],
  "GF-02": [0, 114, 178],
  "GF-03": [0, 158, 115],
  "GF-04": [204, 121, 167],
  "GF-05": [230, 159, 0],
  "GF-06": [86, 180, 233],
  "GF-07": [102, 102, 102],
};

/** Qué tan opaco es el relleno de la región. */
export const OPACIDAD_REGION = 0.18;

const GRIS = [120, 120, 120];

function rgb(color, opacidad = 1) {
  const [r, g, b] = color;
  return opacidad === 1 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${opacidad})`;
}

export function colorDe(grupo) {
  return rgb(COLORES_GRUPO[grupo] ?? GRIS);
}

function esNumero(valor) {
  return typeof valor === "number" && Number.isFinite(valor);
}

function regionValida(region) {
  return Array.isArray(region) && region.length === 2 && region.every(esNumero);
}

function numero(valor) {
  return String(Math.round(valor));
}

/**
 * Las anotaciones de los grupos elegidos.
 *
 * @param {Array<{grupo: string, region_cm1: number[], pico_cm1: number|null}>} elegidos
 * @returns {object} el objeto annotations del complemento.
 */
export function anotacionesDe(elegidos) {
  const anotaciones = {};
  for (const elegido of elegidos) {
    if (!regionValida(elegido.region_cm1)) {
      continue;
    }
    const base = COLORES_GRUPO[elegido.grupo] ?? GRIS;
    const [menor, mayor] = elegido.region_cm1;
    const sinPico = !esNumero(elegido.pico_cm1);

    anotaciones[`region-${elegido.grupo}`] = {
      type: "box",
      xMin: Math.min(menor, mayor),
      xMax: Math.max(menor, mayor),
      backgroundColor: rgb(base, OPACIDAD_REGION),
      // Sin pico, el borde deja claro cuál es la región completa (CA-06.3).
      borderColor: sinPico ? rgb(base) : "transparent",
      borderWidth: sinPico ? 2 : 0,
    };
    if (!sinPico) {
      anotaciones[`pico-${elegido.grupo}`] = {
        type: "line",
        xMin: elegido.pico_cm1,
        xMax: elegido.pico_cm1,
        borderColor: rgb(base),
        borderWidth: 2,
        borderDash: [6, 4],
      };
    }
  }
  return anotaciones;
}

/**
 * La leyenda de los grupos elegidos, en el mismo orden.
 *
 * @returns {Array<{grupo: string, nombre: string, color: string, detalle: string}>}
 */
export function leyendaDe(elegidos) {
  return elegidos
    .filter((elegido) => regionValida(elegido.region_cm1))
    .map((elegido) => {
      const [menor, mayor] = elegido.region_cm1;
      const region = `región de ${numero(Math.min(menor, mayor))} a ${numero(Math.max(menor, mayor))} cm⁻¹`;
      const detalle = esNumero(elegido.pico_cm1)
        ? `${region}, pico en ${numero(elegido.pico_cm1)} cm⁻¹`
        : `${region} completa, sin posición exacta del pico`;
      return {
        grupo: elegido.grupo,
        nombre: elegido.nombre ?? elegido.grupo,
        color: colorDe(elegido.grupo),
        detalle,
      };
    });
}
