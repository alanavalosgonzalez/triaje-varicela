"""Búsqueda de hospitales, clínicas y consultorios cercanos en OpenStreetMap mediante la API de Overpass."""

import math
from dataclasses import dataclass

import requests

# Servidores públicos de Overpass; si uno está saturado (error 429/502/504) se prueba el siguiente.
SERVIDORES_OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Identificador genérico de la aplicación; los servicios de OSM piden un User-Agent descriptivo.
USER_AGENT = "TriajeVaricela/0.1 (aplicacion educativa)"

# Traducción de las etiquetas de OpenStreetMap a texto para el usuario.
TIPOS = {
    "hospital": "Hospital",
    "clinic": "Clínica",
    "doctors": "Consultorio médico",
}


class ErrorGeo(RuntimeError):
    """Error de red o de respuesta al buscar ubicaciones o centros de salud."""


@dataclass
class CentroSalud:
    """Un centro de salud con los datos que se muestran en la lista y en el mapa."""

    nombre: str
    tipo: str
    latitud: float
    longitud: float
    distancia_km: float
    telefono: str | None = None
    direccion: str | None = None
    urgencias: bool = False


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta entre dos puntos de la Tierra (fórmula de haversine)."""
    radio_tierra = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radio_tierra * math.asin(math.sqrt(a))


def construir_consulta(lat: float, lon: float, radio_m: int) -> str:
    """Arma la consulta en lenguaje Overpass QL para los tipos de centro de salud dentro del radio."""
    filtro = "|".join(TIPOS)
    return (
        "[out:json][timeout:25];\n"
        "(\n"
        f'  nwr["amenity"~"^({filtro})$"](around:{radio_m},{lat},{lon});\n'
        ");\n"
        "out center tags;"
    )


def _direccion(etiquetas: dict) -> str | None:
    """Arma una dirección legible con las etiquetas addr:* disponibles."""
    partes = [
        " ".join(p for p in (etiquetas.get("addr:street"), etiquetas.get("addr:housenumber")) if p),
        etiquetas.get("addr:suburb") or etiquetas.get("addr:neighbourhood"),
        etiquetas.get("addr:city"),
    ]
    texto = ", ".join(p for p in partes if p)
    return texto or None


def interpretar_respuesta(datos: dict, lat: float, lon: float) -> list[CentroSalud]:
    """Convierte la respuesta JSON de Overpass en centros ordenados del más cercano al más lejano."""
    centros = []
    for elemento in datos.get("elements", []):
        etiquetas = elemento.get("tags", {})
        # Los nodos traen lat/lon; las áreas y relaciones traen su punto central en "center".
        punto = elemento if "lat" in elemento else elemento.get("center")
        if not punto or etiquetas.get("amenity") not in TIPOS:
            continue
        nombre = etiquetas.get("name") or etiquetas.get("operator")
        if not nombre:
            continue  # Un centro sin nombre no ayuda al usuario a encontrarlo.
        centros.append(CentroSalud(
            nombre=nombre,
            tipo=TIPOS[etiquetas["amenity"]],
            latitud=punto["lat"],
            longitud=punto["lon"],
            distancia_km=round(distancia_km(lat, lon, punto["lat"], punto["lon"]), 2),
            telefono=etiquetas.get("phone") or etiquetas.get("contact:phone"),
            direccion=_direccion(etiquetas),
            urgencias=etiquetas.get("emergency") == "yes",
        ))
    centros.sort(key=lambda c: c.distancia_km)
    return centros


def consultar_overpass(consulta: str) -> dict:
    """Envía la consulta a los servidores de Overpass en orden hasta que uno responda correctamente."""
    errores = []
    for servidor in SERVIDORES_OVERPASS:
        try:
            respuesta = requests.post(servidor, data={"data": consulta}, headers={"User-Agent": USER_AGENT}, timeout=30)
            respuesta.raise_for_status()
            return respuesta.json()
        except (requests.RequestException, ValueError) as error:
            errores.append(f"{servidor.split('/')[2]}: {error}")
    raise ErrorGeo("No se pudo consultar OpenStreetMap (todos los servidores fallaron):\n" + "\n".join(errores))


def buscar_centros(lat: float, lon: float, radio_m: int = 5000, maximo: int = 20) -> list[CentroSalud]:
    """Consulta Overpass y devuelve los centros de salud más cercanos; amplía el radio si no encuentra ninguno."""
    for radio in (radio_m, radio_m * 3):
        centros = interpretar_respuesta(consultar_overpass(construir_consulta(lat, lon, radio)), lat, lon)
        if centros:
            return centros[:maximo]
    return []
