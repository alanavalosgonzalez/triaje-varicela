"""Comprueba al iniciar qué componentes externos están disponibles, para avisar al usuario antes de que falle un módulo."""

import os
from dataclasses import dataclass

from app import config
from app.vision.analizador import RUTA_METADATOS, RUTA_MODELO


@dataclass
class Componente:
    """Estado de un componente: si está disponible y qué hacer si no lo está."""

    nombre: str
    disponible: bool
    detalle: str


def revisar() -> list[Componente]:
    """Revisa Prolog, R, la clave de Gemini y el modelo de visión; no ejecuta nada pesado."""
    swipl, rscript = config.ruta_swipl(), config.ruta_rscript()
    modelo_ok = RUTA_MODELO.is_file() and RUTA_METADATOS.is_file()
    return [
        Componente("Prolog", swipl is not None,
                   swipl or "No se encontró SWI-Prolog: el cuestionario no funcionará. Instálalo o define SWIPL_PATH."),
        Componente("R", rscript is not None,
                   rscript or "No se encontró Rscript: el cuestionario no funcionará. Instala R o define RSCRIPT_PATH."),
        Componente("Gemini", bool(os.getenv("GEMINI_API_KEY")),
                   "Clave configurada." if os.getenv("GEMINI_API_KEY")
                   else "Falta GEMINI_API_KEY en .env: el asistente virtual no funcionará."),
        Componente("Modelo de imagen", modelo_ok,
                   str(RUTA_MODELO) if modelo_ok
                   else "Falta models/varicela.onnx: descárgalo del Release del proyecto para analizar fotos."),
    ]
