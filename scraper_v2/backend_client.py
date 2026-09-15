import re
import unicodedata
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

import requests

from models import TourExtraido


BACKEND_URL = "http://localhost:8080"


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar_nombre(
    texto: str | None,
) -> str:

    texto = texto or ""

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(
            caracter
        )
    )

    texto = texto.lower()

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto,
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


# ============================================================
# LIMPIAR NOMBRE DE ACTIVIDAD
# ============================================================

def limpiar_nombre_actividad(
    nombre: str | None,
) -> str:

    if not nombre:
        return "Actividad sin nombre"

    nombre = nombre.strip()

    patrones = [
        r"\s*-\s*Reserva en Civitatis\.com\s*$",
        r"\s*\|\s*Civitatis\.com\s*$",
        r"\s*-\s*Civitatis\.com\s*$",
        r"\s*-\s*Reserva en Civitatis\s*$",
        r"\s*\|\s*Civitatis\s*$",
    ]

    for patron in patrones:

        nombre = re.sub(
            patron,
            "",
            nombre,
            flags=re.IGNORECASE,
        )

    return nombre.strip()


# ============================================================
# LIMPIAR URL DE ORIGEN
# ============================================================

def limpiar_url_origen(
    url: str | None,
) -> str | None:

    if not url:
        return None

    partes = urlsplit(
        url
    )

    parametros_tracking = {
        "_gl",
        "_ga",
        "_gid",
        "_gcl_au",
        "fbclid",
        "gclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "yclid",
        "dclid",
    }

    query_limpia = []

    for clave, valor in parse_qsl(
        partes.query,
        keep_blank_values=True,
    ):

        clave_lower = (
            clave.lower()
        )

        if (
            clave_lower
            in parametros_tracking
        ):
            continue

        if clave_lower.startswith(
            "utm_"
        ):
            continue

        query_limpia.append(
            (
                clave,
                valor,
            )
        )

    url_limpia = urlunsplit(
        (
            partes.scheme,
            partes.netloc,
            partes.path,
            urlencode(
                query_limpia
            ),
            "",
        )
    )

    return url_limpia


# ============================================================
# OPERADORES
# ============================================================

def obtener_operadores() -> list[dict]:

    respuesta = requests.get(
        f"{BACKEND_URL}/api/operadores",
        timeout=20,
    )

    respuesta.raise_for_status()

    return respuesta.json()


def buscar_operador_por_nombre(
    nombre_operador: str,
) -> dict | None:

    buscado = normalizar_nombre(
        nombre_operador
    )

    operadores = obtener_operadores()

    for operador in operadores:

        nombre = operador.get(
            "nombre"
        )

        if (
            normalizar_nombre(
                nombre
            )
            == buscado
        ):

            return operador

    return None


# ============================================================
# RESOLVER PAÍS Y OPERADOR
# ============================================================

