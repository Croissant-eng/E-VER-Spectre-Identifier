"""Capa HTTP · `POST /api/validar` y el servicio del frontend (T-07).

Es un **orquestador delgado**: no valida nada por su cuenta. Encadena lo que ya
está probado aislado y traduce el resultado al contrato de la sección 5:

    archivo subido → MOD-02 (tamaño, leer como texto) → MOD-03 (formato,
    puntos, rango) → veredicto

Las cinco reglas que este archivo existe para sostener:

1. **La traducción vive en un solo lugar.** MOD-02 y MOD-03 devuelven códigos;
   `veredicto.py` les pone el texto de UT-02. Aquí no se redacta nada.
2. **200 mientras haya veredicto.** Que un espectro se rechace es un resultado
   del negocio, no un error de transporte. El 500 queda para lo que falla por
   dentro, con el mensaje genérico de UT-02 y sin un solo detalle técnico.
3. **El límite lo aplica MOD-02**, leyendo por bloques el tamaño de UT-03. No
   se configura ningún límite en FastAPI ni en el servidor: si lo cortara la
   infraestructura, CA-02.2 dejaría de probar el código del equipo.
4. **Si UT-03 está incompleta, no arranca.** La configuración se lee **una vez**
   al crear la aplicación y se le pasa a MOD-02, MOD-03 y UT-02. Así el 500
   puede armar su mensaje sin volver a leer el archivo de parámetros, y nadie
   atiende peticiones con una configuración a medias (T-01).
5. **Mismo origen.** El frontend se sirve desde aquí, así que el `fetch` del
   navegador a `/api/validar` no cruza dominios y no hace falta CORS.

Para levantarlo en local, desde la raíz del repositorio:

    uvicorn backend.api:crear_aplicacion --factory --reload

y la interfaz queda en `http://127.0.0.1:8000/`.

**Privacidad (RNF-09):** el contenido del archivo existe solo durante la
petición y nunca se escribe en disco desde aquí; MOD-02 cierra la subida en un
`finally`, de modo que el temporal que FastAPI crea arriba de 1 MB desaparece
pase lo que pase. El registro guarda nombre, bytes y resultado; nunca el
espectro.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.api.veredicto import aceptado, rechazado
from backend.manejador_archivos import recibir
from backend.nucleo import obtener_registro
from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion, ErrorDeConfiguracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion import validar

_registro = obtener_registro("api")

#: La ruta y el campo del contrato D-5. `frontend/servicios/validacion.js`
#: repite estos dos valores porque no puede importar Python; una prueba falla si
#: se separan.
RUTA_VALIDAR: str = "/api/validar"
CAMPO_ARCHIVO: str = "archivo"

#: Dónde se sirve cada carpeta del frontend. Se conservan los nombres del
#: repositorio para que las rutas relativas de la página funcionen sin tocar ni
#: una línea del frontend: `/interfaz/interfaz.js` importa
#: `../servicios/validacion.js` y da justo en `/servicios/validacion.js`.
RUTA_INTERFAZ: str = "/interfaz"
RUTA_SERVICIOS: str = "/servicios"

#: La raíz del frontend. `frontend/pruebas/` (D-9) **no** se monta: es del
#: equipo, no de la web.
CARPETA_FRONTEND: Path = Path(__file__).resolve().parents[2] / "frontend"

#: Petición que no se puede atender: no llegó el archivo, así que no hay nada
#: que validar y tampoco falló nada por dentro.
CODIGO_PETICION_INVALIDA: int = 400

#: Fallo interno (sección 5).
CODIGO_FALLO_INTERNO: int = 500


def _preparar_tipos() -> None:
    """Asegura el tipo de los archivos del frontend.

    En Windows, `mimetypes` consulta el registro y `.js` puede quedar como
    `text/plain`. Con ese tipo, el navegador **se niega** a ejecutar un módulo
    (`<script type="module">`) y la página se queda muerta sin decir por qué. Es
    el tipo de detalle que solo aparece al servir de verdad.
    """
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/css", ".css")


def _configuracion_de_arranque() -> Configuracion:
    """Lee UT-03 al arrancar y, si está incompleta, falla ruidoso (T-01)."""
    try:
        return obtener_configuracion()
    except ErrorDeConfiguracion as error:
        # El código de UT-02 queda en el registro para que el equipo lo
        # reconozca; el detalle técnico se queda aquí y no viaja a ninguna
        # pantalla, porque con la configuración rota no hay servicio que dar.
        _registro.critical(
            "api arranque | resultado=%s | detalle=%s",
            mensajes.CONFIGURACION_INCOMPLETA,
            error,
        )
        raise


def crear_aplicacion(
    configuracion: Configuracion | None = None,
    *,
    carpeta_frontend: Path | None = None,
) -> FastAPI:
    """Arma la aplicación.

    Args:
        configuracion: los parámetros con los que trabajará. Si es ``None`` se
            leen de UT-03 —y si falta algo, **no arranca**—. El parámetro existe
            para las pruebas y para la evidencia, que levantan la aplicación con
            una configuración distinta para comprobar que UT-03 manda de verdad.
        carpeta_frontend: de dónde servir la interfaz. Si es ``None``, la del
            repositorio. La herramienta de evidencia pasa una **copia temporal**
            con un archivo extra que dispara la subida sola para la captura; así
            el frontend del repositorio no lleva ganchos de prueba.

    Returns:
        La aplicación lista para servir.

    Raises:
        ErrorDeConfiguracion: si UT-03 está incompleta y no se pasó una
            configuración. Es a propósito: más vale no arrancar que arrancar
            mal (T-01).
    """
    parametros = (
        configuracion if configuracion is not None else _configuracion_de_arranque()
    )
    _preparar_tipos()

    aplicacion = FastAPI(
        title="E-VER Spectre Identifier",
        version="1.0.0-incremento-1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @aplicacion.exception_handler(RequestValidationError)
    async def peticion_sin_archivo(
        peticion: Request, error: RequestValidationError
    ) -> JSONResponse:
        """La petición no trae el campo `archivo`.

        FastAPI respondería un 422 describiendo el campo que falta y el tipo que
        esperaba: eso es información técnica, y la regla 2 dice que el usuario no
        la ve. Se cambia por el mensaje genérico de UT-02.

        El 400 es la única parte que el contrato de la sección 5 no nombra: no
        hay veredicto que emitir —no llegó archivo— y tampoco falló nada por
        dentro, así que ni 200 ni 500 encajan. Queda anotado para el equipo.
        """
        _registro.warning(
            "api peticion invalida | ruta=%s | resultado=%s",
            peticion.url.path,
            mensajes.FALLO_INTERNO,
        )
        return JSONResponse(
            status_code=CODIGO_PETICION_INVALIDA,
            content=rechazado(mensajes.FALLO_INTERNO, parametros),
        )

    @aplicacion.post(RUTA_VALIDAR)
    async def validar_espectro(archivo: UploadFile = File(...)) -> JSONResponse:
        """Recibe el archivo y devuelve el veredicto del contrato de la sección 5."""
        recepcion = None
        try:
            # MOD-02: aplica el tamaño de UT-03, lee por bloques y cierra la
            # subida. Nunca levanta por culpa del archivo.
            recepcion = await recibir(archivo, parametros)
            if not recepcion.aceptado:
                return JSONResponse(rechazado(recepcion.codigo, parametros))

            # MOD-03: formato (T-04) y requisitos (T-05). Solo ve el texto y el
            # nombre; nunca el archivo (contrato de la sección 5).
            resultado = validar(
                recepcion.nombre,
                recepcion.contenido,
                tamano_correcto=recepcion.tamano_correcto,
                configuracion=parametros,
            )
            if not resultado.valido:
                return JSONResponse(rechazado(resultado.codigo, parametros))

            return JSONResponse(aceptado(recepcion.nombre, recepcion.bytes_leidos))
        except Exception:
            # Cualquier cosa inesperada —incluido un código que no esté en
            # UT-02— sale por aquí: el usuario ve el mensaje genérico y el
            # detalle queda en el registro del servidor. El servicio sigue de
            # pie y atiende la siguiente petición (CA-02.4).
            _registro.exception(
                "api fallo interno | resultado=%s", mensajes.FALLO_INTERNO
            )
            return JSONResponse(
                status_code=CODIGO_FALLO_INTERNO,
                content=rechazado(mensajes.FALLO_INTERNO, parametros),
            )
        finally:
            # Suelta el contenido en cuanto termina la petición (RNF-09). El
            # recolector lo haría igual al salir de la función; decirlo aquí deja
            # la intención por escrito y de paso cubre el caso del error.
            del recepcion

    @aplicacion.get("/")
    async def inicio() -> RedirectResponse:
        """La raíz lleva a la interfaz, que es lo único que hay que abrir."""
        return RedirectResponse(url=f"{RUTA_INTERFAZ}/")

    _montar_frontend(aplicacion, carpeta_frontend or CARPETA_FRONTEND)
    return aplicacion


def _montar_frontend(aplicacion: FastAPI, carpeta: Path) -> None:
    """Sirve `interfaz/` y `servicios/` tal como están en la carpeta dada.

    Se montan las dos carpetas por separado, y no toda la carpeta `frontend/`,
    por una razón concreta: así `frontend/pruebas/` (D-9) no queda publicado.
    """
    aplicacion.mount(
        RUTA_INTERFAZ,
        StaticFiles(directory=carpeta / "interfaz", html=True),
        name="interfaz",
    )
    aplicacion.mount(
        RUTA_SERVICIOS,
        StaticFiles(directory=carpeta / "servicios"),
        name="servicios",
    )


def __getattr__(nombre: str) -> Any:  # pragma: no cover - ayuda de importación
    """Avisa claro si alguien importa `aplicacion` esperando una instancia.

    No hay una aplicación creada al importar este módulo, a propósito: crearla
    lee UT-03, y eso no debe pasar por el solo hecho de importar. Se crea con
    `crear_aplicacion()`.
    """
    if nombre == "aplicacion":
        raise AttributeError(
            "backend.api no expone una aplicación ya creada: use "
            "crear_aplicacion() (o «uvicorn backend.api:crear_aplicacion "
            "--factory»)"
        )
    raise AttributeError(nombre)
