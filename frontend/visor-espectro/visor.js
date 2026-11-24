/**
 * MOD-05, la parte que dibuja (T-12 y T-13).
 *
 * Es la única que habla con Chart.js. Recibe el espectro, le pide la
 * configuración a `configuracion.js` y dibuja. No decide nada: si algo se ve
 * mal, lo que decide es `configuracion.js`, y eso se prueba sin navegador.
 *
 * Chart.js y su complemento de anotaciones se cargan antes, con una etiqueta
 * `<script>` desde `frontend/vendor/` (D-1), y quedan en `globalThis.Chart`.
 */

import { configuracionDeGrafica } from "./configuracion.js";
import { anotacionesDe, leyendaDe } from "./resaltado.js";

function libreria() {
  const Chart = globalThis.Chart;
  if (typeof Chart !== "function") {
    throw new Error("Chart.js no está cargado; revise las etiquetas de index.html");
  }
  return Chart;
}

/**
 * Dibuja el espectro en el lienzo. Si ya había una gráfica, la reemplaza.
 *
 * @param {HTMLCanvasElement} lienzo
 * @param {object} espectro
 * @returns {object} la gráfica de Chart.js.
 */
export function dibujar(lienzo, espectro) {
  const Chart = libreria();
  limpiar(lienzo);
  return new Chart(lienzo, configuracionDeGrafica(espectro));
}

/** Quita la gráfica del lienzo, si la había. */
export function limpiar(lienzo) {
  const Chart = globalThis.Chart;
  if (typeof Chart !== "function" || !lienzo) {
    return;
  }
  const actual = Chart.getChart(lienzo);
  if (actual) {
    actual.destroy();
  }
}

/** La gráfica que hay en el lienzo, o `undefined`. Sirve para la evidencia. */
export function graficaDe(lienzo) {
  const Chart = globalThis.Chart;
  return typeof Chart === "function" ? Chart.getChart(lienzo) : undefined;
}

/** Los identificadores que comparten `index.html` y este archivo. */
export const IDS_GRAFICA = {
  seccion: "grafica",
  contenedor: "grafica-contenedor",
  lienzo: "grafica-lienzo",
  titulo: "grafica-titulo",
  mensaje: "grafica-mensaje",
  accion: "grafica-accion",
  leyenda: "grafica-leyenda",
};

/** Busca una vez los elementos de la gráfica. */
export function elementosDeGrafica(documento) {
  const elementos = {};
  for (const [clave, id] of Object.entries(IDS_GRAFICA)) {
    elementos[clave] = documento.getElementById(id);
  }
  return elementos;
}

function escribir(elemento, contenido) {
  if (!elemento) {
    return;
  }
  elemento.textContent = contenido;
  elemento.hidden = contenido === "";
}

/**
 * Pinta la vista que armó `vistaDeGrafica`.
 *
 * Con estado «lista» se ve la gráfica y no el mensaje. En cualquier otro
 * estado el lienzo se vacía y se esconde, para que nunca quede una gráfica
 * vieja ni una vacía en pantalla (CA-04.3).
 */
export function pintarGrafica(vista, elementos) {
  const { seccion, contenedor, lienzo } = elementos;
  const lista = vista.estado === "lista";

  if (seccion) {
    seccion.hidden = vista.estado === "oculta";
    seccion.dataset.estado = vista.estado;
  }
  escribir(elementos.titulo, vista.titulo);
  escribir(elementos.mensaje, vista.mensaje);
  escribir(elementos.accion, vista.accion);

  if (contenedor) {
    contenedor.hidden = !lista;
  }
  if (lista) {
    dibujar(lienzo, vista.espectro);
  } else {
    limpiar(lienzo);
  }
  return lista;
}

/**
 * Resalta sobre la gráfica los grupos elegidos y pinta su leyenda (T-23 y
 * T-24). Con una lista vacía quita todo el resaltado.
 *
 * @param {object} elementos lo que devolvió elementosDeGrafica.
 * @param {Array<object>} elegidos las filas del análisis que se eligieron.
 */
export function resaltar(elementos, elegidos) {
  const grafica = graficaDe(elementos.lienzo);
  if (grafica) {
    grafica.options.plugins.annotation.annotations = anotacionesDe(elegidos);
    grafica.update("none");
  }

  const { leyenda } = elementos;
  if (!leyenda) {
    return;
  }
  leyenda.replaceChildren();
  for (const entrada of leyendaDe(elegidos)) {
    const documento = leyenda.ownerDocument;
    const elemento = documento.createElement("li");
    elemento.dataset.grupo = entrada.grupo;

    const muestra = documento.createElement("span");
    muestra.className = "leyenda-muestra";
    muestra.style.backgroundColor = entrada.color;

    const texto = documento.createElement("span");
    texto.textContent = `${entrada.nombre}: ${entrada.detalle}`;

    elemento.append(muestra, texto);
    leyenda.append(elemento);
  }
  leyenda.hidden = leyenda.children.length === 0;
}

/**
 * La gráfica como imagen PNG para el reporte (incremento 5, T-26).
 *
 * Para la imagen se resaltan todos los grupos detectados, porque CA-09.1 pide
 * la gráfica con las regiones resaltadas. Después se regresa al resaltado
 * que la persona tenía elegido.
 *
 * @returns {string|null} la imagen como data URL, o null si no hay gráfica.
 */
export function imagenDeGrafica(elementos, detectados, elegidos) {
  const grafica = graficaDe(elementos.lienzo);
  if (!grafica) {
    return null;
  }
  resaltar(elementos, detectados);
  const imagen = grafica.toBase64Image("image/png", 1);
  resaltar(elementos, elegidos);
  return imagen;
}
