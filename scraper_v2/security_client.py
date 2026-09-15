from urllib.parse import urljoin

import requests


BACKEND_URL = "http://localhost:8080"

REDIRECT_CODES = {
    301,
    302,
    303,
    307,
    308,
}


def validar_url_segura(url: str) -> dict:
    """
    Consulta al backend Spring Boot antes de permitir
    que el scraper navegue hacia una URL.
    """

    try:
        respuesta = requests.get(
            f"{BACKEND_URL}/api/security/validate",
            params={"url": url},
            timeout=10,
        )
    except requests.RequestException as error:
        raise RuntimeError(
            f"No se pudo consultar la validación de seguridad: {error}"
        ) from error

    try:
        resultado = respuesta.json()
    except ValueError as error:
        raise RuntimeError(
            "El backend de seguridad devolvió una respuesta inválida."
        ) from error

    if not respuesta.ok or not resultado.get("valid", False):
        mensaje = resultado.get(
            "message",
            "URL rechazada por seguridad",
        )

        raise ValueError(
            f"URL bloqueada: {mensaje}"
        )

    return resultado


def get_seguro(
    url: str,
    *,
    headers: dict | None = None,
    timeout: int = 30,
    max_redirecciones: int = 5,
) -> requests.Response:
    """
    Realiza un GET validando la URL inicial y cada redirección.
    """

    url_actual = url

    for _ in range(max_redirecciones + 1):

        validar_url_segura(url_actual)

        respuesta = requests.get(
            url_actual,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
        )

        if respuesta.status_code not in REDIRECT_CODES:
            return respuesta

        location = respuesta.headers.get("Location")

        if not location:
            return respuesta

        url_siguiente = urljoin(
            url_actual,
            location,
        )

        validar_url_segura(url_siguiente)

        url_actual = url_siguiente

    raise RuntimeError(
        "Se excedió el máximo permitido de redirecciones."
    )
