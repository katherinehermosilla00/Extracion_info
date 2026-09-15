
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

from security_client import get_seguro, validar_url_segura

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


def detectar_bloqueo_html(
    html: str | None,
) -> tuple[bool, str | None]:
    """
    Detecta de forma genérica páginas anti-bot, CAPTCHA o de acceso
    denegado. No intenta evadir protecciones: solo evita interpretar
    una página de bloqueo como si fuera una ficha turística válida.
    """

    if not html:
        return True, "La fuente no devolvió contenido HTML."

    contenido = html.lower()

    indicadores_fuertes = (
        "please enable js and disable any ad blocker",
        "please enable javascript and disable any ad blocker",
        "captcha-delivery.com",
        "geo.captcha-delivery.com",
        "verify you are human",
        "verify that you are human",
        "checking your browser",
        "attention required",
        "access denied",
        "are you a human",
        "unusual traffic",
        "challenge-platform",
        "cf-chl-",
        "datadome",
    )

    for indicador in indicadores_fuertes:
        if indicador in contenido:
            return (
                True,
                "La fuente impide la extracción automática "
                f"(se detectó: {indicador}).",
            )

    # CAPTCHA por sí solo se considera bloqueo únicamente cuando la
    # página tiene muy poco contenido visible, para reducir falsos
    # positivos en páginas que solo mencionen esa palabra.
    if "captcha" in contenido:
        soup = BeautifulSoup(html, "html.parser")
        texto_visible = soup.get_text(" ", strip=True)

        if len(texto_visible) < 1500:
            return (
                True,
                "La fuente presentó una verificación CAPTCHA.",
            )

    return False, None


def validar_html_extraible(
    html: str | None,
    url: str,
) -> None:
    """
    Verifica que el HTML corresponda a contenido utilizable antes de
    ejecutar los extractores. Si la fuente está bloqueada o devuelve
    una página vacía/intermedia, se detiene la extracción para impedir
    que se guarde una ficha basura en PostgreSQL.
    """

    bloqueado, motivo = detectar_bloqueo_html(html)

    if bloqueado:
        raise RuntimeError(
            "FUENTE_BLOQUEADA: "
            f"{motivo or 'La fuente no permite extracción automática.'} "
            f"URL: {url}"
        )

    html = html or ""
    soup = BeautifulSoup(html, "html.parser")
    texto_visible = soup.get_text(" ", strip=True)

    tiene_datos_estructurados = bool(
        soup.find(
            "script",
            attrs={"type": "application/ld+json"},
        )
    )

    tiene_titulo_util = bool(
        soup.find("h1")
        or obtener_meta(soup, "og:title")
    )

    if (
        len(texto_visible) < 120
        and not tiene_datos_estructurados
        and not tiene_titulo_util
    ):
        raise RuntimeError(
            "FUENTE_SIN_CONTENIDO: La fuente no entregó contenido "
            "suficiente para construir una ficha confiable. "
            f"URL: {url}"
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
    validar_url_segura(url)
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

        url_bloqueada = {
            "error": None,
        }

        def controlar_navegacion(route):
            request = route.request

            if request.is_navigation_request():
                try:
                    validar_url_segura(request.url)
                except Exception as error:
                    url_bloqueada["error"] = error
                    route.abort("blockedbyclient")
                    return

            route.continue_()

        pagina.route(
            "**/*",
            controlar_navegacion,
        )

        try:
            error_navegacion = None

            for intento in range(3):
                try:
                    pagina.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                    error_navegacion = None
                    break
                except Exception as error:
                    error_navegacion = error

                    if url_bloqueada["error"] is not None:
                        raise url_bloqueada["error"]

                    if intento < 2:
                        pagina.wait_for_timeout(
                            1500 * (intento + 1)
                        )

            if error_navegacion is not None:
                raise error_navegacion

            validar_url_segura(pagina.url)

            try:
                pagina.wait_for_load_state(
                    "networkidle",
                    timeout=12000,
                )
            except Exception:
                # Muchos sitios turísticos mantienen solicitudes
                # de analítica o widgets abiertas permanentemente.
                pagina.wait_for_timeout(2500)

            ultimo_error = None

            for _ in range(4):
                try:
                    return pagina.content()
                except Exception as error:
                    ultimo_error = error
                    pagina.wait_for_timeout(1200)

                    try:
                        pagina.wait_for_load_state(
                            "domcontentloaded",
                            timeout=8000,
                        )
                    except Exception:
                        pass

            # Detiene navegaciones tardías de sliders o redirecciones
            # antes del último intento de lectura.
            try:
                pagina.evaluate("window.stop()")
                pagina.wait_for_timeout(500)
                return pagina.content()
            except Exception:
                raise RuntimeError(
                    "La página no terminó de estabilizarse"
                ) from ultimo_error

        finally:
            navegador.close()



def detectar_tipo_calendario(pagina) -> str:
    """
    Detecta de forma generica el componente de calendario.
    No depende del operador ni del dominio.
    """

    # Componentes ya visibles.
    if pagina.locator(".flatpickr-calendar").count() > 0:
        return "flatpickr"

    if (
        pagina.locator(".MuiDateCalendar-root").count() > 0
        or pagina.locator(".MuiPickersDay-root").count() > 0
    ):
        return "mui"

    # Primero controles explicitos de calendario.
    selectores_fecha = (
        'button[aria-label^="Choose date"]',
        'button[aria-label*="selected date"]',
        'button[aria-label*="calendar" i]',
        'button[aria-label*="date" i]',
        ".bt-datepicker",
        'input[type="date"]',
        'input[name="date"]',
        'input[placeholder*="fecha" i]',
        'input[placeholder*="date" i]',
    )

    for selector in selectores_fecha:
        controles = pagina.locator(selector)

        for indice in range(controles.count()):
            control = controles.nth(indice)

            try:
                if not control.is_visible():
                    continue

                try:
                    control.click(timeout=2000)
                except Exception:
                    control.click(
                        timeout=2000,
                        force=True,
                    )

                pagina.wait_for_timeout(700)

            except Exception:
                continue

            if pagina.locator(
                ".flatpickr-calendar"
            ).count() > 0:
                return "flatpickr"

            if (
                pagina.locator(
                    ".MuiDateCalendar-root"
                ).count() > 0
                or pagina.locator(
                    ".MuiPickersDay-root"
                ).count() > 0
            ):
                return "mui"

    return "desconocido"




def extraer_calendario_flatpickr_desde_pagina(
    pagina,
    resultado_base: dict | None = None,
    limite_meses: int = 3,
) -> dict:
    """
    Extrae disponibilidad desde un calendario Flatpickr.

    No depende del operador ni del dominio.
    """

    if resultado_base is None:
        resultado = {
            "tipo": "desconocido",
            "dias": [],
            "hasta": None,
            "horarios": [],
            "evidencia": [],
        }
    else:
        resultado = {
            "tipo": resultado_base.get(
                "tipo",
                "desconocido",
            ),
            "dias": list(
                resultado_base.get(
                    "dias",
                    [],
                )
            ),
            "hasta": None,
            "horarios": [],
            "evidencia": list(
                resultado_base.get(
                    "evidencia",
                    [],
                )
            ),
        }

    calendario = pagina.locator(
        ".flatpickr-calendar"
    ).last

    if calendario.count() == 0:
        resultado["evidencia"].append(
            "No se encontro el calendario "
            "despues de abrirlo."
        )
        return resultado

    # -----------------------------------------------------
    # Seleccionar una fecha disponible para cargar horarios
    # -----------------------------------------------------

    dias_iniciales = calendario.locator(
        ".flatpickr-day"
    )

    for i in range(dias_iniciales.count()):
        dia = dias_iniciales.nth(i)

        clases = (
            dia.get_attribute("class")
            or ""
        )

        if "flatpickr-disabled" in clases:
            continue

        if (
            "prevMonthDay" in clases
            or "nextMonthDay" in clases
        ):
            continue

        try:
            dia.click()
            pagina.wait_for_timeout(700)
        except Exception:
            continue

        break

    # -----------------------------------------------------
    # Horarios
    # -----------------------------------------------------

    horarios = []

    # Selects HTML tradicionales.
    selects = pagina.locator("select")

    for i in range(selects.count()):
        select = selects.nth(i)

        try:
            if not select.is_visible():
                # Algunos selects pueden estar visualmente
                # reemplazados pero seguir conteniendo opciones.
                pass

            opciones = select.locator("option")

            for j in range(opciones.count()):
                opcion = opciones.nth(j)

                valor = (
                    opcion.get_attribute("value")
                    or ""
                ).strip()

                texto_opcion = (
                    opcion.inner_text()
                    or ""
                ).strip()

                if not valor or not texto_opcion:
                    continue

                texto_lower = texto_opcion.lower()

                if (
                    ":" in texto_opcion
                    or " am" in texto_lower
                    or " pm" in texto_lower
                    or "hrs" in texto_lower
                ):
                    horarios.append(
                        texto_opcion
                    )

        except Exception:
            continue

    resultado["horarios"] = list(
        dict.fromkeys(horarios)
    )

    # -----------------------------------------------------
    # Reabrir Flatpickr si se cerro al elegir una fecha
    # -----------------------------------------------------

    if pagina.locator(
        ".flatpickr-calendar.open"
    ).count() == 0:

        candidatos = (
            ".bt-datepicker",
            "input[type='date']",
            "input[placeholder*='fecha' i]",
            "input[placeholder*='date' i]",
        )

        for selector in candidatos:
            controles = pagina.locator(selector)

            if controles.count() == 0:
                continue

            try:
                control = controles.last

                if control.is_visible():
                    control.click()
                    pagina.wait_for_timeout(300)
                    break

            except Exception:
                continue

    # -----------------------------------------------------
    # Analizar una muestra de meses
    # -----------------------------------------------------

    meses_recorridos = 0
    meses_con_dias = 0

    # Solo consideramos patron diario cuando los meses
    # completos analizados tienen todos sus dias habilitados.
    meses_completos = 0
    meses_completos_diarios = 0

    while meses_recorridos < limite_meses:

        calendario = pagina.locator(
            ".flatpickr-calendar"
        ).last

        if calendario.count() == 0:
            break

        dias = calendario.locator(
            ".flatpickr-day"
        )

        habilitados = 0
        total_mes = 0
        tiene_dias_pasados_deshabilitados = False

        for i in range(dias.count()):
            dia = dias.nth(i)

            clases = (
                dia.get_attribute("class")
                or ""
            )

            if (
                "prevMonthDay" in clases
                or "nextMonthDay" in clases
            ):
                continue

            total_mes += 1

            if "flatpickr-disabled" not in clases:
                habilitados += 1
            else:
                # El mes actual puede contener fechas pasadas.
                if "today" not in clases:
                    tiene_dias_pasados_deshabilitados = True

        if habilitados > 0:
            meses_con_dias += 1

        # Un mes se considera completo para inferir patron
        # solamente cuando no parece ser el mes parcial actual.
        if (
            total_mes > 0
            and habilitados > 0
            and not tiene_dias_pasados_deshabilitados
        ):
            meses_completos += 1

            if habilitados == total_mes:
                meses_completos_diarios += 1

        meses_recorridos += 1

        if meses_recorridos >= limite_meses:
            break

        siguiente = calendario.locator(
            ".flatpickr-next-month"
        )

        if siguiente.count() == 0:
            break

        clases_siguiente = (
            siguiente.get_attribute("class")
            or ""
        )

        if "disabled" in clases_siguiente:
            break

        if (
            siguiente.get_attribute(
                "aria-disabled"
            )
            == "true"
        ):
            break

        try:
            siguiente.click()
            pagina.wait_for_timeout(300)
        except Exception:
            break

    if (
        meses_completos > 0
        and meses_completos_diarios
        == meses_completos
    ):
        resultado["tipo"] = "todo_el_ano"
        resultado["dias"] = [
            "todos_los_dias"
        ]

    if meses_con_dias:
        resultado["evidencia"].append(
            f"Se analizaron {meses_con_dias} "
            "meses con dias habilitados."
        )

    if meses_recorridos >= limite_meses:
        resultado["evidencia"].append(
            f"Se reviso una muestra de "
            f"{limite_meses} meses; "
            "el sitio no publica una fecha "
            "final confiable."
        )

    # Nunca inventar una fecha final solo porque
    # el calendario permite seguir navegando.
    resultado["hasta"] = None

    resultado["evidencia"] = list(
        dict.fromkeys(
            resultado["evidencia"]
        )
    )

    return resultado


def extraer_calendario_mui_desde_pagina(
    pagina,
    limite_meses: int = 3,
) -> dict:
    """
    Extrae disponibilidad desde un MUI Date Picker visible.

    Es generico y no depende de operador ni dominio.
    """

    resultado = {
        "tipo": "segun_calendario",
        "dias": ["segun_calendario"],
        "hasta": None,
        "horarios": [],
        "evidencia": [],
    }

    if pagina.locator(".MuiDateCalendar-root").count() == 0:
        return resultado

    meses_revisados = 0
    meses_con_disponibilidad = 0

    while meses_revisados < limite_meses:
        calendario = pagina.locator(
            ".MuiDateCalendar-root"
        )

        if calendario.count() == 0:
            break

        dias = pagina.locator(
            ".MuiPickersDay-root"
        )

        total_mes = 0
        habilitados = 0

        for i in range(dias.count()):
            dia = dias.nth(i)

            try:
                if not dia.is_visible():
                    continue

                texto_dia = (
                    dia.inner_text()
                    or ""
                ).strip()

                if not texto_dia.isdigit():
                    continue

                clases = (
                    dia.get_attribute("class")
                    or ""
                )

                # MUI muestra dias externos al mes actual.
                if "MuiPickersDay-dayOutsideMonth" in clases:
                    continue

                total_mes += 1

                if not dia.is_disabled():
                    habilitados += 1

            except Exception:
                continue

        if habilitados > 0:
            meses_con_disponibilidad += 1

        meses_revisados += 1

        if meses_revisados >= limite_meses:
            break

        # Buscar de forma generica el boton siguiente.
        siguiente = pagina.locator(
            '.MuiPickersArrowSwitcher-root '
            'button[aria-label*="next" i]'
        )

        if siguiente.count() == 0:
            botones = pagina.locator(
                ".MuiPickersArrowSwitcher-root button"
            )

            if botones.count() >= 2:
                siguiente = botones.last

        if siguiente.count() == 0:
            break

        try:
            if siguiente.is_disabled():
                break

            siguiente.click()
            pagina.wait_for_timeout(350)

        except Exception:
            break

    # Volver a una fecha disponible del calendario visible
    # para obtener los horarios asociados.
    dias = pagina.locator(
        ".MuiPickersDay-root"
    )

    for i in range(dias.count()):
        dia = dias.nth(i)

        try:
            if not dia.is_visible():
                continue

            texto_dia = (
                dia.inner_text()
                or ""
            ).strip()

            if not texto_dia.isdigit():
                continue

            clases = (
                dia.get_attribute("class")
                or ""
            )

            if "MuiPickersDay-dayOutsideMonth" in clases:
                continue

            if dia.is_disabled():
                continue

            dia.click()
            pagina.wait_for_timeout(700)
            break

        except Exception:
            continue

    # Horarios visibles, sin depender de clases de un sitio.
    horarios = []

    botones = pagina.locator(
        "button, [role='button']"
    )

    import re

    patron_hora = re.compile(
        r"^\s*\d{1,2}:\d{2}"
        r"(?:\s*(?:am|pm|hrs?|h))?"
        r"(?:\s+a\s+\d{1,2}:\d{2}"
        r"(?:\s*(?:am|pm|hrs?|h))?)?\s*$",
        re.IGNORECASE,
    )

    for i in range(botones.count()):
        boton = botones.nth(i)

        try:
            if not boton.is_visible():
                continue

            valor = (
                boton.inner_text()
                or ""
            ).strip()

            if valor and patron_hora.match(valor):
                horarios.append(valor)

        except Exception:
            continue

    resultado["horarios"] = list(
        dict.fromkeys(horarios)
    )

    if meses_con_disponibilidad:
        resultado["evidencia"].append(
            f"Se analizaron {meses_con_disponibilidad} "
            "meses con disponibilidad."
        )

    resultado["evidencia"].append(
        f"Se reviso una muestra de "
        f"{meses_revisados} meses."
    )

    return resultado



def extraer_calendario_dinamico(
    pagina,
    resultado_base: dict | None = None,
    limite_meses: int = 3,
) -> dict:
    """
    Punto unico para calendarios dinamicos.

    Detecta la tecnologia por DOM y delega
    al adaptador correspondiente.
    """

    tipo = detectar_tipo_calendario(
        pagina
    )

    if tipo == "flatpickr":
        return (
            extraer_calendario_flatpickr_desde_pagina(
                pagina,
                resultado_base=resultado_base,
                limite_meses=limite_meses,
            )
        )

    if tipo == "mui":
        resultado = (
            extraer_calendario_mui_desde_pagina(
                pagina,
                limite_meses=limite_meses,
            )
        )

        if resultado_base is not None:
            evidencia = (
                list(
                    resultado_base.get(
                        "evidencia",
                        [],
                    )
                )
                + list(
                    resultado.get(
                        "evidencia",
                        [],
                    )
                )
            )

            resultado["evidencia"] = list(
                dict.fromkeys(evidencia)
            )

        return resultado

    if resultado_base is None:
        resultado_base = {
            "tipo": "desconocido",
            "dias": [],
            "hasta": None,
            "horarios": [],
            "evidencia": [],
        }

    resultado = {
        **resultado_base,
        "evidencia": list(
            resultado_base.get(
                "evidencia",
                [],
            )
        ),
    }

    resultado["evidencia"].append(
        "No se encontro un calendario "
        "de disponibilidad compatible."
    )

    resultado["evidencia"] = list(
        dict.fromkeys(
            resultado["evidencia"]
        )
    )

    return resultado


def obtener_html_y_calendario_playwright(
    url: str,
) -> tuple[str, dict]:
    """
    Carga la ficha una sola vez con Playwright.

    Devuelve el HTML y el calendario detectado
    mediante el despachador universal.
    """

    validar_url_segura(url)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )

    resultado_base = {
        "tipo": "desconocido",
        "dias": [],
        "hasta": None,
        "horarios": [],
        "evidencia": [],
    }

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

        url_bloqueada = {
            "error": None
        }

        def controlar_navegacion(route):
            request = route.request

            if request.is_navigation_request():
                try:
                    validar_url_segura(
                        request.url
                    )
                except Exception as error:
                    url_bloqueada[
                        "error"
                    ] = error

                    route.abort(
                        "blockedbyclient"
                    )
                    return

            route.continue_()

        # Mantener proteccion SSRF en navegaciones.
        pagina.route(
            "**/*",
            controlar_navegacion,
        )

        try:
            error_navegacion = None

            for intento in range(2):
                try:
                    pagina.goto(
                        url,
                        wait_until=(
                            "domcontentloaded"
                        ),
                        timeout=25000,
                    )

                    error_navegacion = None
                    break

                except Exception as error:
                    error_navegacion = error

                    if (
                        url_bloqueada["error"]
                        is not None
                    ):
                        raise url_bloqueada[
                            "error"
                        ]

                    if intento < 1:
                        pagina.wait_for_timeout(
                            1000
                            * (intento + 1)
                        )

            if error_navegacion is not None:
                raise error_navegacion

            validar_url_segura(
                pagina.url
            )

            try:
                pagina.wait_for_load_state(
                    "networkidle",
                    timeout=8000,
                )
            except Exception:
                pagina.wait_for_timeout(
                    1500
                )

            pagina.wait_for_timeout(
                1000
            )

            # Guardar HTML antes de modificar
            # el estado visual del calendario.
            html = pagina.content()

            texto_pagina = pagina.locator(
                "body"
            ).inner_text()

            texto_normalizado = normalizar_texto(
                texto_pagina
            )

            frases_todo_el_ano = (
                "todos los dias",
                "salida diaria",
                "salidas diarias",
                "every day",
                "daily departures",
                "open year round",
            )

            frases_consulta = (
                "consultar disponibilidad",
                "consulta disponibilidad",
                "comprueba la disponibilidad",
                "sujeto a disponibilidad",
            )

            if any(
                frase in texto_normalizado
                for frase in frases_todo_el_ano
            ):
                resultado_base["tipo"] = (
                    "todo_el_ano"
                )

                resultado_base["dias"] = [
                    "todos_los_dias"
                ]

                resultado_base[
                    "evidencia"
                ].append(
                    "El operador declara "
                    "funcionamiento diario."
                )

            elif any(
                frase in texto_normalizado
                for frase in frases_consulta
            ):
                resultado_base["tipo"] = (
                    "consulta_directa"
                )

                resultado_base[
                    "evidencia"
                ].append(
                    "El operador solicita "
                    "consultar disponibilidad."
                )

            calendario = (
                extraer_calendario_dinamico(
                    pagina,
                    resultado_base=(
                        resultado_base
                    ),
                    limite_meses=3,
                )
            )

            return html, calendario

        finally:
            navegador.close()