def obtener_paises() -> list[dict]:

    respuesta = requests.get(
        f"{BACKEND_URL}/api/paises",
        timeout=20,
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    if not isinstance(datos, list):
        raise RuntimeError(
            "Spring Boot no devolvió una lista de países."
        )

    return datos


def buscar_pais_por_nombre(
    nombre_pais: str,
) -> dict | None:

    buscado = normalizar_nombre(
        nombre_pais
    )

    if not buscado:
        return None

    for pais in obtener_paises():

        nombre = pais.get(
            "nombre"
        )

        if (
            normalizar_nombre(nombre)
            == buscado
        ):
            return pais

    return None


def crear_operador_desde_tour(
    tour: TourExtraido,
) -> dict:

    nombre_operador = (
        tour.nombre_operador
        or ""
    ).strip()

    if not nombre_operador:
        raise RuntimeError(
            "No se pudo determinar "
            "el nombre del operador."
        )

    ubicacion = getattr(
        tour,
        "ubicacion",
        None,
    )

    nombre_pais = None

    if ubicacion is not None:
        nombre_pais = getattr(
            ubicacion,
            "pais",
            None,
        )

    if not nombre_pais:
        raise RuntimeError(
            "No se puede crear el operador "
            f"'{nombre_operador}' porque la actividad "
            "no contiene un país."
        )

    pais = buscar_pais_por_nombre(
        nombre_pais
    )

    if pais is None:
        raise RuntimeError(
            "No se encontró el país "
            f"'{nombre_pais}' en Spring Boot. "
            "El operador no fue creado."
        )

    pais_id = pais.get(
        "id"
    )

    if pais_id is None:
        raise RuntimeError(
            "El país encontrado no contiene ID."
        )

    sitio_web = (
        tour.url_operador
        or tour.source_url
        or None
    )

    payload = {
        "nombre": nombre_operador,
        "sitioWeb": sitio_web,
        "estado": "ACTIVO",
    }

    respuesta = requests.post(
        f"{BACKEND_URL}/api/operadores",
        params={
            "paisId": pais_id
        },
        json=payload,
        timeout=30,
    )

    if respuesta.status_code not in (
        200,
        201,
    ):
        raise RuntimeError(
            "No se pudo crear el operador "
            f"'{nombre_operador}'. "
            f"HTTP {respuesta.status_code}: "
            f"{respuesta.text[:500]}"
        )

    operador = respuesta.json()

    if operador.get("id") is None:
        raise RuntimeError(
            "Spring Boot creó el operador, "
            "pero no devolvió su ID."
        )

    return operador


def obtener_o_crear_operador(
    tour: TourExtraido,
) -> dict:

    operador = buscar_operador_por_nombre(
        tour.nombre_operador
    )

    if operador is not None:
        return operador

    # Segunda consulta antes de crear para
    # reducir duplicados por concurrencia.
    operador = buscar_operador_por_nombre(
        tour.nombre_operador
    )

    if operador is not None:
        return operador

    return crear_operador_desde_tour(
        tour
    )


# ============================================================
# UBICACIÓN
# ============================================================

def convertir_ubicacion_a_texto(
    tour: TourExtraido,
) -> str | None:

    ubicacion = tour.ubicacion

    if not ubicacion:
        return None

    # Si existe dirección específica,
    # tiene prioridad.
    if ubicacion.direccion:

        direccion = (
            ubicacion.direccion
            .strip()
        )

        if direccion:
            return direccion

    partes = []

    for valor in [
        ubicacion.ciudad,
        ubicacion.region,
        ubicacion.pais,
    ]:

        if not valor:
            continue

        valor_limpio = (
            valor.strip()
        )

        if (
            valor_limpio
            and valor_limpio
            not in partes
        ):

            partes.append(
                valor_limpio
            )

    if not partes:
        return None

    return ", ".join(
        partes
    )


# ============================================================
# DESCRIPCIÓN
# ============================================================

def limpiar_descripcion(
    texto: str | None,
) -> str | None:

    if not texto:
        return None

    texto = texto.strip()

    if len(texto) < 10:
        return None

    return texto


def construir_descripcion(
    tour: TourExtraido,
) -> str | None:

    corta = limpiar_descripcion(
        tour.descripcion_corta
    )

    original = limpiar_descripcion(
        tour.descripcion_original
    )

    if (
        not corta
        and not original
    ):
        return None

    if (
        corta
        and not original
    ):
        return corta

    if (
        original
        and not corta
    ):
        return original

    if (
        normalizar_nombre(
            corta
        )
        == normalizar_nombre(
            original
        )
    ):
        return original

    corta_norm = normalizar_nombre(
        corta
    )

    original_norm = normalizar_nombre(
        original
    )

    if (
        corta_norm
        in original_norm
    ):
        return original

    if (
        original_norm
        in corta_norm
    ):
        return corta

    return (
        f"{corta}\n\n"
        f"{original}"
    )


# ============================================================
# LISTAS / ITINERARIO / HORARIOS
# ============================================================

def limpiar_lista_textos(
    valores,
) -> list[str]:

    resultado = []
    vistos = set()

    for valor in valores or []:

        if valor is None:
            continue

        texto = str(valor).strip()

        if not texto:
            continue

        clave = texto.casefold()

        if clave in vistos:
            continue

        vistos.add(clave)
        resultado.append(texto)

    return resultado


def convertir_itinerario_a_textos(
    tour: TourExtraido,
) -> list[str]:

    resultado = []
    vistos = set()

    for paso in tour.itinerario or []:

        titulo = (
            getattr(
                paso,
                "titulo",
                None,
            )
            or ""
        ).strip()

        descripcion = (
            getattr(
                paso,
                "descripcion",
                None,
            )
            or ""
        ).strip()

        duracion = (
            getattr(
                paso,
                "duracion",
                None,
            )
            or ""
        ).strip()

        if titulo and descripcion:

            if normalizar_nombre(titulo) in normalizar_nombre(descripcion):
                texto = descripcion
            else:
                texto = f"{titulo}: {descripcion}"

        elif descripcion:
            texto = descripcion

        elif titulo:
            texto = titulo

        else:
            continue

        if duracion:

            duracion_normalizada = normalizar_nombre(
                duracion
            )

            texto_normalizado = normalizar_nombre(
                texto
            )

            if (
                duracion_normalizada
                and duracion_normalizada
                not in texto_normalizado
            ):
                texto = (
                    f"{texto} "
                    f"({duracion})"
                )

        texto = texto.strip()

        if not texto:
            continue

        clave = texto.casefold()

        if clave in vistos:
            continue

        vistos.add(clave)
        resultado.append(texto)

    return resultado


def obtener_horarios(
    tour: TourExtraido,
) -> list[str]:

    calendario = getattr(
        tour,
        "calendario",
        None,
    )

    if calendario is None:
        return []

    horarios = getattr(
        calendario,
        "horarios",
        [],
    )

    return limpiar_lista_textos(
        horarios
    )


# ============================================================
# CONVERTIR TOUR -> ACTIVIDAD
# ============================================================

def convertir_tour_a_actividad(
    tour: TourExtraido,
    operador_id: int,
) -> dict:

    nombre = (
        limpiar_nombre_actividad(
            tour.nombre
        )
    )

    descripcion = (
        construir_descripcion(
            tour
        )
    )

    ubicacion = (
        convertir_ubicacion_a_texto(
            tour
        )
    )

    destino = (
        tour.destino.strip()
        if tour.destino
        else None
    )

    url_origen = (
        limpiar_url_origen(
            tour.source_url
        )
    )

    return {

        "nombre":
            nombre,

        "descripcion":
            descripcion,

        "ubicacion":
            ubicacion,

        "destino":
            destino,

        "duracion":
            tour.duracion_original,

        "edadMinima":
            tour.edad_minima,

        "edadMaxima":
            tour.edad_maxima,

        "idiomas":
            limpiar_lista_textos(
                tour.idiomas
            ),

        "imagenes":
            limpiar_lista_textos(
                tour.imagenes
            ),

        "highlights":
            limpiar_lista_textos(
                tour.highlights
            ),

        "itinerario":
            convertir_itinerario_a_textos(
                tour
            ),

        "horarios":
            obtener_horarios(
                tour
            ),

        "restricciones":
            limpiar_lista_textos(
                tour.restricciones
            ),

        "urlOrigen":
            url_origen,

        "operadorTuristico": {
            "id":
                operador_id
        },

        "activo":
            True,
    }


# ============================================================
# BUSCAR ACTIVIDAD EXISTENTE
# ============================================================

def buscar_actividad_existente(
    operador_id: int,
    nombre: str,
    url_origen: str | None,
) -> dict | None:

    endpoint = (
        f"{BACKEND_URL}"
        "/api/actividades/existe"
    )

    # --------------------------------------------------------
    # PRIMERO POR URL
    # --------------------------------------------------------

    if url_origen:

        respuesta = requests.get(
            endpoint,
            params={
                "urlOrigen":
                    url_origen
            },
            timeout=15,
        )

        if (
            respuesta.status_code
            == 200
        ):
            return (
                respuesta.json()
            )

        if (
            respuesta.status_code
            not in (404,)
        ):
            respuesta.raise_for_status()

    # --------------------------------------------------------
    # DESPUÉS POR OPERADOR + NOMBRE
    # --------------------------------------------------------

    respuesta = requests.get(
        endpoint,
        params={
            "operadorTuristicoId":
                operador_id,

            "nombre":
                nombre,
        },
        timeout=15,
    )

    if (
        respuesta.status_code
        == 200
    ):
        return (
            respuesta.json()
        )

    if (
        respuesta.status_code
        == 404
    ):
        return None

    respuesta.raise_for_status()

    return None


# ============================================================
# PROTEGER DATOS EXISTENTES
# ============================================================

def elegir_valor(
    nuevo,
    existente,
):

    if nuevo is None:
        return existente

    if isinstance(
        nuevo,
        str,
    ):

        if not nuevo.strip():
            return existente

    return nuevo


def elegir_lista(
    nueva,
    existente,
):

    if nueva:
        return nueva

    if existente:
        return existente

    return []


def construir_payload_actualizacion(
    nuevo: dict,
    existente: dict,
) -> dict:

    return {

        "nombre":
            nuevo["nombre"],

        "descripcion":
            elegir_valor(
                nuevo.get(
                    "descripcion"
                ),
                existente.get(
                    "descripcion"
                ),
            ),

        "ubicacion":
            elegir_valor(
                nuevo.get(
                    "ubicacion"
                ),
                existente.get(
                    "ubicacion"
                ),
            ),

        "destino":
            elegir_valor(
                nuevo.get(
                    "destino"
                ),
                existente.get(
                    "destino"
                ),
            ),

        "duracion":
            elegir_valor(
                nuevo.get(
                    "duracion"
                ),
                existente.get(
                    "duracion"
                ),
            ),

        "edadMinima":
            elegir_valor(
                nuevo.get(
                    "edadMinima"
                ),
                existente.get(
                    "edadMinima"
                ),
            ),

        "edadMaxima":
            nuevo.get(
                "edadMaxima"
            ),

        "idiomas":
            elegir_lista(
                nuevo.get(
                    "idiomas"
                ),
                existente.get(
                    "idiomas"
                ),
            ),

        "imagenes":
            elegir_lista(
                nuevo.get(
                    "imagenes"
                ),
                existente.get(
                    "imagenes"
                ),
            ),

        "highlights":
            elegir_lista(
                nuevo.get(
                    "highlights"
                ),
                existente.get(
                    "highlights"
                ),
            ),

        "itinerario":
            elegir_lista(
                nuevo.get(
                    "itinerario"
                ),
                existente.get(
                    "itinerario"
                ),
            ),

        "horarios":
            elegir_lista(
                nuevo.get(
                    "horarios"
                ),
                existente.get(
                    "horarios"
                ),
            ),

        "restricciones":
            elegir_lista(
                nuevo.get(
                    "restricciones"
                ),
                existente.get(
                    "restricciones"
                ),
            ),

        "urlOrigen":
            elegir_valor(
                nuevo.get(
                    "urlOrigen"
                ),
                existente.get(
                    "urlOrigen"
                ),
            ),

        "operadorTuristico":
            nuevo[
                "operadorTuristico"
            ],

        "activo":
            True,
    }


# ============================================================
# GUARDAR / ACTUALIZAR
# ============================================================

def guardar_tour_en_backend(
    tour: TourExtraido,
) -> dict:

    # --------------------------------------------------------
    # 1. BUSCAR OPERADOR
    # --------------------------------------------------------

    operador = obtener_o_crear_operador(
        tour
    )

    operador_id = operador.get(
        "id"
    )

    if operador_id is None:

        raise RuntimeError(
            "El operador encontrado "
            "no contiene ID."
        )

    # --------------------------------------------------------
    # 2. CONVERTIR TOUR EXTRAÍDO
    # --------------------------------------------------------

    payload = (
        convertir_tour_a_actividad(
            tour,
            operador_id,
        )
    )

    # --------------------------------------------------------
    # 3. VALIDAR NOMBRE
    # --------------------------------------------------------

    nombre_actividad = (
        payload.get(
            "nombre"
        )
        or ""
    ).strip()

    if not nombre_actividad:

        raise RuntimeError(
            "No se pudo determinar "
            "el nombre de la actividad."
        )

    # --------------------------------------------------------
    # 4. BUSCAR DUPLICADO
    # --------------------------------------------------------

    existente = (
        buscar_actividad_existente(
            operador_id=
                operador_id,

            nombre=
                nombre_actividad,

            url_origen=
                payload.get(
                    "urlOrigen"
                ),
        )
    )

    # --------------------------------------------------------
    # 5. ACTUALIZAR
    # --------------------------------------------------------

    if existente:

        actividad_id = (
            existente.get(
                "id"
            )
        )

        if actividad_id is None:

            raise RuntimeError(
                "Actividad existente "
                "sin ID."
            )

        payload_actualizado = (
            construir_payload_actualizacion(
                payload,
                existente,
            )
        )

        respuesta = requests.put(
            (
                f"{BACKEND_URL}"
                f"/api/actividades/"
                f"{actividad_id}"
            ),
            json=payload_actualizado,
            timeout=30,
        )

        respuesta.raise_for_status()

        return {
            "accion":
                "ACTUALIZADA",

            "actividad":
                respuesta.json(),

            "url_origen":
                payload_actualizado.get(
                    "urlOrigen"
                ),
        }

    # --------------------------------------------------------
    # 6. CREAR
    # --------------------------------------------------------

    respuesta = requests.post(
        (
            f"{BACKEND_URL}"
            "/api/actividades"
        ),
        json=payload,
        timeout=30,
    )

    respuesta.raise_for_status()

    return {
        "accion":
            "CREADA",

        "actividad":
            respuesta.json(),

        "url_origen":
            payload.get(
                "urlOrigen"
            ),
    }