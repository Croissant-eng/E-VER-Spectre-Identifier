/**
 * Pruebas del análisis en la página (incremento 3, T-18 y T-19).
 *
 * Cubren la vista, que decide qué se muestra, y el servicio, que llama a
 * /api/analizar. Todo con respuestas simuladas, sin navegador ni servidor.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ANALISIS_ESPERANDO,
  ANALISIS_FALLO,
  ANALISIS_LISTO,
  ANALISIS_OCULTO,
  ANALISIS_SIN_DETECCIONES,
  vistaAnalisisEsperando,
  vistaAnalisisOculta,
  vistaDeAnalisis,
} from "../interfaz/analisis.js";
import { RUTA_ANALIZAR, analizarEspectro } from "../servicios/analisis.js";

const CON_DETECCIONES = {
  resultado: "veredicto",
  datos: {
    valido: true,
    sin_detecciones: false,
    umbral: 0.6,
    modo: "reglas",
    detecciones: [
      {
        grupo: "GF-05",
        nombre: "C=O (carbonilo)",
        confianza: 0.94,
        porcentaje: 94,
        region_cm1: [1670, 1780],
        pico_cm1: 1715,
        evidencia: { regla: 0.94, ml: null },
      },
      {
        grupo: "GF-03",
        nombre: "C–H alifático",
        confianza: 0.6,
        porcentaje: 60,
        region_cm1: [2850, 2960],
        pico_cm1: 2950,
        evidencia: { regla: 0.6, ml: null },
      },
    ],
  },
};

const AVISO = {
  codigo: "SIN_DETECCIONES",
  titulo: "No se encontraron detecciones confiables",
  mensaje: "Ningún grupo funcional alcanzó el 60 % de confianza.",
  accion: "Revise la calidad del espectro y vuelva a analizarlo.",
};

const SIN_DETECCIONES = {
  resultado: "veredicto",
  datos: {
    valido: true,
    sin_detecciones: true,
    detecciones: [],
    umbral: 0.6,
    modo: "reglas",
    aviso: AVISO,
  },
};

const FALLO_DEL_MOTOR = {
  resultado: "fallo",
  datos: {
    valido: false,
    codigo: "ANALISIS_FALLIDO",
    titulo: "Análisis no completado",
    mensaje: "No fue posible completar el análisis; intenta de nuevo.",
    accion: "Pulse «Analizar» otra vez.",
  },
};

describe("vista del análisis", () => {
  it("nace oculta y luego espera", () => {
    assert.equal(vistaAnalisisOculta().estado, ANALISIS_OCULTO);
    const esperando = vistaAnalisisEsperando();
    assert.equal(esperando.estado, ANALISIS_ESPERANDO);
    assert.ok(esperando.titulo);
  });

  it("T-18: lista los grupos en el orden en que llegan, con su porcentaje", () => {
    const vista = vistaDeAnalisis(CON_DETECCIONES);

    assert.equal(vista.estado, ANALISIS_LISTO);
    assert.deepEqual(
      vista.filas.map((f) => [f.grupo, f.confianza]),
      [
        ["GF-05", "94 %"],
        ["GF-03", "60 %"],
      ],
    );
  });

  it("D-15: muestra el porcentaje que mandó el servidor, sin recalcularlo", () => {
    const respuesta = structuredClone(CON_DETECCIONES);
    respuesta.datos.detecciones[1].confianza = 0.595;
    respuesta.datos.detecciones[1].porcentaje = 60;

    assert.equal(vistaDeAnalisis(respuesta).filas[1].confianza, "60 %");
  });

  it("CA-08: sin detecciones muestra el aviso y ninguna fila", () => {
    const vista = vistaDeAnalisis(SIN_DETECCIONES);

    assert.equal(vista.estado, ANALISIS_SIN_DETECCIONES);
    assert.equal(vista.titulo, "No se encontraron detecciones confiables");
    assert.ok(vista.accion.includes("calidad del espectro"));
    assert.deepEqual(vista.filas, []);
  });

  it("CA-05.4: un fallo del motor muestra el mensaje del servidor", () => {
    const vista = vistaDeAnalisis(FALLO_DEL_MOTOR);

    assert.equal(vista.estado, ANALISIS_FALLO);
    assert.equal(vista.mensaje, "No fue posible completar el análisis; intenta de nuevo.");
    assert.deepEqual(vista.filas, []);
    assert.ok(!JSON.stringify(vista).includes("ANALISIS_FALLIDO"), "el código no se muestra");
  });

  it("sin servidor avisa y deja reintentar", () => {
    const vista = vistaDeAnalisis({ resultado: "sin-servidor", datos: null });

    assert.equal(vista.estado, ANALISIS_FALLO);
    assert.ok(vista.accion.includes("Analizar"));
  });

  it("nunca pinta una lista a medias", () => {
    const incompleta = structuredClone(CON_DETECCIONES);
    delete incompleta.datos.detecciones[1].porcentaje;
    const sinAviso = structuredClone(SIN_DETECCIONES);
    delete sinAviso.datos.aviso;

    for (const respuesta of [incompleta, sinAviso, { resultado: "veredicto", datos: null }, null]) {
      const vista = vistaDeAnalisis(respuesta);
      assert.equal(vista.estado, ANALISIS_FALLO);
      assert.deepEqual(vista.filas, []);
    }
  });
});

describe("servicio de análisis", () => {
  const espectro = { eje_cm1: [4000, 400], intensidad: [0, 1], rango_medido_cm1: [400, 4000] };

  it("manda el espectro en JSON a la ruta del análisis", async () => {
    let llamada;
    const traer = async (ruta, opciones) => {
      llamada = { ruta, opciones };
      return { ok: true, json: async () => SIN_DETECCIONES.datos };
    };

    const respuesta = await analizarEspectro(espectro, { fetch: traer });

    assert.equal(llamada.ruta, RUTA_ANALIZAR);
    assert.equal(llamada.opciones.method, "POST");
    assert.equal(llamada.opciones.headers["Content-Type"], "application/json");
    assert.deepEqual(JSON.parse(llamada.opciones.body), espectro);
    assert.equal(respuesta.resultado, "veredicto");
  });

  it("distingue el fallo del servidor y la falta de red", async () => {
    const fallo = await analizarEspectro(espectro, {
      fetch: async () => ({ ok: false, json: async () => FALLO_DEL_MOTOR.datos }),
    });
    const sinRed = await analizarEspectro(espectro, {
      fetch: async () => {
        throw new TypeError("sin red");
      },
    });

    assert.equal(fallo.resultado, "fallo");
    assert.equal(fallo.datos.codigo, "ANALISIS_FALLIDO");
    assert.equal(sinRed.resultado, "sin-servidor");
  });

  it("la ruta coincide con la del servidor", async () => {
    const { readFile } = await import("node:fs/promises");
    const python = await readFile(
      new URL("../../backend/api/aplicacion.py", import.meta.url),
      "utf8",
    );
    assert.ok(python.includes(`RUTA_ANALIZAR: str = "${RUTA_ANALIZAR}"`));
  });
});
