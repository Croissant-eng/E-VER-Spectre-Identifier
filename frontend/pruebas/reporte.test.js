/**
 * Pruebas del reporte en la página (incremento 5).
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  REPORTE_DESCARGADO,
  REPORTE_FALLO,
  REPORTE_GENERANDO,
  REPORTE_OCULTO,
  vistaDeReporte,
  vistaReporteGenerando,
  vistaReporteListo,
  vistaReporteOculta,
} from "../interfaz/reporte.js";
import {
  RESULTADO_PDF,
  RUTA_REPORTE,
  nombreDeDescarga,
  pedirReporte,
} from "../servicios/reporte.js";

const FALLO = {
  valido: false,
  codigo: "REPORTE_FALLIDO",
  titulo: "No se pudo generar el reporte",
  mensaje: "Ocurrió un problema al generar el PDF. Sus resultados siguen en pantalla.",
  accion: "Pulse «Descargar reporte» para intentarlo de nuevo.",
};

function respuestaFalsa({ ok, tipo, cuerpo, disposicion }) {
  const cabeceras = new Map([
    ["content-type", tipo],
    ["content-disposition", disposicion ?? ""],
  ]);
  return {
    ok,
    headers: { get: (nombre) => cabeceras.get(nombre.toLowerCase()) ?? null },
    blob: async () => new Blob([cuerpo ?? ""], { type: tipo }),
    json: async () => (typeof cuerpo === "object" ? cuerpo : JSON.parse(cuerpo)),
  };
}

describe("vista del reporte", () => {
  it("nace oculta, se habilita con un análisis y se deshabilita mientras genera", () => {
    assert.equal(vistaReporteOculta().estado, REPORTE_OCULTO);
    assert.equal(vistaReporteOculta().habilitado, false);
    assert.equal(vistaReporteListo().habilitado, true);
    assert.equal(vistaReporteGenerando().estado, REPORTE_GENERANDO);
    assert.equal(vistaReporteGenerando().habilitado, false);
  });

  it("al llegar el PDF avisa que se descargó", () => {
    const vista = vistaDeReporte({ resultado: RESULTADO_PDF });
    assert.equal(vista.estado, REPORTE_DESCARGADO);
    assert.equal(vista.habilitado, true);
  });

  it("CA-09.3: un fallo muestra el mensaje y deja reintentar", () => {
    const vista = vistaDeReporte({ resultado: "fallo", datos: FALLO });

    assert.equal(vista.estado, REPORTE_FALLO);
    assert.equal(vista.titulo, FALLO.titulo);
    assert.ok(vista.accion.includes("Descargar reporte"));
    assert.equal(vista.habilitado, true, "el botón queda listo para reintentar");
    assert.ok(!JSON.stringify(vista).includes("REPORTE_FALLIDO"));
  });

  it("sin servidor o sin mensaje completo usa sus propios textos", () => {
    assert.equal(vistaDeReporte({ resultado: "sin-servidor", datos: null }).estado, REPORTE_FALLO);
    const incompleto = vistaDeReporte({ resultado: "fallo", datos: { titulo: "x" } });
    assert.ok(incompleto.accion.includes("Descargar reporte"));
  });
});

describe("servicio del reporte", () => {
  it("manda el cuerpo en JSON y entrega el PDF con su nombre", async () => {
    let llamada;
    const traer = async (ruta, opciones) => {
      llamada = { ruta, opciones };
      return respuestaFalsa({
        ok: true,
        tipo: "application/pdf",
        cuerpo: "%PDF-1.4",
        disposicion: 'attachment; filename="reporte-cetona.pdf"',
      });
    };
    const cuerpo = { nombre: "cetona.csv", espectro: {}, grafica_png: "data:", zona_horaria_min: 360 };

    const respuesta = await pedirReporte(cuerpo, { fetch: traer });

    assert.equal(llamada.ruta, RUTA_REPORTE);
    assert.deepEqual(JSON.parse(llamada.opciones.body), cuerpo);
    assert.equal(respuesta.resultado, RESULTADO_PDF);
    assert.equal(respuesta.nombre, "reporte-cetona.pdf");
    assert.ok(respuesta.pdf instanceof Blob);
  });

  it("un rechazo en JSON no se toma por PDF", async () => {
    const respuesta = await pedirReporte(
      {},
      { fetch: async () => respuestaFalsa({ ok: false, tipo: "application/json", cuerpo: FALLO }) },
    );
    assert.equal(respuesta.resultado, "fallo");
    assert.equal(respuesta.datos.codigo, "REPORTE_FALLIDO");
  });

  it("sin red no lanza", async () => {
    const respuesta = await pedirReporte({}, {
      fetch: async () => {
        throw new TypeError("sin red");
      },
    });
    assert.equal(respuesta.resultado, "sin-servidor");
  });

  it("toma el nombre de Content-Disposition o usa uno de respaldo", () => {
    assert.equal(nombreDeDescarga('attachment; filename="a.pdf"'), "a.pdf");
    assert.equal(nombreDeDescarga(null), "reporte.pdf");
  });

  it("la ruta coincide con la del servidor", async () => {
    const { readFile } = await import("node:fs/promises");
    const python = await readFile(new URL("../../backend/api/aplicacion.py", import.meta.url), "utf8");
    assert.ok(python.includes(`RUTA_REPORTE: str = "${RUTA_REPORTE}"`));
  });
});
