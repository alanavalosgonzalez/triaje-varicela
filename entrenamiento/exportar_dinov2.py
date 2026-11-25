"""Entrena el clasificador final DINOv2 + regresión logística con todas las fotos de MSLD y lo exporta a ONNX.

Uso:
    python -m entrenamiento.exportar_dinov2 --c 0.01 --umbral 0.60

El rendimiento de este método se midió antes con validación cruzada (experimento_dinov2.py); aquí se usan las
755 fotos para entrenar el modelo que se publica. El resultado es un único modelo: red DINOv2 congelada,
normalización de características y capa lineal, que la app usa igual que el modelo anterior.
Salidas: models/varicela.onnx (precisión completa) y models/varicela.json (metadatos).
"""

import argparse
import json

import numpy as np
import timm
import torch
from PIL import Image, ImageOps
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from torch import nn
from torchvision import transforms

from entrenamiento.entrenar_vision import CARPETA_MODELOS, DESVIACION, MEDIA, RAIZ, TAMANO, listar_imagenes
from entrenamiento.experimento_dinov2 import extraer


class ModeloCompleto(nn.Module):
    """Une la red de características, la normalización del escalador y la capa lineal en un solo modelo."""

    def __init__(self, red: nn.Module, escalador: StandardScaler, clasificador: LogisticRegression):
        """Convierte los parámetros de scikit-learn en tensores de PyTorch."""
        super().__init__()
        self.red = red
        self.register_buffer("media", torch.tensor(escalador.mean_, dtype=torch.float32))
        self.register_buffer("escala", torch.tensor(escalador.scale_, dtype=torch.float32))
        self.lineal = nn.Linear(clasificador.coef_.shape[1], clasificador.coef_.shape[0])
        self.lineal.weight.data = torch.tensor(clasificador.coef_, dtype=torch.float32)
        self.lineal.bias.data = torch.tensor(clasificador.intercept_, dtype=torch.float32)

    def forward(self, imagen: torch.Tensor) -> torch.Tensor:
        """Devuelve los logits; aplicarles softmax da las mismas probabilidades que la regresión logística."""
        return self.lineal((self.red(imagen) - self.media) / self.escala)


def main() -> None:
    """Extrae características de todas las fotos, entrena el clasificador, lo verifica y exporta el modelo."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", default="vit_small_patch14_dinov2.lvd142m")
    parser.add_argument("--c", type=float, default=0.01)
    parser.add_argument("--umbral", type=float, default=0.60)
    parser.add_argument("--version", default="vision-2.0.0")
    args = parser.parse_args()

    red = timm.create_model(args.modelo, pretrained=True, num_classes=0, img_size=TAMANO).eval()
    # Mismo preprocesamiento que la app (app/vision/analizador.py): lado corto a 255 px y recorte central de 224.
    preprocesar = transforms.Compose([
        transforms.Resize(int(TAMANO * 1.14)), transforms.CenterCrop(TAMANO), transforms.ToTensor(),
        transforms.Normalize(MEDIA, DESVIACION),
    ])
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    red_gpu = red.to(dispositivo)

    # Todas las fotos de MSLD: las tres particiones del pliegue 1 juntas son las 755 fotos originales.
    rutas, etiquetas, clases = [], [], None
    for particion in ("entrenamiento", "validacion", "prueba"):
        r, e, clases = listar_imagenes(RAIZ / "datasets" / "msld" / "fold1" / particion)
        rutas += r
        etiquetas += e
    x = np.concatenate([extraer(red_gpu, rutas, preprocesar, dispositivo),
                        extraer(red_gpu, rutas, preprocesar, dispositivo, espejo=True)])
    y = np.array(etiquetas * 2)
    print(f"{len(rutas)} fotos ({len(x)} con espejo), {len(clases)} clases: {clases}")
    escalador = StandardScaler().fit(x)
    clasificador = LogisticRegression(C=args.c, max_iter=5000, class_weight="balanced").fit(escalador.transform(x), y)

    # Verificación: el modelo unido debe dar las mismas probabilidades que scikit-learn.
    completo = ModeloCompleto(red.cpu(), escalador, clasificador).eval()
    muestra = torch.stack([preprocesar(ImageOps.exif_transpose(Image.open(rutas[i])).convert("RGB"))
                           for i in range(0, len(rutas), 75)])
    with torch.no_grad():
        prob_torch = torch.softmax(completo(muestra), dim=1).numpy()
        prob_sklearn = clasificador.predict_proba(escalador.transform(red(muestra).numpy()))
    print(f"Diferencia máxima PyTorch vs scikit-learn: {np.abs(prob_torch - prob_sklearn).max():.2e}")

    CARPETA_MODELOS.mkdir(exist_ok=True)
    torch.onnx.export(
        completo, torch.randn(1, 3, TAMANO, TAMANO), CARPETA_MODELOS / "varicela.onnx",
        input_names=["imagen"], output_names=["logits"], dynamic_axes={"imagen": {0: "lote"}, "logits": {0: "lote"}},
        opset_version=17, dynamo=False,
    )
    metadatos = {
        "arquitectura": f"{args.modelo} (congelado) + regresión logística (C={args.c})", "version": args.version,
        "clases": clases, "clase_objetivo": "varicela",
        "temperatura": 1.0,  # La regresión logística ya da probabilidades calibradas; no se reescala.
        "tamano": TAMANO, "media": MEDIA, "desviacion": DESVIACION, "umbral_recomendado": args.umbral, "tta": False,
        "entrenado_con": f"{len(rutas)} fotos originales de MSLD v2.0 (todas); rendimiento medido con validación cruzada",
    }
    (CARPETA_MODELOS / "varicela.json").write_text(json.dumps(metadatos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Modelo exportado en {CARPETA_MODELOS / 'varicela.onnx'}")


if __name__ == "__main__":
    main()
