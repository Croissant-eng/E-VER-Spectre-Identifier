/**
 * Pruebas de T-06 · la lógica «veredicto → vista» de MOD-01.
 *
 * Corren con el corredor que ya trae Node, sin instalar nada:
 *
 *     node --test frontend/pruebas
 *
 * (También las corre `pytest`, desde `backend/pruebas/prueba_mod01_interfaz.py`,
 * para que haya un solo comando.)
 *
 * Los veredictos son **simulados**: el endpoint es T-07. Lo que se prueba aquí
 * es la decisión, que no toca ni el DOM ni la red.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  ESTADO_ACEPTADO,
  ESTADO_ESPERANDO,
  ESTADO_INICIAL,
  ESTADO_RECHAZADO,
  ESTADO_SIN_VEREDICTO,
  TEXTOS,
  vistaDeVeredicto,
  vistaDesdeRespuesta,
  vistaEsperando,
  vistaInicial,
} from "../interfaz/vista.js";
import {
  RESULTADO_FALLO,
  RESULTADO_SIN_SERVIDOR,
  RESULTADO_VEREDICTO,
} from "../servicios/validacion.js";

/** Un veredicto de aceptación como el del contrato de la sección 5. */
const ACEPTADO = { valido: true, nombre: "acetona.jdx", bytes: 307200 };

/**
 * Los ocho códigos de UT-02 con textos de ejemplo. Los textos de verdad los
 * redacta UT-02 en el servidor; aquí lo que importa es la forma del veredicto.
 * (Una prueba de `pytest` pasa los ocho mensajes **reales** por esta misma
 * función, para que nadie tenga que copiarlos a mano en este archivo.)
 */
const RECHAZOS = [
  "FORMATO_NO_SOPORTADO",
  "TAMANO_EXCEDIDO",
  "RANGO_INSUFICIENTE",
  "PUNTOS_INSUFICIENTES",
  "ARCHIVO_NO_ES_TEXTO",
  "ESTRUCTURA_INVALIDA",
  "CONFIGURACION_INCOMPLETA",
  "LECTURA_INTERRUMPIDA",
].map((codigo, numero) => ({
  valido: false,
  codigo,
  // Los textos no mencionan el código a propósito: así la prueba de que el
  // código no se muestra mide la vista y no el texto de ejemplo.
  titulo: `Título del rechazo ${numero + 1}`,
  mensaje: `Motivo del rechazo ${numero + 1}.`,
  accion: `Acción sugerida ${numero + 1}.`,
}));

describe("antes de validar", () => {
  it("no hay resultado que pintar", () => {
    const vista = vistaInicial();

    assert.equal(vista.estado, ESTADO_INICIAL);
    assert.equal(vista.titulo, "");
    assert.equal(vista.mensaje, "");
    assert.equal(vista.analizar.visible, false);
  });

  it("mientras se valida se avisa, con el nombre del archivo", () => {
    const vista = vistaEsperando("acetona.jdx");

    assert.equal(vista.estado, ESTADO_ESPERANDO);
    assert.equal(vista.nombre, "acetona.jdx");
    assert.equal(vista.titulo, TEXTOS.esperando.titulo);
    assert.equal(vista.analizar.visible, false, "todavía no hay nada aprobado");
  });
});

describe("veredicto aceptado (D-4)", () => {
  it("muestra el nombre del archivo y el aviso de aprobado", () => {
    const vista = vistaDeVeredicto(ACEPTADO);

    assert.equal(vista.estado, ESTADO_ACEPTADO);
    assert.equal(vista.nombre, "acetona.jdx");
    assert.equal(vista.titulo, TEXTOS.aceptado.titulo);
    assert.ok(vista.mensaje.length > 0);
  });

  it("deja «Analizar» presente y habilitado", () => {
    const vista = vistaDeVeredicto(ACEPTADO);

    assert.equal(vista.analizar.visible, true);
    assert.equal(vista.analizar.habilitado, true);
  });

  it("avisa que analizar llega en el siguiente incremento", () => {
    const vista = vistaDeVeredicto(ACEPTADO);

    assert.ok(
      vista.analizar.nota.includes("incremento"),
      "la nota explica por qué el botón no hace nada todavía",
    );
  });

  it("no inventa una acción que la persona deba hacer", () => {
    assert.equal(vistaDeVeredicto(ACEPTADO).accion, "");
  });

  it("pinta el nombre tal como lo entregó MOD-02", () => {
    // MOD-02 ya quitó rutas y caracteres de control; aquí no se vuelve a tocar.
    const vista = vistaDeVeredicto({ valido: true, nombre: "espectro final.csv" });

    assert.equal(vista.nombre, "espectro final.csv");
  });
});

