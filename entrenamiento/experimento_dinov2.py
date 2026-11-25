"""Experimento B: características de DINOv2 (red congelada) + regresión logística, con validación cruzada.

Uso:
    python -m entrenamiento.experimento_dinov2 [--modelo vit_small_patch14_dinov2.lvd142m]

Idea: en lugar de ajustar toda la red con muy pocas fotos (riesgo de memorizarlas), se usa DINOv2, preentrenado
por Meta con 142 millones de imágenes, solo para convertir cada foto en un vector de características. Encima se
entrena un clasificador lineal, que tiene muy pocos parámetros que ajustar. Se mide con los mismos 5 pliegues.
"""

import argparse

import numpy as np
import timm
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from torchvision import transforms
from PIL import Image, ImageOps

from entrenamiento.entrenar_vision import RAIZ, listar_imagenes
from entrenamiento.validacion_cruzada import resumir

VALORES_C = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0]  # Regularización a probar: menor C = clasificador más simple.


@torch.no_grad()
def extraer(modelo, rutas, preprocesar, dispositivo, espejo: bool = False) -> np.ndarray:
    """Convierte cada imagen en su vector de características (opcionalmente de la imagen en espejo)."""
    vectores = []
    for inicio in range(0, len(rutas), 32):
        lote = []
        for ruta in rutas[inicio:inicio + 32]:
            imagen = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
            lote.append(preprocesar(ImageOps.mirror(imagen) if espejo else imagen))
        vectores.append(modelo(torch.stack(lote).to(dispositivo)).float().cpu().numpy())
    return np.concatenate(vectores)


def exactitud_balanceada(reales: np.ndarray, predicciones: np.ndarray) -> float:
    """Promedio del acierto por clase."""
    return float(np.mean([(predicciones[reales == c] == c).mean() for c in np.unique(reales)]))


def main() -> None:
    """Extrae características por pliegue, elige la regularización con validación y evalúa en prueba."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", default="vit_small_patch14_dinov2.lvd142m")
    parser.add_argument("--c", type=float, nargs="+", default=None,
                        help="Valores de C fijos a evaluar en todos los pliegues (si se omite, se elige C por pliegue con validación).")
    args = parser.parse_args()

    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # num_classes=0: la red devuelve el vector de características en lugar de una clasificación.
    modelo = timm.create_model(args.modelo, pretrained=True, num_classes=0, img_size=224).to(dispositivo).eval()
    configuracion = timm.data.resolve_data_config({}, model=modelo)
    preprocesar = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize(configuracion["mean"], configuracion["std"]),
    ])

    # Las características no dependen de C: se extraen una vez por pliegue y se reutilizan.
    datos_pliegues, clases = [], None
    for pliegue in sorted(p for p in (RAIZ / "datasets" / "msld").iterdir() if p.is_dir()):
        r_ent, e_ent, clases = listar_imagenes(pliegue / "entrenamiento")
        r_val, e_val, _ = listar_imagenes(pliegue / "validacion")
        r_pru, e_pru, _ = listar_imagenes(pliegue / "prueba")
        # El entrenamiento se duplica con las fotos en espejo (aumento de datos sencillo).
        x_ent = np.concatenate([extraer(modelo, r_ent, preprocesar, dispositivo),
                                extraer(modelo, r_ent, preprocesar, dispositivo, espejo=True)])
        y_ent = np.array(e_ent * 2)
        x_val, x_pru = extraer(modelo, r_val, preprocesar, dispositivo), extraer(modelo, r_pru, preprocesar, dispositivo)
        escalador = StandardScaler().fit(x_ent)
        x_ent, x_val, x_pru = escalador.transform(x_ent), escalador.transform(x_val), escalador.transform(x_pru)

        datos_pliegues.append((pliegue.name, x_ent, y_ent, x_val, np.array(e_val), x_pru, np.array(e_pru)))

    nombre = args.modelo.split(".")[0]
    for c_fijo in (args.c or [None]):
        por_pliegue = []
        for nombre_pliegue, x_ent, y_ent, x_val, y_val, x_pru, y_pru in datos_pliegues:
            mejor = None
            for c in ([c_fijo] if c_fijo else VALORES_C):
                clasificador = LogisticRegression(C=c, max_iter=5000, class_weight="balanced").fit(x_ent, y_ent)
                puntaje = exactitud_balanceada(y_val, clasificador.predict(x_val))
                if mejor is None or puntaje > mejor[0]:
                    mejor = (puntaje, c, clasificador)
            print(f"{nombre_pliegue}: C={mejor[1]}  exactitud balanceada val {mejor[0]:.3f}", flush=True)
            por_pliegue.append((y_pru, mejor[2].predict_proba(x_pru)))
        sufijo = f"_c{c_fijo}" if c_fijo else ""
        resumir(por_pliegue, clases, {"arquitectura": args.modelo, "metodo": "caracteristicas congeladas + regresion logistica",
                                      "C": c_fijo or "elegido por pliegue"}, f"validacion_cruzada_{nombre}_lineal{sufijo}.json")


if __name__ == "__main__":
    main()
