"""Generación del mapa interactivo con Folium (OpenStreetMap) para mostrarlo dentro de la aplicación.

Los mapas avisan a la aplicación cuando el usuario hace clic: escriben en la consola del navegador un mensaje
con el prefijo PREFIJO_CLIC y las coordenadas, y la página de Qt lo intercepta (ver app/ui/pagina_mapa.py).
"""

from html import escape

import folium

from app.geo.centros import CentroSalud
from app.geo.ubicacion import Ubicacion

# Colores de los marcadores: rojo para urgencias, azul clínico para el resto.
COLOR_URGENCIAS = "red"
COLOR_CENTRO = "darkblue"

# Prefijo del mensaje que el mapa envía al hacer clic; la app solo reacciona a mensajes con este prefijo.
PREFIJO_CLIC = "TRIAJE_UBICACION_ELEGIDA:"

# Vista inicial para elegir un punto cuando aún no hay ubicación: la República Mexicana completa.
CENTRO_MEXICO = (23.6, -102.5)


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


def _avisar_clics(mapa: folium.Map) -> None:
    """Agrega el código que, al hacer clic en el mapa, envía las coordenadas a la aplicación."""
    nombre = mapa.get_name()
    # Se espera al evento "load": Folium escribe este código antes de crear el mapa en la página.
    codigo = (
        "window.addEventListener('load', function () {"
        f"  {nombre}.on('click', function (e) {{"
        f"    console.log('{PREFIJO_CLIC}' + e.latlng.lat.toFixed(6) + ',' + e.latlng.lng.toFixed(6));"
        "  });"
        f"  {nombre}.getContainer().style.cursor = 'crosshair';"
        "});"
    )
    mapa.get_root().script.add_child(folium.Element(codigo))


def interpretar_clic(mensaje: str) -> tuple[float, float] | None:
    """Extrae (latitud, longitud) de un mensaje de clic del mapa; None si el mensaje no es de clic o es inválido."""
    if not mensaje.startswith(PREFIJO_CLIC):
        return None
    try:
        latitud, longitud = (float(v) for v in mensaje[len(PREFIJO_CLIC):].split(","))
    except ValueError:
        return None
    if not (-90 <= latitud <= 90 and -180 <= longitud <= 180):
        return None
    return latitud, longitud


def generar_mapa(ubicacion: Ubicacion, centros: list[CentroSalud]) -> folium.Map:
    """Crea el mapa con la ubicación del usuario y un marcador por centro, ajustando el encuadre a todos."""
    mapa = folium.Map(location=[ubicacion.latitud, ubicacion.longitud], zoom_start=14, tiles="OpenStreetMap")
    folium.Marker(
        [ubicacion.latitud, ubicacion.longitud],
        tooltip="Punto de búsqueda" if ubicacion.precision == "mapa" else "Tu ubicación",
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
    _avisar_clics(mapa)  # También aquí: un clic busca de nuevo desde otro punto.
    return mapa


def mapa_html(ubicacion: Ubicacion, centros: list[CentroSalud]) -> str:
    """Devuelve el mapa como una página HTML completa, lista para cargarla en el visor web de PySide6."""
    return generar_mapa(ubicacion, centros).get_root().render()


def mapa_seleccion_html(centro: tuple[float, float] | None = None) -> str:
    """Mapa vacío para que el usuario haga clic donde está; se centra en su última ubicación o en México."""
    lat, lon = centro or CENTRO_MEXICO
    mapa = folium.Map(location=[lat, lon], zoom_start=14 if centro else 5, tiles="OpenStreetMap")
    _avisar_clics(mapa)
    return mapa.get_root().render()