def extraer_resumen_calendario_playwright(
    url: str,
) -> dict:
    """
    Resume la disponibilidad real visible en el calendario.

    No almacena todas las fechas. Recorre los meses que el calendario
    permite consultar y conserva solamente:
    - tipo de disponibilidad
    - patr?n de d?as
    - ?ltimo mes con d?as habilitados
    - horarios visibles
    - evidencia
    """

    validar_url_segura(url)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )

    resultado = {
        "tipo": "desconocido",
        "dias": [],
        "hasta": None,
        "horarios": [],
        "evidencia": [],
    }

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
            pagina.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            validar_url_segura(pagina.url)

            try:
                pagina.wait_for_load_state(
                    "networkidle",
                    timeout=12000,
                )
            except Exception:
                pagina.wait_for_timeout(2500)

            pagina.wait_for_timeout(2000)

            selectores_fecha = (
                ".bt-datepicker",
                "input[type='date']",
                "input[placeholder*='fecha']",
                "input[placeholder*='date']",
            )

            campo = None

            for selector in selectores_fecha:
                locator = pagina.locator(selector)

                if locator.count() > 0:
                    campo = locator.last
                    break

            if campo is None:
                resultado["evidencia"].append(
                    "No se encontr? un calendario de disponibilidad."
                )
                return resultado

            try:
                campo.click()
            except Exception:
                pass

            pagina.wait_for_timeout(500)

            calendario = pagina.locator(
                ".flatpickr-calendar"
            ).last

            if calendario.count() == 0:
                resultado["evidencia"].append(
                    "No se encontr? el calendario despu?s de abrirlo."
                )
                return resultado

            texto = pagina.locator("body").inner_text()

            texto_normalizado = normalizar_texto(
                texto
            )

            frases_todo_el_ano = (
                "todos los dias",
                "salida diaria",
                "salidas diarias",
                "every day",
                "daily departures",
                "open year round",
            )

            frases_consulta = (
                "consultar disponibilidad",
                "consulta disponibilidad",
                "comprueba la disponibilidad",
                "sujeto a disponibilidad",
            )

            if any(
                frase in texto_normalizado
                for frase in frases_todo_el_ano
            ):
                resultado["tipo"] = "todo_el_ano"
                resultado["dias"] = [
                    "todos_los_dias"
                ]
                resultado["evidencia"].append(
                    "El operador declara funcionamiento diario."
                )

            elif any(
                frase in texto_normalizado
                for frase in frases_consulta
            ):
                resultado["tipo"] = "consulta_directa"
                resultado["evidencia"].append(
                    "El operador solicita consultar disponibilidad."
                )

            # Horarios disponibles para la fecha seleccionada
            horarios = []

            selector_hora = pagina.locator("#bt_time")

            if selector_hora.count() > 0:
                opciones = selector_hora.locator("option")

                for i in range(opciones.count()):
                    opcion = opciones.nth(i)

                    valor = (
                        opcion.get_attribute("value")
                        or ""
                    ).strip()

                    texto_opcion = (
                        opcion.inner_text()
                        or ""
                    ).strip()

                    if not valor:
                        continue

                    if texto_opcion:
                        horarios.append(texto_opcion)

            resultado["horarios"] = sorted(
                set(horarios)
            )

            ultimo_mes = None
            meses_recorridos = 0
            limite_meses = 3
            meses_con_dias = 0

            while meses_recorridos < limite_meses:
                meses_recorridos += 1

                calendario = pagina.locator(
                    ".flatpickr-calendar"
                ).last

                if calendario.count() == 0:
                    break

                dias = calendario.locator(
                    ".flatpickr-day"
                )

                fechas_habilitadas = []

                for i in range(dias.count()):
                    dia = dias.nth(i)

                    clases = (
                        dia.get_attribute("class")
                        or ""
                    )

                    if "flatpickr-disabled" in clases:
                        continue

                    aria = dia.get_attribute(
                        "aria-label"
                    )

                    if not aria:
                        continue

                    # Ignorar d?as del mes anterior
                    # o siguiente que Flatpickr muestra
                    # visualmente dentro de la misma grilla.
                    if (
                        "prevMonthDay" in clases
                        or "nextMonthDay" in clases
                    ):
                        continue

                    fechas_habilitadas.append(
                        aria
                    )

                if fechas_habilitadas:
                    meses_con_dias += 1

                    fechas_iso = []

                    for fecha in fechas_habilitadas:
                        try:
                            fecha_obj = datetime.strptime(
                                fecha,
                                "%B %d, %Y",
                            )

                            fechas_iso.append(
                                fecha_obj
                            )
                        except ValueError:
                            try:
                                fecha_obj = datetime.strptime(
                                    fecha,
                                    "%B %d, %Y",
                                )

                                fechas_iso.append(
                                    fecha_obj
                                )
                            except Exception:
                                pass

                    if fechas_iso:
                        ultimo = max(fechas_iso)

                        ultimo_mes = (
                            f"{ultimo.year:04d}-"
                            f"{ultimo.month:02d}"
                        )

                    total_dias_mes = 0

                    for i in range(dias.count()):
                        dia = dias.nth(i)

                        clases = (
                            dia.get_attribute("class")
                            or ""
                        )

                        if (
                            "flatpickr-disabled" in clases
                            or "prevMonthDay" in clases
                            or "nextMonthDay" in clases
                        ):
                            continue

                        total_dias_mes += 1

                    if (
                        total_dias_mes > 0
                        and len(fechas_habilitadas)
                        == total_dias_mes
                    ):
                        resultado["tipo"] = "todo_el_ano"

                        if (
                            "todos_los_dias"
                            not in resultado["dias"]
                        ):
                            resultado["dias"] = [
                                "todos_los_dias"
                            ]

                siguiente = calendario.locator(
                    ".flatpickr-next-month"
                )

                if siguiente.count() == 0:
                    break

                try:
                    clases_siguiente = (
                        siguiente.get_attribute("class")
                        or ""
                    )

                    if "disabled" in clases_siguiente:
                        break

                    aria_disabled = (
                        siguiente.get_attribute(
                            "aria-disabled"
                        )
                    )

                    if aria_disabled == "true":
                        break

                    siguiente.click()

                    pagina.wait_for_timeout(300)

                except Exception:
                    break

            # No usar el ?ltimo mes navegado como fecha final,
            # porque algunos calendarios permiten avanzar indefinidamente.
            # Solo se informa "hasta" si el sitio publica un l?mite real.
            resultado["hasta"] = None

            if meses_con_dias:
                resultado["evidencia"].append(
                    f"Se analizaron {meses_con_dias} "
                    "meses con d?as habilitados."
                )

            if meses_recorridos >= limite_meses:
                resultado["evidencia"].append(
                    f"Se reviso una muestra de {limite_meses} meses; "
                    "el sitio no publica una fecha final confiable."
                )

            if not resultado["dias"]:
                resultado["dias"] = [
                    "seg?n_calendario"
                ]

            return resultado

        finally:
            navegador.close()

