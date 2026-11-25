"""Generación del mapa interactivo con Folium (OpenStreetMap) para mostrarlo dentro de la aplicación."""

from html import escape

import folium

from app.geo.centros import CentroSalud
from app.geo.ubicacion import Ubicacion

# Colores de los marcadores: rojo para urgencias, azul clínico para el resto.
COLOR_URGENCIAS = "red"
COLOR_CENTRO = "darkblue"


def _ventana(centro: CentroSalud) -> str:
    """HTML de la ventana emergente de un centro; se escapa el texto porque proviene de OpenStreetMap."""
    lineas = [f"<b>{escape(centro.nombre)}</b>", escape(centro.tipo), f"{centro.distancia_km:.1f} km"]
    if centro.urgencias:
        lineas.append("<b>Atiende urgencias</b>")
    if centro.direccion:
        lineas.append(escape(centro.direccion))
    if centro.telefono:
        telefono = escape(centro.telefono)
        lineas.append(f'Tel.: <a href="tel:{telefono}">{telefono}</a>')
    return "<br>".join(lineas)


def generar_mapa(ubicacion: Ubicacion, centros: list[CentroSalud]) -> folium.Map:
    """Crea el mapa con la ubicación del usuario y un marcador por centro, ajustando el encuadre a todos."""
    mapa = folium.Map(location=[ubicacion.latitud, ubicacion.longitud], zoom_start=14, tiles="OpenStreetMap")
    folium.Marker(
        [ubicacion.latitud, ubicacion.longitud],
        tooltip="Tu ubicación" + (" (aproximada)" if ubicacion.precision == "ip" else ""),
        icon=folium.Icon(color="green", icon="user", prefix="fa"),
    ).add_to(mapa)
    for centro in centros:
        folium.Marker(
            [centro.latitud, centro.longitud],
            # El nombre viene de OpenStreetMap (editable por cualquiera), así que se escapa también aquí.
            tooltip=f"{escape(centro.nombre)} ({centro.distancia_km:.1f} km)",
            popup=folium.Popup(_ventana(centro), max_width=280),
            icon=folium.Icon(color=COLOR_URGENCIAS if centro.urgencias else COLOR_CENTRO, icon="plus-square", prefix="fa"),
        ).add_to(mapa)
    if centros:
        puntos = [[ubicacion.latitud, ubicacion.longitud]] + [[c.latitud, c.longitud] for c in centros]
        mapa.fit_bounds(puntos, padding=(30, 30))
    return mapa


def mapa_html(ubicacion: Ubicacion, centros: list[CentroSalud]) -> str:
    """Devuelve el mapa como una página HTML completa, lista para cargarla en el visor web de PySide6."""
    return generar_mapa(ubicacion, centros).get_root().render()
