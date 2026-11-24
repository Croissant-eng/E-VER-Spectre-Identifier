/**
 * MOD-01 · interfaz · conecta la pantalla con el servicio (T-06).
 *
 * El reparto de MOD-01, a propósito, en tres archivos:
 *
 * - `vista.js` decide **qué** se muestra (puro, probado sin navegador).
 * - `pintar.js` lo escribe en el DOM.
 * - este archivo escucha al formulario y encadena las dos cosas con el
 *   servicio de `servicios/`.
 *
 * Desde el incremento 3 el botón «Analizar» ya tiene acción: manda al motor
 * el espectro que se acaba de graficar y pinta la lista de grupos (T-18) o el
 * aviso que corresponda (T-19). El espectro se guarda solo en memoria, en
 * esta página, y se olvida al subir otro archivo.
 */

import { analizarEspectro } from "../servicios/analisis.js";
import { RESULTADO_PDF, pedirReporte } from "../servicios/reporte.js";
import { procesarEspectro } from "../servicios/procesamiento.js";
import { validarEspectro } from "../servicios/validacion.js";
import {
  vistaDeGrafica,
  vistaGraficaEsperando,
  vistaGraficaOculta,
} from "../visor-espectro/configuracion.js";
import {
  elementosDeGrafica,
  imagenDeGrafica,
  pintarGrafica,
  resaltar,
} from "../visor-espectro/visor.js";
import {
  ANALISIS_LISTO,
  ANALISIS_SIN_DETECCIONES,
  vistaAnalisisEsperando,
  vistaAnalisisOculta,
  vistaDeAnalisis,
} from "./analisis.js";
import { elementosDe, pintar } from "./pintar.js";
import { elementosDeAnalisis, pintarAnalisis } from "./pintar-analisis.js";
import {
  vistaDeReporte,
  vistaReporteGenerando,
  vistaReporteListo,
  vistaReporteOculta,
} from "./reporte.js";

/** Los elementos del bloque del reporte (incremento 5). */
function elementosDeReporte(documento) {
  return {
    bloque: documento.getElementById("bloque-reporte"),
    boton: documento.getElementById("descargar-reporte"),
    titulo: documento.getElementById("reporte-titulo"),
    mensaje: documento.getElementById("reporte-mensaje"),
    accion: documento.getElementById("reporte-accion"),
  };
}

function escribirTexto(elemento, contenido) {
  if (elemento) {
    elemento.textContent = contenido;
    elemento.hidden = contenido === "";
  }
}

function pintarReporte(vista, elementos) {
  if (elementos.bloque) {
    elementos.bloque.hidden = vista.estado === "oculto";
    elementos.bloque.dataset.estado = vista.estado;
  }
  if (elementos.boton) {
    elementos.boton.disabled = !vista.habilitado;
  }
  escribirTexto(elementos.titulo, vista.titulo);
  escribirTexto(elementos.mensaje, vista.mensaje);
  escribirTexto(elementos.accion, vista.accion);
}

/** Entrega el PDF al navegador para que lo guarde. */
function guardarPdf(documento, pdf, nombre) {
  const enlace = documento.createElement("a");
  const direccion = URL.createObjectURL(pdf);
  enlace.href = direccion;
  enlace.download = nombre;
  documento.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(direccion), 0);
}
import { vistaDesdeRespuesta, vistaEsperando, vistaInicial } from "./vista.js";

/**
 * Deja la pantalla lista: el botón de validar se habilita al elegir archivo y
 * el formulario valida al enviarse.
 *
 * @param {Document} documento
 * @param {object} [opciones] `fetch` a inyectar en pruebas manuales.
 */
