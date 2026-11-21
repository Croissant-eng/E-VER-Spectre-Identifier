/**
 * Pruebas de T-06 · el servicio que llamará a `POST /api/validar` (D-5).
 *
 * El endpoint **no existe todavía** (es T-07), así que el `fetch` se simula y
 * se inyecta. Lo que se prueba es que la llamada cumpla el contrato —ruta,
 * método, `multipart/form-data` con el campo `archivo`— y que ninguna respuesta
 * rota se convierta en una excepción.
 *
 * Aquí no hay red: el `fetch` simulado nunca sale a ninguna parte.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  CAMPO_ARCHIVO,
  RESULTADO_FALLO,
  RESULTADO_SIN_SERVIDOR,
  RESULTADO_VEREDICTO,
  RUTA_VALIDAR,
  validarEspectro,
} from "../servicios/validacion.js";

const ARCHIVO = new File(["400.0,0.80\n500.0,0.75\n"], "acetona.csv", {
  type: "text/csv",
});

/** Un `fetch` simulado que anota cómo lo llamaron. */
function fetchSimulado({ estado = 200, cuerpo = {}, roto = false } = {}) {
  const llamadas = [];
  const simulado = async (ruta, opciones) => {
    llamadas.push({ ruta, opciones });
    return {
      ok: estado >= 200 && estado < 300,
      status: estado,
      json: async () => {
        if (roto) {
          throw new SyntaxError("el cuerpo no es JSON");
        }
        return cuerpo;
      },
    };
  };
  simulado.llamadas = llamadas;
  return simulado;
}

describe("la llamada cumple el contrato D-5", () => {
  it("es un POST a /api/validar", async () => {
    const traer = fetchSimulado({ cuerpo: { valido: true, nombre: "a.csv" } });

    await validarEspectro(ARCHIVO, { fetch: traer });

    assert.equal(traer.llamadas.length, 1);
    assert.equal(traer.llamadas[0].ruta, RUTA_VALIDAR);
    assert.equal(traer.llamadas[0].opciones.method, "POST");
  });

  it("manda el archivo en el campo «archivo», como formulario", async () => {
    const traer = fetchSimulado({ cuerpo: { valido: true, nombre: "a.csv" } });

    await validarEspectro(ARCHIVO, { fetch: traer });
    const cuerpo = traer.llamadas[0].opciones.body;

    assert.ok(cuerpo instanceof FormData, "multipart/form-data");
    assert.equal(cuerpo.get(CAMPO_ARCHIVO), ARCHIVO);
    assert.equal(cuerpo.get(CAMPO_ARCHIVO).name, "acetona.csv");
  });

  it("no le pone a mano el encabezado de tipo de contenido", async () => {
    // Lo pone el navegador junto con la frontera del multipart; escribirlo a
    // mano rompe la subida.
    const traer = fetchSimulado({ cuerpo: { valido: true, nombre: "a.csv" } });

    await validarEspectro(ARCHIVO, { fetch: traer });

    assert.equal(traer.llamadas[0].opciones.headers, undefined);
  });
});

describe("lo que devuelve", () => {
  it("un 200 aceptado trae el veredicto tal cual", async () => {
    const veredicto = { valido: true, nombre: "acetona.jdx", bytes: 307200 };

    const respuesta = await validarEspectro(ARCHIVO, {
      fetch: fetchSimulado({ cuerpo: veredicto }),
    });

    assert.equal(respuesta.resultado, RESULTADO_VEREDICTO);
    assert.deepEqual(respuesta.veredicto, veredicto);
  });

  it("un 200 rechazado también es un resultado, no un error", async () => {
    const veredicto = {
      valido: false,
      codigo: "FORMATO_NO_SOPORTADO",
      titulo: "Formato no admitido",
      mensaje: "Formato no soportado. Formatos admitidos: .jdx, .csv",
      accion: "Exporte el espectro en uno de los formatos admitidos.",
    };

    const respuesta = await validarEspectro(ARCHIVO, {
      fetch: fetchSimulado({ cuerpo: veredicto }),
    });

    assert.equal(respuesta.resultado, RESULTADO_VEREDICTO);
    assert.equal(respuesta.veredicto.codigo, "FORMATO_NO_SOPORTADO");
  });

  it("un 500 se distingue, y conserva el mensaje genérico si vino", async () => {
    const respuesta = await validarEspectro(ARCHIVO, {
      fetch: fetchSimulado({
        estado: 500,
        cuerpo: { valido: false, codigo: "CONFIGURACION_INCOMPLETA" },
      }),
    });

    assert.equal(respuesta.resultado, RESULTADO_FALLO);
    assert.equal(respuesta.veredicto.codigo, "CONFIGURACION_INCOMPLETA");
  });

  it("un cuerpo que no es JSON no tumba la llamada", async () => {
    const respuesta = await validarEspectro(ARCHIVO, {
      fetch: fetchSimulado({ roto: true }),
    });

    assert.equal(respuesta.resultado, RESULTADO_VEREDICTO);
    assert.equal(respuesta.veredicto, null);
  });

  it("un cuerpo que es JSON pero no objeto se descarta", async () => {
    const respuesta = await validarEspectro(ARCHIVO, {
      fetch: fetchSimulado({ cuerpo: "aceptado" }),
    });

    assert.equal(respuesta.veredicto, null);
  });

  it("si no hay servidor lo dice, sin arrastrar la excepción", async () => {
    const traer = async () => {
      throw new TypeError("Failed to fetch");
    };

    const respuesta = await validarEspectro(ARCHIVO, { fetch: traer });

    assert.equal(respuesta.resultado, RESULTADO_SIN_SERVIDOR);
    assert.equal(respuesta.veredicto, null);
  });

  it("si le pasan algo que no es fetch, avisa al programador", async () => {
    // Un error de programación no se disfraza de mensaje para el usuario.
    await assert.rejects(
      () => validarEspectro(ARCHIVO, { fetch: "no soy una función" }),
      TypeError,
    );
  });
});