def obtener_html(url: str) -> str:
    try:
        respuesta = get_seguro(
            url,
            headers=HEADERS,
            timeout=25,
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
            respuesta = get_seguro(
                sitemap_url,
                headers=HEADERS,
                timeout=20,
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


def parece_enlace_reserva(
    url: str,
    texto: str,
) -> bool:
    """
    Detecta enlaces externos que representan una ficha
    individual de reserva o disponibilidad.

    Evita paginas generales de reservas.
    No depende de operadores ni dominios concretos.
    """

    contenido = normalizar_texto(
        f"{url} {texto}"
    )

    palabras_descartar = (
        "facebook",
        "instagram",
        "linkedin",
        "youtube",
        "tiktok",
        "twitter",
        "x.com",
        "whatsapp",
        "wa.me",
        "mailto",
        "tel:",
        "privacy",
        "privacidad",
        "terms",
        "terminos",
    )

    if any(
        palabra in contenido
        for palabra in palabras_descartar
    ):
        return False

    parsed = urlparse(url)

    ruta = normalizar_texto(
        parsed.path
    )

    query = normalizar_texto(
        parsed.query
    )

    texto_normalizado = normalizar_texto(
        texto
    )

    # Se?ales de que la URL apunta a una ficha concreta.
    senales_ficha = (
        "detail",
        "details",
        "detalle",
        "tour",
        "activity",
        "actividad",
        "experience",
        "experiencia",
        "excursion",
        "product",
        "producto",
        "service",
        "servicio",
        "extra-detail",
        "extra detail",
    )

    if any(
        senal in ruta
        for senal in senales_ficha
    ):
        return True

    # IDs num?ricos dentro de la ruta suelen identificar
    # una actividad, producto o servicio individual.
    segmentos = [
        segmento
        for segmento in parsed.path.split("/")
        if segmento
    ]

    if any(
        re.fullmatch(r"\d{2,}", segmento)
        for segmento in segmentos
    ):
        return True

    # Algunos sistemas identifican la actividad mediante
    # par?metros en la URL en vez de usar una ruta /detail/.
    parametros_individuales = (
        "activity=",
        "actividad=",
        "tour=",
        "tour_id=",
        "activity_id=",
        "product=",
        "product_id=",
        "experience=",
        "experience_id=",
        "service_id=",
        "extra_id=",
        "item_id=",
    )

    if any(
        parametro in query
        for parametro in parametros_individuales
    ):
        return True

    # El texto puede aportar evidencia adicional,
    # pero una palabra gen?rica como "Reservas" por s? sola
    # no transforma una landing page en ficha individual.
    palabras_genericas = {
        "reservar",
        "reserva",
        "reservas",
        "booking",
        "book",
        "book now",
        "availability",
        "disponibilidad",
        "tickets",
        "ticket",
        "entrada",
        "entrada parque",
    }

    if (
        texto_normalizado
        in palabras_genericas
    ):
        return False

    return False



def titulo_contextual_enlace(
    enlace,
    url: str,
) -> str:
    """
    Obtiene un titulo util para enlaces cuyo texto es
    generico, por ejemplo 'Reservar' o 'Ver mas'.

    Busca primero dentro de la tarjeta o bloque HTML
    que contiene el enlace.
    """

    texto_enlace = enlace.get_text(
        " ",
        strip=True,
    )

    textos_genericos = {
        normalizar_texto(valor)
        for valor in TEXTOS_ENLACE_GENERICOS
    }

    textos_genericos.update({
        "reservar",
        "reserva",
        "book",
        "book now",
        "booking",
        "ver",
        "detalle",
        "detalles",
        "more info",
    })

    if (
        texto_enlace
        and normalizar_texto(texto_enlace)
        not in textos_genericos
    ):
        return texto_enlace

    titulo_attr = (
        enlace.get("title")
        or ""
    ).strip()

    if (
        titulo_attr
        and normalizar_texto(titulo_attr)
        not in textos_genericos
    ):
        return titulo_attr

    # Buscar un encabezado dentro de la tarjeta,
    # bloque o contenedor asociado al enlace.
    ancestro = enlace

    for _ in range(6):
        ancestro = (
            ancestro.parent
            if ancestro
            else None
        )

        if ancestro is None:
            break

        encabezado = ancestro.find(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            ]
        )

        if encabezado:
            titulo = encabezado.get_text(
                " ",
                strip=True,
            )

            if (
                titulo
                and normalizar_texto(titulo)
                not in textos_genericos
            ):
                return titulo

        # Muchos sitios no usan headings en las tarjetas.
        candidato = ancestro.find(
            attrs={
                "class": re.compile(
                    r"(title|titulo|name|nombre)",
                    re.IGNORECASE,
                )
            }
        )

        if candidato:
            titulo = candidato.get_text(
                " ",
                strip=True,
            )

            if (
                titulo
                and len(titulo) <= 180
                and normalizar_texto(titulo)
                not in textos_genericos
            ):
                return titulo

    return (
        titulo_attr
        or texto_enlace
        or titulo_desde_url(url)
    )


def descubrir_tours(
    url_operador: str,
    max_paginas: int = 5,
) -> list[dict]:
    """
    Descubre actividades desde un sitio de operador.

    Los enlaces internos pueden seguir explorandose.
    Los enlaces externos solo se aceptan cuando parecen
    representar una reserva o disponibilidad y nunca se
    agregan a la cola de rastreo.
    """

    url_inicial = limpiar_url(
        url_operador
    )

    validar_url_segura(
        url_inicial
    )

    dominio = urlparse(
        url_inicial
    ).netloc

    paginas_pendientes = [
        url_inicial
    ]

    paginas_visitadas = set()
    resultados = {}

    # -----------------------------------------------------
    # Sitemap
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Navegacion del dominio principal
    # -----------------------------------------------------

    while (
        paginas_pendientes
        and len(paginas_visitadas)
        < max_paginas
    ):
        pagina_actual = (
            paginas_pendientes.pop(0)
        )

        if (
            pagina_actual
            in paginas_visitadas
        ):
            continue

        paginas_visitadas.add(
            pagina_actual
        )

        print(
            f"Descubriendo tours en: "
            f"{pagina_actual}"
        )

        html = obtener_html_playwright(
            pagina_actual
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        contenido_principal = (
            soup.find("main")
            or soup.find(
                attrs={
                    "role": "main"
                }
            )
            or soup
        )

        enlaces = (
            contenido_principal.find_all(
                "a",
                href=True,
            )
        )

        for enlace in enlaces:

            href = (
                enlace.get(
                    "href",
                    "",
                )
                or ""
            ).strip()

            if (
                not href
                or href.startswith("#")
                or href.startswith(
                    "javascript:"
                )
                or href.startswith(
                    "mailto:"
                )
                or href.startswith(
                    "tel:"
                )
            ):
                continue

            url_absoluta = limpiar_url(
                urljoin(
                    pagina_actual,
                    href,
                )
            )

            if not url_absoluta:
                continue

            if (
                url_absoluta
                == url_inicial
            ):
                continue

            texto_enlace = enlace.get_text(
                " ",
                strip=True,
            )

            es_interno = mismo_dominio(
                url_absoluta,
                dominio,
            )

            # =============================================
            # ENLACE INTERNO
            # =============================================

            if es_interno:

                if not parece_enlace_tour(
                    url_absoluta,
                    texto_enlace,
                ):
                    continue

                titulo = (
                    titulo_contextual_enlace(
                        enlace,
                        url_absoluta,
                    )
                )

                if (
                    url_absoluta
                    not in resultados
                ):
                    resultados[
                        url_absoluta
                    ] = {
                        "titulo": titulo,
                        "url": url_absoluta,
                    }

                # Solo las URLs del sitio principal
                # pueden entrar al rastreo.
                if (
                    url_absoluta
                    not in paginas_visitadas
                    and url_absoluta
                    not in paginas_pendientes
                ):
                    paginas_pendientes.append(
                        url_absoluta
                    )

                continue

            # =============================================
            # ENLACE EXTERNO
            # =============================================

            # Nunca rastrear dominios externos.
            # Solo registrar candidatos claros de reserva.
            if not parece_enlace_reserva(
                url_absoluta,
                texto_enlace,
            ):
                continue

            try:
                validar_url_segura(
                    url_absoluta
                )
            except Exception as error:
                print(
                    "Enlace externo descartado "
                    "por seguridad: "
                    f"{url_absoluta} -> {error}"
                )
                continue

            titulo = (
                titulo_contextual_enlace(
                    enlace,
                    url_absoluta,
                )
            )

            if (
                url_absoluta
                not in resultados
            ):
                resultados[
                    url_absoluta
                ] = {
                    "titulo": titulo,
                    "url": url_absoluta,
                }

    return list(
        resultados.values()
    )




def parece_ficha_individual(
    url: str,
    titulo: str = "",
    dominio_operador: str | None = None,
) -> bool:
    """
    Clasifica conservadoramente una URL como ficha individual.

    No depende de operadores ni dominios concretos.
    """

    parsed = urlparse(url)

    dominio_url = parsed.netloc.lower()
    ruta = normalizar_texto(
        parsed.path
    )

    segmentos = [
        segmento
        for segmento in parsed.path.split("/")
        if segmento
    ]

    # -----------------------------------------------------
    # Fichas externas de reserva
    # -----------------------------------------------------

    if (
        dominio_operador
        and dominio_url
        != dominio_operador.lower()
    ):
        return parece_enlace_reserva(
            url,
            titulo,
        )

    # -----------------------------------------------------
    # Fichas internas
    # -----------------------------------------------------

    senales_ruta = (
        "tour",
        "tours",
        "activity",
        "actividad",
        "activities",
        "experience",
        "experiencia",
        "excursion",
        "excursion",
        "product",
        "producto",
        "detail",
        "detalle",
    )

    if any(
        senal in ruta
        for senal in senales_ruta
    ):
        # Evitar p?ginas ra?z de categor?a como /tours/
        # cuando no contienen una ficha concreta.
        if len(segmentos) >= 2:
            return True

    # IDs en la ruta suelen corresponder a una entidad concreta.
    if any(
        re.fullmatch(
            r"\d{2,}",
            segmento,
        )
        for segmento in segmentos
    ):
        return True

    return False



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


def enriquecer_imagenes_desde_catalogo(
    tour,
    url_catalogo: str,
    url_ficha: str,
    minimo: int = 4,
):
    """
    Intenta completar imagenes usando exclusivamente
    el bloque del catalogo que enlaza a la ficha concreta.

    No usa imagenes globales del catalogo.
    No duplica imagenes.
    No inventa asociaciones entre actividades.
    """

    imagenes_actuales = list(
        getattr(tour, "imagenes", None)
        or []
    )

    if len(imagenes_actuales) >= minimo:
        return tour

    validar_url_segura(url_catalogo)
    validar_url_segura(url_ficha)

    try:
        html = obtener_html_playwright(
            url_catalogo
        )
    except Exception:
        return tour

    soup_catalogo = BeautifulSoup(
        html,
        "html.parser",
    )

    objetivo_limpio, _ = urldefrag(
        url_ficha
    )

    enlace_objetivo = None

    for enlace in soup_catalogo.find_all(
        "a",
        href=True,
    ):
        candidata = urljoin(
            url_catalogo,
            enlace.get("href", ""),
        )

        candidata_limpia, _ = urldefrag(
            candidata
        )

        if candidata_limpia == objetivo_limpio:
            enlace_objetivo = enlace
            break

    if enlace_objetivo is None:
        return tour

    # -----------------------------------------------------
    # BUSCAR EL BLOQUE MAS CERCANO DE LA FICHA
    # -----------------------------------------------------

    bloque = enlace_objetivo

    etiquetas_bloque = {
        "article",
        "li",
        "section",
        "div",
    }

    for _ in range(6):
        padre = getattr(
            bloque,
            "parent",
            None,
        )

        if padre is None:
            break

        bloque = padre

        if getattr(
            bloque,
            "name",
            None,
        ) in etiquetas_bloque:

            enlaces_bloque = bloque.find_all(
                "a",
                href=True,
            )

            urls_ficha_bloque = set()

            for enlace in enlaces_bloque:
                href = enlace.get(
                    "href",
                    "",
                )

                absoluta = urljoin(
                    url_catalogo,
                    href,
                )

                limpia, _ = urldefrag(
                    absoluta
                )

                if limpia == objetivo_limpio:
                    urls_ficha_bloque.add(
                        limpia
                    )

            if objetivo_limpio in urls_ficha_bloque:
                break

    # -----------------------------------------------------
    # EXTRAER SOLO IMAGENES DE ESE BLOQUE
    # -----------------------------------------------------

    soup_bloque = BeautifulSoup(
        str(bloque),
        "html.parser",
    )

    imagenes_bloque = extraer_imagenes(
        {},
        soup_bloque,
        url_catalogo,
    )

    combinadas = []
    vistas = set()

    for imagen in (
        imagenes_actuales
        + imagenes_bloque
    ):
        if not isinstance(imagen, str):
            continue

        imagen = imagen.strip()

        if not imagen:
            continue

        limpia, _ = urldefrag(
            imagen
        )

        if limpia in vistas:
            continue

        vistas.add(limpia)
        combinadas.append(limpia)

    tour.imagenes = combinadas[:10]

    return tour



def extraer_imagenes(
    entidad: dict,
    soup: BeautifulSoup,
    url: str,
) -> list[str]:
    candidatas = []

    # -----------------------------------------------------
    # FILTRO UNIVERSAL
    # -----------------------------------------------------

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
        "app.png",
        "civitatis-app",
        "mascota",
        "mascot",
        "espanol",
        "english",
        "idioma",
        "language",
        "flag",
        "banner",
        "newsletter",
        "tracking",
        "analytics",
        "loader",
        "spinner",
        "marker",
        "map-marker",
        "map_marker",
        "pin-map",
        "map-pin",
    )

    palabras_relacionadas = (
        "related",
        "relacionado",
        "recomendado",
        "recommend",
        "tambien-te-puede",
        "otros-tours",
        "similar",
    )

    dominios_cartograficos = (
        "tile.openstreetmap.org",
        "tiles.openstreetmap.org",
        "maps.googleapis.com",
        "maps.google.com",
        "maps.gstatic.com",
        "googleapis.com/maps",
        "mapbox.com",
        "mapbox.cn",
        "tiles.mapbox.com",
        "api.mapbox.com",
        "cartocdn.com",
        "tile.openstreetmap.fr",
        "tile.opentopomap.org",
        "tiles.stadiamaps.com",
        "tile.jawg.io",
        "tiles.arcgis.com",
        "server.arcgisonline.com",
    )

    patrones_cartograficos = (
        "/tiles/",
        "/tile/",
        "/maptiles/",
        "/map-tiles/",
        "staticmap",
        "static-map",
        "map_tile",
        "map-tile",
    )

    def imagen_valida(
        imagen: str | None,
        contexto: str = "",
    ) -> str | None:

        if not imagen:
            return None

        imagen = str(imagen).strip()

        if not imagen:
            return None

        if imagen.startswith("data:"):
            return None

        absoluta = urljoin(url, imagen)
        lower = absoluta.lower()

        parsed = urlparse(absoluta)
        host = parsed.netloc.lower()

        # Solo recursos HTTP/HTTPS.
        if parsed.scheme not in ("http", "https"):
            return None

        # Recursos cartograficos.
        if any(
            dominio in host
            for dominio in dominios_cartograficos
        ):
            return None

        if any(
            patron in lower
            for patron in patrones_cartograficos
        ):
            return None

        texto_completo = (
            f"{lower} {contexto.lower()}"
        )

        if any(
            palabra in texto_completo
            for palabra in palabras_no_validas
        ):
            return None

        return absoluta

    # -----------------------------------------------------
    # JSON-LD
    # -----------------------------------------------------

    imagen_entidad = entidad.get("image")

    if isinstance(imagen_entidad, str):
        candidatas.append(
            (imagen_entidad, "")
        )

    elif isinstance(imagen_entidad, list):
        for imagen in imagen_entidad:
            if isinstance(imagen, str):
                candidatas.append(
                    (imagen, "")
                )

            elif isinstance(imagen, dict):
                valor = (
                    imagen.get("url")
                    or imagen.get("contentUrl")
                )

                if valor:
                    candidatas.append(
                        (valor, "")
                    )

    elif isinstance(imagen_entidad, dict):
        imagen = (
            imagen_entidad.get("url")
            or imagen_entidad.get("contentUrl")
        )

        if imagen:
            candidatas.append(
                (imagen, "")
            )

    # -----------------------------------------------------
    # OPEN GRAPH
    # -----------------------------------------------------

    imagen_meta = obtener_meta(
        soup,
        "og:image",
    )

    if imagen_meta:
        candidatas.append(
            (imagen_meta, "")
        )

    # -----------------------------------------------------
    # IMAGENES HTML
    # -----------------------------------------------------

    principal = soup.find("main") or soup

    for etiqueta in principal.find_all("img"):
        imagen = (
            etiqueta.get("src")
            or etiqueta.get("data-src")
            or etiqueta.get("data-lazy-src")
            or etiqueta.get("data-original")
        )

        if not imagen:
            continue

        contexto_imagen = " ".join([
            etiqueta.get("alt", ""),
            etiqueta.get("title", ""),
            " ".join(
                etiqueta.get("class", [])
            ),
            etiqueta.get("id", ""),
        ])

        # Evitar bloques de tours relacionados.
        ancestro = etiqueta
        bloque_relacionado = False

        for _ in range(5):
            ancestro = (
                ancestro.parent
                if ancestro
                else None
            )

            if ancestro is None:
                break

            clases = " ".join(
                ancestro.get("class", [])
            )

            identificador = ancestro.get(
                "id",
                "",
            )

            contexto = (
                f"{clases} {identificador}"
            ).lower()

            if any(
                palabra in contexto
                for palabra
                in palabras_relacionadas
            ):
                bloque_relacionado = True
                break

        if bloque_relacionado:
            continue

        candidatas.append(
            (
                imagen,
                contexto_imagen,
            )
        )

    # -----------------------------------------------------
    # VALIDAR + DEDUPLICAR
    # -----------------------------------------------------

    finales = []
    vistas = set()

    for imagen, contexto in candidatas:
        valida = imagen_valida(
            imagen,
            contexto,
        )

        if not valida:
            continue

        # Deduplicacion sin fragmentos.
        limpia, _ = urldefrag(valida)

        if limpia in vistas:
            continue

        vistas.add(limpia)
        finales.append(limpia)

    return finales[:10]



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
    soup: BeautifulSoup | None = None,
) -> tuple[str | None, int | None]:
    if not texto:
        return None, None

    numeros_texto = {
        "una": 1, "un": 1, "uno": 1, "dos": 2, "tres": 3,
        "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
        "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
        "doce": 12,
    }

    def convertir_cantidad(valor: str) -> float | None:
        valor_normalizado = valor.strip().lower()
        if valor_normalizado in numeros_texto:
            return float(numeros_texto[valor_normalizado])
        try:
            return float(valor_normalizado.replace(",", "."))
        except ValueError:
            return None

    def crear_resultado(
        cantidad: float,
        unidad: str,
        original: str,
    ) -> tuple[str, int]:
        unidad_lower = unidad.lower()

        if "min" in unidad_lower and "hora" not in unidad_lower:
            minutos = cantidad
        elif (
            "día" in unidad_lower
            or "dia" in unidad_lower
            or "day" in unidad_lower
            or "noche" in unidad_lower
            or "night" in unidad_lower
        ):
            minutos = cantidad * 24 * 60
        else:
            minutos = cantidad * 60

        return original.strip(), int(minutos)

    # Prioridad 1: sección explícita de duración.
    if soup is not None:
        seccion_duracion = extraer_contenido_seccion(
            soup,
            (
                "duración", "duracion", "duration",
                "duración de la actividad", "duracion de la actividad",
            ),
            limite=5,
        )

        if seccion_duracion:
            texto_duracion = " ".join(seccion_duracion)
            patron = re.search(
                r"\b("
                r"\d+(?:[.,]\d+)?"
                r"|una?|uno|dos|tres|cuatro|cinco|seis|"
                r"siete|ocho|nueve|diez|once|doce"
                r")\s*"
                r"(minutos?|minutes?|mins?|horas?|hours?|hrs?|"
                r"d[ií]as?|days?|noches?|nights?)\b",
                texto_duracion,
                re.IGNORECASE,
            )
            if patron:
                cantidad = convertir_cantidad(patron.group(1))
                if cantidad is not None:
                    return crear_resultado(
                        cantidad,
                        patron.group(2),
                        patron.group(0),
                    )

    # Prioridad 2: frases como "cuatro horas después de la recogida".
    patron_final = re.search(
        r"\b("
        r"\d+(?:[.,]\d+)?"
        r"|una?|uno|dos|tres|cuatro|cinco|seis|"
        r"siete|ocho|nueve|diez|once|doce"
        r")\s*(horas?|hours?|hrs?)"
        r"\s+despu[eé]s\s+de\s+la\s+"
        r"(?:recogida|salida|partida)",
        texto,
        re.IGNORECASE,
    )

    if patron_final:
        cantidad = convertir_cantidad(patron_final.group(1))
        if cantidad is not None:
            cantidad_texto = int(cantidad) if cantidad.is_integer() else cantidad
            return f"{cantidad_texto} horas", int(cantidad * 60)

    # Prioridad 3: expresiones explícitas y cercanas al concepto de duración.
    patrones_contextuales = [
        (
            r"(?:duraci[oó]n|duration)\s*(?:total)?\s*[:\-]?\s*"
            r"(?:de\s*)?(\d+(?:[.,]\d+)?)\s*"
            r"(minutos?|minutes?|mins?|horas?|hours?|hrs?|d[ií]as?|days?)"
        ),
        (
            r"(?:tour|recorrido|actividad|experiencia)\s+(?:de|dura(?:ción)?\s+de)\s+"
            r"(\d+(?:[.,]\d+)?)\s*"
            r"(minutos?|horas?|hrs?|d[ií]as?)"
        ),
    ]

    for patron_texto in patrones_contextuales:
        patron = re.search(patron_texto, texto, re.IGNORECASE)
        if patron:
            cantidad = convertir_cantidad(patron.group(1))
            if cantidad is not None:
                return crear_resultado(cantidad, patron.group(2), patron.group(0))

    # Fallback controlado: evita tomar ventanas de cancelación/reserva.
    patron_general = re.compile(
        r"\b\d+(?:[.,]\d+)?\s*"
        r"(?:minutos?|minutes?|mins?|horas?|hours?|hrs?|d[ií]as?|days?)\b",
        re.IGNORECASE,
    )

    for coincidencia in patron_general.finditer(texto):
        inicio = max(0, coincidencia.start() - 80)
        fin = min(len(texto), coincidencia.end() + 80)
        contexto = texto[inicio:fin].lower()

        palabras_descartar = (
            "cancelación", "cancelacion", "cancel", "antes de",
            "antelación", "antelacion", "reserva", "booking", "reembolso",
        )

        if any(palabra in contexto for palabra in palabras_descartar):
            continue

        original = coincidencia.group(0)
        numero_match = re.search(r"\d+(?:[.,]\d+)?", original)
        unidad_match = re.search(
            r"(minutos?|minutes?|mins?|horas?|hours?|hrs?|d[ií]as?|days?)",
            original,
            re.IGNORECASE,
        )

        if not numero_match or not unidad_match:
            continue

        cantidad = float(numero_match.group(0).replace(",", "."))
        return crear_resultado(cantidad, unidad_match.group(1), original)

    return None, None

