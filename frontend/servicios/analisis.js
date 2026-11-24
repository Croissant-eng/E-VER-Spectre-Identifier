/**
 * Servicio de análisis, la llamada a POST /api/analizar (incremento 3).
 *
 * Manda en JSON el mismo objeto espectro que llegó de /api/procesar. No manda
 * el archivo: el motor solo trabaja con números (D-17). Si todo sale bien el
 * servidor responde 200 con las detecciones, o con el aviso de que no hubo
 * detecciones confiables. Si el espectro no tiene la forma esperada también
 * responde 200, con valido en false y el mensaje de UT-02. El 500 queda para
 * un fallo del motor (CA-05.4).
 *
 * Igual que los otros servicios, no interpreta nada: dice qué pasó y entrega
 * lo que llegó.
 */

import {
  RESULTADO_FALLO,
  RESULTADO_SIN_SERVIDOR,
  RESULTADO_VEREDICTO,
} from "./validacion.js";

/** La ruta del análisis. `backend/api/aplicacion.py` la repite. */
export const RUTA_ANALIZAR = "/api/analizar";

async function cuerpoJson(respuesta) {
  try {
    const datos = await respuesta.json();
    return typeof datos === "object" && datos !== null ? datos : null;
  } catch {
    return null;
  }
}

/**
 * Pide el análisis de un espectro ya procesado.
 *
 * @param {object} espectro el objeto espectro de /api/procesar.
 * @param {object} [opciones]
 * @param {Function} [opciones.fetch] el fetch a usar; se inyecta en pruebas.
 * @returns {Promise<{resultado: string, datos: object|null}>} no lanza por
 *   culpa de la red.
 */
export async function analizarEspectro(espectro, opciones = {}) {
  const traer = opciones.fetch ?? globalThis.fetch;
  const ruta = opciones.rutaAnalizar ?? RUTA_ANALIZAR;

  if (typeof traer !== "function") {
    throw new TypeError("no hay fetch disponible para llamar al servidor");
  }

  let respuesta;
  try {
    respuesta = await traer(ruta, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(espectro),
    });
  } catch {
    return { resultado: RESULTADO_SIN_SERVIDOR, datos: null };
  }

  const datos = await cuerpoJson(respuesta);
  if (!respuesta.ok) {
    return { resultado: RESULTADO_FALLO, datos };
  }
  return { resultado: RESULTADO_VEREDICTO, datos };
}
