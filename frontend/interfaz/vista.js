/**
 * MOD-01 · la vista · de un veredicto a lo que ve el usuario (T-06).
 *
 * Este archivo **no toca el DOM**: recibe el veredicto que describe el contrato
 * de la sección 5 y devuelve un objeto plano con lo que hay que pintar. Así la
 * parte que decide se prueba sola, con veredictos simulados, sin navegador y
 * sin servidor (`pintar.js` es el que mueve el DOM).
 *
 * Tres reglas que este archivo existe para sostener:
 *
 * 1. **El código del rechazo no se muestra.** `FORMATO_NO_SOPORTADO` es para el
 *    registro y para el equipo; el usuario lee título, mensaje y acción (RNF-01).
 * 2. **Nunca una vista a medias.** Si la respuesta no trae un veredicto que se
 *    pueda mostrar completo, no se pinta un resultado a medias: se muestra el
 *    estado «no se pudo mostrar el resultado», que es honesto y completo.
 * 3. **Los textos de los rechazos vienen del servidor** (UT-02), no de aquí. Lo
 *    único que el frontend escribe son las etiquetas de su propia pantalla: el
 *    aviso de documento aprobado que pide D-4, el «validando…» y el aviso de
 *    que no hubo respuesta. UT-02 es el catálogo de *rechazos*, y ninguno de
 *    esos tres lo es.
 */

/** No se ha validado nada todavía: no hay resultado que pintar. */
export const ESTADO_INICIAL = "inicial";

/** El archivo va camino al servidor. */
export const ESTADO_ESPERANDO = "esperando";

/** Veredicto válido: el documento fue aprobado (D-4). */
export const ESTADO_ACEPTADO = "aceptado";

/** Veredicto de rechazo, con motivo y acción de UT-02. */
export const ESTADO_RECHAZADO = "rechazado";

/** Hubo respuesta, pero no un veredicto que se pueda mostrar. */
export const ESTADO_SIN_VEREDICTO = "sin-veredicto";

/**
 * Los únicos textos que escribe el frontend. Ninguno es un rechazo: los
 * rechazos los redacta UT-02 y llegan en el veredicto.
 */
export const TEXTOS = {
  esperando: {
    titulo: "Validando el archivo…",
    mensaje: "Un momento, se está revisando el espectro.",
  },
  aceptado: {
    // D-4: «la interfaz muestra que el documento fue aprobado».
    titulo: "Documento aprobado",
    mensaje: "El archivo pasó la validación y está listo para analizarse.",
    nota: "El análisis de los grupos funcionales llega en el siguiente incremento.",
  },
  sinVeredicto: {
    titulo: "No se pudo mostrar el resultado",
    mensaje: "El servidor no devolvió un resultado que se pueda mostrar.",
    accion: "Vuelva a intentarlo en un momento.",
  },
  sinServidor: {
    titulo: "No se pudo contactar al servidor",
    mensaje: "La aplicación no recibió respuesta al enviar el archivo.",
    accion: "Revise su conexión y vuelva a intentarlo.",
  },
};

/** Texto limpio de un campo del veredicto, o `""` si no sirve. */
function texto(valor) {
  return typeof valor === "string" ? valor.trim() : "";
}

function esObjeto(valor) {
  return typeof valor === "object" && valor !== null;
}

/** La vista base: sin resultado y con «Analizar» fuera de la pantalla. */
function base(estado) {
  return {
    estado,
    titulo: "",
    nombre: "",
    mensaje: "",
    accion: "",
    analizar: { visible: false, habilitado: false, nota: "" },
  };
}

/** Antes de validar nada. */
export function vistaInicial() {
  return base(ESTADO_INICIAL);
}

/** Mientras el archivo viaja al servidor. */
export function vistaEsperando(nombre = "") {
  return {
    ...base(ESTADO_ESPERANDO),
    titulo: TEXTOS.esperando.titulo,
    nombre: texto(nombre),
    mensaje: TEXTOS.esperando.mensaje,
  };
}

/** Hubo respuesta, pero no se puede mostrar un resultado con ella. */
export function vistaSinVeredicto(textos = TEXTOS.sinVeredicto) {
  return {
    ...base(ESTADO_SIN_VEREDICTO),
    titulo: textos.titulo,
    mensaje: textos.mensaje,
    accion: textos.accion,
  };
}

/**
 * La vista que corresponde a un veredicto (contrato de la sección 5).
 *
 * Aceptado → nombre del archivo, aviso de aprobado y «Analizar» habilitado y
 * sin acción (D-4). Rechazado → título, mensaje y acción del veredicto, sin el
 * código. Cualquier respuesta incompleta → `vistaSinVeredicto()`.
 *
 * @param {unknown} veredicto lo que respondió `POST /api/validar`.
 * @returns {object} la vista, siempre completa.
 */
export function vistaDeVeredicto(veredicto) {
  if (!esObjeto(veredicto) || typeof veredicto.valido !== "boolean") {
    return vistaSinVeredicto();
  }

  if (veredicto.valido) {
    // El nombre ya viene limpio de MOD-02: se pinta tal cual.
    const nombre = texto(veredicto.nombre);
    if (!nombre) {
      return vistaSinVeredicto();
    }
    return {
      estado: ESTADO_ACEPTADO,
      titulo: TEXTOS.aceptado.titulo,
      nombre,
      mensaje: TEXTOS.aceptado.mensaje,
      accion: "",
      analizar: {
        visible: true,
        habilitado: true,
        nota: TEXTOS.aceptado.nota,
      },
    };
  }

  const titulo = texto(veredicto.titulo);
  const mensaje = texto(veredicto.mensaje);
  const accion = texto(veredicto.accion);
  if (!titulo || !mensaje || !accion) {
    // Un rechazo sin motivo y acción incumpliría RNF-01: mejor decir que no se
    // pudo mostrar que pintar media explicación.
    return vistaSinVeredicto();
  }

  return {
    ...base(ESTADO_RECHAZADO),
    titulo,
    mensaje,
    accion,
  };
}

/**
 * La vista que corresponde a lo que devolvió el servicio de `servicios/`.
 *
 * @param {{resultado: string, veredicto: object|null}} respuesta
 */
export function vistaDesdeRespuesta(respuesta) {
  if (!esObjeto(respuesta)) {
    return vistaSinVeredicto();
  }

  if (respuesta.resultado === "sin-servidor") {
    return vistaSinVeredicto(TEXTOS.sinServidor);
  }

  // Un 500 también trae un mensaje genérico de UT-02 (sección 5): si se puede
  // mostrar, se muestra, porque es más útil que el aviso de aquí.
  return vistaDeVeredicto(respuesta.veredicto);
}
