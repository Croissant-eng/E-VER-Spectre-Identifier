/**
 * MOD-01, la vista del análisis (incremento 3, T-18 y T-19).
 *
 * Igual que vista.js, este archivo no toca el DOM. Recibe lo que devolvió el
 * servicio de análisis y arma un objeto plano con lo que hay que mostrar. Así
 * se prueba con respuestas simuladas, sin navegador y sin servidor.
 *
 * Cinco estados:
 *
 * oculta: todavía no se ha pedido ningún análisis.
 * esperando: el espectro va camino al motor.
 * lista: hay grupos detectados, de mayor a menor confianza (T-18).
 * sin-detecciones: el motor analizó y ningún grupo llegó al umbral. Se
 *   muestra el aviso de UT-02 y ninguna fila de grupo (CA-08). No es un error.
 * fallo: el motor falló o el espectro no tenía la forma esperada. Se
 *   muestran título, mensaje y acción del servidor, sin detalles técnicos, y
 *   el archivo se queda cargado para reintentar (CA-05.4).
 *
 * El porcentaje que se muestra es el mismo número con el que el motor decidió
 * (D-15). Este archivo no lo recalcula: lo toma tal cual de la respuesta.
 */

export const ANALISIS_OCULTO = "oculta";
export const ANALISIS_ESPERANDO = "esperando";
export const ANALISIS_LISTO = "lista";
export const ANALISIS_SIN_DETECCIONES = "sin-detecciones";
export const ANALISIS_FALLO = "fallo";

/** Los únicos textos que escribe la página en esta parte. */
export const TEXTOS_ANALISIS = {
  esperando: {
    titulo: "Analizando el espectro…",
    mensaje: "Un momento, se están buscando los grupos funcionales.",
  },
  lista: {
    titulo: "Grupos funcionales detectados",
    mensaje: "Ordenados de mayor a menor confianza.",
  },
  sinRespuesta: {
    titulo: "No se pudo mostrar el análisis",
    mensaje: "El servidor no devolvió un resultado que se pueda mostrar.",
    accion: "Pulse «Analizar» otra vez.",
  },
  sinServidor: {
    titulo: "No se pudo contactar al servidor",
    mensaje: "La aplicación no recibió respuesta al pedir el análisis.",
    accion: "Revise su conexión y pulse «Analizar» otra vez.",
  },
};

function texto(valor) {
  return typeof valor === "string" ? valor.trim() : "";
}

function esObjeto(valor) {
  return typeof valor === "object" && valor !== null;
}

function base(estado) {
  return { estado, titulo: "", mensaje: "", accion: "", filas: [] };
}

export function vistaAnalisisOculta() {
  return base(ANALISIS_OCULTO);
}

export function vistaAnalisisEsperando() {
  return {
    ...base(ANALISIS_ESPERANDO),
    titulo: TEXTOS_ANALISIS.esperando.titulo,
    mensaje: TEXTOS_ANALISIS.esperando.mensaje,
  };
}

function vistaDeFallo(textos) {
  return {
    ...base(ANALISIS_FALLO),
    titulo: textos.titulo,
    mensaje: textos.mensaje,
    accion: textos.accion,
  };
}

/** Un mensaje del servidor, o null si le falta alguna de sus tres partes. */
function mensajeCompleto(datos) {
  if (!esObjeto(datos)) {
    return null;
  }
  const completo = {
    titulo: texto(datos.titulo),
    mensaje: texto(datos.mensaje),
    accion: texto(datos.accion),
  };
  return completo.titulo && completo.mensaje && completo.accion ? completo : null;
}

/** El texto de respaldo si el servidor no mandó el aviso completo. */
export const EXPLICACION_NO_DISPONIBLE = "Explicación no disponible";

/**
 * La explicación de MOD-07 lista para pintar (incremento 4), o null si la
 * respuesta no trae ninguna.
 *
 * Disponible: sus partes en el orden de CA-07.1 (región, posición, rasgo y
 * porqué) más la distinción si la hay (CA-07.2). No disponible: el aviso de
 * UT-02 (CA-07.3), y el grupo se sigue mostrando.
 */
