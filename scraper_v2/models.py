from typing import Any

from pydantic import BaseModel, Field


class BuscarRequest(BaseModel):
    url_operador: str = Field(min_length=8)
    pedido: str = Field(min_length=2)
    nombre_operador: str | None = None
    max_paginas: int = Field(default=10, ge=1, le=100)
    limite: int = Field(default=5, ge=1, le=50)
    puntaje_minimo: float = Field(default=25, ge=0, le=100)


class ExtraerRequest(BaseModel):
    url: str = Field(min_length=8)
    nombre_operador: str | None = None


class Precio(BaseModel):
    # Se conserva solo para compatibilidad con funciones antiguas. No forma
    # parte de TourExtraido y, por lo tanto, no aparece en la respuesta.
    nombre: str | None = None
    valor: float | None = None
    valor_anterior: float | None = None
    moneda: str | None = None
    unidad: str | None = None
    texto_original: str | None = None


class Ubicacion(BaseModel):
    pais: str | None = None
    region: str | None = None
    ciudad: str | None = None
    direccion: str | None = None
    latitud: float | None = None
    longitud: float | None = None


class PasoItinerario(BaseModel):
    orden: int
    titulo: str | None = None
    descripcion: str
    duracion: str | None = None


class Calendario(BaseModel):
    tipo: str = "desconocido"
    periodo_consultado_desde: str | None = None
    periodo_consultado_hasta: str | None = None
    inicio_temporada: str | None = None
    fin_temporada: str | None = None
    fechas_disponibles: list[str] = Field(default_factory=list)
    horarios: list[str] = Field(default_factory=list)
    evidencia: list[str] = Field(default_factory=list)


class TourExtraido(BaseModel):
    nombre_operador: str
    url_operador: str
    source_url: str
    nombre: str | None = None
    descripcion_original: str | None = None
    descripcion_corta: str | None = None
    categoria: str | None = None
    ubicacion: Ubicacion = Field(default_factory=Ubicacion)
    duracion_original: str | None = None
    duracion_minutos: int | None = None
    edad_minima: int | None = None
    edad_maxima: int | None = None
    idiomas: list[str] = Field(default_factory=list)
    imagenes: list[str] = Field(default_factory=list)
    itinerario: list[PasoItinerario] = Field(default_factory=list)
    incluye: list[str] = Field(default_factory=list)
    no_incluye: list[str] = Field(default_factory=list)
    que_llevar: list[str] = Field(default_factory=list)
    no_llevar: list[str] = Field(default_factory=list)
    recomendaciones: list[str] = Field(default_factory=list)
    restricciones: list[str] = Field(default_factory=list)
    informacion_importante: list[str] = Field(default_factory=list)
    politica_cancelacion: str | None = None
    contacto: str | None = None
    calendario: Calendario = Field(default_factory=Calendario)
    evidencia_original: dict[str, Any] = Field(default_factory=dict)
    extraido_en: str
