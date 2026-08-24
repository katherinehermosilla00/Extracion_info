import re
import unicodedata
from difflib import SequenceMatcher


PALABRAS_VACIAS = {
    "a", "al", "and", "con", "da", "das", "de", "del", "do", "dos",
    "el", "en", "for", "la", "las", "los", "of", "o", "para", "por",
    "the", "un", "una", "y",
}


GRUPOS_SINONIMOS = {
    "aves": {
        "ave", "aves", "avistaje de aves", "avistamiento de aves", "bird",
        "birding", "birds", "birdwatching", "observacao de aves",
        "observacion de aves", "ornitologia", "pajareo",
    },
    "ballenas": {
        "avistaje de ballenas", "avistamiento de ballenas", "baleia",
        "baleias", "ballena", "ballenas", "cetaceo", "cetaceos",
        "observacao de baleias", "safari marino", "whale", "whales",
        "whale watching",
    },
    "delfines": {
        "avistamiento de delfines", "delfin", "delfines", "dolphin",
        "dolphins", "golfinho", "golfinhos",
    },
    "senderismo": {
        "caminata", "caminhada", "excursionismo", "hiking", "senderismo",
        "trekking", "trilha",
    },
    "cabalgata": {
        "cabalgata", "cabalgatas", "cavalgada", "horseback riding",
        "paseo a caballo", "ruta ecuestre",
    },
    "kayak": {
        "canoa", "canoagem", "canotaje", "kayak", "kayaking", "remo",
    },
    "rafting": {
        "balsismo", "descenso de rio", "rafting", "rapidos",
        "white water rafting",
    },
    "buceo": {
        "buceo", "mergulho", "scuba", "scuba diving", "submarinismo",
    },
    "snorkel": {
        "careteo", "esnorquel", "snorkel", "snorkeling",
    },
    "navegacion": {
        "barco", "boat trip", "boat tour", "embarcacion", "navegacao",
        "navegacion", "paseo de barco", "passeio de barco",
    },
    "ciudad": {
        "city tour", "paseo por la ciudad", "recorrido urbano",
        "sightseeing", "visita panoramica",
    },
    "ciclismo": {
        "bike tour", "bicicleta", "ciclismo", "cicloturismo", "cycling",
    },
    "canopy": {
        "arborismo", "canopy", "tirolesa", "tirolina", "zip line", "zipline",
    },
    "gastronomia": {
        "culinaria", "experiencia culinaria", "food tour", "gastronomia",
        "ruta gastronomica", "tour culinario",
    },
    "vino": {
        "degustacion", "enoturismo", "ruta del vino", "vinhedo", "vino",
        "vinedo", "wine tour", "winery",
    },
    "pesca": {
        "angling", "fishing", "pesca", "pesca deportiva", "pesca recreativa",
    },
    "cascada": {
        "cachoeira", "cascada", "salto de agua", "waterfall",
    },
    "traslado": {
        "pick up", "pickup", "recogida", "recojo", "transfer", "traslado",
        "transporte",
    },
}


def normalizar_texto(texto: str | None) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    texto = texto.lower().replace("-", " ").replace("_", " ")
    return re.sub(r"[^a-z0-9\s]", " ", texto)


SINONIMO_A_CANONICO = {
    normalizar_texto(sinonimo): canonico
    for canonico, sinonimos in GRUPOS_SINONIMOS.items()
    for sinonimo in sinonimos | {canonico}
}


def expandir_conceptos(texto: str) -> tuple[str, set[str]]:
    normalizado = normalizar_texto(texto)
    conceptos = set()
    for sinonimo, canonico in sorted(
        SINONIMO_A_CANONICO.items(), key=lambda elemento: len(elemento[0]), reverse=True
    ):
        if re.search(rf"\b{re.escape(sinonimo)}\b", normalizado):
            conceptos.add(canonico)
    ampliado = f"{normalizado} {' '.join(sorted(conceptos))}".strip()
    return ampliado, conceptos


def palabras_significativas(texto: str) -> set[str]:
    return {
        palabra for palabra in normalizar_texto(texto).split()
        if len(palabra) > 1 and palabra not in PALABRAS_VACIAS
    }


def calcular_coincidencia(pedido: str, titulo: str) -> dict:
    pedido_ampliado, conceptos_pedido = expandir_conceptos(pedido)
    titulo_ampliado, conceptos_titulo = expandir_conceptos(titulo)

    palabras_pedido = palabras_significativas(pedido_ampliado)
    palabras_titulo = palabras_significativas(titulo_ampliado)
    coincidentes = palabras_pedido & palabras_titulo

    cobertura = (
        len(coincidentes) / len(palabras_pedido) * 100
        if palabras_pedido else 0
    )
    similitud = SequenceMatcher(None, pedido_ampliado, titulo_ampliado).ratio() * 100
    bono_conceptos = 25 if conceptos_pedido & conceptos_titulo else 0
    puntaje = min(100, cobertura * 0.65 + similitud * 0.35 + bono_conceptos)

    if puntaje >= 75:
        nivel = "alta"
    elif puntaje >= 45:
        nivel = "media"
    else:
        nivel = "baja"

    return {
        "puntaje": round(puntaje, 2),
        "nivel": nivel,
        "palabras_buscadas": sorted(palabras_significativas(pedido)),
        "palabras_coincidentes": sorted(coincidentes),
    }