def extraer_edades(
    texto: str,
) -> tuple[int | None, int | None]:
    """
    Extrae edad mínima y máxima de forma contextual y genérica.

    Distingue entre límites reales de edad, rangos descriptivos
    de grupos de participantes y condiciones particulares.

    No depende de un operador, dominio ni actividad específica.
    """

    if not texto:
        return None, None

    texto_normalizado = re.sub(
        r"\s+",
        " ",
        texto,
    ).strip()

    if re.search(
        r"(?:"
        r"sin\s+restricci[oó]n\s+de\s+edad|"
        r"sin\s+l[ií]mite\s+de\s+edad|"
        r"no\s+age\s+restriction|"
        r"no\s+age\s+limit|"
        r"sem\s+restri[cç][aã]o\s+de\s+idade|"
        r"sem\s+limite\s+de\s+idade"
        r")",
        texto_normalizado,
        re.IGNORECASE,
    ):
        return 0, None

    edad_minima = None
    edad_maxima = None

    patrones_minimo = (
        r"edad\s+m[ií]nima\s*[:\-]?\s*(\d{1,2})",
        r"minimum\s+age\s*[:\-]?\s*(\d{1,2})",
        r"min(?:imum)?\.?\s+age\s*[:\-]?\s*(\d{1,2})",
        r"idade\s+m[ií]nima\s*[:\-]?\s*(\d{1,2})",
        r"[aâ]ge\s+minimum\s*[:\-]?\s*(\d{1,2})",
        r"mindestalter\s*[:\-]?\s*(\d{1,2})",
        r"et[aà]\s+minima\s*[:\-]?\s*(\d{1,2})",
        r"(?:mayores?|mayor)\s+de\s+(\d{1,2})\s*años",
        r"(?:desde|a\s+partir\s+de)\s+(?:los\s+)?(\d{1,2})\s*años",
        r"(?:mínimo|minimo)\s+(?:de\s+)?(\d{1,2})\s*años",
        r"(\d{1,2})\s*años\s+(?:como\s+)?m[ií]nimo",
        r"ages?\s+(\d{1,2})\s*(?:\+|and\s+up)",
        r"(\d{1,2})\s*(?:years?|yrs?)\s*(?:and\s+up|\+)",
    )

    for patron in patrones_minimo:
        coincidencia = re.search(
            patron,
            texto_normalizado,
            re.IGNORECASE,
        )

        if coincidencia:
            edad_minima = int(
                coincidencia.group(1)
            )
            break

    patrones_maximo = (
        r"edad\s+m[aá]xima\s*[:\-]?\s*(\d{1,2})",
        r"maximum\s+age\s*[:\-]?\s*(\d{1,2})",
        r"max(?:imum)?\.?\s+age\s*[:\-]?\s*(\d{1,2})",
        r"idade\s+m[aá]xima\s*[:\-]?\s*(\d{1,2})",
        r"[aâ]ge\s+maximum\s*[:\-]?\s*(\d{1,2})",
        r"h[oö]chstalter\s*[:\-]?\s*(\d{1,2})",
        r"et[aà]\s+massima\s*[:\-]?\s*(\d{1,2})",
        r"(?:hasta|máximo|maximo)\s+(?:los\s+)?(\d{1,2})\s*años",
        r"(\d{1,2})\s*años\s+(?:como\s+)?m[aá]ximo",
        r"up\s+to\s+(\d{1,2})\s*(?:years?|yrs?)",
    )

    for patron in patrones_maximo:
        coincidencia = re.search(
            patron,
            texto_normalizado,
            re.IGNORECASE,
        )

        if coincidencia:
            edad_maxima = int(
                coincidencia.group(1)
            )
            break

    patron_rango = re.compile(
        r"(?:de\s+)?(\d{1,2})\s*"
        r"(?:a|hasta|-|–|—)\s*"
        r"(\d{1,2})\s*"
        r"(?:años?|anos?|years?|yrs?|ans?|jahre?|anni)\b",
        re.IGNORECASE,
    )

    for coincidencia in patron_rango.finditer(
        texto_normalizado
    ):
        inferior = int(
            coincidencia.group(1)
        )
        superior = int(
            coincidencia.group(2)
        )

        inicio = max(
            0,
            coincidencia.start() - 220,
        )
        fin = min(
            len(texto_normalizado),
            coincidencia.end() + 220,
        )

        contexto = texto_normalizado[
            inicio:fin
        ]

        contexto_grupo = re.search(
            r"(?:"
            r"niñ[oa]s?|menores?|infantes?|adolescentes?|"
            r"children|child|kids?|minors?|teenagers?|"
            r"crian[cç]as?|"
            r"pueden\s+(?:ir|asistir|participar|realizar|hacer|acompañar)|"
            r"puede\s+(?:ir|asistir|participar|realizar|hacer|acompañar)|"
            r"no\s+pueden\s+(?:practicar|realizar|hacer|participar|usar)|"
            r"no\s+puede\s+(?:practicar|realizar|hacer|participar|usar)|"
            r"can\s+(?:attend|join|participate|go|accompany)|"
            r"cannot\s+(?:participate|practice|do|use)|"
            r"can't\s+(?:participate|practice|do|use)|"
            r"podem\s+(?:ir|participar|acompanhar)|"
            r"n[aã]o\s+podem\s+(?:participar|praticar|fazer)"
            r")",
            contexto,
            re.IGNORECASE,
        )

        contexto_limite = re.search(
            r"(?:"
            r"rango\s+de\s+edad|"
            r"rango\s+etario|"
            r"edades?\s+permitidas?|"
            r"edad\s+permitida|"
            r"edad\s+requerida|"
            r"l[ií]mite\s+de\s+edad|"
            r"age\s+range|"
            r"allowed\s+ages?|"
            r"required\s+age|"
            r"faixa\s+et[aá]ria|"
            r"idade\s+permitida|"
            r"tranche\s+d['’]âge|"
            r"altersbereich|"
            r"fascia\s+di\s+et[aà]"
            r")",
            contexto,
            re.IGNORECASE,
        )

        if not contexto_limite:
            contexto_limite = re.search(
                r"(?:"
                r"edad.{0,40}entre\s+\d{1,2}\s+y\s+\d{1,2}\s*años|"
                r"ages?.{0,40}between\s+\d{1,2}\s+and\s+\d{1,2}\s*years?|"
                r"idade.{0,40}entre\s+\d{1,2}\s+e\s+\d{1,2}\s*anos"
                r")",
                contexto,
                re.IGNORECASE,
            )

        if contexto_limite and not contexto_grupo:
            if edad_minima is None:
                edad_minima = inferior

            if edad_maxima is None:
                edad_maxima = superior

        elif contexto_grupo:
            if edad_minima is None:
                edad_minima = inferior

    if edad_minima is None:
        patrones_acceso = (
            r"(?:mayores?\s+de|a\s+partir\s+de|desde\s+los?)"
            r"\s*(\d{1,2})\s*años",
            r"minimum\s+age\s*[:\-]?\s*(\d{1,2})",
            r"ages?\s+(\d{1,2})\s*(?:\+|and\s+up)",
        )

        for patron in patrones_acceso:
            coincidencia = re.search(
                patron,
                texto_normalizado,
                re.IGNORECASE,
            )

            if coincidencia:
                edad_minima = int(
                    coincidencia.group(1)
                )
                break

    if (
        edad_minima is not None
        and edad_maxima is not None
        and edad_maxima < edad_minima
    ):
        edad_maxima = None

    return edad_minima, edad_maxima


