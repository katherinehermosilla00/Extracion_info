import asyncio
import sys
import time
import json
import re
from datetime import datetime, timezone
from urllib.parse import (
    urljoin,
    urlparse,
    urldefrag,
)

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from matcher import (
    calcular_coincidencia,
    normalizar_texto,
)

from models import (
    Calendario,
    PasoItinerario,
    Precio,
    TourExtraido,
    Ubicacion,
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


INDICADORES_BLOQUEO = (
    "access denied",
    "captcha",
    "verify you are human",
    "checking your browser",
    "cloudflare",
)


PALABRAS_TOUR = (
    "tour",
    "tours",
    "excursion",
    "excursiones",
    "experiencia",
    "experiencias",
    "actividad",
    "actividades",
    "aventura",
    "trekking",
    "sendero",
    "senderismo",
    "hiking",
    "ave",
    "aves",
    "bird",
    "birds",
    "birdwatching",
    "avistamiento",
    "observacion",
    "kayak",
    "kayaking",
    "cabalgata",
    "cabalgatas",
    "navegacion",
    "paseo",
    "paseos",
    "ballena",
    "ballenas",
    "baleia",
    "baleias",
    "whale",
    "cetaceo",
    "cetaceos",
    "delfin",
    "delfines",
    "dolphin",
    "pingüino",
    "pinguino",
    "penguin",
    "fauna",
    "flora",
    "safari",
    "rafting",
    "buceo",
    "mergulho",
    "diving",
    "snorkel",
    "surf",
    "pesca",
    "fishing",
    "escalada",
    "climbing",
    "montañismo",
    "montanismo",
    "volcan",
    "canopy",
    "tirolesa",
    "zipline",
    "rappel",
    "bicicleta",
    "ciclismo",
    "cycling",
    "gastronomia",
    "culinaria",
    "vino",
    "viñedo",
    "vinedo",
    "enoturismo",
    "cultura",
    "cultural",
    "patrimonio",
    "museo",
    "crucero",
    "cruise",
    "esqui",
    "ski",
    "snowboard",
    "nieve",
    "cachoeira",
    "cascada",
    "waterfall",
    "programa",
    "transporte",
    "traslado",
)


PALABRAS_EXCLUIDAS = (
    "contacto",
    "login",
    "registro",
    "privacidad",
    "terminos",
    "facebook",
    "instagram",
    "whatsapp",
    "mailto:",
    "tel:",
    ".pdf",
    ".webp",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".mp4",
    ".webm",
    ".zip",
    "/wp-content/uploads/",
)


TEXTOS_ENLACE_GENERICOS = {
    "ver mas",
    "ver más",
    "leer mas",
    "leer más",
    "conocer mas",
    "conocer más",
    "more",
    "read more",
    "saiba mais",
    "ver detalhes",
}


def limpiar_url(url: str) -> str:
    url_sin_fragmento, _ = urldefrag(url)

    return url_sin_fragmento.rstrip("/")


def mismo_dominio(
    url: str,
    dominio: str,
) -> bool:
    dominio_url = urlparse(url).netloc.lower()
    dominio_esperado = dominio.lower()

    if dominio_url.startswith("www."):
        dominio_url = dominio_url[4:]

    if dominio_esperado.startswith("www."):
        dominio_esperado = dominio_esperado[4:]

    return dominio_url == dominio_esperado

def obtener_html_playwright(url: str) -> str:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(
            headless=True
        )

        pagina = navegador.new_page(
            user_agent=HEADERS["User-Agent"],
            ignore_https_errors=True,
            viewport={
                "width": 1366,
                "height": 900,
            },
        )

        try:
            # No esperamos "networkidle": analítica, chats y calendarios
            # suelen dejar conexiones abiertas y retrasan innecesariamente.
            pagina.goto(
                url,
                wait_until="domcontentloaded",
                timeout=20000,
            )
            pagina.wait_for_timeout(2000)

            try:
                pagina.evaluate("window.stop()")
            except Exception:
                pass

            return pagina.content()

        finally:
            navegador.close()

def obtener_html(url: str) -> str:
    try:
        respuesta = requests.get(
            url,
            headers=HEADERS,
            timeout=(5, 10),
        )

        respuesta.raise_for_status()

        contenido = respuesta.text
        contenido_minusculas = contenido.lower()

        pagina_bloqueada = any(
            indicador in contenido_minusculas
            for indicador in INDICADORES_BLOQUEO
        )

        if pagina_bloqueada:
            raise RuntimeError(
                "El sitio devolvió una página de bloqueo"
            )

        return contenido

    except Exception as error:
        print(
            f"Requests no pudo abrir {url}: {error}. "
            "Intentando con Playwright."
        )

        return obtener_html_playwright(url)


def html_tiene_detalle_turistico(html: str) -> bool:
    """Determina si la respuesta rápida contiene una ficha utilizable."""
    soup = BeautifulSoup(html, "html.parser")
    texto = normalizar_texto(soup.get_text(" ", strip=True))

    marcadores = (
        "incluye",
        "includes",
        "incluido",
        "itinerario",
        "itinerary",
        "dia 1",
        "day 1",
        "duracion",
        "duration",
        "recomendaciones",
        "recommendations",
        "no incluye",
        "not included",
    )
    coincidencias = sum(
        1 for marcador in marcadores
        if marcador in texto
    )

    # Una página con poco texto o sin secciones suele ser solo la
    # estructura inicial de una aplicación JavaScript.
    return len(texto) >= 1000 and coincidencias >= 2

def parece_enlace_tour(
    url: str,
    texto: str,
) -> bool:
    contenido = f"{url} {texto}".lower()

    if any(
        palabra in contenido
        for palabra in PALABRAS_EXCLUIDAS
    ):
        return False

    return any(
        palabra in contenido
        for palabra in PALABRAS_TOUR
    )


def titulo_desde_url(url: str) -> str:
    ruta = urlparse(url).path.strip("/")

    if not ruta:
        return urlparse(url).netloc

    ultima_parte = ruta.split("/")[-1]

    return ultima_parte.replace("-", " ").replace(
        "_",
        " ",
    ).strip()


def descubrir_urls_sitemap(
    url_operador: str,
    limite: int = 1000,
) -> list[str]:
    """Obtiene páginas públicas declaradas por el propio operador."""
    url_inicial = limpiar_url(url_operador)
    partes = urlparse(url_inicial)
    base = f"{partes.scheme}://{partes.netloc}"
    dominio = partes.netloc

    pendientes = [
        f"{base}/wp-sitemap.xml",
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
    ]
    visitados = set()
    paginas = []

    while pendientes and len(visitados) < 30:
        sitemap_url = pendientes.pop(0)

        if sitemap_url in visitados:
            continue

        visitados.add(sitemap_url)

        try:
            respuesta = requests.get(
                sitemap_url,
                headers=HEADERS,
                timeout=(4, 7),
            )

            if respuesta.status_code != 200:
                continue

            ubicaciones = re.findall(
                r"<loc>\s*(.*?)\s*</loc>",
                respuesta.text,
                flags=re.IGNORECASE,
            )

            for ubicacion in ubicaciones:
                url_encontrada = limpiar_url(
                    ubicacion.replace("&amp;", "&")
                )

                if not mismo_dominio(
                    url_encontrada,
                    dominio,
                ):
                    continue

                if urlparse(url_encontrada).path.lower().endswith(
                    ".xml"
                ):
                    if url_encontrada not in visitados:
                        pendientes.append(url_encontrada)
                    continue

                if url_encontrada not in paginas:
                    paginas.append(url_encontrada)

                if len(paginas) >= limite:
                    return paginas

        except Exception as error:
            print(
                f"No se pudo leer {sitemap_url}: {error}"
            )

    return paginas

def descubrir_tours(
    url_operador: str,
    max_paginas: int = 5,
) -> list[dict]:
    url_inicial = limpiar_url(url_operador)
    dominio = urlparse(url_inicial).netloc

    paginas_pendientes = [url_inicial]
    paginas_visitadas = set()

    resultados = {}

    # Primero consulta los mapas públicos del sitio. Esto permite
    # descubrir páginas aunque las tarjetas se creen con JavaScript.
    for url_sitemap in descubrir_urls_sitemap(
        url_inicial
    ):
        titulo_sitemap = titulo_desde_url(
            url_sitemap
        )

        if parece_enlace_tour(
            url_sitemap,
            titulo_sitemap,
        ):
            resultados[url_sitemap] = {
                "titulo": titulo_sitemap,
                "url": url_sitemap,
            }

    while (
        paginas_pendientes
        and len(paginas_visitadas) < max_paginas
    ):
        pagina_actual = paginas_pendientes.pop(0)

        if pagina_actual in paginas_visitadas:
            continue

        paginas_visitadas.add(pagina_actual)

        print(
            f"Descubriendo tours en: {pagina_actual}"
        )

        # Requests resuelve la mayoría de los sitios en menos de un segundo.
        # obtener_html usa Playwright automáticamente solo si requests falla
        # o si el sitio devuelve una pantalla de bloqueo.
        html = obtener_html(pagina_actual)
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        contenido_principal = (
            soup.find("main")
            or soup.find(
                attrs={"role": "main"}
            )
            or soup
        )

        enlaces = contenido_principal.find_all(
            "a",
            href=True,
        )

        for enlace in enlaces:
            href = enlace.get(
                "href",
                "",
            ).strip()

            if (
                not href
                or href.startswith("#")
                or href.startswith("javascript:")
            ):
                continue

            url_absoluta = limpiar_url(
                urljoin(
                    pagina_actual,
                    href,
                )
            )

            if not mismo_dominio(
                url_absoluta,
                dominio,
            ):
                continue

            if url_absoluta == url_inicial:
                continue

            texto = enlace.get_text(
                " ",
                strip=True,
            )

            if not parece_enlace_tour(
                url_absoluta,
                texto,
            ):
                continue

            titulo = (
                texto
                or enlace.get("title")
                or titulo_desde_url(url_absoluta)
            )

            if normalizar_texto(titulo) in {
                normalizar_texto(valor)
                for valor in TEXTOS_ENLACE_GENERICOS
            }:
                titulo = titulo_desde_url(
                    url_absoluta
                )

            if url_absoluta not in resultados:
                resultados[url_absoluta] = {
                    "titulo": titulo,
                    "url": url_absoluta,
                }

            if (
                url_absoluta not in paginas_visitadas
                and url_absoluta
                not in paginas_pendientes
            ):
                paginas_pendientes.append(
                    url_absoluta
                )

    return list(resultados.values())

def buscar_tours_relacionados(
    url_operador: str,
    pedido: str,
    max_paginas: int = 5,
    limite: int = 5,
    puntaje_minimo: float = 25,
) -> dict:
    tours_descubiertos = descubrir_tours(
        url_operador=url_operador,
        max_paginas=max_paginas,
    )

    resultados = []

    for tour in tours_descubiertos:
        titulo = tour["titulo"]
        url = tour["url"]

        texto_comparable = (
            f"{titulo} {titulo_desde_url(url)}"
        )

        coincidencia = calcular_coincidencia(
            pedido=pedido,
            titulo=texto_comparable,
        )

        if (
            coincidencia["puntaje"]
            < puntaje_minimo
        ):
            continue

        resultados.append({
            "titulo_encontrado": titulo,
            "url": url,
            "puntaje": coincidencia["puntaje"],
            "nivel": coincidencia["nivel"],
            "palabras_buscadas": coincidencia[
                "palabras_buscadas"
            ],
            "palabras_coincidentes": coincidencia[
                "palabras_coincidentes"
            ],
        })

    resultados.sort(
        key=lambda resultado: resultado["puntaje"],
        reverse=True,
    )

    resultados = resultados[:limite]

    if resultados:
        mensaje = (
            "Se encontraron opciones relacionadas."
        )
    else:
        mensaje = (
            "No se encontraron coincidencias sobre "
            "el puntaje mínimo. Prueba con una "
            "ubicación, categoría o palabra más general."
        )

    return {
        "pedido": pedido,
        "url_operador": url_operador,
        "tours_descubiertos": len(
            tours_descubiertos
        ),
        "cantidad_resultados": len(resultados),
        "resultados": resultados,
        "mensaje": mensaje,
    }

def obtener_json_ld(
    soup: BeautifulSoup,
) -> list[dict]:
    resultados = []

    scripts = soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    )

    for script in scripts:
        try:
            contenido = json.loads(
                script.string or ""
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            continue

        if isinstance(contenido, list):
            resultados.extend(
                elemento
                for elemento in contenido
                if isinstance(elemento, dict)
            )

        elif isinstance(contenido, dict):
            grafo = contenido.get("@graph")

            if isinstance(grafo, list):
                resultados.extend(
                    elemento
                    for elemento in grafo
                    if isinstance(elemento, dict)
                )
            else:
                resultados.append(contenido)

    return resultados

def buscar_entidad_tour(
    datos_json_ld: list[dict],
) -> dict:
    tipos_permitidos = {
        "Product",
        "TouristTrip",
        "Trip",
        "Event",
        "Service",
        "Offer",
    }

    for elemento in datos_json_ld:
        tipo = elemento.get("@type", "")

        if isinstance(tipo, list):
            coincide = any(
                valor in tipos_permitidos
                for valor in tipo
            )
        else:
            coincide = tipo in tipos_permitidos

        if coincide:
            return elemento

    return {}


def obtener_meta(
    soup: BeautifulSoup,
    nombre: str,
) -> str | None:
    etiqueta = (
        soup.find(
            "meta",
            attrs={"property": nombre},
        )
        or soup.find(
            "meta",
            attrs={"name": nombre},
        )
    )

    if not etiqueta:
        return None

    contenido = etiqueta.get("content")

    if not contenido:
        return None

    return contenido.strip()

def extraer_imagenes(
    entidad: dict,
    soup: BeautifulSoup,
    url: str,
) -> list[str]:
    imagenes = []

    imagen_entidad = entidad.get("image")

    if isinstance(imagen_entidad, str):
        imagenes.append(imagen_entidad)

    elif isinstance(imagen_entidad, list):
        imagenes.extend(
            imagen
            for imagen in imagen_entidad
            if isinstance(imagen, str)
        )

    elif isinstance(imagen_entidad, dict):
        imagen = (
            imagen_entidad.get("url")
            or imagen_entidad.get("contentUrl")
        )

        if imagen:
            imagenes.append(imagen)

    imagen_meta = obtener_meta(
        soup,
        "og:image",
    )

    if imagen_meta:
        imagenes.append(imagen_meta)

        palabras_no_validas = (
        "logo",
        "icon",
        "favicon",
        "sprite",
        "placeholder",
        "avatar",
        "payment",
        "ticket",
        "pixel",
        "mascota",
        "mascot",
        "espanol",
        "english",
        "idioma",
        "language",
        "flag",
    )

    for etiqueta in soup.find_all("img"):
        imagen = (
            etiqueta.get("src")
            or etiqueta.get("data-src")
            or etiqueta.get("data-lazy-src")
        )

        if (
            not imagen
            or imagen.startswith("data:")
        ):
            continue

        if any(
            palabra in imagen.lower()
            for palabra in palabras_no_validas
        ):
            continue

        imagenes.append(imagen)

    imagenes_finales = []

    for imagen in imagenes:
        imagen_absoluta = urljoin(
            url,
            imagen,
        )

        if imagen_absoluta not in imagenes_finales:
            imagenes_finales.append(
                imagen_absoluta
            )

    return imagenes_finales[:10]

def convertir_numero(
    valor: str | int | float | None,
) -> float | None:
    if valor is None:
        return None

    texto = re.sub(
        r"[^\d,.]",
        "",
        str(valor),
    )

    if not texto:
        return None

    if "." in texto and "," in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "")
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")

    elif re.fullmatch(
        r"\d{1,3}([.,]\d{3})+",
        texto,
    ):
        texto = re.sub(r"[.,]", "", texto)

    else:
        texto = texto.replace(",", ".")

    try:
        return float(texto)

    except ValueError:
        return None