export function conectar(documento, opciones = {}) {
  const elementos = elementosDe(documento);
  const grafica = elementosDeGrafica(documento);
  const analisis = elementosDeAnalisis(documento);
  const { formulario, archivo, validar, analizar: botonAnalizar } = elementos;

  const reporte = elementosDeReporte(documento);
  // El espectro procesado del archivo actual. Es lo que se manda a analizar.
  let espectroActual = null;
  // Incremento 5: el nombre que devolvió MOD-02, para el reporte.
  let nombreActual = "";
  // Incremento 4: las filas del último análisis y los grupos resaltados.
  let filasActuales = [];
  const elegidos = new Set();

  const alResaltar = (grupo, elegido) => {
    if (elegido) {
      elegidos.add(grupo);
    } else {
      elegidos.delete(grupo);
    }
    resaltar(
      grafica,
      filasActuales.filter((fila) => elegidos.has(fila.grupo)),
    );
  };

  const olvidarResaltado = () => {
    filasActuales = [];
    elegidos.clear();
    resaltar(grafica, []);
    pintarReporte(vistaReporteOculta(), reporte);
  };

  pintar(vistaInicial(), elementos);
  pintarGrafica(vistaGraficaOculta(), grafica);
  pintarAnalisis(vistaAnalisisOculta(), analisis);

  if (!formulario || !archivo || !validar) {
    return elementos;
  }

  // Sin archivo elegido no hay nada que validar: en vez de inventar un mensaje
  // de error, el botón espera deshabilitado.
  const alElegir = () => {
    validar.disabled = archivo.files.length === 0;
  };
  alElegir();
  archivo.addEventListener("change", alElegir);

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const elegido = archivo.files[0];
    if (!elegido) {
      return;
    }

    validar.disabled = true;
    espectroActual = null;
    olvidarResaltado();
    pintar(vistaEsperando(elegido.name), elementos);
    // Una gráfica o un análisis de un archivo anterior no se quedan en pantalla.
    pintarGrafica(vistaGraficaOculta(), grafica);
    pintarAnalisis(vistaAnalisisOculta(), analisis);

    const respuesta = await validarEspectro(elegido, opciones);
    nombreActual = respuesta?.veredicto?.valido ? respuesta.veredicto.nombre : "";
    const aprobado = pintar(vistaDesdeRespuesta(respuesta), elementos);

    // Incremento 2: solo un archivo aprobado pasa a MOD-04 y se dibuja. Uno
    // rechazado se queda con su mensaje y sin gráfica (CA-04.3).
    if (aprobado) {
      // Mientras no haya espectro no hay nada que analizar.
      if (botonAnalizar) {
        botonAnalizar.disabled = true;
      }
      pintarGrafica(vistaGraficaEsperando(), grafica);
      const procesado = await procesarEspectro(elegido, opciones);
      pintarGrafica(vistaDeGrafica(procesado), grafica);
      espectroActual = procesado?.datos?.valido ? procesado.datos.espectro : null;
      if (botonAnalizar) {
        botonAnalizar.disabled = espectroActual === null;
      }
    }

    validar.disabled = false;
  });

  botonAnalizar?.addEventListener("click", async () => {
    if (espectroActual === null) {
      return;
    }
    botonAnalizar.disabled = true;
    olvidarResaltado();
    pintarAnalisis(vistaAnalisisEsperando(), analisis);
    const respuesta = await analizarEspectro(espectroActual, opciones);
    const vista = vistaDeAnalisis(respuesta);
    filasActuales = vista.filas;
    pintarAnalisis(vista, analisis, { alResaltar, elegidos });
    // Hay reporte con grupos y también sin ellos (CA-09.2).
    if (vista.estado === ANALISIS_LISTO || vista.estado === ANALISIS_SIN_DETECCIONES) {
      pintarReporte(vistaReporteListo(), reporte);
    }
    // Pase lo que pase, el archivo y su espectro siguen cargados y se puede
    // volver a intentar (CA-05.4).
    botonAnalizar.disabled = false;
  });

  reporte.boton?.addEventListener("click", async () => {
    if (espectroActual === null) {
      return;
    }
    pintarReporte(vistaReporteGenerando(), reporte);
    const elegidas = filasActuales.filter((fila) => elegidos.has(fila.grupo));
    const cuerpo = {
      nombre: nombreActual,
      espectro: espectroActual,
      grafica_png: imagenDeGrafica(grafica, filasActuales, elegidas),
      zona_horaria_min: new Date().getTimezoneOffset(),
    };
    const respuesta = await pedirReporte(cuerpo, opciones);
    if (respuesta.resultado === RESULTADO_PDF) {
      guardarPdf(documento, respuesta.pdf, respuesta.nombre);
    }
    // Los resultados del análisis no se tocan, salga bien o mal (CA-09.3).
    pintarReporte(vistaDeReporte(respuesta), reporte);
  });

  return elementos;
}

// En el navegador se conecta al cargar; al importarlo desde Node (pruebas) no
// hay `document` y no pasa nada.
if (typeof document !== "undefined") {
  conectar(document);
}