def extraer_idiomas(
    texto: str,
    soup: BeautifulSoup | None = None,
    secciones: dict | None = None,
) -> list[str]:
    """
    Extrae idiomas ofrecidos por la actividad.

    La detección es multidioma y no depende de un operador concreto.
    Prioriza secciones relacionadas con el servicio/guía para evitar
    falsos positivos provenientes del menú o selector de idioma del sitio.
    """

    idiomas_variantes = {
        "Español": (
            "español", "espanol", "spanish", "espagnol", "espanhol"
        ),
        "Inglés": (
            "inglés", "ingles", "english", "anglais", "inglês", "inglese"
        ),
        "Portugués": (
            "portugués", "portugues", "portuguese", "português", "portugais"
        ),
        "Francés": (
            "francés", "frances", "french", "français", "francais", "francese"
        ),
        "Alemán": (
            "alemán", "aleman", "german", "deutsch", "allemand", "tedesco"
        ),
        "Italiano": (
            "italiano", "italian", "italien"
        ),
        "Neerlandés": (
            "neerlandés", "neerlandes", "dutch", "nederlands", "néerlandais"
        ),
        "Catalán": (
            "catalán", "catalan", "català", "catala"
        ),
        "Gallego": (
            "gallego", "galician", "galego"
        ),
        "Euskera": (
            "euskera", "basque", "vasco"
        ),
        "Ruso": (
            "ruso", "russian", "русский"
        ),
        "Ucraniano": (
            "ucraniano", "ukrainian", "українська"
        ),
        "Polaco": (
            "polaco", "polish", "polski"
        ),
        "Checo": (
            "checo", "czech", "čeština", "cestina"
        ),
        "Eslovaco": (
            "eslovaco", "slovak", "slovenčina", "slovencina"
        ),
        "Esloveno": (
            "esloveno", "slovenian", "slovenščina", "slovenscina"
        ),
        "Croata": (
            "croata", "croatian", "hrvatski"
        ),
        "Serbio": (
            "serbio", "serbian", "srpski", "српски"
        ),
        "Búlgaro": (
            "búlgaro", "bulgaro", "bulgarian", "български"
        ),
        "Rumano": (
            "rumano", "romanian", "română", "romana"
        ),
        "Húngaro": (
            "húngaro", "hungaro", "hungarian", "magyar"
        ),
        "Griego": (
            "griego", "greek", "ελληνικά"
        ),
        "Turco": (
            "turco", "turkish", "türkçe", "turkce"
        ),
        "Árabe": (
            "árabe", "arabe", "arabic", "العربية"
        ),
        "Hebreo": (
            "hebreo", "hebrew", "עברית"
        ),
        "Persa": (
            "persa", "persian", "farsi", "فارسی"
        ),
        "Hindi": (
            "hindi", "हिन्दी", "हिंदी"
        ),
        "Bengalí": (
            "bengalí", "bengali", "বাংলা"
        ),
        "Urdu": (
            "urdu", "اردو"
        ),
        "Chino": (
            "chino", "chinese", "mandarin", "中文", "普通话", "國語"
        ),
        "Japonés": (
            "japonés", "japones", "japanese", "日本語"
        ),
        "Coreano": (
            "coreano", "korean", "한국어"
        ),
        "Tailandés": (
            "tailandés", "tailandes", "thai", "ภาษาไทย"
        ),
        "Vietnamita": (
            "vietnamita", "vietnamese", "tiếng việt", "tieng viet"
        ),
        "Indonesio": (
            "indonesio", "indonesian", "bahasa indonesia"
        ),
        "Malayo": (
            "malayo", "malay", "bahasa melayu"
        ),
        "Filipino": (
            "filipino", "tagalog"
        ),
        "Sueco": (
            "sueco", "swedish", "svenska"
        ),
        "Noruego": (
            "noruego", "norwegian", "norsk"
        ),
        "Danés": (
            "danés", "danes", "danish", "dansk"
        ),
        "Finés": (
            "finés", "fines", "finnish", "suomi"
        ),
        "Islandés": (
            "islandés", "islandes", "icelandic", "íslenska", "islenska"
        ),
        "Estonio": (
            "estonio", "estonian", "eesti"
        ),
        "Letón": (
            "letón", "leton", "latvian", "latviešu", "latviesu"
        ),
        "Lituano": (
            "lituano", "lithuanian", "lietuvių", "lietuviu"
        ),
    }

    indicadores = (
        "guía", "guia", "guide", "guides",
        "idioma", "idiomas", "language", "languages",
        "langue", "langues",
        "sprache", "sprachen",
        "lingua", "lingue",
        "língua", "linguas", "línguas",
        "bilingüe", "bilingue", "bilingual",
        "multilingüe", "multilingue", "multilingual",
        "staff", "spoken", "speaks",
        "hablado", "hablada",
        "falado", "falada",
    )

    encontrados: list[str] = []

    def agregar_desde_texto(texto_fuente: str) -> None:
        if not texto_fuente:
            return

        texto_lower = texto_fuente.lower()

        for nombre, variantes in idiomas_variantes.items():
            if nombre in encontrados:
                continue

            for variante in variantes:
                if variante.lower() in texto_lower:
                    encontrados.append(nombre)
                    break

    # 1. Secciones prioritarias del servicio.
    textos_prioritarios = []

    if secciones:
        for clave in (
            "incluye",
            "informacion_importante",
            "recomendaciones",
            "restricciones",
        ):
            textos_prioritarios.extend(
                secciones.get(clave) or []
            )

    texto_prioritario = " ".join(textos_prioritarios)

    if any(
        indicador in texto_prioritario.lower()
        for indicador in indicadores
    ):
        agregar_desde_texto(texto_prioritario)

        if encontrados:
            return list(dict.fromkeys(encontrados))

    # 2. Sección explícita de idiomas/guía.
    if soup is not None:
        seccion_idioma = extraer_contenido_seccion(
            soup,
            (
                "idioma", "idiomas",
                "language", "languages",
                "langue", "langues",
                "sprache", "sprachen",
                "lingua", "lingue",
                "língua", "linguas", "línguas",
                "guía", "guia",
                "guide", "guides",
            ),
            limite=12,
        )

        texto_seccion = " ".join(seccion_idioma)

        if texto_seccion:
            agregar_desde_texto(texto_seccion)

            if encontrados:
                return list(dict.fromkeys(encontrados))

    # 3. Contexto general limpio, sin header/footer/nav.
    if soup is not None:
        copia = BeautifulSoup(
            str(soup),
            "html.parser",
        )

        for etiqueta in copia.find_all(
            ["nav", "footer", "header", "aside"]
        ):
            etiqueta.decompose()

        principal = copia.find("main") or copia

        texto_limpio = principal.get_text(
            " ",
            strip=True,
        )
    else:
        texto_limpio = texto

    texto_limpio_lower = texto_limpio.lower()

    indicadores_regex = "|".join(
        re.escape(indicador.lower())
        for indicador in indicadores
    )

    for nombre, variantes in idiomas_variantes.items():
        if nombre in encontrados:
            continue

        for variante in variantes:
            variante_regex = re.escape(
                variante.lower()
            )

            patron = (
                rf"(?:{indicadores_regex}).{{0,120}}{variante_regex}"
                rf"|{variante_regex}.{{0,120}}(?:{indicadores_regex})"
            )

            if re.search(
                patron,
                texto_limpio_lower,
                re.IGNORECASE,
            ):
                encontrados.append(nombre)
                break

    return list(dict.fromkeys(encontrados))

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
            "itinerary",
            "itinéraire",
            "itineraire",
            "itinerário",
            "programa",
            "program",
            "programme",
            "programma",
            "recorrido",
            "route",
            "roteiro",
            "ablauf",
            "reiseverlauf",
        ),
        limite=30,
    )

    pasos_por_dia = []

    patron_dia = (
        r"^(?:"
        r"day|d[ií]a|jour|giorno|tag|dia"
        r")\s*(\d+)\s*[:.-]?\s*(.*)$"
    )

    for etiqueta in soup.find_all(
        ["li", "p", "h2", "h3", "h4", "h5"]
    ):
        texto = etiqueta.get_text(
            " ",
            strip=True,
        )

        coincidencia = re.match(
            patron_dia,
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



def extraer_highlights(
    soup: BeautifulSoup,
) -> list[str]:
    """
    Extrae puntos destacados aunque el sitio no use headings HTML reales.
    Busca primero una sección semántica y luego un bloque textual cercano
    a títulos como "¿Qué te espera?".
    """

    nombres = (
        "qué te espera",
        "que te espera",
        "qué esperar",
        "que esperar",
        "destacados",
        "lo más destacado",
        "lo mas destacado",
        "highlights",
        "what to expect",
        "why you'll love it",
        "why you will love it",
        "points forts",
        "temps forts",
        "destaques",
        "o que esperar",
        "höhepunkte",
        "hoehepunkte",
        "punti salienti",
        "cosa aspettarsi",
    )

    # 1. Método normal por encabezados.
    resultados = extraer_contenido_seccion(
        soup,
        nombres,
        limite=20,
    )

    if resultados:
        return list(dict.fromkeys(
            valor.strip()
            for valor in resultados
            if valor and valor.strip()
        ))[:20]

    nombres_norm = tuple(
        normalizar_texto(nombre)
        for nombre in nombres
    )

    # 2. Buscar cualquier nodo cuyo texto sea exactamente el título.
    candidatos_titulo = []

    for etiqueta in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6",
         "div", "span", "strong", "b", "p"]
    ):
        texto = etiqueta.get_text(" ", strip=True)

        if not texto or len(texto) > 100:
            continue

        texto_norm = normalizar_texto(texto).strip(" :.-")

        if texto_norm in nombres_norm:
            candidatos_titulo.append(etiqueta)

    for titulo in candidatos_titulo:
        encontrados = []

        # 2a. Buscar listas en el contenedor cercano.
        contenedor = titulo.parent

        for _ in range(4):
            if contenedor is None:
                break

            listas = contenedor.find_all(["ul", "ol"])

            for lista in listas:
                for li in lista.find_all("li", recursive=False):
                    valor = li.get_text(" ", strip=True)

                    if 15 <= len(valor) <= 350:
                        encontrados.append(valor)

            if encontrados:
                break

            contenedor = contenedor.parent

        if encontrados:
            return list(dict.fromkeys(encontrados))[:20]

        # 2b. Buscar hermanos posteriores hasta el siguiente bloque/título.
        for hermano in titulo.find_next_siblings(limit=12):
            if hermano.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                break

            if hermano.name in {"ul", "ol"}:
                for li in hermano.find_all("li"):
                    valor = li.get_text(" ", strip=True)
                    if 15 <= len(valor) <= 350:
                        encontrados.append(valor)

            elif hermano.name in {"p", "div"}:
                valor = hermano.get_text(" ", strip=True)

                if (
                    15 <= len(valor) <= 350
                    and normalizar_texto(valor) not in nombres_norm
                ):
                    encontrados.append(valor)

            if len(encontrados) >= 8:
                break

        if encontrados:
            return list(dict.fromkeys(encontrados))[:20]

    # 3. Fallback textual específico pero genérico:
    # localizar el título dentro del texto visible y capturar líneas
    # inmediatamente posteriores.
    copia = BeautifulSoup(str(soup), "html.parser")

    for etiqueta in copia.find_all(
        ["script", "style", "nav", "footer", "header", "aside"]
    ):
        etiqueta.decompose()

    principal = copia.find("main") or copia
    texto_lineas = principal.get_text("\n", strip=True)

    lineas = [
        linea.strip()
        for linea in texto_lineas.splitlines()
        if linea.strip()
    ]

    for indice, linea in enumerate(lineas):
        linea_norm = normalizar_texto(linea).strip(" :.-")

        if linea_norm not in nombres_norm:
            continue

        encontrados = []

        for siguiente in lineas[indice + 1: indice + 15]:
            siguiente_norm = normalizar_texto(siguiente).strip(" :.-")

            if not siguiente_norm:
                continue

            # Detener al llegar a otra sección conocida.
            cortes = (
                "itinerario",
                "incluye",
                "no incluye",
                "recomendaciones",
                "restricciones",
                "informacion importante",
                "duracion",
                "salidas",
                "horarios",
                "ubicacion",
                "destino",
            )

            if any(
                siguiente_norm == corte
                or siguiente_norm.startswith(corte + ":")
                for corte in cortes
            ):
                break

            if 15 <= len(siguiente) <= 350:
                encontrados.append(siguiente)

            if len(encontrados) >= 8:
                break

        if encontrados:
            return list(dict.fromkeys(encontrados))[:20]

    return []