def detectar_moneda(texto: str | None) -> str | None:
    texto = (texto or "").upper()

    monedas = {
        "CLP": "CLP",
        "COP": "COP",
        "USD": "USD",
        "US$": "USD",
        "EUR": "EUR",
        "€": "EUR",
        "BRL": "BRL",
        "R$": "BRL",
        "ARS": "ARS",
        "PEN": "PEN",
        "MXN": "MXN",
        "UYU": "UYU",
    }

    for indicador, moneda in monedas.items():
        if indicador in texto:
            return moneda

    return None

def extraer_precios(
    entidad: dict,
    soup: BeautifulSoup,
) -> list[Precio]:
    resultados = []

    # Primero intenta obtener precios estructurados.
    ofertas = entidad.get("offers", {})

    if isinstance(ofertas, dict):
        ofertas = [ofertas]

    if isinstance(ofertas, list):
        for oferta in ofertas:
            if not isinstance(oferta, dict):
                continue

            valor_original = (
                oferta.get("price")
                or oferta.get("lowPrice")
                or oferta.get("highPrice")
            )

            moneda = oferta.get(
                "priceCurrency"
            )

            valor = convertir_numero(
                valor_original
            )

            if valor is None or valor == 0:
                continue

            if (
                moneda in {"COP", "CLP"}
                and valor < 1000
            ):
                continue

            resultados.append(
                Precio(
                    valor=valor,
                    moneda=moneda,
                    texto_original=str(
                        valor_original
                    ),
                )
            )

    # Obtiene el texto visible de la página.
    texto_pagina = soup.get_text(
        " ",
        strip=True,
    )

    # Elimina la parte donde aparecen otros tours.
    frases_corte = (
        "Otros tours que te pueden interesar",
        "También te puede interesar",
        "Tours relacionados",
        "Experiencias relacionadas",
    )

    for frase in frases_corte:
        posicion = texto_pagina.lower().find(
            frase.lower()
        )

        if posicion != -1:
            texto_pagina = texto_pagina[
                :posicion
            ]

    # Detecta la moneda general publicada.
    moneda_pagina = detectar_moneda(
        texto_pagina
    )

    patron_precio = re.compile(
        r"(?:CLP|COP|USD|US\$|EUR|BRL|R\$|"
        r"ARS|PEN|MXN|UYU|\$|€)"
        r"\s*[\d][\d.,]*"
        r"|[\d][\d.,]*\s*"
        r"(?:CLP|COP|USD|EUR|BRL|ARS|PEN|MXN|UYU)",
        re.IGNORECASE,
    )

    coincidencias = patron_precio.findall(
        texto_pagina
    )

    for coincidencia in coincidencias:
        valor_original = coincidencia.strip()

        valor = convertir_numero(
            valor_original
        )

        moneda = (
            detectar_moneda(
                valor_original
            )
            or moneda_pagina
        )

        if valor is None or valor == 0:
            continue

        # Evita interpretar duraciones como precios:
        # por ejemplo, "COP 3.5 horas".
        if (
            moneda in {"COP", "CLP"}
            and valor < 1000
        ):
            continue

        repetido = any(
            precio.valor == valor
            and precio.moneda == moneda
            for precio in resultados
        )

        if repetido:
            continue

        resultados.append(
            Precio(
                valor=valor,
                moneda=moneda,
                texto_original=valor_original,
            )
        )

    return resultados[:20]

