# Incremento 4: capa educativa, explicar y resaltar

Este archivo registra cómo quedó el incremento 4, tareas T-20 a T-24 del Plan de Implementación V3. No es un plan de decisiones como el del incremento 3: el Plan V3 ya dice qué hace cada tarea, y aquí se anota cómo quedó en el código, qué falta revisar y qué queda pendiente. Lo marcado como SUPUESTO falta que el equipo lo confirme.

Se construyó encima del incremento 3 tal como quedó en la rama incremento-3-continuacion (T-17, T-18 y T-19), porque la lista de grupos es donde se muestra todo lo de este incremento.

## Cómo quedó

**T-20, plantillas.** Viven en `datos/catalogo/plantillas.json` y las lee UT-01 con `obtener_plantillas()`. Cada plantilla trae solo el porqué del grupo, sus dos fuentes y, en el caso del N–H, el texto que lo distingue del O–H. No llevan números: el lector rechaza cualquier cifra, y donde hace falta nombrar la banda que confirma al grupo se escribe `{confirmacion}` y MOD-07 pone el rango del catálogo. La prueba de cobertura revisa que los siete grupos tengan plantilla.

**T-21, la explicación.** MOD-07 vive en `backend/educativo/explicador.py`. Para cada grupo detectado arma las cuatro partes de CA-07.1: la región del catálogo, la posición que dio la vía de reglas, el rasgo dicho con la intensidad y la forma del catálogo (para el carbonilo sale «pico intenso y agudo») y el porqué de la plantilla. Si el pico cae también en la región del vecino que nombra la plantilla, se agrega la distinción, que es lo que pide CA-07.2. `/api/analizar` agrega la explicación a cada detección en la llave `explicacion`.

**T-22, el grupo sin plantilla.** El grupo se queda en la lista y en lugar del texto lleva el aviso `EXPLICACION_NO_DISPONIBLE` de UT-02, con el título «Explicación no disponible». El error se anota en el registro con el grupo. Si la explicación de un grupo falla por cualquier otra razón pasa lo mismo, y los demás grupos se explican igual.

**T-23 y T-24, el resaltado.** Cada grupo de la lista tiene el botón «Resaltar en la gráfica» y un desplegable «Ver por qué» con su explicación. Al elegir un grupo se pinta su región con un relleno transparente de su color y su pico con una línea punteada, con el complemento de anotaciones guardado desde D-1. Se pueden elegir varios: cada grupo tiene su color fijo y aparece en una leyenda bajo la gráfica. Si el motor no dio la posición del pico, la región lleva borde y la leyenda dice que es la región completa. Las anotaciones y la leyenda salen de funciones puras en `frontend/visor-espectro/resaltado.js`. Los colores son de la paleta de Okabe e Ito, que se distinguen también con daltonismo común.

**Evidencia.** `docs/evidencia/t-23-resaltado-y-explicacion.png` muestra la página real con un CSV fabricado con un carbonilo: el C=O resaltado, su leyenda y su explicación abierta.

## Lo que falta del equipo

**La revisión química de las plantillas (SUPUESTO).** Los siete textos son un borrador escrito con ayuda de IA. El plan pide compararlos contra la tabla de la University of Colorado Boulder y contra LibreTexts, que los apruebe quien no los escribió y, si se puede, que los revise un profesor de química. Cada plantilla tiene `revisado_por` y `fecha_revision` vacíos para registrar esa revisión.

**CA-06.2 depende de T-15e.** El resaltado con colores y leyenda para O–H y N–H ya funciona y tiene su prueba con datos simulados. Pero hoy la vía de reglas no reporta los dos grupos a la vez en un espectro real (sección D-23 del plan del incremento 3), así que en la aplicación todavía no se puede ver ese caso de punta a punta. Se podrá en cuanto T-15e quede hecha.

**El modo reglas.** Mientras no haya modelo entrenado, `evidencia.ml` llega en null. La capa educativa no la usa, así que no le afecta.
