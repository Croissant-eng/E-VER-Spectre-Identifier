/**
 * MOD-05, la parte que decide (T-12 y T-13).
 *
 * Igual que `interfaz/vista.js`, este archivo no toca el DOM ni la librería
 * de gráficas: recibe lo que respondió el servidor y devuelve objetos planos.
 * Así se prueba con el corredor de Node, sin navegador (D-9), y el navegador
 * corre exactamente estas mismas funciones.
 *
 * Tres cosas viven aquí:
 *
 * 1. `vistaDeGrafica` decide si hay gráfica o un mensaje en su lugar. Nunca
 *    se dibuja una gráfica vacía (CA-04.3).
 * 2. `puntosGraficables` revisa el espectro que llegó y se queda solo con el
 *    tramo que el archivo de verdad midió, para no dibujar valores inventados.
 * 3. `configuracionDeGrafica` arma la configuración de Chart.js: número de
 *    onda en el eje horizontal, de mayor a menor, e intensidad en el vertical
 *    (CA-04.1).
 *
 * Los límites del eje no se escriben aquí: salen del eje que mandó el
 * servidor, que a su vez sale de UT-03 (regla 1).
 */

import {
  RESULTADO_SIN_SERVIDOR,
  RESULTADO_VEREDICTO,
} from "../servicios/validacion.js";

/** No hay nada que mostrar todavía. */
export const GRAFICA_OCULTA = "oculta";

/** El archivo va camino a MOD-04. */
export const GRAFICA_ESPERANDO = "esperando";

/** Hay espectro y se dibuja. */
export const GRAFICA_LISTA = "lista";

/** No hay espectro que dibujar: se muestra un mensaje en su lugar. */
export const GRAFICA_SIN_ESPECTRO = "sin-espectro";

/** Los únicos textos que escribe MOD-05. Los rechazos los redacta UT-02. */
export const TEXTOS = {
  ejeX: "Número de onda (cm⁻¹)",
  ejeY: "Absorbancia normalizada",
  serie: "Espectro",
  esperando: {
    titulo: "Preparando la gráfica…",
    mensaje: "Un momento, se está procesando el espectro.",
  },
  sinEspectro: {
    titulo: "No se pudo mostrar la gráfica",
    mensaje: "El servidor no devolvió un espectro que se pueda dibujar.",
    accion: "Vuelva a subir el archivo en un momento.",
  },
  sinServidor: {
    titulo: "No se pudo contactar al servidor",
    mensaje: "La aplicación no recibió respuesta al procesar el espectro.",
    accion: "Revise su conexión y vuelva a intentarlo.",
  },
};

/** Color de la línea del espectro. */
export const COLOR_LINEA = "#1d4ed8";

function esObjeto(valor) {
  return typeof valor === "object" && valor !== null;
}

function esNumero(valor) {
  return typeof valor === "number" && Number.isFinite(valor);
}

function texto(valor) {
  return typeof valor === "string" ? valor.trim() : "";
}

/**
 * Los puntos que se pueden dibujar, o `null` si el espectro no sirve.
 *
 * Fuera del tramo medido la rejilla trae ceros que no son datos (MOD-04 no
 * inventa valores), así que esos puntos no se dibujan.
 *
 * @param {unknown} espectro el objeto `espectro` de `POST /api/procesar`.
 * @returns {{x: number, y: number}[] | null}
 */
export function puntosGraficables(espectro) {
  if (!esObjeto(espectro)) {
    return null;
  }
  const { eje_cm1: eje, intensidad, rango_medido_cm1: rango } = espectro;
  if (!Array.isArray(eje) || !Array.isArray(intensidad)) {
    return null;
  }
  if (eje.length < 2 || eje.length !== intensidad.length) {
    return null;
  }
  if (!eje.every(esNumero) || !intensidad.every(esNumero)) {
    return null;
  }
  if (!Array.isArray(rango) || rango.length !== 2 || !rango.every(esNumero)) {
    return null;
  }

  const desde = Math.min(rango[0], rango[1]);
  const hasta = Math.max(rango[0], rango[1]);
  const puntos = [];
  for (let i = 0; i < eje.length; i += 1) {
    if (eje[i] >= desde && eje[i] <= hasta) {
      puntos.push({ x: eje[i], y: intensidad[i] });
    }
  }
  return puntos.length >= 2 ? puntos : null;
}