def extraer_duracion(
    texto: str,
) -> tuple[str | None, int | None]:
    patron = re.compile(
        r"\b\d+(?:[.,]\d+)?\s*"
        r"(?:minutos?|minutes?|mins?|"
        r"horas?|hours?|hrs?|"
        r"d[ií]as?|days?|"
        r"noches?|nights?)\b",
        re.IGNORECASE,
    )

    coincidencia = patron.search(texto)

    if not coincidencia:
        return None, None

    duracion_original = coincidencia.group(0)

    numero_match = re.search(
        r"\d+(?:[.,]\d+)?",
        duracion_original,
    )

    if not numero_match:
        return duracion_original, None

    cantidad = float(
        numero_match.group(0).replace(",", ".")
    )

    texto_minusculas = duracion_original.lower()

    if (
        "min" in texto_minusculas
        and "hora" not in texto_minusculas
    ):
        minutos = cantidad

    elif (
        "día" in texto_minusculas
        or "dia" in texto_minusculas
        or "day" in texto_minusculas
        or "noche" in texto_minusculas
        or "night" in texto_minusculas
    ):
        minutos = cantidad * 24 * 60

    else:
        minutos = cantidad * 60

    return (
        duracion_original,
        int(minutos),
    )


def extraer_edades(
    texto: str,
) -> tuple[int | None, int | None]:
    patron_rango = re.search(
        r"(?:de\s*)?(\d+)\s*(?:a|-)\s*(\d+)"
        r"\s*años",
        texto,
        re.IGNORECASE,
    )

    if patron_rango:
        return (
            int(patron_rango.group(1)),
            int(patron_rango.group(2)),
        )

    patron_minimo = re.search(
        r"(?:mayores?|desde|mínimo|minimo)"
        r"\s*(?:de)?\s*(\d+)\s*años",
        texto,
        re.IGNORECASE,
    )

    if patron_minimo:
        return int(patron_minimo.group(1)), None

    if re.search(
        r"sin restricci[oó]n de edad",
        texto,
        re.IGNORECASE,
    ):
        return 0, None

    return None, None


