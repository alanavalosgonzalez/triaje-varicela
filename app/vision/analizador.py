"""Análisis de fotos de la erupción con el modelo ONNX; funciona solo con el procesador, sin PyTorch ni GPU."""

import hashlib
import os
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from app import config

RUTA_MODELO = config.RAIZ / "models" / "varicela.onnx"
RUTA_METADATOS = config.RAIZ / "models" / "varicela.json"

# Límites de calidad de imagen, calibrados con las fotos del dataset MSLD v2.0: se fijaron por debajo
# del percentil 1 de cada medida, para rechazar solo fotos realmente inservibles.
BRILLO_MINIMO = 30          # Media de gris de 0 a 255 (percentil 1 del dataset: 53).
BRILLO_MAXIMO = 235         # Más es una foto sobreexpuesta.
NITIDEZ_MINIMA = 3.0        # Varianza del laplaciano a 224 px (percentil 1 del dataset: 4.6).
LADO_MINIMO = 100           # Lado corto mínimo en píxeles (percentil 1 del dataset: 121).
LADO_REFERENCIA = 224       # La nitidez se mide a esta escala para comparar fotos de cualquier resolución.


class ErrorVision(RuntimeError):
    """Error al cargar el modelo o al leer la imagen."""


@dataclass
class ResultadoImagen:
    """Resultado que se muestra al usuario y se guarda en analisis_imagen."""

    decision: str                    # COMPATIBLE, NO_COMPATIBLE o INDETERMINADO.
    clase_predicha: str
    confianza: float                 # Probabilidad calibrada de la clase predicha.
    probabilidades: dict[str, float]
    umbral: float
    motivo: str
    sha256: str
    version_modelo: str


def calidad_imagen(imagen: Image.Image) -> str | None:
    """Revisa tamaño, brillo y nitidez; devuelve un motivo si la foto no sirve o None si es aceptable."""
    if min(imagen.size) < LADO_MINIMO:
        return f"La imagen es muy pequeña (mínimo {LADO_MINIMO} píxeles por lado)."
    # Se reduce al tamaño de referencia: una foto de celular de 4000 px tiene bordes más "suaves" por píxel.
    escala = LADO_REFERENCIA / min(imagen.size)
    reducida = imagen.resize((round(imagen.width * escala), round(imagen.height * escala)), Image.BILINEAR)
    gris = np.asarray(reducida.convert("L"), dtype=np.float32)
    brillo = gris.mean()
    if brillo < BRILLO_MINIMO:
        return "La foto está demasiado oscura; tómala con buena luz."
    if brillo > BRILLO_MAXIMO:
        return "La foto está sobreexpuesta; evita el flash directo."
    # Laplaciano discreto: mide los cambios bruscos de intensidad, que desaparecen cuando la foto está movida.
    laplaciano = (gris[:-2, 1:-1] + gris[2:, 1:-1] + gris[1:-1, :-2] + gris[1:-1, 2:] - 4 * gris[1:-1, 1:-1])
    if laplaciano.var() < NITIDEZ_MINIMA:
        return "La foto está borrosa; sostén la cámara firme y enfoca la lesión."
    return None


def decidir(probabilidades: dict[str, float], clase_objetivo: str, umbral: float) -> tuple[str, str, float, str]:
    """Convierte las probabilidades en una decisión prudente: solo se afirma algo si supera el umbral."""
    clase, confianza = max(probabilidades.items(), key=lambda par: par[1])
    if confianza < umbral:
        return "INDETERMINADO", clase, confianza, (
            f"La confianza del modelo ({confianza:.0%}) no alcanza el umbral de {umbral:.0%}."
        )
    if clase == clase_objetivo:
        return "COMPATIBLE", clase, confianza, "Las lesiones son compatibles con varicela."
    return "NO_COMPATIBLE", clase, confianza, f"Las lesiones se parecen más a: {clase}."


class AnalizadorImagen:
    """Carga el modelo una sola vez y analiza las imágenes que el usuario suba."""

    def __init__(self, ruta_modelo: Path = RUTA_MODELO, ruta_metadatos: Path = RUTA_METADATOS, umbral: float | None = None):
        """Abre el modelo ONNX y lee sus metadatos (clases, temperatura y normalización)."""
        if not ruta_modelo.is_file():
            raise ErrorVision("No se encontró models/varicela.onnx. Entrena el modelo o descárgalo del Release.")
        import onnxruntime as ort  # Importación tardía: la app abre aunque falte el modelo.

        self.sesion = ort.InferenceSession(str(ruta_modelo), providers=["CPUExecutionProvider"])
        self.meta = json.loads(ruta_metadatos.read_text(encoding="utf-8"))
        # Prioridad del umbral: argumento explícito, variable VISION_UMBRAL_CONFIANZA (para pruebas)
        # y, por defecto, el umbral recomendado que se calculó con la validación cruzada al entrenar.
        if umbral is None:
            umbral = os.getenv("VISION_UMBRAL_CONFIANZA") or self.meta.get("umbral_recomendado", 0.85)
        self.umbral = float(umbral)

    def preprocesar(self, imagen: Image.Image) -> np.ndarray:
        """Redimensiona, recorta al centro y normaliza igual que en la evaluación del entrenamiento."""
        tamano = self.meta["tamano"]
        escala = int(tamano * 1.14) / min(imagen.size)
        imagen = imagen.resize((round(imagen.width * escala), round(imagen.height * escala)), Image.BILINEAR)
        izquierda, arriba = (imagen.width - tamano) // 2, (imagen.height - tamano) // 2
        imagen = imagen.crop((izquierda, arriba, izquierda + tamano, arriba + tamano))
        datos = np.asarray(imagen, dtype=np.float32) / 255.0
        datos = (datos - np.array(self.meta["media"], dtype=np.float32)) / np.array(self.meta["desviacion"], dtype=np.float32)
        return datos.transpose(2, 0, 1)[np.newaxis]  # De alto x ancho x canal a 1 x canal x alto x ancho.

    def analizar(self, ruta: Path | str) -> ResultadoImagen:
        """Analiza una foto y devuelve la decisión; las fotos de mala calidad quedan como INDETERMINADO."""
        ruta = Path(ruta)
        try:
            contenido = ruta.read_bytes()
            imagen = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
        except (OSError, ValueError) as error:
            raise ErrorVision(f"No se pudo abrir la imagen: {error}") from error
        sha256 = hashlib.sha256(contenido).hexdigest()
        version = self.meta.get("version", "desconocida")

        problema = calidad_imagen(imagen)
        if problema:
            return ResultadoImagen("INDETERMINADO", "sin_analizar", 0.0, {}, self.umbral, problema, sha256, version)

        logits = self.sesion.run(None, {"imagen": self.preprocesar(imagen)})[0][0]
        # Softmax con la temperatura calibrada para que la confianza sea realista.
        escalados = logits / self.meta["temperatura"]
        exponenciales = np.exp(escalados - escalados.max())
        probabilidades = dict(zip(self.meta["clases"], (exponenciales / exponenciales.sum()).tolist()))
        decision, clase, confianza, motivo = decidir(probabilidades, self.meta["clase_objetivo"], self.umbral)
        return ResultadoImagen(decision, clase, confianza, probabilidades, self.umbral, motivo, sha256, version)
