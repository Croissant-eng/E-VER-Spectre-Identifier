/**
 * MOD-01 · pintar · la única parte que toca el DOM (T-06).
 *
 * Recibe la vista que armó `vista.js` y la escribe en la pantalla. No decide
 * nada: si algo se ve mal, el que decide es `vista.js`, y eso se prueba sin
 * navegador.
 *
 * Todo se escribe con `textContent`, nunca con `innerHTML`: el nombre del
 * archivo lo eligió quien sube el espectro, así que se trata como texto y no
 * como código, aunque MOD-02 ya lo haya limpiado (RNF-03, dos cerrojos en vez
 * de uno).
 */

import { ESTADO_ACEPTADO, ESTADO_INICIAL } from "./vista.js";

/** Los identificadores que `index.html` y este archivo comparten. */
export const IDS = {
  formulario: "formulario",
  archivo: "archivo",
  validar: "validar",
  resultado: "resultado",
  titulo: "resultado-titulo",
  nombre: "resultado-nombre",
  mensaje: "resultado-mensaje",
  accion: "resultado-accion",
  bloqueAnalizar: "bloque-analizar",
  analizar: "analizar",
  notaAnalizar: "nota-analizar",
};

/**
 * Busca una vez los elementos de la pantalla.
 *
 * @param {Document} documento
 */
export function elementosDe(documento) {
  const elementos = {};
  for (const [clave, id] of Object.entries(IDS)) {
    elementos[clave] = documento.getElementById(id);
  }
  return elementos;
}

/** Escribe un texto y esconde el elemento cuando no hay nada que decir. */
function escribir(elemento, contenido) {
  if (!elemento) {
    return;
  }
  elemento.textContent = contenido;
  elemento.hidden = contenido === "";
}

/**
 * Pinta la vista.
 *
 * @param {object} vista lo que devolvió `vista.js`.
 * @param {object} elementos lo que devolvió `elementosDe`.
 */
export function pintar(vista, elementos) {
  const { resultado } = elementos;

  if (resultado) {
    // Antes de validar no hay resultado: la tarjeta no existe en pantalla.
    resultado.hidden = vista.estado === ESTADO_INICIAL;
    resultado.dataset.estado = vista.estado;
  }

  escribir(elementos.titulo, vista.titulo);
  escribir(elementos.nombre, vista.nombre);
  escribir(elementos.mensaje, vista.mensaje);
  escribir(elementos.accion, vista.accion);

  if (elementos.bloqueAnalizar) {
    elementos.bloqueAnalizar.hidden = !vista.analizar.visible;
  }
  if (elementos.analizar) {
    // D-4: presente y habilitado al aceptar, y sin acción. Nadie le pone un
    // escuchador de clic: el botón no hace nada hasta el incremento 3.
    elementos.analizar.disabled = !vista.analizar.habilitado;
  }
  escribir(elementos.notaAnalizar, vista.analizar.nota);

  return vista.estado === ESTADO_ACEPTADO;
}