def extraer_idiomas(texto: str) -> list[str]:
    idiomas_posibles = (
        "Español",
        "Inglés",
        "Portugués",
        "Portugués brasileño",
        "Francés",
        "Alemán",
        "Italiano",
    )

    encontrados = []

    for idioma in idiomas_posibles:
        if re.search(
            rf"\b{re.escape(idioma)}\b",
            texto,
            re.IGNORECASE,
        ):
            encontrados.append(idioma)

    return encontrados

def buscar_encabezado(
    soup: BeautifulSoup,
    nombres: tuple[str, ...],
):
    nombres_normalizados = [
        normalizar_texto(nombre)
        for nombre in nombres
    ]

    for encabezado in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    ):
        texto = normalizar_texto(
            encabezado.get_text(
                " ",
                strip=True,
            )
        )

        if any(
            nombre in texto
            for nombre in nombres_normalizados
        ):
            return encabezado

    return None


def extraer_contenido_seccion(
    soup: BeautifulSoup,
    nombres: tuple[str, ...],
    limite: int = 30,
) -> list[str]:
    encabezado = buscar_encabezado(
        soup,
        nombres,
    )

    if not encabezado:
        return []

    nivel_encabezado = int(encabezado.name[1])
    resultados = []

    for elemento in encabezado.find_all_next():
        if elemento is encabezado:
            continue

        if elemento.name in {
            "h1", "h2", "h3",
            "h4", "h5", "h6",
        }:
            nivel_actual = int(elemento.name[1])

            if nivel_actual <= nivel_encabezado:
                break

            texto = elemento.get_text(
                " ",
                strip=True,
            )

        elif elemento.name == "li":
            texto = elemento.get_text(
                " ",
                strip=True,
            )

        elif (
            elemento.name == "p"
            and elemento.find_parent("li") is None
        ):
            texto = elemento.get_text(
                " ",
                strip=True,
            )

        else:
            continue

        if texto and texto not in resultados:
            resultados.append(texto)

        if len(resultados) >= limite:
            break

    return resultados

