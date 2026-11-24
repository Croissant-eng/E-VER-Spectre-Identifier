/**
 * Pruebas del resaltado sobre la gráfica y de la explicación en la lista
 * (incremento 4: T-21 a T-24).
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { EXPLICACION_NO_DISPONIBLE, vistaDeAnalisis } from "../interfaz/analisis.js";
import {
  COLORES_GRUPO,
  anotacionesDe,
  colorDe,
  leyendaDe,
} from "../visor-espectro/resaltado.js";

const CARBONILO = {
  grupo: "GF-05",
  nombre: "C=O (carbonilo)",
  region_cm1: [1670, 1780],
  pico_cm1: 1715,
};
const OH = { grupo: "GF-01", nombre: "O–H", region_cm1: [3200, 3550], pico_cm1: 3350 };
const NH = { grupo: "GF-02", nombre: "N–H", region_cm1: [3300, 3500], pico_cm1: 3420 };

describe("resaltado en la gráfica", () => {
  it("CA-06.1: resalta la región del carbonilo y marca su pico", () => {
    const anotaciones = anotacionesDe([CARBONILO]);

    assert.equal(anotaciones["region-GF-05"].type, "box");
    assert.equal(anotaciones["region-GF-05"].xMin, 1670);
    assert.equal(anotaciones["region-GF-05"].xMax, 1780);
    assert.equal(anotaciones["pico-GF-05"].type, "line");
    assert.equal(anotaciones["pico-GF-05"].xMin, 1715);
    assert.equal(anotaciones["pico-GF-05"].xMax, 1715);
  });

  it("CA-06.2: O–H y N–H llevan cada uno su color y su entrada en la leyenda", () => {
    const anotaciones = anotacionesDe([OH, NH]);
    const leyenda = leyendaDe([OH, NH]);

    assert.notEqual(anotaciones["pico-GF-01"].borderColor, anotaciones["pico-GF-02"].borderColor);
    assert.notEqual(
      anotaciones["region-GF-01"].backgroundColor,
      anotaciones["region-GF-02"].backgroundColor,
    );
    assert.deepEqual(
      leyenda.map((e) => e.grupo),
      ["GF-01", "GF-02"],
    );
    assert.notEqual(leyenda[0].color, leyenda[1].color);
    assert.equal(leyenda[0].color, colorDe("GF-01"));
  });

  it("los siete grupos tienen colores distintos", () => {
    const colores = Object.values(COLORES_GRUPO).map((c) => c.join(","));
    assert.equal(colores.length, 7);
    assert.equal(new Set(colores).size, 7);
  });

  it("CA-06.3: sin posición de pico resalta la región completa y lo dice", () => {
    const sinPico = { ...CARBONILO, pico_cm1: null };

    const anotaciones = anotacionesDe([sinPico]);
    const [entrada] = leyendaDe([sinPico]);

    assert.ok(anotaciones["region-GF-05"], "la gráfica no se queda sin marca");
    assert.equal(anotaciones["pico-GF-05"], undefined);
    assert.ok(anotaciones["region-GF-05"].borderWidth > 0);
    assert.ok(entrada.detalle.includes("completa"));
  });

  it("sin grupos elegidos no queda nada resaltado", () => {
    assert.deepEqual(anotacionesDe([]), {});
    assert.deepEqual(leyendaDe([]), []);
  });

  it("un grupo sin región no se dibuja", () => {
    assert.deepEqual(anotacionesDe([{ grupo: "GF-05", region_cm1: null, pico_cm1: 1715 }]), {});
  });
});

function respuestaCon(explicacion, extra = {}) {
  return {
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
          confianza: 0.9,
          porcentaje: 90,
          region_cm1: [1670, 1780],
          pico_cm1: 1715,
          evidencia: { regla: 0.9, ml: null },
          explicacion,
          ...extra,
        },
      ],
    },
  };
}

describe("explicación en la lista", () => {
  it("CA-07.1: trae las partes en orden", () => {
    const vista = vistaDeAnalisis(
      respuestaCon({
        disponible: true,
        region: "Su región característica está entre 1670 y 1780 cm⁻¹.",
        posicion: "El pico observado está en 1715 cm⁻¹.",
        rasgo: "Lo delata un pico intenso y agudo.",
        por_que: "El doble enlace es muy polar.",
        distincion: null,
      }),
    );

    const fila = vista.filas[0];
    assert.equal(fila.explicacion.disponible, true);
    assert.equal(fila.explicacion.partes.length, 4);
    assert.ok(fila.explicacion.partes[2].includes("pico intenso y agudo"));
    assert.deepEqual(fila.region_cm1, [1670, 1780]);
    assert.equal(fila.pico_cm1, 1715);
  });

  it("CA-07.3: sin plantilla el grupo sigue y lleva el aviso", () => {
    const vista = vistaDeAnalisis(
      respuestaCon({ disponible: false, titulo: "Explicación no disponible", mensaje: "x", accion: "y." }),
    );

    assert.equal(vista.estado, "lista");
    assert.equal(vista.filas.length, 1);
    assert.equal(vista.filas[0].explicacion.disponible, false);
    assert.equal(vista.filas[0].explicacion.titulo, EXPLICACION_NO_DISPONIBLE);
  });

  it("el pico nulo se conserva como nulo para CA-06.3", () => {
    const vista = vistaDeAnalisis(respuestaCon(undefined, { pico_cm1: null }));

    assert.equal(vista.filas[0].pico_cm1, null);
    assert.equal(vista.filas[0].explicacion, null);
  });
});
