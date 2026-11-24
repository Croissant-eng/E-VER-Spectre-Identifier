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

/** El texto del botón que resalta un grupo en la gráfica. */
export const TEXTO_RESALTAR = "Resaltar en la gráfica";

/** El texto que abre la explicación de un grupo. */
export const TEXTO_EXPLICACION = "Ver por qué";

function crear(documento, etiqueta, clase, contenido = "") {
  const elemento = documento.createElement(etiqueta);
  if (clase) {
    elemento.className = clase;
  }
  if (contenido) {
    elemento.textContent = contenido;
  }
  return elemento;
}

/** La explicación de un grupo, dentro de un desplegable (incremento 4). */
function bloqueDeExplicacion(documento, explicacion) {
  const desplegable = crear(documento, "details", "analisis-explicacion");
  desplegable.append(crear(documento, "summary", "", TEXTO_EXPLICACION));

  if (explicacion.disponible) {
    for (const parte of explicacion.partes) {
      desplegable.append(crear(documento, "p", "", parte));
    }
  } else {
    // CA-07.3: el grupo se queda y en lugar del texto va el aviso.
    desplegable.dataset.disponible = "no";
    desplegable.append(crear(documento, "p", "explicacion-aviso", explicacion.titulo));
    for (const parte of [explicacion.mensaje, explicacion.accion]) {
      if (parte) {
        desplegable.append(crear(documento, "p", "", parte));
      }
    }
  }
  return desplegable;
}

/**
 * Pinta la vista del análisis.
 *
 * @param {object} vista lo que devolvió analisis.js.
 * @param {object} elementos lo que devolvió elementosDeAnalisis.
 * @param {object} [opciones]
 * @param {Function} [opciones.alResaltar] se llama con el grupo y si quedó
 *   elegido cada vez que la persona pulsa «Resaltar en la gráfica».
 * @param {Set<string>} [opciones.elegidos] los grupos ya resaltados.
 */
export function pintarAnalisis(vista, elementos, opciones = {}) {
  const { seccion, lista } = elementos;
  const elegidos = opciones.elegidos ?? new Set();
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
  const documento = lista.ownerDocument;
  lista.replaceChildren();
  for (const fila of vista.filas) {
    const elemento = crear(documento, "li", "analisis-fila");
    elemento.dataset.grupo = fila.grupo;

    const cabecera = crear(documento, "div", "analisis-cabecera");
    cabecera.append(
      crear(documento, "span", "analisis-nombre", fila.nombre),
      crear(documento, "span", "analisis-confianza", fila.confianza),
    );
    elemento.append(cabecera);

    if (fila.region_cm1 && opciones.alResaltar) {
      const boton = crear(documento, "button", "boton boton-resaltar", TEXTO_RESALTAR);
      boton.type = "button";
      boton.dataset.grupo = fila.grupo;
      boton.setAttribute("aria-pressed", String(elegidos.has(fila.grupo)));
      boton.addEventListener("click", () => {
        const elegido = boton.getAttribute("aria-pressed") !== "true";
        boton.setAttribute("aria-pressed", String(elegido));
        opciones.alResaltar(fila.grupo, elegido);
      });
      elemento.append(boton);
    }

    if (fila.explicacion) {
      elemento.append(bloqueDeExplicacion(documento, fila.explicacion));
    }
    lista.append(elemento);
  }
  lista.hidden = vista.filas.length === 0;
}
