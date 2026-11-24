# Origen del conjunto de entrenamiento · Chemotion IR

| | |
|---|---|
| **Nombre** | Chemotion repository — data collection: ft-ir spectroscopy data (chemotion ir) |
| **DOI** | `10.22000/OGoEQGlsZGElrgst` (RADAR4Chem, versión 1) |
| **Licencia** | **CC BY-SA 4.0** — atribución y compartir igual |
| **Descargado** | 24/11/2026 |
| **Paquete** | `10.22000-OGoEQGlsZGElrgst.tar`, 47 502 336 bytes |
| **SHA-256 del paquete** | `37fec9f65a3dc07ff9e4b876090392f22b66d1a49139444b00926fbe6906bcaa` |
| **Contenido** | 4 183 archivos JCAMP-DX y `meta_data.json` |

**Cita exigida:**

> Jung, Nicole; Tremouilhac, Pierre; Punjabi, Dev; Huang, Pei-Chi (2024). *Chemotion repository — data collection: ft-ir spectroscopy data (chemotion ir)*. Karlsruhe Institute of Technology. DOI 10.22000/OGoEQGlsZGElrgst

## Qué está en el repositorio y qué no

- **No:** los espectros ni `meta_data.json` (`datos/dataset/espectros/`, en `.gitignore`).
- **Sí:** `indice.csv`, que deriva del metadato del conjunto (`sample_id`, `cano_smiles`, `instrument`, `kind`) y de las cabeceras de los archivos. **SUPUESTO:** por ser obra derivada se distribuye bajo la misma CC BY-SA 4.0, con esta atribución; que lo confirme el equipo o un profesor (D-12, verificación 4).

Cambios hechos a los archivos: **ninguno en su contenido.** En el paquete son UUID sin extensión; aquí se guardan como `<uuid>.jdx`.

## Cómo reproducirlo

```bash
python -m herramientas.dataset.descargar_chemotion               # baja, verifica y extrae
python -m herramientas.dataset.descargar_chemotion --verificar   # solo comprueba lo de disco
python -m herramientas.dataset.embudo_chemotion                  # escribe indice.csv (necesita RDKit)
python -m herramientas.dataset.medir_reserva2                    # mediciones de la reserva 2
```

RDKit va en un entorno aparte (`herramientas/dataset/requisitos.txt`): no es dependencia de la aplicación.

Los resultados están en `docs/evidencia/t-16a-1-embudo.md`.
