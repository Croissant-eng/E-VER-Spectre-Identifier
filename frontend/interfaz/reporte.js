/**
 * MOD-01, la vista del botón «Descargar reporte» (incremento 5).
 *
 * No toca el DOM. Decide qué se dice alrededor del botón según lo que
 * respondió el servicio del reporte. Pase lo que pase, los resultados del
 * análisis no se tocan: siguen en pantalla y el botón queda listo para
 * reintentar (CA-09.3).
 */

export const REPORTE_OCULTO = "oculto";
export const REPORTE_LISTO = "listo";
export const REPORTE_GENERANDO = "generando";
export const REPORTE_DESCARGADO = "descargado";
export const REPORTE_FALLO = "fallo";

export const TEXTOS_REPORTE = {
  generando: "Generando el reporte…",
  descargado: "El reporte se descargó.",
  sinRespuesta: {
    titulo: "No se pudo generar el reporte",
    mensaje: "El servidor no devolvió el reporte.",
    accion: "Pulse «Descargar reporte» para intentarlo de nuevo.",
  },
  sinServidor: {
    titulo: "No se pudo contactar al servidor",
    mensaje: "La aplicación no recibió respuesta al pedir el reporte.",
    accion: "Revise su conexión y pulse «Descargar reporte» otra vez.",
  },
};

function base(estado) {
  return { estado, titulo: "", mensaje: "", accion: "", habilitado: true };
}

function texto(valor) {
  return typeof valor === "string" ? valor.trim() : "";
}

export function vistaReporteOculta() {
  return { ...base(REPORTE_OCULTO), habilitado: false };
}

export function vistaReporteListo() {
  return base(REPORTE_LISTO);
}

export function vistaReporteGenerando() {
  return { ...base(REPORTE_GENERANDO), mensaje: TEXTOS_REPORTE.generando, habilitado: false };
}

/** La vista que corresponde a la respuesta del servicio. */
export function vistaDeReporte(respuesta) {
  if (respuesta?.resultado === "pdf") {
    return { ...base(REPORTE_DESCARGADO), mensaje: TEXTOS_REPORTE.descargado };
  }
  const textos =
    respuesta?.resultado === "sin-servidor" ? TEXTOS_REPORTE.sinServidor : TEXTOS_REPORTE.sinRespuesta;
  const datos = respuesta?.datos;
  const delServidor = {
    titulo: texto(datos?.titulo),
    mensaje: texto(datos?.mensaje),
    accion: texto(datos?.accion),
  };
  const completo = delServidor.titulo && delServidor.mensaje && delServidor.accion;
  return { ...base(REPORTE_FALLO), ...(completo ? delServidor : textos) };
}
