/**
 * Pruebas de T-12 y T-13, la parte que decide de MOD-05.
 *
 * Corren con el corredor que ya trae Node (D-9), igual que las de MOD-01:
 *
 *     node --test frontend/pruebas
 *
 * Se prueba la construcción de la configuración de Chart.js como función pura
 * (espectro a configuración), como pide el plan del incremento 2, y la
 * decisión de cuándo hay gráfica y cuándo un mensaje. La verificación visual
 * va por captura (herramientas/capturar_grafica.py).
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  RESULTADO_FALLO,
  RESULTADO_SIN_SERVIDOR,
  RESULTADO_VEREDICTO,
} from "../servicios/validacion.js";
import {
  GRAFICA_ESPERANDO,
  GRAFICA_LISTA,
  GRAFICA_OCULTA,
  GRAFICA_SIN_ESPECTRO,
  TEXTOS,
  configuracionDeGrafica,
  puntosGraficables,
  vistaDeGrafica,
  vistaGraficaEsperando,
  vistaGraficaOculta,
} from "../visor-espectro/configuracion.js";

/** Un espectro como el del contrato: rejilla de mayor a menor, 0 a 1. */
function espectro({ puntos = 10, desde = 4000, hasta = 400, medido = [400, 4000] } = {}) {
  const paso = (hasta - desde) / (puntos - 1);
  const eje = Array.from({ length: puntos }, (_, i) => desde + i * paso);
  const intensidad = eje.map((_, i) => (i % 3) / 2);
  return { eje_cm1: eje, intensidad, rango_medido_cm1: medido, unidad_original: "absorbancia" };
}

const PROCESADO = { valido: true, nombre: "acetona.jdx", espectro: espectro() };

describe("CA-04.1: la configuración de la gráfica", () => {
  it("pone el número de onda en el eje horizontal, de mayor a menor", () => {
    const config = configuracionDeGrafica(espectro());
    assert.equal(config.options.scales.x.type, "linear");
    assert.equal(config.options.scales.x.reverse, true);
    assert.equal(config.options.scales.x.title.text, TEXTOS.ejeX);
  });

  it("toma los límites del eje del espectro que mandó el servidor", () => {
    const config = configuracionDeGrafica(espectro({ desde: 3000, hasta: 500 }));
    assert.equal(config.options.scales.x.min, 500);
    assert.equal(config.options.scales.x.max, 3000);
  });

  it("pone la intensidad normalizada en el eje vertical, de 0 a 1", () => {
    const config = configuracionDeGrafica(espectro());
    assert.equal(config.options.scales.y.min, 0);
    assert.equal(config.options.scales.y.max, 1);
    assert.equal(config.options.scales.y.title.text, TEXTOS.ejeY);
  });

  it("mapea cada punto como número de onda e intensidad", () => {
    const entrada = espectro({ puntos: 4 });
    const datos = configuracionDeGrafica(entrada).data.datasets[0].data;
    assert.deepEqual(
      datos,
      entrada.eje_cm1.map((x, i) => ({ x, y: entrada.intensidad[i] })),
    );
  });

  it("se ajusta al ancho de la pantalla (CA-04.2)", () => {
    const opciones = configuracionDeGrafica(espectro()).options;
    assert.equal(opciones.responsive, true);
    assert.equal(opciones.maintainAspectRatio, false);
  });

  it("deja listo el complemento de anotaciones para el incremento 4", () => {
    const opciones = configuracionDeGrafica(espectro()).options;
    assert.deepEqual(opciones.plugins.annotation, { annotations: {} });
  });

  it("no acepta un espectro que no se puede dibujar", () => {
    assert.throws(() => configuracionDeGrafica({}), TypeError);
  });
});

