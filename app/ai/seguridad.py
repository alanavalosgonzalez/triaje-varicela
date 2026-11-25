"""Filtro de seguridad clínica que se ejecuta en Python antes y después del modelo de lenguaje.

La detección de urgencias no se deja solo al LLM: si el mensaje del usuario describe un signo
de alarma, la conversación se detiene y se recomienda atención médica inmediata sin consultar al modelo.
"""

import re
import unicodedata
from dataclasses import dataclass

# Marca que el modelo debe escribir al final cuando detecta duda o un cuadro atípico.
MARCA_DERIVAR = "[[DERIVAR]]"

# Patrones de signos de alarma en lenguaje coloquial, escritos sin acentos y en minúsculas.
PATRONES_ALARMA: dict[str, list[str]] = {
    "dificultad_respiratoria": [
        # Se cubre primera y tercera persona porque a menudo escribe un familiar por el paciente.
        r"no (puedo|puede|podemos|pueden) respirar", r"(me|le|les|nos) cuesta respirar",
        r"(dificultad|problemas?) (para|al) respirar", r"(me|le|les) falta (el )?aire",
        r"(me|se) ahog", r"respira (muy )?rapido", r"labios (morados|azules)",
        r"dolor (en el|de) pecho",
    ],
    "alteracion_neurologica": [
        r"convulsi", r"rigidez (de|en la) nuca", r"cuello rigido", r"confundid", r"desorientad",
        r"no (se )?despierta", r"muy somnolient", r"desmay", r"perdio el conocimiento",
    ],
    "lesiones_infectadas": [
        r"\bpus\b", r"supura", r"(muy|mas) (rojos?|rojas?|calientes?|hinchad)", r"huele mal",
        r"se esta extendiendo lo rojo",
    ],
    "sangrado": [r"sangr", r"moretones? sin motivo", r"manchas moradas"],
    "deshidratacion": [r"no (ha )?orinad", r"no puede tomar (agua|liquidos)", r"vomita todo"],
    "lesion_ocular": [r"(en|cerca de)( el| los)? ojos?\b", r"dolor (en el|de) ojo", r"vision borrosa"],
}

# Fiebre igual o mayor a este valor se considera signo de alarma.
FIEBRE_ALARMA = 39.5

# Captura temperaturas como "39.8", "40 grados" o "39,5 °C".
PATRON_FIEBRE = re.compile(r"\b(3[5-9]|4[0-3])(?:[.,](\d))?\s*(?:°|º|grados|c\b)")

# Respuesta fija cuando hay un signo de alarma; no se genera con el modelo para que nunca varíe.
MENSAJE_URGENCIA = (
    "Lo que describes ({signos}) puede ser un signo de alarma. "
    "Por seguridad, detengo aquí la orientación: acude de inmediato a urgencias o a un médico, "
    "o llama al número de emergencias de tu país (en México, 911). "
    "Si es posible, no vayas solo y lleva la lista de síntomas y medicamentos."
)

# Nota que se añade cuando el modelo decide derivar al médico.
NOTA_DERIVACION = (
    "Te recomiendo acudir con un médico para una valoración presencial; "
    "puedes ver los centros de salud cercanos en el mapa."
)


def normalizar(texto: str) -> str:
    """Pasa el texto a minúsculas y quita los acentos para comparar patrones."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).lower()


def detectar_alarmas(texto: str) -> list[str]:
    """Devuelve la lista de signos de alarma presentes en un mensaje del usuario."""
    texto = normalizar(texto)
    encontrados = [
        signo for signo, patrones in PATRONES_ALARMA.items()
        if any(re.search(patron, texto) for patron in patrones)
    ]
    for entero, decimal in PATRON_FIEBRE.findall(texto):
        if float(f"{entero}.{decimal or 0}") >= FIEBRE_ALARMA:
            encontrados.append("fiebre_muy_alta")
            break
    return encontrados


@dataclass
class RespuestaRevisada:
    """Texto final para el usuario y si se activó el umbral de duda."""

    texto: str
    derivar: bool


def revisar_respuesta(texto_modelo: str) -> RespuestaRevisada:
    """Quita la marca de derivación del texto del modelo y, si estaba, añade la nota para el usuario."""
    derivar = MARCA_DERIVAR in texto_modelo
    texto = texto_modelo.replace(MARCA_DERIVAR, "").strip()
    if derivar:
        texto = f"{texto}\n\n{NOTA_DERIVACION}"
    return RespuestaRevisada(texto=texto, derivar=derivar)
