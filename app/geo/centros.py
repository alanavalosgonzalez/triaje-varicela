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
            # Tiempo límite corto: un servidor saturado no debe dejar al usuario esperando más de unos segundos.
            respuesta = requests.post(servidor, data={"data": consulta}, headers={"User-Agent": USER_AGENT}, timeout=10)
            respuesta.raise_for_status()
            return respuesta.json()
        except (requests.RequestException, ValueError) as error:
            errores.append(f"{servidor.split('/')[2]}: {error}")
    raise ErrorGeo("No se pudo consultar OpenStreetMap (todos los servidores fallaron):\n" + "\n".join(errores))


URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"


def interpretar_nominatim(resultados: list[dict], lat: float, lon: float) -> list[CentroSalud]:
    """Convierte los resultados de Nominatim en centros de salud (mismo formato que los de Overpass)."""
    centros = []
    for r in resultados:
        tipo = r.get("type")
        if r.get("category") != "amenity" or tipo not in TIPOS or not r.get("name"):
            continue
        extra, dir_ = r.get("extratags") or {}, r.get("address") or {}
        etiquetas_dir = {  # Se adaptan a los nombres addr:* para reutilizar _direccion().
            "addr:street": dir_.get("road"), "addr:housenumber": dir_.get("house_number"),
            "addr:suburb": dir_.get("suburb") or dir_.get("neighbourhood"),
            "addr:city": dir_.get("city") or dir_.get("town") or dir_.get("village"),
        }
        lat_c, lon_c = float(r["lat"]), float(r["lon"])
        centros.append(CentroSalud(
            nombre=r["name"], tipo=TIPOS[tipo], latitud=lat_c, longitud=lon_c,
            distancia_km=round(distancia_km(lat, lon, lat_c, lon_c), 2),
            telefono=extra.get("phone") or extra.get("contact:phone"),
            direccion=_direccion({k: v for k, v in etiquetas_dir.items() if v}),
            urgencias=extra.get("emergency") == "yes",
        ))
    return centros


def buscar_nominatim(lat: float, lon: float, radio_m: int) -> list[CentroSalud]:
    """Busca cada tipo de centro con Nominatim dentro de un recuadro alrededor del punto (una petición por segundo)."""
    import time

    grados = radio_m / 111_000  # Aproximación: un grado de latitud mide unos 111 km.
    recuadro = f"{lon - grados},{lat + grados},{lon + grados},{lat - grados}"
    encontrados: dict[tuple, CentroSalud] = {}
    for indice, tipo in enumerate(TIPOS):
        if indice:
            time.sleep(1.0)  # Política de uso de Nominatim: máximo una petición por segundo.
        respuesta = requests.get(URL_NOMINATIM, headers={"User-Agent": USER_AGENT}, timeout=15, params={
            "q": f"[{tipo}]", "format": "jsonv2", "limit": 40, "bounded": 1, "viewbox": recuadro,
            "extratags": 1, "addressdetails": 1,
        })
        respuesta.raise_for_status()
        for centro in interpretar_nominatim(respuesta.json(), lat, lon):
            encontrados[(centro.nombre, round(centro.latitud, 4))] = centro  # Evita duplicados entre búsquedas.
    return sorted(encontrados.values(), key=lambda c: c.distancia_km)


def buscar_centros(lat: float, lon: float, radio_m: int = 3000, maximo: int = 20) -> list[CentroSalud]:
    """Busca centros de salud cercanos: primero con Nominatim (rápido) y, si falla, con Overpass (respaldo).

    Empieza con un radio pequeño para obtener los más cercanos y lo amplía si encuentra pocos.
    """
    errores = []
    for radio in (radio_m, radio_m * 3, radio_m * 8):
        try:
            centros = buscar_nominatim(lat, lon, radio)
        except (requests.RequestException, ValueError) as error:
            errores.append(f"Nominatim: {error}")
            break
        if len(centros) >= 5 or radio == radio_m * 8:
            return centros[:maximo]
    # Respaldo: Overpass, que tiene datos más completos pero sus servidores públicos a menudo están saturados.
    try:
        return interpretar_respuesta(consultar_overpass(construir_consulta(lat, lon, radio_m * 3)), lat, lon)[:maximo]
    except ErrorGeo as error:
        errores.append(str(error))
    raise ErrorGeo("No se pudo consultar OpenStreetMap:\n" + "\n".join(errores))