def extraer_itinerario(
    soup: BeautifulSoup,
) -> list[PasoItinerario]:
    elementos = extraer_contenido_seccion(
        soup,
        (
            "itinerario",
            "qué esperar",
            "que esperar",
            "programa",
            "recorrido",
        ),
        limite=25,
    )

    pasos_por_dia = []

    for etiqueta in soup.find_all(
        ["li", "p", "h2", "h3", "h4", "h5"]
    ):
        texto = etiqueta.get_text(
            " ",
            strip=True,
        )
        coincidencia = re.match(
            r"^(?:day|d[ií]a)\s*(\d+)\s*[:.-]?\s*(.*)$",
            texto,
            flags=re.IGNORECASE,
        )

        if not coincidencia:
            continue

        numero = int(coincidencia.group(1))
        descripcion = coincidencia.group(2).strip()

        if not descripcion:
            siguiente = etiqueta.find_next(
                ["p", "li", "h3", "h4"]
            )
            if siguiente:
                descripcion = siguiente.get_text(
                    " ",
                    strip=True,
                )

        if descripcion and not any(
            paso.orden == numero
            for paso in pasos_por_dia
        ):
            pasos_por_dia.append(
                PasoItinerario(
                    orden=numero,
                    titulo=f"Día {numero}",
                    descripcion=descripcion,
                )
            )

    if pasos_por_dia:
        return sorted(
            pasos_por_dia,
            key=lambda paso: paso.orden,
        )

    return [
        PasoItinerario(
            orden=indice,
            descripcion=elemento,
        )
        for indice, elemento in enumerate(
            elementos,
            start=1,
        )
    ]