def extraer_horarios_salidas(
    soup: BeautifulSoup,
) -> list[str]:
    """
    Extrae horarios y rangos de salida publicados como texto.
    Funciona aunque 'Salidas' no esté implementado como heading HTML.
    """

    elementos = extraer_contenido_seccion(
        soup,
        (
            "salidas", "salida", "horarios", "horario",
            "hora de salida", "departure", "departures",
            "departure time", "departure times", "schedule",
            "schedules", "times", "départ", "départs",
            "heure de départ", "horaires", "saídas", "saidas",
            "horários", "horarios de saída", "abfahrt",
            "abfahrtszeiten", "orari", "partenze",
        ),
        limite=20,
    )

    # Fallback: buscar en el texto visible completo. Esto cubre textos como:
    # "Salidas: 8.00 horas a 13.00 horas / 14.00 horas a 19 horas".
    if not elementos:
        copia = BeautifulSoup(str(soup), "html.parser")
        for etiqueta in copia.find_all(["nav", "footer", "header", "aside"]):
            etiqueta.decompose()
        principal = copia.find("main") or copia
        elementos = [principal.get_text(" ", strip=True)]

    horarios = []

    # Acepta 8.00, 08:00, 13.00, y también "19 horas".
    patron_rango = re.compile(
        r"\b([01]?\d|2[0-3])(?:[.:]([0-5]\d))?\s*"
        r"(?:horas?|hrs?|h|hours?)?\s*"
        r"(?:a|-|–|—|hasta|to|até|ate|bis|à)\s*"
        r"([01]?\d|2[0-3])(?:[.:]([0-5]\d))?\s*"
        r"(?:horas?|hrs?|h|hours?)\b",
        re.IGNORECASE,
    )

    for elemento in elementos:
        texto = elemento.strip()

        for coincidencia in patron_rango.finditer(texto):
            hora_inicio = int(coincidencia.group(1))
            minuto_inicio = int(coincidencia.group(2) or 0)
            hora_fin = int(coincidencia.group(3))
            minuto_fin = int(coincidencia.group(4) or 0)

            horario = (
                f"{hora_inicio:02d}:{minuto_inicio:02d} - "
                f"{hora_fin:02d}:{minuto_fin:02d}"
            )
            if horario not in horarios:
                horarios.append(horario)

    return horarios[:20]

