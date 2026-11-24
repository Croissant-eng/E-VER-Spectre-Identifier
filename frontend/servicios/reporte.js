/**
 * Servicio del reporte, la llamada a POST /api/reporte (incremento 5).
 *
 * Manda en JSON el nombre del archivo, el espectro, la gráfica resaltada como
 * imagen PNG y la zona horaria del navegador. Si todo sale bien el servidor
 * responde el PDF; si no, responde JSON con el mensaje de UT-02.
 */

import { RESULTADO_FALLO, RESULTADO_SIN_SERVIDOR } from "./validacion.js";

/** La ruta del reporte. `backend/api/aplicacion.py` la repite. */
export const RUTA_REPORTE = "/api/reporte";

/** Llegó el PDF. */
export const RESULTADO_PDF = "pdf";

/** El nombre del PDF que viene en Content-Disposition, o uno de respaldo. */
export function nombreDeDescarga(disposicion) {
  const encontrado = /filename="([^"]+)"/.exec(disposicion ?? "");
  return encontrado ? encontrado[1] : "reporte.pdf";
}

/**
 * Pide el reporte.
 *
 * @param {object} cuerpo nombre, espectro, grafica_png y zona_horaria_min.
 * @param {object} [opciones]
 * @param {Function} [opciones.fetch] el fetch a usar; se inyecta en pruebas.
 * @returns {Promise<object>} con resultado "pdf" trae el Blob y su nombre;
 *   si no, el cuerpo JSON que haya llegado. No lanza por culpa de la red.
 */
export async function pedirReporte(cuerpo, opciones = {}) {
  const traer = opciones.fetch ?? globalThis.fetch;
  if (typeof traer !== "function") {
    throw new TypeError("no hay fetch disponible para llamar al servidor");
  }

  let respuesta;
  try {
    respuesta = await traer(opciones.rutaReporte ?? RUTA_REPORTE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
  } catch {
    return { resultado: RESULTADO_SIN_SERVIDOR, datos: null };
  }

  const tipo = respuesta.headers?.get?.("content-type") ?? "";
  if (respuesta.ok && tipo.startsWith("application/pdf")) {
    return {
      resultado: RESULTADO_PDF,
      pdf: await respuesta.blob(),
      nombre: nombreDeDescarga(respuesta.headers.get("content-disposition")),
    };
  }

  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }
  return { resultado: RESULTADO_FALLO, datos };
}
