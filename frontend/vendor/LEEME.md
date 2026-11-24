# Librerías guardadas en el repositorio (D-1)

La gráfica de MOD-05 usa Chart.js con su complemento de anotaciones. Las dos
librerías se guardan aquí, con la versión fijada, para que la aplicación y sus
pruebas no dependan de internet. Ninguna se descarga al abrir la página.

| Archivo | Librería | Versión | Licencia | SHA-256 |
|---|---|---|---|---|
| `chart.umd.js` | Chart.js | 4.4.7 | MIT (`LICENSE-chartjs.md`) | `2812cb8825fdc57469eb2f7bb055e9429244e599920511ee477e828499b632cb` |
| `chartjs-plugin-annotation.min.js` | chartjs-plugin-annotation | 3.1.0 | MIT (`LICENSE-chartjs-plugin-annotation.md`) | `ff03786a60f6c93ccacfe0fbb6c2e3c671d7930856a3689f2f393113d8d655ec` |

Las dos se cargan con una etiqueta `<script>` normal antes de la interfaz, y
quedan disponibles como `Chart` y como el complemento ya registrado. El
complemento de anotaciones dibuja las regiones y los picos del incremento 4.

Para cambiar de versión hay que reemplazar el archivo, actualizar esta tabla y
correr las pruebas. Una prueba compara la huella SHA-256 de cada archivo con la
de esta tabla, para que nadie cambie una librería sin dejarlo escrito.
