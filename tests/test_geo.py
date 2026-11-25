"""Pruebas del módulo de geolocalización sin conexión: distancias, lectura de Overpass y generación del mapa.

Ejecutar desde la raíz del proyecto: python -m unittest -v
"""

import unittest

from app.geo.centros import construir_consulta, distancia_km, interpretar_respuesta
from app.geo.mapa import mapa_html
from app.geo.ubicacion import Ubicacion

# Punto de referencia público para las pruebas: el Zócalo de la Ciudad de México.
LAT, LON = 19.4326, -99.1332

# Respuesta de ejemplo con la forma que devuelve Overpass (un nodo, un área y elementos a descartar).
RESPUESTA_OVERPASS = {
    "elements": [
        {"type": "way", "center": {"lat": 19.4500, "lon": -99.1332},
         "tags": {"amenity": "hospital", "name": "Hospital Lejano", "emergency": "yes", "phone": "+52 55 1234 5678"}},
        {"type": "node", "lat": 19.4330, "lon": -99.1335,
         "tags": {"amenity": "doctors", "name": "Consultorio <Cercano>", "addr:street": "Madero", "addr:housenumber": "10"}},
        {"type": "node", "lat": 19.4340, "lon": -99.1340, "tags": {"amenity": "clinic"}},        # Sin nombre.
        {"type": "node", "lat": 19.4340, "lon": -99.1340, "tags": {"amenity": "pharmacy", "name": "Farmacia"}},
    ]
}


class PruebasCentros(unittest.TestCase):
    """Comprueba el cálculo de distancias y la interpretación de la respuesta de Overpass."""

    def test_distancia_conocida(self):
        """Del Zócalo al Ángel de la Independencia hay unos 3.7 km en línea recta."""
        self.assertAlmostEqual(distancia_km(LAT, LON, 19.4270, -99.1677), 3.67, delta=0.3)

    def test_distancia_cero(self):
        """La distancia de un punto a sí mismo es cero."""
        self.assertEqual(distancia_km(LAT, LON, LAT, LON), 0)

    def test_consulta_incluye_tipos_y_radio(self):
        """La consulta pide hospitales, clínicas y consultorios en el radio indicado."""
        consulta = construir_consulta(LAT, LON, 5000)
        self.assertIn("hospital|clinic|doctors", consulta)
        self.assertIn(f"around:5000,{LAT},{LON}", consulta)

    def test_interpretar_respuesta(self):
        """Se descartan farmacias y centros sin nombre, y se ordena por cercanía."""
        centros = interpretar_respuesta(RESPUESTA_OVERPASS, LAT, LON)
        self.assertEqual([c.nombre for c in centros], ["Consultorio <Cercano>", "Hospital Lejano"])
        self.assertEqual(centros[0].direccion, "Madero 10")
        self.assertTrue(centros[1].urgencias)
        self.assertEqual(centros[1].telefono, "+52 55 1234 5678")


class PruebasMapa(unittest.TestCase):
    """Comprueba que el mapa contiene los marcadores y que el texto externo se escapa."""

    def test_mapa_con_marcadores(self):
        """El HTML incluye a los centros y escapa los caracteres especiales de sus nombres."""
        centros = interpretar_respuesta(RESPUESTA_OVERPASS, LAT, LON)
        html = mapa_html(Ubicacion(LAT, LON, "Zócalo", "direccion"), centros)
        self.assertIn("Hospital Lejano", html)
        self.assertIn("&lt;Cercano&gt;", html)
        self.assertNotIn("<Cercano>", html)
        self.assertIn("Tu ubicación", html)


class PruebasClicEnMapa(unittest.TestCase):
    """Comprueba el mensaje que el mapa envía a la app al hacer clic."""

    def test_interpretar_clic_valido(self):
        """Un mensaje con el prefijo y coordenadas válidas se convierte en (latitud, longitud)."""
        from app.geo.mapa import PREFIJO_CLIC, interpretar_clic

        self.assertEqual(interpretar_clic(f"{PREFIJO_CLIC}19.432600,-99.133200"), (19.4326, -99.1332))

    def test_ignora_otros_mensajes(self):
        """Mensajes ajenos, mal formados o con coordenadas imposibles se ignoran."""
        from app.geo.mapa import PREFIJO_CLIC, interpretar_clic

        self.assertIsNone(interpretar_clic("otro mensaje de la consola"))
        self.assertIsNone(interpretar_clic(f"{PREFIJO_CLIC}abc,def"))
        self.assertIsNone(interpretar_clic(f"{PREFIJO_CLIC}95,10"))

    def test_mapas_avisan_los_clics(self):
        """Tanto el mapa para elegir como el de resultados incluyen el código que avisa de los clics."""
        from app.geo.mapa import PREFIJO_CLIC, mapa_seleccion_html

        self.assertIn(PREFIJO_CLIC, mapa_seleccion_html())
        centros = interpretar_respuesta(RESPUESTA_OVERPASS, LAT, LON)
        self.assertIn(PREFIJO_CLIC, mapa_html(Ubicacion(LAT, LON, "Zócalo", "direccion"), centros))


if __name__ == "__main__":
    unittest.main()
