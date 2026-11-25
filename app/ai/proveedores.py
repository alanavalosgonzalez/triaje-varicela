"""Proveedores de modelo de lenguaje. El asistente solo conoce la interfaz ProveedorLLM, así se puede cambiar de proveedor."""

import os
import time
from dataclasses import dataclass
from typing import Protocol

from app import config  # noqa: F401  Importarlo carga las variables del archivo .env.

# Modelo por defecto; se puede cambiar en .env con GEMINI_MODELO sin tocar el código.
MODELO_GEMINI_POR_DEFECTO = "gemini-3.8-flash"

# Modelos de respaldo (separados por comas en GEMINI_MODELOS_RESPALDO) para cuando el principal está saturado.
# Los modelos "lite" son más ligeros, responden en pocos segundos y suelen tener menos demanda.
MODELOS_RESPALDO_POR_DEFECTO = "gemini-3.5-flash-lite,gemini-3.5-flash"

# Errores temporales de la API: límite de uso, error interno, saturación y tiempo agotado en el servidor.
CODIGOS_TEMPORALES = {429, 500, 503, 504}

# Tiempo máximo de espera por intento. Un modelo saturado puede aceptar la petición y tardar minutos en responder.
TIEMPO_LIMITE_SEGUNDOS = 20

# Intentos por modelo antes de pasar al siguiente, y espera entre ellos (el cambio de modelo ya es un reintento).
INTENTOS_POR_MODELO = 2
ESPERA_REINTENTO = 1

# Tras fallar por saturación, el modelo se salta durante este tiempo para no hacer esperar al usuario en cada mensaje.
PAUSA_MODELO_SATURADO = 300

# Nivel de razonamiento previo a la respuesta: "LOW" basta para un chat de orientación y responde mucho más rápido.
NIVEL_RAZONAMIENTO = "LOW"


def es_error_temporal(error: Exception) -> bool:
    """Indica si vale la pena reintentar: códigos de saturación o tiempo de espera agotado en la conexión."""
    return getattr(error, "code", None) in CODIGOS_TEMPORALES or "timeout" in type(error).__name__.lower()


@dataclass
class Mensaje:
    """Un turno de la conversación; rol es "usuario" o "asistente"."""

    rol: str
    contenido: str


class ProveedorLLM(Protocol):
    """Interfaz común: recibe instrucciones de sistema e historial y devuelve el texto de la respuesta."""

    nombre_modelo: str

    def responder(self, instrucciones: str, historial: list[Mensaje]) -> str:
        """Genera la respuesta del asistente al último mensaje del historial."""
        ...


class ErrorProveedor(RuntimeError):
    """Error de configuración o de comunicación con el proveedor del modelo."""


class ProveedorGemini:
    """Proveedor basado en la API de Google Gemini (paquete google-genai), resistente a la saturación del servicio."""

    def __init__(self, api_key: str | None = None, modelo: str | None = None, temperatura: float = 0.3):
        """Crea el cliente con tiempo límite; la clave se lee de GEMINI_API_KEY si no se pasa explícitamente."""
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise ErrorProveedor("Falta el paquete google-genai: ejecuta pip install -r requirements.txt.") from error
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ErrorProveedor("No hay clave de Gemini: define GEMINI_API_KEY en el archivo .env.")
        self._types = types
        # El tiempo límite se indica en milisegundos; sin él, una petición en cola puede tardar varios minutos.
        self._cliente = genai.Client(api_key=api_key,
                                     http_options=types.HttpOptions(timeout=TIEMPO_LIMITE_SEGUNDOS * 1000))
        self.nombre_modelo = modelo or os.getenv("GEMINI_MODELO") or MODELO_GEMINI_POR_DEFECTO
        respaldo = os.getenv("GEMINI_MODELOS_RESPALDO", MODELOS_RESPALDO_POR_DEFECTO)
        self.modelos_respaldo = [m.strip() for m in respaldo.split(",") if m.strip() and m.strip() != self.nombre_modelo]
        self.modelo_usado = self.nombre_modelo  # Modelo que respondió el último mensaje (se guarda en la base).
        self._temperatura = temperatura  # Temperatura baja: respuestas más estables y prudentes.
        self._esperar = time.sleep  # Se puede sustituir en las pruebas para no esperar de verdad.
        self._reloj = time.monotonic
        self._pausados: dict[str, float] = {}  # Modelo -> momento hasta el que se salta por saturación.
        self._sin_razonamiento: set[str] = set()  # Modelos que no aceptan el nivel de razonamiento configurado.

    def _configuracion(self, instrucciones: str, modelo: str):
        """Configuración de la petición; el nivel de razonamiento se omite en los modelos que no lo admiten."""
        extra = {}
        if modelo not in self._sin_razonamiento:
            extra["thinking_config"] = self._types.ThinkingConfig(thinking_level=NIVEL_RAZONAMIENTO)
        return self._types.GenerateContentConfig(system_instruction=instrucciones, temperature=self._temperatura, **extra)

    def _orden_modelos(self) -> list[str]:
        """Modelos en orden de preferencia, dejando al final los que están en pausa por saturación."""
        ahora = self._reloj()
        todos = [self.nombre_modelo, *self.modelos_respaldo]
        disponibles = [m for m in todos if self._pausados.get(m, 0) <= ahora]
        return disponibles + [m for m in todos if m not in disponibles]

    def responder(self, instrucciones: str, historial: list[Mensaje]) -> str:
        """Envía la conversación a Gemini; ante saturación o demora pasa rápido al siguiente modelo de respaldo."""
        contenidos = [
            self._types.Content(
                role="user" if m.rol == "usuario" else "model",
                parts=[self._types.Part(text=m.contenido)],
            )
            for m in historial
        ]
        ultimo_error: Exception | None = None
        for modelo in self._orden_modelos():
            for intento in range(INTENTOS_POR_MODELO):
                try:
                    respuesta = self._cliente.models.generate_content(
                        model=modelo, contents=contenidos, config=self._configuracion(instrucciones, modelo))
                except Exception as error:  # El SDK lanza varios tipos de error de red y de API.
                    ultimo_error = error
                    if getattr(error, "code", None) == 400 and "hinking" in str(error) and modelo not in self._sin_razonamiento:
                        self._sin_razonamiento.add(modelo)  # Este modelo no admite el nivel: se repite sin él.
                        continue
                    if not es_error_temporal(error):
                        raise ErrorProveedor(f"Error al consultar Gemini: {error}") from error
                    if "timeout" in type(error).__name__.lower() or getattr(error, "code", None) == 504:
                        break  # Si ya tardó el tiempo límite, no se repite con el mismo modelo.
                    if intento < INTENTOS_POR_MODELO - 1:
                        self._esperar(ESPERA_REINTENTO)
                    continue
                if not respuesta.text:
                    raise ErrorProveedor("Gemini devolvió una respuesta vacía (posible bloqueo por filtros de seguridad).")
                self.modelo_usado = modelo
                self._pausados.pop(modelo, None)
                return respuesta.text
            self._pausados[modelo] = self._reloj() + PAUSA_MODELO_SATURADO
        raise ErrorProveedor(
            "Los servidores de Gemini están saturados en este momento (se probaron varios modelos). "
            f"Intenta de nuevo en unos minutos. Detalle: {ultimo_error}"
        )
