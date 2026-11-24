/**
 * MOD-01, pinta la vista del análisis en la página (incremento 3).
 *
 * No decide nada: escribe lo que armó analisis.js. Todo va con textContent,
 * nunca con innerHTML, aunque los nombres de los grupos vengan del catálogo.
 */

import { ANALISIS_OCULTO } from "./analisis.js";

/** Los identificadores que index.html y este archivo comparten. */
export const IDS_ANALISIS = {
  seccion: "analisis",
  titulo: "analisis-titulo",
  mensaje: "analisis-mensaje",
  accion: "analisis-accion",
  lista: "analisis-lista",
};

export function elementosDeAnalisis(documento) {
  const elementos = {};
  for (const [clave, id] of Object.entries(IDS_ANALISIS)) {
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
 * Pinta la vista del análisis.
 *
 * @param {object} vista lo que devolvió analisis.js.
 * @param {object} elementos lo que devolvió elementosDeAnalisis.
 */
export function pintarAnalisis(vista, elementos) {
  const { seccion, lista } = elementos;
  if (seccion) {
    seccion.hidden = vista.estado === ANALISIS_OCULTO;
    seccion.dataset.estado = vista.estado;
  }

  escribir(elementos.titulo, vista.titulo);
  escribir(elementos.mensaje, vista.mensaje);
  escribir(elementos.accion, vista.accion);

  if (!lista) {
    return;
  }
  lista.replaceChildren();
  for (const fila of vista.filas) {
    const elemento = lista.ownerDocument.createElement("li");
    elemento.className = "analisis-fila";
    elemento.dataset.grupo = fila.grupo;

    const nombre = lista.ownerDocument.createElement("span");
    nombre.className = "analisis-nombre";
    nombre.textContent = fila.nombre;

    const confianza = lista.ownerDocument.createElement("span");
    confianza.className = "analisis-confianza";
    confianza.textContent = fila.confianza;

    elemento.append(nombre, confianza);
    lista.append(elemento);
  }
  lista.hidden = vista.filas.length === 0;
}
