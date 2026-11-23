/**
 * CA-01.1 · pasa la respuesta **real** de `POST /api/validar` por la vista.
 *
 * Lee por la entrada estándar el cuerpo que devolvió el servidor de verdad
 * —`{"valido": true, "nombre": "...", "bytes": N}`, tal como lo recibió
 * `backend/pruebas/prueba_t07_integracion.py`— y comprueba lo que CA-01.1
 * exige ver: **el nombre del archivo** y el botón **«Analizar» habilitado**,
 * con el aviso de documento aprobado (D-4).
 *
 * Entra por la misma puerta que usa el navegador, `vistaDesdeRespuesta`, así
 * que lo que se prueba es la cadena completa: HTTP → servicio → vista. Nada
 * aquí está simulado; el único eslabón que falta es el clic de la persona, y
 * ese queda en la captura de evidencia.
 *
 * Sale con código 0 si todo está bien, o con 1 e imprime los problemas.
 *
 * No es un archivo `*.test.js`: no lo recoge `node --test`.
 */

import { ESTADO_ACEPTADO, vistaDesdeRespuesta } from "../interfaz/vista.js";
import { RESULTADO_VEREDICTO } from "../servicios/validacion.js";

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

const cuerpo = JSON.parse(await leerEntrada());
const problemas = [];

// Se arma la respuesta tal como la entrega `servicios/validacion.js` ante un
// 200, para no saltarse ningún eslabón del camino real.
const vista = vistaDesdeRespuesta({
  resultado: RESULTADO_VEREDICTO,
  veredicto: cuerpo,
});

if (vista.estado !== ESTADO_ACEPTADO) {
  problemas.push(`la vista quedó en «${vista.estado}», no en «aceptado»`);
}
if (!vista.nombre) {
  problemas.push("la vista no muestra el nombre del archivo (CA-01.1)");
} else if (vista.nombre !== cuerpo.nombre) {
  problemas.push(
    `la vista muestra «${vista.nombre}» y el servidor dijo «${cuerpo.nombre}»`,
  );
}
if (!vista.titulo) {
  problemas.push("la vista no muestra el aviso de documento aprobado (D-4)");
}
if (!vista.analizar.visible) {
  problemas.push("«Analizar» no aparece después de aceptar (D-4)");
}
if (!vista.analizar.habilitado) {
  problemas.push("«Analizar» no quedó habilitado (CA-01.1)");
}
if (vista.accion) {
  problemas.push("una aceptación no pide ninguna acción correctiva");
}

if (problemas.length > 0) {
  console.error(problemas.join("\n"));
  process.exit(1);
}

console.log(`CA-01.1 ok | nombre=${vista.nombre} | analizar=habilitado`);
