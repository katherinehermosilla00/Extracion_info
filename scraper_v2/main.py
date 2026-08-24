from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import BuscarRequest, ExtraerRequest
from scraper import buscar_tours_relacionados, extraer_tour


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
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo realizar la búsqueda: "
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
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo extraer el tour: "
                f"{type(error).__name__}: {error}"
            ),
        ) from error