def extraer_destino(
    nombre: str | None,
    ubicacion: Ubicacion,
    soup: BeautifulSoup | None = None,
) -> str | None:
    """
    Obtiene un destino explícito cuando existe.
    No inventa destinos.
    """

    if soup is not None:
        seccion_destino = extraer_contenido_seccion(
            soup,
            (
                "destino",
                "destination",
                "destination du tour",
                "destinação",
                "destinacao",
                "destinazione",
                "ziel",
                "reiseziel",
            ),
            limite=3,
        )

        if seccion_destino:
            candidato = seccion_destino[0].strip()

            if 1 < len(candidato) <= 100:
                return candidato

    if nombre:
        patrones = (
            r"\ben\s+([^–—|,:]+)",
            r"\bin\s+([^–—|,:]+)",
            r"\bà\s+([^–—|,:]+)",
            r"\bem\s+([^–—|,:]+)",
        )

        for patron in patrones:
            coincidencia = re.search(
                patron,
                nombre,
                re.IGNORECASE,
            )

            if coincidencia:
                candidato = (
                    coincidencia.group(1)
                    .strip(" -–—")
                )

                if 1 < len(candidato) <= 80:
                    return candidato

    if ubicacion and ubicacion.ciudad:
        return ubicacion.ciudad.strip() or None

    if ubicacion and ubicacion.region:
        return ubicacion.region.strip() or None

    if ubicacion and ubicacion.pais:
        return ubicacion.pais.strip() or None

    return None