def extraer_secciones(
    soup: BeautifulSoup,
) -> dict:
    cancelacion = extraer_contenido_seccion(
        soup,
        (
            "política de cancelación",
            "politica de cancelacion",
            "cancelación gratuita",
            "cancelacion gratuita",
        ),
        limite=5,
    )

    return {
        "incluye": extraer_contenido_seccion(
            soup,
            (
                "qué incluye",
                "que incluye",
                "incluye",
                "included",
                "includes",
                "inclusions",
                "inclui",
                "o que inclui",
            ),
        ),
        "no_incluye": extraer_contenido_seccion(
            soup,
            (
                "qué no incluye",
                "que no incluye",
                "no incluye",
                "not included",
                "exclusions",
                "nao inclui",
                "não inclui",
            ),
        ),
        "que_llevar": extraer_contenido_seccion(
            soup,
            (
                "qué llevar",
                "que llevar",
                "qué traer",
                "que traer",
                "equipo personal",
                "what to bring",
                "what to pack",
                "o que levar",
            ),
        ),
        "no_llevar": extraer_contenido_seccion(
            soup,
            (
                "qué no llevar",
                "que no llevar",
                "no llevar",
                "no permitido",
                "objetos prohibidos",
                "what not to bring",
                "not allowed",
                "nao permitido",
                "não permitido",
            ),
        ),
        "recomendaciones": extraer_contenido_seccion(
            soup,
            (
                "recomendaciones",
                "consejos",
                "tips",
                "recommendations",
                "recomendacoes",
                "recomendações",
            ),
        ),
        "restricciones": extraer_contenido_seccion(
            soup,
            (
                "restricciones",
                "prohibiciones",
                "requisitos",
                "requirements",
                "restrictions",
                "restricoes",
                "restrições",
            ),
        ),
        "informacion_importante":
            extraer_contenido_seccion(
                soup,
                (
                    "información importante",
                    "informacion importante",
                    "lo que debes saber",
                    "importante",
                    "important information",
                    "informacoes importantes",
                    "informações importantes",
                ),
            ),
        "politica_cancelacion": (
            " ".join(cancelacion)
            if cancelacion
            else None
        ),
    }

