"""MOD-06 · Motor de identificación. **Zona aislada.**

Qué entra: el vector de intensidades normalizado, su eje y el tramo que de
verdad se midió, según el contrato MOD-04 → MOD-06. Nada más.

Qué **no** entra, nunca: el archivo, su nombre, su formato, ni el veredicto de
MOD-03. El motor no abre archivos en inferencia y no sale a la red. Si una tarea
necesita algo que no está en ese contrato, la tarea está mal planteada: hay que
replantearla, no ensanchar el contrato.

Tres vías, en tres tareas:

- `reglas` — detecta picos y los compara con el catálogo de UT-01 (T-15).
- `modelo` — la CNN 1D multi-etiqueta (T-16).
- `inferencia` — la fusión de las dos con su umbral (T-17).
"""
