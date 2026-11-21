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
 * El botón «Analizar» **no aparece aquí**: D-4 pide que esté presente y
 * habilitado al aceptar, y **sin acción**. No tiene escuchador de clic, y eso
 * es lo que lo mantiene sin acción de verdad (RF-04 es del incremento 3).
 */

import { validarEspectro } from "../servicios/validacion.js";
import { elementosDe, pintar } from "./pintar.js";
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
  const { formulario, archivo, validar } = elementos;

  pintar(vistaInicial(), elementos);

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
    pintar(vistaEsperando(elegido.name), elementos);

    const respuesta = await validarEspectro(elegido, opciones);
    pintar(vistaDesdeRespuesta(respuesta), elementos);

    validar.disabled = false;
  });

  return elementos;
}

// En el navegador se conecta al cargar; al importarlo desde Node (pruebas) no
// hay `document` y no pasa nada.
if (typeof document !== "undefined") {
  conectar(document);
}
