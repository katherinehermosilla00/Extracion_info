
from backend_client import guardar_tour_en_backend
from validator import validar_tour
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from urllib.parse import urlparse
from fastapi.middleware.cors import CORSMiddleware
from scraper import (
    buscar_tours_relacionados,
    descubrir_tours,
    extraer_tour,
    parece_ficha_individual,
    enriquecer_imagenes_desde_catalogo,
)

from models import (
    BuscarRequest,
    ExtraerRequest,
    ExtraerYGuardarRequest,
)


class CatalogoRequest(BaseModel):
    url: str
    nombre_operador: str | None = None
    max_paginas: int = Field(
        default=3,
        ge=1,
        le=10,
    )




class CatalogoExtraerRequest(BaseModel):
    url: str
    nombre_operador: str | None = None
    max_paginas: int = Field(
        default=3,
        ge=1,
        le=10,
    )
    limite: int = Field(
        default=10,
        ge=1,
        le=50,
    )



app = FastAPI(
    title="Scraper Universal de Tours",
    version="3.0.0",
    description=(
        "Busca actividades relacionadas y extrae información publicada "
        "por operadores turísticos sin incorporar precios."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio() -> dict:
    return {
        "servicio": "Scraper Universal de Tours",
        "version": "3.0.0",
        "documentacion": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/scraper/search")
def buscar(solicitud: BuscarRequest) -> dict:
    try:
        resultado = buscar_tours_relacionados(
            url_operador=solicitud.url_operador,
            pedido=solicitud.pedido,
            max_paginas=solicitud.max_paginas,
            limite=solicitud.limite,
            puntaje_minimo=solicitud.puntaje_minimo,
        )
        resultado["nombre_operador"] = solicitud.nombre_operador
        return resultado
    except ValueError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo realizar la búsqueda: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error



@app.post("/scraper/catalog")
def procesar_catalogo(
    solicitud: CatalogoRequest,
) -> dict:
    """
    Descubre fichas individuales desde una p?gina cat?logo.

    Este endpoint no guarda informaci?n en PostgreSQL.
    """

    try:
        descubiertos = descubrir_tours(
            url_operador=solicitud.url,
            max_paginas=solicitud.max_paginas,
        )

        dominio_operador = urlparse(
            solicitud.url
        ).netloc

        fichas = []

        for item in descubiertos:
            url = item.get("url", "")
            titulo = item.get("titulo", "")

            if not parece_ficha_individual(
                url=url,
                titulo=titulo,
                dominio_operador=dominio_operador,
            ):
                continue

            fichas.append({
                "titulo": titulo,
                "url": url,
            })

        return {
            "ok": True,
            "nombre_operador": solicitud.nombre_operador,
            "url_catalogo": solicitud.url,
            "total_descubiertos": len(descubiertos),
            "total_fichas": len(fichas),
            "fichas": fichas,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo procesar el catalogo: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error




@app.post("/scraper/catalog/extract")
def extraer_catalogo(
    solicitud: CatalogoExtraerRequest,
) -> dict:
    """
    Descubre y extrae fichas individuales desde un catalogo.

    No guarda actividades en PostgreSQL.
    Una ficha con error no detiene el resto del proceso.
    """

    try:
        descubiertos = descubrir_tours(
            url_operador=solicitud.url,
            max_paginas=solicitud.max_paginas,
        )

        dominio_operador = urlparse(
            solicitud.url
        ).netloc

        candidatos = []
        urls_vistas = set()

        # -------------------------------------------------
        # FILTRAR FICHAS INDIVIDUALES
        # -------------------------------------------------

        for item in descubiertos:
            url = item.get("url", "")
            titulo = item.get("titulo", "")

            if not url:
                continue

            if url in urls_vistas:
                continue

            if not parece_ficha_individual(
                url=url,
                titulo=titulo,
                dominio_operador=dominio_operador,
            ):
                continue

            urls_vistas.add(url)

            candidatos.append({
                "titulo": titulo,
                "url": url,
            })

        candidatos = candidatos[
            :solicitud.limite
        ]

        # -------------------------------------------------
        # EXTRAER CADA FICHA
        # -------------------------------------------------

        resultados = []
        errores = []

        for indice, candidato in enumerate(
            candidatos,
            start=1,
        ):
            try:
                tour = extraer_tour(
                    url=candidato["url"],
                    nombre_operador=(
                        solicitud.nombre_operador
                    ),
                )

                # En catalogos, la ficha individual puede
                # vivir en un proveedor externo de reservas.
                # Conservamos como web del operador la URL
                # de catalogo recibida originalmente.
                tour.url_operador = solicitud.url

                if len(tour.imagenes or []) < 4:
                    tour = enriquecer_imagenes_desde_catalogo(
                        tour=tour,
                        url_catalogo=solicitud.url,
                        url_ficha=candidato["url"],
                        minimo=4,
                    )

                validacion = validar_tour(
                    tour
                )

                resultados.append({
                    "indice": indice,
                    "titulo_descubierto": (
                        candidato["titulo"]
                    ),
                    "url": candidato["url"],
                    "validacion": validacion,
                    "tour": tour,
                })

            except Exception as error:
                errores.append({
                    "indice": indice,
                    "titulo_descubierto": (
                        candidato["titulo"]
                    ),
                    "url": candidato["url"],
                    "error": (
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                })

        # -------------------------------------------------
        # RESPUESTA
        # -------------------------------------------------

        return {
            "ok": len(resultados) > 0,
            "nombre_operador": (
                solicitud.nombre_operador
            ),
            "url_catalogo": solicitud.url,
            "total_descubiertos": len(
                descubiertos
            ),
            "total_fichas_detectadas": len(
                urls_vistas
            ),
            "total_procesadas": len(
                candidatos
            ),
            "total_extraidas": len(
                resultados
            ),
            "total_errores": len(
                errores
            ),
            "total_listas_para_guardar": sum(
                1
                for item in resultados
                if item["validacion"][
                    "lista_para_guardar"
                ]
            ),
            "total_requieren_revision": sum(
                1
                for item in resultados
                if not item["validacion"][
                    "lista_para_guardar"
                ]
            ),
            "resultados": resultados,
            "errores": errores,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo procesar el catalogo: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error




@app.post("/scraper/catalog/extract-and-save")
def extraer_y_guardar_catalogo(
    solicitud: CatalogoExtraerRequest,
) -> dict:
    """
    Descubre, extrae, valida y guarda actividades.

    Solo guarda fichas que pasan la validacion.
    Una ficha con error no detiene las demas.
    """

    try:
        descubiertos = descubrir_tours(
            url_operador=solicitud.url,
            max_paginas=solicitud.max_paginas,
        )

        dominio_operador = urlparse(
            solicitud.url
        ).netloc

        candidatos = []
        urls_vistas = set()

        # ---------------------------------------------
        # DESCUBRIR FICHAS
        # ---------------------------------------------

        for item in descubiertos:
            url = item.get("url", "")
            titulo = item.get("titulo", "")

            if not url:
                continue

            if url in urls_vistas:
                continue

            if not parece_ficha_individual(
                url=url,
                titulo=titulo,
                dominio_operador=dominio_operador,
            ):
                continue

            urls_vistas.add(url)

            candidatos.append({
                "titulo": titulo,
                "url": url,
            })

        candidatos = candidatos[
            :solicitud.limite
        ]

        guardadas = []
        revision = []
        errores = []

        # ---------------------------------------------
        # EXTRAER + VALIDAR + GUARDAR
        # ---------------------------------------------

        for indice, candidato in enumerate(
            candidatos,
            start=1,
        ):
            try:
                tour = extraer_tour(
                    url=candidato["url"],
                    nombre_operador=(
                        solicitud.nombre_operador
                    ),
                )

                # En catalogos, la ficha individual puede
                # vivir en un proveedor externo de reservas.
                # Conservamos como web del operador la URL
                # de catalogo recibida originalmente.
                tour.url_operador = solicitud.url

                if len(tour.imagenes or []) < 4:
                    tour = enriquecer_imagenes_desde_catalogo(
                        tour=tour,
                        url_catalogo=solicitud.url,
                        url_ficha=candidato["url"],
                        minimo=4,
                    )

                validacion = validar_tour(
                    tour
                )

                # No guardar fichas incompletas.
                if not validacion[
                    "lista_para_guardar"
                ]:
                    revision.append({
                        "indice": indice,
                        "titulo_descubierto": (
                            candidato["titulo"]
                        ),
                        "url": candidato["url"],
                        "validacion": validacion,
                        "tour": tour,
                    })

                    continue

                resultado_guardado = (
                    guardar_tour_en_backend(
                        tour
                    )
                )

                guardadas.append({
                    "indice": indice,
                    "titulo_descubierto": (
                        candidato["titulo"]
                    ),
                    "url": candidato["url"],
                    "validacion": validacion,
                    "accion": (
                        resultado_guardado.get(
                            "accion"
                        )
                    ),
                    "actividad": (
                        resultado_guardado.get(
                            "actividad"
                        )
                    ),
                })

            except ValueError as error:
                errores.append({
                    "indice": indice,
                    "titulo_descubierto": (
                        candidato["titulo"]
                    ),
                    "url": candidato["url"],
                    "tipo": "seguridad_o_validacion",
                    "error": str(error),
                })

            except Exception as error:
                errores.append({
                    "indice": indice,
                    "titulo_descubierto": (
                        candidato["titulo"]
                    ),
                    "url": candidato["url"],
                    "tipo": "extraccion_o_guardado",
                    "error": (
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                })

        # ---------------------------------------------
        # RESPUESTA
        # ---------------------------------------------

        return {
            "ok": (
                len(guardadas) > 0
                or len(revision) > 0
            ),
            "nombre_operador": (
                solicitud.nombre_operador
            ),
            "url_catalogo": solicitud.url,
            "total_descubiertos": len(
                descubiertos
            ),
            "total_fichas_detectadas": len(
                urls_vistas
            ),
            "total_procesadas": len(
                candidatos
            ),
            "total_guardadas": len(
                guardadas
            ),
            "total_requieren_revision": len(
                revision
            ),
            "total_errores": len(
                errores
            ),
            "guardadas": guardadas,
            "requieren_revision": revision,
            "errores": errores,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo procesar el catalogo: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error



@app.post("/scraper/extract")
def extraer(solicitud: ExtraerRequest):
    try:
        return extraer_tour(
            url=solicitud.url,
            nombre_operador=solicitud.nombre_operador,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo extraer el tour: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error

@app.post("/scraper/extract-and-save")
def extraer_y_guardar(
    solicitud: ExtraerYGuardarRequest,
) -> dict:
    try:
        # 1. Extraer la información desde la web
        tour = extraer_tour(
            url=solicitud.url,
            nombre_operador=solicitud.nombre_operador,
        )

        # 2. Enviar la actividad al backend Spring Boot
        resultado_guardado = guardar_tour_en_backend(
            tour
        )

        # 3. Devolver resultado
        return {
            "ok": True,
            "accion": resultado_guardado["accion"],
            "tour_extraido": tour,
            "actividad": resultado_guardado["actividad"],
        }

    except ValueError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo extraer y guardar la actividad: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error

