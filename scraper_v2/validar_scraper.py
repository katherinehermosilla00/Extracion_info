from bs4 import BeautifulSoup

from matcher import calcular_coincidencia
from scraper import (
    extraer_itinerario,
    extraer_secciones,
    extraer_ubicacion,
)


HTML_PRUEBA = """
<html><main>
  <h2>Wildlife &amp; Birds</h2>
  <ul>
    <li>DAY 1 Welcome and orientation</li>
    <li>DAY 2 Forest birds</li>
    <li>DAY 3 Pacific coastal birds</li>
    <li>DAY 4 Inland sea birds</li>
  </ul>
  <h2>INCLUDES:</h2>
  <h3>Park Entrance</h3>
  <h3>Transportation</h3>
  <h3>Accommodation</h3>
  <h3>Meals and beverages</h3>
  <h3>Guide</h3>
  <h3>Birdwatching activities</h3>
  <h3>Equipment</h3>
  <h2>Photography</h2>
  <h2>What to bring</h2>
  <ul><li>Water</li><li>Comfortable shoes</li></ul>
  <h2>Not allowed</h2>
  <ul><li>Alcohol</li></ul>
  <footer>
    <div class="location">
      Información News Tienda Contáctanos Isla Grande Chiloé
      Región de Los Lagos - Chile reservas@example.com
    </div>
  </footer>
</main></html>
"""


def validar() -> None:
    soup = BeautifulSoup(HTML_PRUEBA, "html.parser")
    secciones = extraer_secciones(soup)
    itinerario = extraer_itinerario(soup)
    ubicacion = extraer_ubicacion({}, [], soup)

    assert secciones["incluye"] == [
        "Park Entrance",
        "Transportation",
        "Accommodation",
        "Meals and beverages",
        "Guide",
        "Birdwatching activities",
        "Equipment",
    ]
    assert secciones["que_llevar"] == [
        "Water",
        "Comfortable shoes",
    ]
    assert secciones["no_llevar"] == ["Alcohol"]
    assert [paso.orden for paso in itinerario] == [1, 2, 3, 4]
    assert ubicacion.pais == "Chile"
    assert ubicacion.region == "Región de Los Lagos"
    assert ubicacion.ciudad == "Chiloé"
    assert ubicacion.direccion is None

    casos = (
        (
            "observación de aves en Chiloé",
            "Birds of Chiloé: Birdwatching",
            75,
        ),
        (
            "tour para ver ballenas",
            "Avistaje de cetáceos",
            45,
        ),
        (
            "caminata en montaña",
            "Trilha e trekking na montanha",
            45,
        ),
    )

    for pedido, titulo, minimo in casos:
        resultado = calcular_coincidencia(pedido, titulo)
        assert resultado["puntaje"] >= minimo

    print("OK: todas las validaciones locales pasaron.")


if __name__ == "__main__":
    validar()