/** La vista base: sin gráfica y sin mensaje. */
export function vistaGraficaOculta() {
  return { estado: GRAFICA_OCULTA, espectro: null, titulo: "", mensaje: "", accion: "" };
}

/** Mientras el archivo viaja a MOD-04. */
export function vistaGraficaEsperando() {
  return {
    ...vistaGraficaOculta(),
    estado: GRAFICA_ESPERANDO,
    titulo: TEXTOS.esperando.titulo,
    mensaje: TEXTOS.esperando.mensaje,
  };
}

function sinEspectro(textos) {
  return {
    estado: GRAFICA_SIN_ESPECTRO,
    espectro: null,
    titulo: textos.titulo,
    mensaje: textos.mensaje,
    accion: textos.accion,
  };
}

/**
 * Qué mostrar en el lugar de la gráfica, según lo que devolvió el servicio.
 *
 * Con espectro dibujable, la gráfica. Con un rechazo completo de UT-02, ese
 * mensaje. Con cualquier otra cosa, un aviso propio. En ningún caso una
 * gráfica vacía (CA-04.3).
 *
 * @param {{resultado: string, datos: object|null}} respuesta
 */
export function vistaDeGrafica(respuesta) {
  if (!esObjeto(respuesta)) {
    return sinEspectro(TEXTOS.sinEspectro);
  }
  if (respuesta.resultado === RESULTADO_SIN_SERVIDOR) {
    return sinEspectro(TEXTOS.sinServidor);
  }

  const datos = respuesta.datos;
  if (respuesta.resultado === RESULTADO_VEREDICTO && esObjeto(datos) && datos.valido === true) {
    const puntos = puntosGraficables(datos.espectro);
    if (puntos) {
      return { ...vistaGraficaOculta(), estado: GRAFICA_LISTA, espectro: datos.espectro };
    }
    return sinEspectro(TEXTOS.sinEspectro);
  }

  if (esObjeto(datos)) {
    const titulo = texto(datos.titulo);
    const mensaje = texto(datos.mensaje);
    const accion = texto(datos.accion);
    if (titulo && mensaje && accion) {
      return sinEspectro({ titulo, mensaje, accion });
    }
  }
  return sinEspectro(TEXTOS.sinEspectro);
}

/**
 * La configuración de Chart.js para un espectro (CA-04.1).
 *
 * @param {object} espectro el objeto `espectro` de `POST /api/procesar`.
 * @returns {object} lista para `new Chart(lienzo, configuracion)`.
 * @throws {TypeError} si el espectro no se puede dibujar. Quien llama ya pasó
 *   por `vistaDeGrafica`, así que esto solo protege de un error de programa.
 */
export function configuracionDeGrafica(espectro) {
  const puntos = puntosGraficables(espectro);
  if (!puntos) {
    throw new TypeError("el espectro no se puede dibujar");
  }
  const eje = espectro.eje_cm1;

  return {
    type: "line",
    data: {
      datasets: [
        {
          label: TEXTOS.serie,
          data: puntos,
          borderColor: COLOR_LINEA,
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      parsing: false,
      normalized: true,
      interaction: { mode: "nearest", axis: "x", intersect: false },
      plugins: {
        legend: { display: false },
        // El complemento de anotaciones (D-1) queda listo y vacío. El
        // incremento 4 le agrega las regiones y los picos.
        annotation: { annotations: {} },
      },
      scales: {
        x: {
          type: "linear",
          // El espectro infrarrojo se lee de mayor a menor número de onda.
          reverse: true,
          min: Math.min(...eje),
          max: Math.max(...eje),
          title: { display: true, text: TEXTOS.ejeX },
          ticks: { maxRotation: 0, autoSkip: true },
        },
        y: {
          min: 0,
          max: 1,
          title: { display: true, text: TEXTOS.ejeY },
        },
      },
    },
  };
}
