/**
 * Pruebas del servicio que llama a `POST /api/procesar` (incremento 2).
 *
 * El `fetch` se simula y se inyecta, igual que en las pruebas del servicio de
 * validación. Aquí no hay red.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { RUTA_PROCESAR, procesarEspectro } from "../servicios/procesamiento.js";
import {
  CAMPO_ARCHIVO,
  RESULTADO_FALLO,
  RESULTADO_SIN_SERVIDOR,
  RESULTADO_VEREDICTO,
} from "../servicios/validacion.js";

const ARCHIVO = new File(["onda,absorbancia\n400.0,0.80\n500.0,0.75\n"], "a.csv");

function fetchSimulado({ estado = 200, cuerpo = {}, roto = false, sinRed = false } = {}) {
  const llamadas = [];
  const simulado = async (ruta, opciones) => {
    llamadas.push({ ruta, opciones });
    if (sinRed) {
      throw new TypeError("Failed to fetch");
    }
    return {
      ok: estado >= 200 && estado < 300,
      status: estado,
      json: async () => {
        if (roto) {
          throw new SyntaxError("no es JSON");
        }
        return cuerpo;
      },
    };
  };
  simulado.llamadas = llamadas;
  return simulado;
}

describe("la llamada a /api/procesar", () => {
  it("es un POST con el archivo en el campo «archivo»", async () => {
    const traer = fetchSimulado({ cuerpo: { valido: true } });
    await procesarEspectro(ARCHIVO, { fetch: traer });

    assert.equal(traer.llamadas[0].ruta, RUTA_PROCESAR);
    assert.equal(traer.llamadas[0].opciones.method, "POST");
    assert.equal(traer.llamadas[0].opciones.body.get(CAMPO_ARCHIVO).name, "a.csv");
  });

  it("un 200 entrega lo que llegó, sea espectro o rechazo", async () => {
    const cuerpo = { valido: false, titulo: "t", mensaje: "m", accion: "a" };
    const respuesta = await procesarEspectro(ARCHIVO, { fetch: fetchSimulado({ cuerpo }) });
    assert.deepEqual(respuesta, { resultado: RESULTADO_VEREDICTO, datos: cuerpo });
  });

  it("un 500 es un fallo, con el cuerpo si se pudo leer", async () => {
    const cuerpo = { valido: false, titulo: "t", mensaje: "m", accion: "a" };
    const respuesta = await procesarEspectro(ARCHIVO, {
      fetch: fetchSimulado({ estado: 500, cuerpo }),
    });
    assert.deepEqual(respuesta, { resultado: RESULTADO_FALLO, datos: cuerpo });
  });

  it("un cuerpo roto no lanza", async () => {
    const respuesta = await procesarEspectro(ARCHIVO, { fetch: fetchSimulado({ roto: true }) });
    assert.deepEqual(respuesta, { resultado: RESULTADO_VEREDICTO, datos: null });
  });

  it("sin red no lanza", async () => {
    const respuesta = await procesarEspectro(ARCHIVO, { fetch: fetchSimulado({ sinRed: true }) });
    assert.deepEqual(respuesta, { resultado: RESULTADO_SIN_SERVIDOR, datos: null });
  });
});
