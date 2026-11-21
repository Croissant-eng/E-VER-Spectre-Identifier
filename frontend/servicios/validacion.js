/**
 * Servicio de validación · la llamada a `POST /api/validar` (contrato D-5).
 *
 * `multipart/form-data` con el archivo en el campo `archivo`. El servidor
 * responde **200 con un veredicto** siempre que pueda emitirlo —un rechazo es
 * un resultado de negocio, no un error de transporte— y **500** solo si falla
 * por dentro, con un mensaje genérico de UT-02.
 *
 * **El endpoint todavía no existe:** es T-07. Este archivo se prueba con un
 * `fetch` simulado, que se pasa por parámetro; en el navegador usa el de
 * siempre. Por eso no hay nada que montar para probarlo.
 *
 * Este servicio **no interpreta** el veredicto: no decide qué se muestra ni
 * traduce códigos. Solo distingue tres situaciones y entrega lo que llegó.
 */

/** La ruta del contrato D-5. */
export const RUTA_VALIDAR = "/api/validar";

/** El nombre del campo del formulario, también del contrato D-5. */
export const CAMPO_ARCHIVO = "archivo";

/** El servidor emitió un veredicto (200), sea de aceptación o de rechazo. */
export const RESULTADO_VEREDICTO = "veredicto";

/** El servidor falló por dentro (500 u otro código de error). */
export const RESULTADO_FALLO = "fallo";

/** No hubo respuesta: sin red, servidor apagado o petición cancelada. */
export const RESULTADO_SIN_SERVIDOR = "sin-servidor";

/** Lee el cuerpo como JSON sin dejar que un cuerpo roto tumbe la llamada. */
async function cuerpoJson(respuesta) {
  try {
    const datos = await respuesta.json();
    return typeof datos === "object" && datos !== null ? datos : null;
  } catch {
    return null;
  }
}

/**
 * Envía el archivo a validar.
 *
 * @param {File|Blob} archivo el archivo que eligió la persona.
 * @param {object} [opciones]
 * @param {Function} [opciones.fetch] el `fetch` a usar; se inyecta en pruebas.
 * @param {string} [opciones.ruta] la ruta del endpoint.
 * @returns {Promise<{resultado: string, veredicto: object|null}>} qué pasó y el
 *   veredicto si llegó alguno. **No lanza** por culpa de la red ni de una
 *   respuesta rota: eso es un resultado, no una excepción.
 */
export async function validarEspectro(archivo, opciones = {}) {
  const traer = opciones.fetch ?? globalThis.fetch;
  const ruta = opciones.ruta ?? RUTA_VALIDAR;

  if (typeof traer !== "function") {
    throw new TypeError("no hay fetch disponible para llamar al servidor");
  }

  const cuerpo = new FormData();
  cuerpo.append(CAMPO_ARCHIVO, archivo);

  let respuesta;
  try {
    respuesta = await traer(ruta, { method: "POST", body: cuerpo });
  } catch {
    // Sin detalles técnicos: lo que haya dicho la excepción no se le muestra a
    // nadie ni se arrastra hacia la vista.
    return { resultado: RESULTADO_SIN_SERVIDOR, veredicto: null };
  }

  const datos = await cuerpoJson(respuesta);

  if (!respuesta.ok) {
    // El 500 del contrato trae mensaje genérico de UT-02; se pasa tal cual para
    // que la vista lo muestre si está completo.
    return { resultado: RESULTADO_FALLO, veredicto: datos };
  }

  return { resultado: RESULTADO_VEREDICTO, veredicto: datos };
}
