# Incremento 5: reporte en PDF

Este archivo registra cómo quedó el incremento 5, tareas T-25 a T-27 del Plan de Implementación V3. Se construyó encima del incremento 4 (rama incremento-4-capa-educativa). Lo marcado como SUPUESTO falta que el equipo lo confirme.

## D-3, la librería del PDF

**Cerrada el 24/11/2026: ReportLab 4.2.5**, elegida por el equipo. Cumple lo que pide el Plan V3 para D-3: es Python, mete la imagen de la gráfica y arma el PDF en memoria sin guardarlo en el servidor. Necesita Pillow para leer la imagen PNG. Para que se vean bien símbolos como C≡N o cm⁻¹ se usan las fuentes DejaVu, guardadas en `backend/reportes/fuentes` con su licencia. Las pruebas leen el PDF con pypdf 5.1.0. Las tres quedaron en `requirements.txt`.

## Cómo quedó

**La ruta.** `POST /api/reporte` recibe en JSON el nombre del archivo, el espectro, la gráfica resaltada como imagen PNG y la zona horaria del navegador. El servidor vuelve a correr el motor y MOD-07 con ese espectro, así los grupos, las confianzas y las explicaciones del PDF salen del mismo cálculo que se vio en pantalla y no de lo que diga la página. Lo único que se toma tal cual es la imagen, y antes se revisa que sea un PNG y que no pase del tamaño máximo de archivo de UT-03. El cuerpo se lee por bloques y se corta al pasar el límite, igual que MOD-02 con los archivos. Si falta algo responde 200 con `REPORTE_INVALIDO`; si algo falla al generar, 500 con `REPORTE_FALLIDO`.

**T-25, el PDF.** MOD-08 vive en `backend/reportes/generador.py`. El PDF lleva el nombre del archivo, la fecha y hora en la zona de quien analizó, cada grupo con su confianza y su explicación, y el aviso de resultado orientativo. Si el motor trabajó solo con reglas, lo dice, como dejó pedido D-16. Todo se arma en un BytesIO; una prueba vigila que nada se abra para escribir mientras se genera (RNF-09).

**T-26, la gráfica.** Al pulsar «Descargar reporte», la página resalta todos los grupos detectados, toma la imagen con Chart.js y regresa al resaltado que la persona tenía elegido. En el PDF la imagen se escala para caber en la hoja.

**T-27, sin detecciones y fallo.** Sin detecciones el PDF lo dice con el aviso de UT-02 (CA-09.2). Si el reporte falla, el mensaje de UT-02 sale junto al botón, el botón queda listo para reintentar y los resultados del análisis no se tocan (CA-09.3).

**Evidencia.** `docs/evidencia/t-25-reporte-pagina-1.png` es la primera hoja del PDF descargado desde la página real, con un CSV fabricado con un carbonilo.

## Pendientes

**El texto del aviso orientativo (SUPUESTO).** RF-08 pide el aviso pero no da su redacción. El texto está en `AVISO_ORIENTATIVO`, dentro de `generador.py`; conviene que el equipo lo revise.

**La gráfica sale con el ancho de la pantalla.** En un teléfono la imagen es angosta y en el PDF se ve pequeña pero legible. Si se quiere más nitidez, se puede dibujar una copia más grande solo para el reporte.