def extraer_restricciones_contextuales(
    soup: BeautifulSoup,
) -> list[str]:
    """
    Extrae restricciones contextuales sin arrastrar texto narrativo
    anterior del itinerario.

    La lógica es genérica: detecta marcadores de restricción o información
    importante y conserva desde ese marcador; además reconoce frases
    independientes con condiciones de edad, acceso o prohibición.
    """

    indicadores_inicio = (
        "importante",
        "important",
        "important information",
        "atenção",
        "atencao",
        "attention",
        "achtung",
        "attenzione",
        "restricción",
        "restriccion",
        "restricciones",
        "restriction",
        "restrictions",
        "requisito",
        "requisitos",
        "requirement",
        "requirements",
        "edad mínima",
        "edad minima",
        "minimum age",
        "âge minimum",
        "age minimum",
        "idade mínima",
        "idade minima",
        "mindestalter",
        "età minima",
        "eta minima",
        "no permitido",
        "not allowed",
        "não permitido",
        "nao permitido",
        "interdit",
        "nicht erlaubt",
        "non consentito",
    )

    indicadores_condicion = (
        "puede",
        "pueden",
        "no puede",
        "no pueden",
        "permitido",
        "permitida",
        "permitidos",
        "permitidas",
        "prohibido",
        "prohibida",
        "prohibidos",
        "prohibidas",
        "debe",
        "deben",
        "requiere",
        "requieren",
        "can ",
        "cannot",
        "can't",
        "must ",
        "not allowed",
        "allowed",
        "podem",
        "pode ",
        "não podem",
        "nao podem",
        "não pode",
        "nao pode",
        "interdit",
        "autorisé",
        "autorise",
        "nicht erlaubt",
        "muss ",
        "dürfen",
        "durfen",
        "non consentito",
        "vietato",
    )

    patron_edad = re.compile(
        r"\b\d{1,2}\s*"
        r"(?:años?|anos?|years?|yrs?|ans?|jahre?|anni)\b",
        re.IGNORECASE,
    )

    resultados = []

    def limpiar_fragmento(texto: str) -> str:
        texto = re.sub(r"\s+", " ", texto).strip()

        if not texto:
            return ""

        texto_normalizado = normalizar_texto(texto)

        # Si existe un marcador explícito dentro de un párrafo narrativo,
        # conservar solamente desde ese marcador.
        posiciones = []

        for indicador in indicadores_inicio:
            indicador_normalizado = normalizar_texto(indicador)

            posicion = texto_normalizado.find(indicador_normalizado)

            if posicion >= 0:
                posiciones.append(
                    (
                        posicion,
                        indicador_normalizado,
                    )
                )

        if posiciones:
            posicion_normalizada, indicador_encontrado = min(
                posiciones,
                key=lambda valor: valor[0],
            )

            # Buscar la misma zona en el texto original sin depender
            # exactamente de tildes o mayúsculas.
            palabras_indicador = indicador_encontrado.split()

            if palabras_indicador:
                primera = re.escape(
                    palabras_indicador[0]
                )

                coincidencia = re.search(
                    rf"\b{primera}\b",
                    texto,
                    re.IGNORECASE,
                )

                if coincidencia:
                    texto = texto[
                        coincidencia.start():
                    ].strip()

        texto = re.sub(
            r"^[\s:;,\-–—.]+",
            "",
            texto,
        ).strip()

        return texto

    def agregar(texto: str) -> None:
        texto = limpiar_fragmento(texto)

        if not texto:
            return

        if len(texto) < 10 or len(texto) > 700:
            return

        normalizado = normalizar_texto(texto)

        contiene_indicador = any(
            normalizar_texto(indicador) in normalizado
            for indicador in indicadores_inicio
        )

        contiene_edad = bool(
            patron_edad.search(texto)
        )

        contiene_condicion = any(
            normalizar_texto(indicador) in normalizado
            for indicador in indicadores_condicion
        )

        contiene_restriccion_semantica = any(
            raiz in normalizado
            for raiz in (
                "restric",
                "requis",
                "permit",
                "prohib",
                "important",
                "importante",
                "minimum age",
                "edad minima",
                "idade minima",
                "mindestalter",
            )
        )

        if not (
            contiene_restriccion_semantica
            or (
                contiene_edad
                and contiene_condicion
            )
            or (
                contiene_indicador
                and contiene_edad
            )
        ):
            return

        if texto not in resultados:
            resultados.append(texto)

    # Revisar elementos relativamente atómicos. Evitar div grandes porque
    # suelen concatenar itinerario, descripción y restricciones completas.
    for etiqueta in soup.find_all(
        ["li", "p"]
    ):
        texto = etiqueta.get_text(
            " ",
            strip=True,
        )

        agregar(texto)

    # Fallback para sitios que colocan IMPORTANTE/RESTRICCIONES en divs
    # sin párrafos ni listas. Solo aceptar divs sin otros div/p/li internos,
    # para reducir la captura de bloques contenedores gigantes.
    for etiqueta in soup.find_all("div"):
        if etiqueta.find(
            ["div", "p", "li"],
            recursive=False,
        ):
            continue

        texto = etiqueta.get_text(
            " ",
            strip=True,
        )

        agregar(texto)

    return resultados[:10]

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
            "cancellation policy",
            "free cancellation",
            "politique d'annulation",
            "annulation gratuite",
            "política de cancelamento",
            "politica de cancelamento",
            "kostenlose stornierung",
            "stornierungsbedingungen",
            "politica di cancellazione",
            "cancellazione gratuita",
        ),
        limite=8,
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
                "what's included",
                "what is included",
                "inclui",
                "o que inclui",
                "inclus",
                "ce qui est inclus",
                "enthalten",
                "incluso",
                "cosa include",
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
                "what's not included",
                "what is not included",
                "nao inclui",
                "não inclui",
                "non inclus",
                "ce qui n'est pas inclus",
                "nicht enthalten",
                "non incluso",
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
                "quoi apporter",
                "à apporter",
                "a apporter",
                "mitbringen",
                "was mitbringen",
                "cosa portare",
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
                "interdit",
                "objets interdits",
                "nicht erlaubt",
                "verboten",
                "non consentito",
                "vietato",
            ),
        ),
        "recomendaciones": extraer_contenido_seccion(
            soup,
            (
                "recomendaciones",
                "consejos",
                "tips",
                "recommendations",
                "advice",
                "recomendacoes",
                "recomendações",
                "conseils",
                "empfehlungen",
                "raccomandazioni",
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
                "conditions",
                "einschränkungen",
                "einschrankungen",
                "beschränkungen",
                "beschrankungen",
                "restrizioni",
                "requisiti",
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
                    "important",
                    "good to know",
                    "informacoes importantes",
                    "informações importantes",
                    "informations importantes",
                    "à savoir",
                    "a savoir",
                    "wichtige informationen",
                    "gut zu wissen",
                    "informazioni importanti",
                    "da sapere",
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
    url: str | None = None,
) -> Ubicacion:
    ubicacion = Ubicacion()

    dato_ubicacion = entidad.get("location")

    if isinstance(dato_ubicacion, str):
        ubicacion.direccion = dato_ubicacion

    elif isinstance(dato_ubicacion, dict):
        ubicacion.direccion = dato_ubicacion.get("name")
        direccion = dato_ubicacion.get("address")

        if isinstance(direccion, str):
            ubicacion.direccion = direccion

        elif isinstance(direccion, dict):
            ubicacion.pais = direccion.get("addressCountry")
            ubicacion.region = direccion.get("addressRegion")
            ubicacion.ciudad = direccion.get("addressLocality")
            ubicacion.direccion = direccion.get("streetAddress") or ubicacion.direccion

        geo = dato_ubicacion.get("geo")
        if isinstance(geo, dict):
            ubicacion.latitud = convertir_numero(geo.get("latitude"))
            ubicacion.longitud = convertir_numero(geo.get("longitude"))

    # Solo Place/TouristAttraction: evita tomar la dirección corporativa
    # de una plataforma como Civitatis como ubicación de la actividad.
    for elemento in datos_json_ld:
        tipo = elemento.get("@type")
        tipos = set(tipo) if isinstance(tipo, list) else {tipo}

        if not (tipos & {"Place", "TouristAttraction"}):
            continue

        direccion = elemento.get("address")

        if isinstance(direccion, str):
            if not ubicacion.direccion:
                ubicacion.direccion = direccion

        elif isinstance(direccion, dict):
            ubicacion.pais = ubicacion.pais or direccion.get("addressCountry")
            ubicacion.region = ubicacion.region or direccion.get("addressRegion")
            ubicacion.ciudad = ubicacion.ciudad or direccion.get("addressLocality")
            ubicacion.direccion = ubicacion.direccion or direccion.get("streetAddress")

    copia = BeautifulSoup(str(soup), "html.parser")
    for etiqueta in copia.find_all(["footer", "header", "nav", "aside"]):
        etiqueta.decompose()

    principal = copia.find("main") or copia
    texto_principal = principal.get_text(" ", strip=True)
    texto_normalizado = normalizar_texto(texto_principal)
    texto_url = normalizar_texto(url or "")

    ciudades = {
        "medellin": ("Medellín", "Colombia"),
        "cartagena": ("Cartagena", "Colombia"),
        "bogota": ("Bogotá", "Colombia"),
        "guatape": ("Guatapé", "Colombia"),
        "rionegro": ("Rionegro", "Colombia"),
        "guarne": ("Guarne", "Colombia"),
        "chiloe": ("Chiloé", "Chile"),
        "castro": ("Castro", "Chile"),
        "santiago": ("Santiago", "Chile"),
        "cusco": ("Cusco", "Perú"),
        "arequipa": ("Arequipa", "Perú"),
        "lima": ("Lima", "Perú"),
        "punta cana": ("Punta Cana", "República Dominicana"),
    }

    # URL primero, porque suele contener el destino y es menos propensa
    # a contaminación por footer o selector de países.
    for clave, (ciudad, pais) in ciudades.items():
        if clave in texto_url:
            if not ubicacion.ciudad:
                ubicacion.ciudad = ciudad
            if not ubicacion.pais:
                ubicacion.pais = pais
            break

    if not ubicacion.ciudad:
        for clave, (ciudad, pais) in ciudades.items():
            if clave in texto_normalizado:
                ubicacion.ciudad = ciudad
                if not ubicacion.pais:
                    ubicacion.pais = pais
                break

    paises = {
        "colombia": "Colombia",
        "chile": "Chile",
        "brasil": "Brasil",
        "argentina": "Argentina",
        "peru": "Perú",
        "ecuador": "Ecuador",
        "mexico": "México",
        "uruguay": "Uruguay",
        "republica dominicana": "República Dominicana",
        "costa rica": "Costa Rica",
        "panama": "Panamá",
    }

    if not ubicacion.pais:
        for clave, pais in paises.items():
            if clave in texto_url or clave in texto_normalizado:
                ubicacion.pais = pais
                break

    regiones = {
        "antioquia": "Antioquia",
        "bolivar": "Bolívar",
        "los lagos": "Región de Los Lagos",
        "region de los lagos": "Región de Los Lagos",
    }

    if not ubicacion.region:
        for clave, region in regiones.items():
            if clave in texto_normalizado:
                ubicacion.region = region
                break

    texto_ubicacion = extraer_contenido_seccion(
        principal,
        (
            "ubicación", "ubicacion", "location",
            "punto de encuentro", "meeting point",
            "cómo llegar", "como llegar",
            "lieu", "point de rencontre",
            "localização", "localizacao", "ponto de encontro",
            "ort", "treffpunkt",
            "luogo", "punto d'incontro",
        ),
        limite=5,
    )

    if not ubicacion.direccion and texto_ubicacion:
        posible = " ".join(texto_ubicacion).strip()
        if posible and len(posible) <= 160:
            ubicacion.direccion = posible

    if ubicacion.direccion:
        direccion_normalizada = normalizar_texto(ubicacion.direccion)
        palabras_sospechosas = (
            "privacy", "contactanos", "reservas whatsapp",
            "informacion news", "tienda", "newsletter",
            "copyright", "civitatis",
        )
        paises_aislados = {
            "espana", "spain", "chile", "colombia", "peru",
            "brasil", "argentina",
        }

        if (
            len(ubicacion.direccion) > 160
            or any(palabra in direccion_normalizada for palabra in palabras_sospechosas)
            or direccion_normalizada in paises_aislados
        ):
            ubicacion.direccion = None

    # Si la ciudad permite inferir el país con seguridad, corregimos
    # posibles falsos positivos de texto global.
    for _, (ciudad, pais) in ciudades.items():
        if ubicacion.ciudad == ciudad:
            ubicacion.pais = pais
            break

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

def extraer_descripcion_fallback(
    soup: BeautifulSoup,
    nombre: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Obtiene una descripción visible cuando JSON-LD/meta no la publica.
    Evita navegación, footer y bloques típicamente operativos.
    """

    copia = BeautifulSoup(str(soup), "html.parser")

    for etiqueta in copia.find_all(
        ["script", "style", "nav", "footer", "header", "aside", "form"]
    ):
        etiqueta.decompose()

    principal = copia.find("main") or copia

    h1 = principal.find("h1")
    candidatos = []

    # Prioridad: párrafos inmediatamente posteriores al título principal.
    if h1 is not None:
        for elemento in h1.find_all_next(["p", "div"], limit=30):
            texto = elemento.get_text(" ", strip=True)

            if not texto:
                continue

            normalizado = normalizar_texto(texto)

            if nombre and normalizado == normalizar_texto(nombre):
                continue

            if len(texto) < 50 or len(texto) > 1500:
                continue

            descartes = (
                "reservar", "precio", "desde ", "salidas",
                "duracion", "idioma", "incluye", "itinerario",
                "politica de cancelacion", "whatsapp",
            )

            if any(
                normalizado.startswith(valor)
                for valor in descartes
            ):
                continue

            candidatos.append(texto)

            if len(candidatos) >= 3:
                break

    # Segundo fallback: primeros párrafos sustanciales del contenido.
    if not candidatos:
        for p in principal.find_all("p"):
            texto = p.get_text(" ", strip=True)
            normalizado = normalizar_texto(texto)

            if len(texto) < 50 or len(texto) > 1500:
                continue

            if nombre and normalizado == normalizar_texto(nombre):
                continue

            if texto not in candidatos:
                candidatos.append(texto)

            if len(candidatos) >= 3:
                break

    if not candidatos:
        return None, None

    descripcion_original = " ".join(candidatos).strip()
    descripcion_corta = candidatos[0].strip()

    if len(descripcion_corta) > 500:
        descripcion_corta = descripcion_corta[:497].rsplit(" ", 1)[0] + "..."

    return descripcion_original, descripcion_corta


def extraer_tour(
    url: str,
    nombre_operador: str | None = None,
) -> TourExtraido:
    # La ficha completa suele cargarse con JavaScript. Usar siempre
    # Playwright evita respuestas parciales que omiten itinerario,
    # incluidos, recomendaciones e imágenes.
    resumen_calendario = None

    try:
        html, resumen_calendario = (
            obtener_html_y_calendario_playwright(url)
        )
    except Exception as error_playwright:
        print(
            "Playwright no pudo cargar la ficha: "
            f"{error_playwright}. Usando HTML basico."
        )
        respuesta = get_seguro(
            url,
            headers=HEADERS,
            timeout=30,
        )
        respuesta.raise_for_status()
        html = respuesta.text

    # Validar el HTML final venga de Playwright o del fallback HTTP.
    # Esto evita guardar títulos como el dominio o fichas casi vacías
    # cuando la fuente responde con CAPTCHA, anti-bot o acceso denegado.
    validar_html_extraible(
        html,
        url,
    )

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

    if nombre:
        import unicodedata

        nombre_normalizado = unicodedata.normalize(
            "NFKD",
            nombre.strip().lower(),
        )
        nombre_normalizado = "".join(
            caracter
            for caracter in nombre_normalizado
            if not unicodedata.combining(caracter)
        )

        indicadores_no_encontrada = (
            "pagina no encontrada",
            "page not found",
            "404",
            "not found",
        )

        if any(
            indicador in nombre_normalizado
            for indicador in indicadores_no_encontrada
        ):
            raise ValueError(
                f"La URL no corresponde a una actividad valida: {nombre}"
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

    if not descripcion or not descripcion_corta:
        descripcion_fallback, descripcion_corta_fallback = (
            extraer_descripcion_fallback(
                soup,
                nombre,
            )
        )

        if not descripcion:
            descripcion = descripcion_fallback

        if not descripcion_corta:
            descripcion_corta = descripcion_corta_fallback

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
        extraer_duracion(
            texto_pagina,
            soup,
        )
    )

    edad_minima, edad_maxima = (
        extraer_edades(texto_pagina)
    )

    secciones = extraer_secciones(soup)

    ubicacion_extraida = extraer_ubicacion(
        entidad,
        datos_json_ld,
        soup,
        url,
    )

    highlights_extraidos = extraer_highlights(
        soup
    )

    horarios_salidas = extraer_horarios_salidas(
        soup
    )

    restricciones_finales = list(
        dict.fromkeys(
            (secciones["restricciones"] or [])
            + extraer_restricciones_contextuales(soup)
        )
    )

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
                ubicacion=ubicacion_extraida,
        destino=extraer_destino(
            nombre,
            ubicacion_extraida,
            soup,
        ),
        highlights=highlights_extraidos,
duracion_original=duracion_original,
        duracion_minutos=duracion_minutos,
        edad_minima=edad_minima,
        edad_maxima=edad_maxima,
        idiomas=extraer_idiomas(
            texto_pagina,
            soup,
            secciones,
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
        restricciones=restricciones_finales,
        informacion_importante=secciones[
            "informacion_importante"
        ],
        politica_cancelacion=secciones[
            "politica_cancelacion"
        ],
        contacto=extraer_contacto(soup),
        calendario=Calendario(
            **(
                lambda calendario_base, calendario_dinamico: {
                    **calendario_base,
                    **calendario_dinamico,
                    "horarios": list(
                        dict.fromkeys(
                            (
                                calendario_dinamico.get(
                                    "horarios",
                                    [],
                                )
                                or calendario_base.get(
                                    "horarios",
                                    [],
                                )
                            )
                            + horarios_salidas
                        )
                    ),
                }
            )(
                extraer_calendario(
                    soup
                ).model_dump(),
                (
                    resumen_calendario
                    if resumen_calendario is not None
                    else {}
                ),
            )
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

