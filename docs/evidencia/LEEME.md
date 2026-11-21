# Evidencia visual

Capturas que pide el plan del incremento 1 como evidencia de las tareas.

Se regeneran desde la raíz del repositorio con:

```bash
python -m herramientas.capturar_interfaz
```

## T-06 · MOD-01 interfaz mínima

| Captura | Qué muestra |
|---|---|
| `t-06-escritorio-inicial.png` | La pantalla antes de validar: no hay resultado pintado, y «Validar» espera deshabilitado hasta que se elija un archivo |
| `t-06-escritorio-aceptado.png` | Veredicto aceptado (D-4): el nombre del archivo, el aviso de **documento aprobado** y «Analizar» presente, habilitado y sin acción, con la nota de que el análisis llega en el siguiente incremento |
| `t-06-escritorio-rechazado.png` | Un rechazo con el texto de UT-02: título, motivo y acción. Sin «Analizar» y **sin el código** del error, que es interno |
| `t-06-movil-360-aceptado.png` | Lo mismo, aceptado, a 360 px de ancho |
| `t-06-movil-360-rechazado.png` | Lo mismo, rechazado, a 360 px de ancho |

**Cómo se hicieron.** Son la página de verdad: la herramienta copia
`frontend/` a una carpeta temporal, le agrega un solo archivo que pinta un
veredicto simulado —el endpoint `POST /api/validar` es T-07— y la dibuja con
Chrome en modo headless. Los archivos del repositorio no llevan ganchos de
prueba.

**Por qué las de 360 px salen dentro de un marco gris.** El modo headless no
acepta ventanas de menos de unos 500 px de ancho: si se le piden 360, dibuja
una página de 512 y **recorta** la imagen, lo que aparenta un diseño roto que
no lo está. El marco da los 360 px de verdad y, de paso, deja medir: la línea
`MEDIDA360` al pie de cada captura compara el ancho del contenido contra el del
marco. `desborda=no` es la evidencia de que no hay desplazamiento horizontal
(adelanto de RNF-05; la prueba formal es del incremento 2).

**Las capturas salieron en tema oscuro** porque así venía configurado el
navegador que las tomó. La hoja de estilos define los dos temas y sigue el del
sistema.

El texto del rechazo de las capturas no está escrito en la herramienta: se pide
al catálogo de UT-02, así que si el equipo cambia la redacción, la siguiente
captura sale con el texto nuevo.