describe("veredicto rechazado", () => {
  for (const veredicto of RECHAZOS) {
    it(`muestra motivo y acción de ${veredicto.codigo}`, () => {
      const vista = vistaDeVeredicto(veredicto);

      assert.equal(vista.estado, ESTADO_RECHAZADO);
      assert.equal(vista.titulo, veredicto.titulo);
      assert.equal(vista.mensaje, veredicto.mensaje);
      assert.equal(vista.accion, veredicto.accion);
    });

    it(`no muestra el código ${veredicto.codigo}`, () => {
      const vista = vistaDeVeredicto(veredicto);

      assert.ok(
        !JSON.stringify(vista).includes(veredicto.codigo),
        "el código es interno, para el registro y el equipo",
      );
    });

    it(`no ofrece «Analizar» tras ${veredicto.codigo}`, () => {
      const vista = vistaDeVeredicto(veredicto);

      assert.equal(vista.analizar.visible, false);
      assert.equal(vista.analizar.habilitado, false);
    });
  }

  it("recorta los espacios de los textos del servidor", () => {
    const vista = vistaDeVeredicto({
      valido: false,
      codigo: "TAMANO_EXCEDIDO",
      titulo: "  Archivo grande  ",
      mensaje: "  Pasó del límite.  ",
      accion: "  Suba uno más chico.  ",
    });

    assert.equal(vista.titulo, "Archivo grande");
    assert.equal(vista.mensaje, "Pasó del límite.");
    assert.equal(vista.accion, "Suba uno más chico.");
  });
});

describe("nunca una vista a medias", () => {
  const INSERVIBLES = [
    ["nada", undefined],
    ["nulo", null],
    ["texto", "valido"],
    ["sin el campo valido", { nombre: "acetona.jdx" }],
    ["valido que no es booleano", { valido: "si", nombre: "acetona.jdx" }],
    ["aceptado sin nombre", { valido: true }],
    ["aceptado con nombre vacío", { valido: true, nombre: "   " }],
    ["rechazo sin textos", { valido: false, codigo: "TAMANO_EXCEDIDO" }],
    [
      "rechazo sin acción",
      {
        valido: false,
        codigo: "TAMANO_EXCEDIDO",
        titulo: "Grande",
        mensaje: "Pasó del límite.",
      },
    ],
    [
      "rechazo sin mensaje",
      {
        valido: false,
        codigo: "TAMANO_EXCEDIDO",
        titulo: "Grande",
        accion: "Suba otro.",
      },
    ],
  ];

  for (const [caso, veredicto] of INSERVIBLES) {
    it(`con ${caso} no se pinta un resultado`, () => {
      const vista = vistaDeVeredicto(veredicto);

      assert.equal(vista.estado, ESTADO_SIN_VEREDICTO);
      assert.equal(vista.titulo, TEXTOS.sinVeredicto.titulo);
      assert.ok(vista.accion.length > 0, "siempre se le dice qué hacer");
      assert.equal(vista.analizar.visible, false);
      assert.equal(vista.nombre, "", "no se pinta nada del veredicto roto");
    });
  }
});

describe("de la respuesta del servicio a la vista", () => {
  it("un veredicto de 200 se muestra", () => {
    const vista = vistaDesdeRespuesta({
      resultado: RESULTADO_VEREDICTO,
      veredicto: ACEPTADO,
    });

    assert.equal(vista.estado, ESTADO_ACEPTADO);
  });

  it("sin servidor se avisa, sin detalles técnicos", () => {
    const vista = vistaDesdeRespuesta({
      resultado: RESULTADO_SIN_SERVIDOR,
      veredicto: null,
    });

    assert.equal(vista.estado, ESTADO_SIN_VEREDICTO);
    assert.equal(vista.titulo, TEXTOS.sinServidor.titulo);
    for (const tecnico of ["fetch", "TypeError", "500", "undefined"]) {
      assert.ok(!JSON.stringify(vista).includes(tecnico), tecnico);
    }
  });

  it("un 500 con mensaje genérico de UT-02 sí se muestra", () => {
    // La sección 5 dice que el 500 trae mensaje genérico: si viene completo, es
    // más útil que el aviso que escribe el frontend.
    const vista = vistaDesdeRespuesta({
      resultado: RESULTADO_FALLO,
      veredicto: {
        valido: false,
        codigo: "CONFIGURACION_INCOMPLETA",
        titulo: "El servicio no está disponible por ahora",
        mensaje: "La aplicación no pudo iniciar con su configuración.",
        accion: "Avise al equipo del proyecto e intente de nuevo más tarde.",
      },
    });

    assert.equal(vista.estado, ESTADO_RECHAZADO);
    assert.ok(!JSON.stringify(vista).includes("CONFIGURACION_INCOMPLETA"));
  });

  it("un 500 sin cuerpo no deja la pantalla a medias", () => {
    const vista = vistaDesdeRespuesta({
      resultado: RESULTADO_FALLO,
      veredicto: null,
    });

    assert.equal(vista.estado, ESTADO_SIN_VEREDICTO);
  });

  it("una respuesta que no es objeto tampoco", () => {
    assert.equal(vistaDesdeRespuesta(undefined).estado, ESTADO_SIN_VEREDICTO);
  });
});