function explicacionDe(explicacion) {
  if (!esObjeto(explicacion)) {
    return null;
  }
  if (explicacion.disponible === true) {
    const partes = ["region", "posicion", "rasgo", "por_que", "distincion"]
      .map((clave) => texto(explicacion[clave]))
      .filter((parte) => parte !== "");
    if (partes.length > 0) {
      return { disponible: true, partes };
    }
  }
  return {
    disponible: false,
    titulo: texto(explicacion.titulo) || EXPLICACION_NO_DISPONIBLE,
    mensaje: texto(explicacion.mensaje),
    accion: texto(explicacion.accion),
  };
}

function esRegion(valor) {
  return (
    Array.isArray(valor) &&
    valor.length === 2 &&
    valor.every((x) => typeof x === "number" && Number.isFinite(x))
  );
}

/** Una fila de la lista, o null si la detección viene incompleta. */
function filaDe(deteccion) {
  if (!esObjeto(deteccion)) {
    return null;
  }
  const grupo = texto(deteccion.grupo);
  const nombre = texto(deteccion.nombre);
  const porcentaje = deteccion.porcentaje;
  if (!grupo || !nombre || !Number.isInteger(porcentaje)) {
    return null;
  }
  const pico = deteccion.pico_cm1;
  return {
    grupo,
    nombre,
    porcentaje,
    confianza: `${porcentaje} %`,
    // Lo que necesita el resaltado (T-23 y T-24). Sin región no se resalta.
    region_cm1: esRegion(deteccion.region_cm1) ? deteccion.region_cm1 : null,
    pico_cm1: typeof pico === "number" && Number.isFinite(pico) ? pico : null,
    explicacion: explicacionDe(deteccion.explicacion),
  };
}

/**
 * La vista que corresponde a la respuesta del servicio de análisis.
 *
 * @param {{resultado: string, datos: object|null}} respuesta
 * @returns {object} la vista, siempre completa.
 */
export function vistaDeAnalisis(respuesta) {
  if (!esObjeto(respuesta)) {
    return vistaDeFallo(TEXTOS_ANALISIS.sinRespuesta);
  }
  if (respuesta.resultado === "sin-servidor") {
    return vistaDeFallo(TEXTOS_ANALISIS.sinServidor);
  }

  const datos = respuesta.datos;
  if (!esObjeto(datos) || typeof datos.valido !== "boolean") {
    return vistaDeFallo(TEXTOS_ANALISIS.sinRespuesta);
  }

  // Un rechazo o un fallo del motor: el texto viene de UT-02 (CA-05.4).
  if (!datos.valido || respuesta.resultado !== "veredicto") {
    return vistaDeFallo(mensajeCompleto(datos) ?? TEXTOS_ANALISIS.sinRespuesta);
  }

  if (datos.sin_detecciones === true) {
    const aviso = mensajeCompleto(datos.aviso);
    if (!aviso) {
      return vistaDeFallo(TEXTOS_ANALISIS.sinRespuesta);
    }
    return { ...base(ANALISIS_SIN_DETECCIONES), ...aviso };
  }

  if (!Array.isArray(datos.detecciones) || datos.detecciones.length === 0) {
    return vistaDeFallo(TEXTOS_ANALISIS.sinRespuesta);
  }
  const filas = datos.detecciones.map(filaDe);
  if (filas.some((fila) => fila === null)) {
    // Una lista a medias podría esconder justo el grupo importante.
    return vistaDeFallo(TEXTOS_ANALISIS.sinRespuesta);
  }

  return {
    ...base(ANALISIS_LISTO),
    titulo: TEXTOS_ANALISIS.lista.titulo,
    mensaje: TEXTOS_ANALISIS.lista.mensaje,
    filas,
  };
}