describe("solo se dibuja el tramo que el archivo midió", () => {
  it("deja fuera los puntos de la rejilla que no se midieron", () => {
    const puntos = puntosGraficables(espectro({ puntos: 10, medido: [1600, 2800] }));
    assert.ok(puntos.length > 0);
    assert.ok(puntos.every((p) => p.x >= 1600 && p.x <= 2800));
  });

  for (const [caso, roto] of [
    ["sin eje", { intensidad: [0, 1], rango_medido_cm1: [400, 4000] }],
    ["largos distintos", { ...espectro(), intensidad: [0, 1] }],
    ["un valor que no es número", { ...espectro({ puntos: 2 }), intensidad: [0, "x"] }],
    ["sin tramo medido", { ...espectro(), rango_medido_cm1: null }],
    ["un tramo con un solo punto", espectro({ puntos: 10, medido: [3990, 3999] })],
  ]) {
    it(`no hay puntos con ${caso}`, () => {
      assert.equal(puntosGraficables(roto), null);
    });
  }
});

describe("CA-04.3: nunca una gráfica vacía", () => {
  it("antes de aprobar un archivo no hay sección de gráfica", () => {
    assert.equal(vistaGraficaOculta().estado, GRAFICA_OCULTA);
    assert.equal(vistaGraficaOculta().espectro, null);
  });

  it("mientras se procesa dice que está esperando", () => {
    const vista = vistaGraficaEsperando();
    assert.equal(vista.estado, GRAFICA_ESPERANDO);
    assert.equal(vista.espectro, null);
  });

  it("con espectro, la gráfica", () => {
    const vista = vistaDeGrafica({ resultado: RESULTADO_VEREDICTO, datos: PROCESADO });
    assert.equal(vista.estado, GRAFICA_LISTA);
    assert.deepEqual(vista.espectro, PROCESADO.espectro);
    assert.equal(vista.mensaje, "");
  });

  it("con un rechazo de MOD-04, su mensaje de UT-02 y nada de gráfica", () => {
    const rechazo = {
      valido: false,
      codigo: "SIN_SENAL",
      titulo: "Sin señal analizable",
      mensaje: "El espectro no contiene señal analizable.",
      accion: "Revise la medición.",
    };
    const vista = vistaDeGrafica({ resultado: RESULTADO_VEREDICTO, datos: rechazo });
    assert.equal(vista.estado, GRAFICA_SIN_ESPECTRO);
    assert.equal(vista.espectro, null);
    assert.equal(vista.titulo, rechazo.titulo);
    assert.equal(vista.accion, rechazo.accion);
    assert.ok(!JSON.stringify(vista).includes("SIN_SENAL"), "el código no se muestra");
  });

  it("con el 500 genérico, ese mensaje", () => {
    const fallo = { valido: false, titulo: "Algo falló", mensaje: "Intente de nuevo.", accion: "Recargue." };
    const vista = vistaDeGrafica({ resultado: RESULTADO_FALLO, datos: fallo });
    assert.equal(vista.estado, GRAFICA_SIN_ESPECTRO);
    assert.equal(vista.titulo, fallo.titulo);
  });

  it("sin servidor, el aviso propio", () => {
    const vista = vistaDeGrafica({ resultado: RESULTADO_SIN_SERVIDOR, datos: null });
    assert.equal(vista.estado, GRAFICA_SIN_ESPECTRO);
    assert.equal(vista.titulo, TEXTOS.sinServidor.titulo);
  });

  for (const [caso, respuesta] of [
    ["una respuesta vacía", null],
    ["un aceptado sin espectro", { resultado: RESULTADO_VEREDICTO, datos: { valido: true } }],
    ["un espectro roto", { resultado: RESULTADO_VEREDICTO, datos: { valido: true, espectro: { eje_cm1: [] } } }],
    ["un rechazo sin acción", { resultado: RESULTADO_VEREDICTO, datos: { valido: false, titulo: "t", mensaje: "m" } }],
  ]) {
    it(`con ${caso}, mensaje y no gráfica`, () => {
      const vista = vistaDeGrafica(respuesta);
      assert.equal(vista.estado, GRAFICA_SIN_ESPECTRO);
      assert.equal(vista.espectro, null);
      assert.ok(vista.titulo && vista.mensaje && vista.accion);
    });
  }
});
