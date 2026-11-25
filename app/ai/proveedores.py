"""Proveedores de modelo de lenguaje. El asistente solo conoce la interfaz ProveedorLLM, así se puede cambiar de proveedor."""

import os
from dataclasses import dataclass
from typing import Protocol

# Modelo por defecto; se puede cambiar en .env con GEMINI_MODELO sin tocar el código.
MODELO_GEMINI_POR_DEFECTO = "gemini-3.8-flash"


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
    """Proveedor basado en la API de Google Gemini (paquete google-genai)."""

    def __init__(self, api_key: str | None = None, modelo: str | None = None, temperatura: float = 0.3):
        """Crea el cliente; la clave se lee de GEMINI_API_KEY si no se pasa explícitamente."""
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise ErrorProveedor("Falta el paquete google-genai: ejecuta pip install -r requirements.txt.") from error
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ErrorProveedor("No hay clave de Gemini: define GEMINI_API_KEY en el archivo .env.")
        self._types = types
        self._cliente = genai.Client(api_key=api_key)
        self.nombre_modelo = modelo or os.getenv("GEMINI_MODELO") or MODELO_GEMINI_POR_DEFECTO
        self._temperatura = temperatura  # Temperatura baja: respuestas más estables y prudentes.

    def responder(self, instrucciones: str, historial: list[Mensaje]) -> str:
        """Envía la conversación completa a Gemini y devuelve el texto generado."""
        contenidos = [
            self._types.Content(
                role="user" if m.rol == "usuario" else "model",
                parts=[self._types.Part(text=m.contenido)],
            )
            for m in historial
        ]
        try:
            respuesta = self._cliente.models.generate_content(
                model=self.nombre_modelo,
                contents=contenidos,
                config=self._types.GenerateContentConfig(
                    system_instruction=instrucciones, temperature=self._temperatura
                ),
            )
        except Exception as error:  # El SDK lanza varios tipos de error de red y de API.
            raise ErrorProveedor(f"Error al consultar Gemini: {error}") from error
        if not respuesta.text:
            raise ErrorProveedor("Gemini devolvió una respuesta vacía (posible bloqueo por filtros de seguridad).")
        return respuesta.text