def extraer_ubicacion(
    entidad: dict,
    datos_json_ld: list[dict],
    soup: BeautifulSoup,
) -> Ubicacion:
    ubicacion = Ubicacion()

    dato_ubicacion = entidad.get("location")

    if isinstance(dato_ubicacion, str):
        ubicacion.direccion = dato_ubicacion

    elif isinstance(dato_ubicacion, dict):
        ubicacion.direccion = (
            dato_ubicacion.get("name")
        )

        direccion = dato_ubicacion.get(
            "address"
        )

        if isinstance(direccion, str):
            ubicacion.direccion = direccion

        elif isinstance(direccion, dict):
            ubicacion.pais = direccion.get(
                "addressCountry"
            )

            ubicacion.region = direccion.get(
                "addressRegion"
            )

            ubicacion.ciudad = direccion.get(
                "addressLocality"
            )

            ubicacion.direccion = (
                direccion.get("streetAddress")
                or ubicacion.direccion
            )

        coordenadas = dato_ubicacion.get("geo")

        if isinstance(coordenadas, dict):
            ubicacion.latitud = convertir_numero(
                coordenadas.get("latitude")
            )

            ubicacion.longitud = convertir_numero(
                coordenadas.get("longitude")
            )

    for elemento in datos_json_ld:
        tipo = elemento.get("@type")

        if tipo not in {
            "Place",
            "LocalBusiness",
            "TouristAttraction",
            "Organization",
        }:
            continue

        direccion = elemento.get("address")

        if isinstance(direccion, str):
            if not ubicacion.direccion:
                ubicacion.direccion = direccion

        elif isinstance(direccion, dict):
            ubicacion.pais = (
                ubicacion.pais
                or direccion.get("addressCountry")
            )

            ubicacion.region = (
                ubicacion.region
                or direccion.get("addressRegion")
            )

            ubicacion.ciudad = (
                ubicacion.ciudad
                or direccion.get("addressLocality")
            )

            ubicacion.direccion = (
                ubicacion.direccion
                or direccion.get("streetAddress")
            )

    selectores_ubicacion = (
        "[class*='location']",
        "[class*='ubicacion']",
        "[class*='address']",
        "[itemprop='address']",
    )

    for selector in selectores_ubicacion:
        for etiqueta in soup.select(selector):
            texto = etiqueta.get_text(
                " ",
                strip=True,
            )

            if (
                texto
                and len(texto) <= 200
                and not ubicacion.direccion
            ):
                ubicacion.direccion = texto
                break

        if ubicacion.direccion:
            break

    texto_pagina = soup.get_text(
        " ",
        strip=True,
    )
    texto_normalizado = normalizar_texto(texto_pagina)

    paises = {
        "chile": "Chile",
        "colombia": "Colombia",
        "brasil": "Brasil",
        "argentina": "Argentina",
        "peru": "Perú",
        "ecuador": "Ecuador",
        "mexico": "México",
        "uruguay": "Uruguay",
    }
    regiones = {
        "antioquia": "Antioquia",
        "bolivar": "Bolívar",
        "los lagos": "Región de Los Lagos",
        "region de los lagos": "Región de Los Lagos",
    }
    ciudades = {
        "medellin": "Medellín",
        "cartagena": "Cartagena",
        "guatape": "Guatapé",
        "rionegro": "Rionegro",
        "guarne": "Guarne",
        "chiloe": "Chiloé",
        "castro": "Castro",
    }

    if not ubicacion.pais:
        for palabra, nombre in paises.items():
            if palabra in texto_normalizado:
                ubicacion.pais = nombre
                break

    if not ubicacion.region:
        for palabra, nombre in regiones.items():
            if palabra in texto_normalizado:
                ubicacion.region = nombre
                break

    if not ubicacion.ciudad:
        for palabra, nombre in ciudades.items():
            if palabra in texto_normalizado:
                ubicacion.ciudad = nombre
                break

    texto_ubicacion = extraer_contenido_seccion(
        soup,
        (
            "ubicación",
            "ubicacion",
            "location",
            "cómo llegar",
            "como llegar",
        ),
        limite=5,
    )

    if not ubicacion.direccion and texto_ubicacion:
        ubicacion.direccion = " ".join(texto_ubicacion)

    if ubicacion.direccion:
        direccion_normalizada = normalizar_texto(
            ubicacion.direccion
        )
        indicadores_pie = (
            "informacion news tienda contactanos",
            "privacy policy",
            "reservas whatsapp",
        )

        if (
            len(ubicacion.direccion) > 160
            or any(
                indicador in direccion_normalizada
                for indicador in indicadores_pie
            )
        ):
            ubicacion.direccion = None

    return ubicacion

def extraer_calendario(
    soup: BeautifulSoup,
) -> Calendario:
    calendario = Calendario()

    texto = soup.get_text(
        " ",
        strip=True,
    )

    texto_normalizado = normalizar_texto(texto)

    frases_todo_el_ano = (
        "todos los dias",
        "salida diaria",
        "salidas diarias",
        "abierto todo el ano",
        "durante todo el ano",
        "every day",
        "daily departures",
        "open year round",
    )

    frases_consulta = (
        "consultar disponibilidad",
        "consulta disponibilidad",
        "comprueba la disponibilidad",
        "sujeto a disponibilidad",
        "contactanos para reservar",
        "solicita tu cotizacion",
    )

    if any(
        frase in texto_normalizado
        for frase in frases_todo_el_ano
    ):
        calendario.tipo = "todo_el_ano"
        calendario.evidencia.append(
            "El operador declara funcionamiento diario."
        )

    elif "temporada" in texto_normalizado:
        calendario.tipo = "temporada"
        calendario.evidencia.append(
            "La página menciona una temporada."
        )

    elif any(
        frase in texto_normalizado
        for frase in frases_consulta
    ):
        calendario.tipo = "consulta_directa"
        calendario.evidencia.append(
            "El operador solicita consultar disponibilidad."
        )

    fechas = set()

    for elemento in soup.select(
        "[data-date], time[datetime], input[type='date']"
    ):
        if (
            elemento.has_attr("disabled")
            or elemento.get("aria-disabled") == "true"
        ):
            continue

        valor = (
            elemento.get("data-date")
            or elemento.get("datetime")
            or elemento.get("value")
            or elemento.get("aria-label")
            or ""
        )

        coincidencia = re.search(
            r"\d{4}-\d{2}-\d{2}",
            valor,
        )

        if coincidencia:
            fechas.add(coincidencia.group(0))

    calendario.fechas_disponibles = sorted(fechas)

    if fechas:
        calendario.periodo_consultado_desde = min(fechas)
        calendario.periodo_consultado_hasta = max(fechas)

    calendario.horarios = sorted(
        set(
            re.findall(
                r"\b(?:[01]\d|2[0-3]):[0-5]\d\b",
                texto,
            )
        )
    )

    return calendario

