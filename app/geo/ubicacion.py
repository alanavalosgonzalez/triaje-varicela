"""Obtención de la ubicación del usuario: con el servicio de ubicación de Windows o por dirección escrita.

Un equipo de escritorio normalmente no tiene GPS; Windows estima la posición con las redes WiFi cercanas.
Si ninguna opción sirve, el usuario puede elegir el punto haciendo clic en el mapa (app/ui/pagina_mapa.py).
"""

from dataclasses import dataclass

from geopy.exc import GeopyError
from geopy.geocoders import Nominatim

from app.geo.centros import USER_AGENT, ErrorGeo

@dataclass
class Ubicacion:
    """Coordenadas del usuario, una descripción legible y qué tan precisa es."""

    latitud: float
    longitud: float
    descripcion: str
    precision: str  # "windows", "direccion" o "mapa" (punto elegido con un clic).


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


# Script de PowerShell que lee el servicio de ubicación de Windows (WiFi o GPS) e imprime "latitud;longitud;precisión".
SCRIPT_UBICACION_WINDOWS = r"""
Add-Type -AssemblyName System.Device
$w = New-Object System.Device.Location.GeoCoordinateWatcher([System.Device.Location.GeoPositionAccuracy]::High)
$null = $w.TryStart($false, [TimeSpan]::FromSeconds(10))
$i = 0
while ($w.Position.Location.IsUnknown -and $i -lt 30) { Start-Sleep -Milliseconds 500; $i++ }
$l = $w.Position.Location
if ($w.Permission -ne 'Granted') { 'SIN_PERMISO' } elseif ($l.IsUnknown) { 'SIN_POSICION' }
else { '{0};{1};{2}' -f $l.Latitude.ToString([cultureinfo]::InvariantCulture), $l.Longitude.ToString([cultureinfo]::InvariantCulture), [int]$l.HorizontalAccuracy }
$w.Stop()
"""


def desde_windows() -> Ubicacion:
    """Obtiene la ubicación precisa del servicio de ubicación de Windows; las coordenadas no salen del equipo en este paso."""
    import subprocess

    try:
        proceso = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", SCRIPT_UBICACION_WINDOWS],
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),  # Evita que aparezca una ventana de consola.
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ErrorGeo(f"No se pudo consultar la ubicación de Windows: {error}") from error
    salida = proceso.stdout.strip().splitlines()[-1] if proceso.stdout.strip() else ""
    if salida == "SIN_PERMISO":
        raise ErrorGeo("Windows no permite el acceso a la ubicación. Actívalo en Configuración > Privacidad y seguridad > "
                       "Ubicación (incluida la opción para aplicaciones de escritorio).")
    if salida in ("SIN_POSICION", "") or salida.count(";") != 2:
        raise ErrorGeo("Windows no pudo determinar tu ubicación. Verifica que el WiFi esté encendido o escribe tu dirección.")
    latitud, longitud, precision = salida.split(";")
    return Ubicacion(float(latitud), float(longitud), f"Ubicación del equipo (precisión aproximada: {precision} m)", "windows")
