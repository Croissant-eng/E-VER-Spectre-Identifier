/**
 * Servicio de procesamiento, la llamada a `POST /api/procesar` (incremento 2).
 *
 * Manda el mismo archivo que ya se validó, en el mismo campo `archivo`, y el
 * servidor lo pasa por MOD-02, MOD-03 y MOD-04. Si todo sale bien responde 200
 * con el espectro normalizado; si MOD-04 lo rechaza (por ejemplo, una línea
 * plana o una unidad que no se reconoce) también responde 200, con el mensaje
 * de UT-02. El 500 queda para un fallo interno.
 *
 * Igual que el servicio de validación, este archivo no interpreta nada: solo
 * distingue qué pasó y entrega lo que llegó. Se prueba con un `fetch`
 * simulado que se pasa por parámetro.
 */

import {
  CAMPO_ARCHIVO,
  RESULTADO_FALLO,
  RESULTADO_SIN_SERVIDOR,
  RESULTADO_VEREDICTO,
} from "./validacion.js";

/** La ruta del procesamiento. `backend/api/aplicacion.py` la repite. */
export const RUTA_PROCESAR = "/api/procesar";

async function cuerpoJson(respuesta) {
  try {
    const datos = await respuesta.json();
    return typeof datos === "object" && datos !== null ? datos : null;
  } catch {
    return null;
  }
}

/**
 * Envía el archivo a procesar.
 *
 * @param {File|Blob} archivo el archivo que eligió la persona.
 * @param {object} [opciones]
 * @param {Function} [opciones.fetch] el `fetch` a usar; se inyecta en pruebas.
 * @returns {Promise<{resultado: string, datos: object|null}>} qué pasó y el
 *   cuerpo si llegó alguno. No lanza por culpa de la red.
 */
export async function procesarEspectro(archivo, opciones = {}) {
  const traer = opciones.fetch ?? globalThis.fetch;
  const ruta = opciones.ruta ?? RUTA_PROCESAR;

  if (typeof traer !== "function") {
    throw new TypeError("no hay fetch disponible para llamar al servidor");
  }

  const cuerpo = new FormData();
  cuerpo.append(CAMPO_ARCHIVO, archivo);

  let respuesta;
  try {
    respuesta = await traer(ruta, { method: "POST", body: cuerpo });
  } catch {
    return { resultado: RESULTADO_SIN_SERVIDOR, datos: null };
  }

  const datos = await cuerpoJson(respuesta);
  if (!respuesta.ok) {
    return { resultado: RESULTADO_FALLO, datos };
  }
  return { resultado: RESULTADO_VEREDICTO, datos };
}
