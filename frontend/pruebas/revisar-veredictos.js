/**
 * Pasa veredictos **reales** por la vista de MOD-01 y revisa las invariantes.
 *
 * Lee por la entrada estándar un JSON con la forma
 * `[{"codigo": "...", "veredicto": {...}}, ...]` y, para cada uno, comprueba
 * que la vista muestre título, mensaje y acción, que **no** muestre el código y
 * que no ofrezca «Analizar».
 *
 * Existe para que los textos de UT-02 no se copien a mano en las pruebas de
 * JavaScript: los genera `pytest` desde el catálogo de verdad
 * (`backend/pruebas/prueba_mod01_interfaz.py`) y los manda por aquí. Así, si
 * alguien cambia una redacción en UT-02, esto sigue probando la pantalla con
 * el texto nuevo.
 *
 * Sale con código 0 si todo está bien, o con 1 e imprime los problemas.
 *
 * No es un archivo `*.test.js`: no lo recoge `node --test`.
 */

import { ESTADO_RECHAZADO, vistaDeVeredicto } from "../interfaz/vista.js";

function leerEntrada() {
  return new Promise((listo, falla) => {
    let texto = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (trozo) => {
      texto += trozo;
    });
    process.stdin.on("end", () => listo(texto));
    process.stdin.on("error", falla);
  });
}

function revisar(caso) {
  const problemas = [];
  const { codigo, veredicto } = caso;
  const vista = vistaDeVeredicto(veredicto);
  const pintado = JSON.stringify(vista);

  if (vista.estado !== ESTADO_RECHAZADO) {
    problemas.push(`${codigo}: la vista quedó en «${vista.estado}»`);
  }
  for (const campo of ["titulo", "mensaje", "accion"]) {
    if (!vista[campo]) {
      problemas.push(`${codigo}: la vista no muestra ${campo}`);
    }
  }
  if (vista.titulo !== veredicto.titulo) {
    problemas.push(`${codigo}: el título no es el de UT-02`);
  }
  if (vista.mensaje !== veredicto.mensaje) {
    problemas.push(`${codigo}: el mensaje no es el de UT-02`);
  }
  if (vista.accion !== veredicto.accion) {
    problemas.push(`${codigo}: la acción no es la de UT-02`);
  }
  if (pintado.includes(codigo)) {
    problemas.push(`${codigo}: el código llegó a la pantalla`);
  }
  if (vista.analizar.visible || vista.analizar.habilitado) {
    problemas.push(`${codigo}: ofrece «Analizar» después de un rechazo`);
  }
  return problemas;
}

const casos = JSON.parse(await leerEntrada());
if (!Array.isArray(casos) || casos.length === 0) {
  console.error("no llegó ningún veredicto que revisar");
  process.exit(1);
}

const problemas = casos.flatMap(revisar);
if (problemas.length > 0) {
  console.error(problemas.join("\n"));
  process.exit(1);
}

console.log(`${casos.length} veredictos de UT-02 se pintan completos`);
