"""Obtención de la ubicación del usuario: por dirección escrita (preciso) o por su conexión a internet (aproximado).

Un equipo de escritorio normalmente no tiene GPS. La interfaz debe pedir permiso antes de usar la
ubicación por IP, porque implica enviar la dirección IP del usuario a un servicio externo.
"""

from dataclasses import dataclass

import requests
from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

from app.geo.centros import USER_AGENT, ErrorGeo

URL_IP = "https://ipapi.co/json/"


@dataclass
class Ubicacion:
    """Coordenadas del usuario, una descripción legible y qué tan precisa es."""

    latitud: float
    longitud: float
    descripcion: str
    precision: str  # "direccion" (precisa) o "ip" (aproximada, a nivel de ciudad).


def desde_direccion(direccion: str) -> Ubicacion:
    """Convierte una dirección o colonia escrita por el usuario en coordenadas con Nominatim (OpenStreetMap)."""
    try:
        geocodificador = Nominatim(user_agent=USER_AGENT, timeout=15)
        resultado = geocodificador.geocode(direccion, language="es")
    except GeopyError as error:
        raise ErrorGeo(f"No se pudo buscar la dirección: {error}") from error
    if resultado is None:
        raise ErrorGeo("No se encontró esa dirección. Prueba añadiendo la ciudad y el estado.")
    return Ubicacion(resultado.latitude, resultado.longitude, resultado.address, "direccion")


def desde_ip() -> Ubicacion:
    """Estima la ubicación a partir de la conexión a internet; su precisión suele ser de la ciudad."""
    try:
        respuesta = requests.get(URL_IP, headers={"User-Agent": USER_AGENT}, timeout=10)
        respuesta.raise_for_status()
        datos = respuesta.json()
        lugar = ", ".join(p for p in (datos.get("city"), datos.get("region"), datos.get("country_name")) if p)
        return Ubicacion(float(datos["latitude"]), float(datos["longitude"]), lugar or "Ubicación aproximada", "ip")
    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        raise ErrorGeo(f"No se pudo estimar la ubicación por la conexión: {error}") from error