def extraer_contacto(
    soup: BeautifulSoup,
) -> str | None:
    enlaces = soup.find_all(
        "a",
        href=True,
    )

    for enlace in enlaces:
        href = enlace.get(
            "href",
            "",
        )

        if (
            href.startswith("mailto:")
            or href.startswith("tel:")
            or "wa.me" in href
            or "whatsapp.com" in href
        ):
            return href

    return None

def extraer_tour(
    url: str,
    nombre_operador: str | None = None,
) -> TourExtraido:
    # Primero usa HTTP normal (rápido). Playwright queda como respaldo
    # automático para sitios bloqueados o completamente dinámicos.
    try:
        html = obtener_html(url)

        if not html_tiene_detalle_turistico(html):
            print(
                "El HTML rápido está incompleto. "
                "Cargando detalles con Playwright."
            )
            html = obtener_html_playwright(url)
    except Exception as error_descarga:
        print(
            "No se pudo cargar la ficha: "
            f"{error_descarga}. Reintentando con navegador."
        )
        html = obtener_html_playwright(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    datos_json_ld = obtener_json_ld(soup)

    entidad = buscar_entidad_tour(
        datos_json_ld
    )

    encabezado_h1 = soup.find("h1")

    nombre = (
        entidad.get("name")
        or obtener_meta(soup, "og:title")
        or (
            encabezado_h1.get_text(
                " ",
                strip=True,
            )
            if encabezado_h1
            else None
        )
        or (
            soup.title.get_text(
                " ",
                strip=True,
            )
            if soup.title
            else None
        )
    )

    descripcion = (
        entidad.get("description")
        or obtener_meta(soup, "description")
        or obtener_meta(soup, "og:description")
    )

    descripcion_corta = (
        obtener_meta(soup, "og:description")
        or obtener_meta(soup, "description")
    )

    categoria = (
        entidad.get("category")
        or obtener_meta(
            soup,
            "article:section",
        )
    )

    texto_pagina = soup.get_text(
        " ",
        strip=True,
    )

    duracion_original, duracion_minutos = (
        extraer_duracion(texto_pagina)
    )

    edad_minima, edad_maxima = (
        extraer_edades(texto_pagina)
    )

    secciones = extraer_secciones(soup)

    dominio = urlparse(url).netloc

    if not nombre_operador:
        nombre_operador = dominio.replace(
            "www.",
            "",
        )

    url_operador = (
        f"{urlparse(url).scheme}://{dominio}"
    )

    resultado = TourExtraido(
        nombre_operador=nombre_operador,
        url_operador=url_operador,
        source_url=url,
        nombre=nombre,
        descripcion_original=descripcion,
        descripcion_corta=descripcion_corta,
        categoria=categoria,
        ubicacion=extraer_ubicacion(
            entidad,
            datos_json_ld,
            soup,
        ),
       
        duracion_original=duracion_original,
        duracion_minutos=duracion_minutos,
        edad_minima=edad_minima,
        edad_maxima=edad_maxima,
        idiomas=extraer_idiomas(
            texto_pagina
        ),
        imagenes=extraer_imagenes(
            entidad,
            soup,
            url,
        ),
        itinerario=extraer_itinerario(
            soup
        ),
        incluye=secciones["incluye"],
        no_incluye=secciones[
            "no_incluye"
        ],
        que_llevar=secciones[
            "que_llevar"
        ],
        no_llevar=secciones[
            "no_llevar"
        ],
        recomendaciones=secciones[
            "recomendaciones"
        ],
        restricciones=secciones[
            "restricciones"
        ],
        informacion_importante=secciones[
            "informacion_importante"
        ],
        politica_cancelacion=secciones[
            "politica_cancelacion"
        ],
        contacto=extraer_contacto(soup),
        calendario=extraer_calendario(
            soup
        ),
        evidencia_original={
            "json_ld_encontrado": bool(
                datos_json_ld
            ),
            "entidad_estructurada_encontrada":
                bool(entidad),
            "cantidad_imagenes_html": len(
                soup.find_all("img")
            ),
        },
        extraido_en=datetime.now(
            timezone.utc
        ).isoformat(),
    )

    return resultado
