/**
 * T-12 y T-13: pasa la respuesta real de `POST /api/procesar` por MOD-05.
 *
 * Lee por la entrada estándar el cuerpo que devolvió el servidor de verdad y
 * lo pasa por `vistaDeGrafica` y `configuracionDeGrafica`, las mismas
 * funciones que corre el navegador. Con un argumento «lista» espera una
 * gráfica; con «sin-espectro» espera un mensaje en su lugar (CA-04.3).
 *
 * Sale con código 0 si todo está bien, o con 1 e imprime los problemas.
 * No es un archivo `*.test.js`: no lo recoge `node --test`.
 */

import { RESULTADO_VEREDICTO } from "../servicios/validacion.js";
import {
  GRAFICA_LISTA,
  configuracionDeGrafica,
  vistaDeGrafica,
} from "../visor-espectro/configuracion.js";

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

const esperado = process.argv[2];
const cuerpo = JSON.parse(await leerEntrada());
const vista = vistaDeGrafica({ resultado: RESULTADO_VEREDICTO, datos: cuerpo });
const problemas = [];

if (vista.estado !== esperado) {
  problemas.push(`la vista quedó en «${vista.estado}» y se esperaba «${esperado}»`);
}

if (vista.estado === GRAFICA_LISTA) {
  const config = configuracionDeGrafica(vista.espectro);
  const x = config.options.scales.x;
  if (!x.reverse) {
    problemas.push("el eje horizontal no va de mayor a menor (CA-04.1)");
  }
  if (config.data.datasets[0].data.length < 2) {
    problemas.push("la gráfica quedaría sin puntos");
  }
  console.log(
    `CA-04.1 ok | puntos=${config.data.datasets[0].data.length} | ` +
      `eje=${x.max}->${x.min} | invertido=${x.reverse}`,
  );
} else if (!vista.titulo || !vista.mensaje || !vista.accion) {
  problemas.push("sin gráfica, el mensaje tiene que venir completo (CA-04.3)");
} else {
  console.log(`CA-04.3 ok | titulo=${vista.titulo}`);
}

if (problemas.length > 0) {
  console.error(problemas.join("\n"));
  process.exit(1);
}
