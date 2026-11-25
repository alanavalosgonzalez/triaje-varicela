"""Entrena el clasificador de lesiones cutáneas y lo exporta a ONNX para la aplicación.

Este script solo se ejecuta en el equipo de desarrollo (requiere requirements-train.txt y, de
preferencia, una GPU NVIDIA). La aplicación final solo usa el archivo .onnx resultante.

Uso:
    python -m entrenamiento.entrenar_vision --datos datasets/msld/fold1 --epocas 20

La carpeta de datos puede traer ya las particiones entrenamiento/, validacion/ y prueba/ (cada una con
una subcarpeta por clase) o solo las subcarpetas de clase, y entonces se divide al azar.
Salidas en models/: varicela.onnx, varicela.json (clases, temperatura, umbral) y metricas.json.
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
import timm
import torch
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_MODELOS = RAIZ / "models"
TAMANO = 224                      # Tamaño de entrada de EfficientNet-B0.
MEDIA = (0.485, 0.456, 0.406)      # Normalización de ImageNet, con la que se preentrenó la red.
DESVIACION = (0.229, 0.224, 0.225)
EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def fijar_semilla(semilla: int) -> None:
    """Fija las semillas aleatorias para que el entrenamiento sea reproducible."""
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)
    torch.cuda.manual_seed_all(semilla)


def listar_imagenes(carpeta: Path) -> tuple[list[Path], list[int], list[str]]:
    """Recorre las subcarpetas de clase y devuelve rutas, etiquetas numéricas y nombres de clase."""
    clases = sorted(d.name for d in carpeta.iterdir() if d.is_dir())
    rutas, etiquetas = [], []
    for indice, clase in enumerate(clases):
        for archivo in sorted((carpeta / clase).rglob("*")):
            if archivo.suffix.lower() in EXTENSIONES:
                rutas.append(archivo)
                etiquetas.append(indice)
    return rutas, etiquetas, clases


class DatasetImagenes(Dataset):
    """Carga todas las imágenes en memoria una sola vez (el dataset es pequeño) y aplica las transformaciones."""

    def __init__(self, rutas: list[Path], etiquetas: list[int], transformacion):
        """Lee y corrige la orientación EXIF de cada imagen al crear el conjunto."""
        self.imagenes = [ImageOps.exif_transpose(Image.open(r)).convert("RGB") for r in rutas]
        self.etiquetas, self.transformacion = etiquetas, transformacion

    def __len__(self) -> int:
        """Número de imágenes del conjunto."""
        return len(self.imagenes)

    def __getitem__(self, i: int):
        """Devuelve el tensor de la imagen i (con aumentos aleatorios si es de entrenamiento) y su etiqueta."""
        return self.transformacion(self.imagenes[i]), self.etiquetas[i]


def transformaciones() -> tuple:
    """Aumentos de datos para entrenar y preprocesamiento fijo para validar y probar."""
    entrenamiento = transforms.Compose([
        transforms.RandomResizedCrop(TAMANO, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(20),
        # Variaciones de brillo y tono simulan distintas cámaras, luces y tonos de piel.
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.03),
        transforms.ToTensor(),
        transforms.Normalize(MEDIA, DESVIACION),
    ])
    evaluacion = transforms.Compose([
        transforms.Resize(int(TAMANO * 1.14)),
        transforms.CenterCrop(TAMANO),
        transforms.ToTensor(),
        transforms.Normalize(MEDIA, DESVIACION),
    ])
    return entrenamiento, evaluacion


@torch.no_grad()
def obtener_logits(modelo: nn.Module, cargador: DataLoader, dispositivo) -> tuple[torch.Tensor, torch.Tensor]:
    """Ejecuta el modelo sobre un conjunto completo y devuelve logits y etiquetas reales."""
    modelo.eval()
    todos_logits, todas_etiquetas = [], []
    for imagenes, etiquetas in cargador:
        todos_logits.append(modelo(imagenes.to(dispositivo)).cpu())
        todas_etiquetas.append(etiquetas)
    return torch.cat(todos_logits), torch.cat(todas_etiquetas)


def calibrar_temperatura(logits: torch.Tensor, etiquetas: torch.Tensor) -> float:
    """Busca la temperatura que hace que las probabilidades reflejen la precisión real (temperature scaling)."""
    log_t = torch.zeros(1, requires_grad=True)
    optimizador = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)
    perdida = nn.CrossEntropyLoss()

    def paso():
        """Calcula la pérdida con la temperatura actual."""
        optimizador.zero_grad()
        valor = perdida(logits / log_t.exp(), etiquetas)
        valor.backward()
        return valor

    optimizador.step(paso)
    return float(log_t.detach().exp())


def crear_parser() -> argparse.ArgumentParser:
    """Define los argumentos de línea de comandos del entrenamiento."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datos", type=Path, required=True, help="Carpeta con una subcarpeta por clase.")
    parser.add_argument("--epocas", type=int, default=20)
    parser.add_argument("--lote", type=int, default=32)
    parser.add_argument("--arquitectura", default="efficientnet_b0")
    parser.add_argument("--clase-objetivo", default="varicela")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--lr", type=float, default=1e-3, help="Tasa de aprendizaje de la capa final nueva.")
    parser.add_argument("--lr-base", type=float, default=1e-4, help="Tasa de aprendizaje de la red preentrenada.")
    parser.add_argument("--umbral", type=float, default=0.70,
                        help="Umbral de confianza recomendado (elegido con la validación cruzada); se guarda en los metadatos.")
    parser.add_argument("--no-exportar", action="store_true", help="Solo mide; no guarda el modelo ONNX.")
    return parser


def exactitud_balanceada(logits: torch.Tensor, etiquetas: torch.Tensor, n_clases: int) -> float:
    """Promedio del acierto por clase; a diferencia de la exactitud simple, no lo dominan las clases con más fotos."""
    predicciones = logits.argmax(1)
    aciertos = [(predicciones[etiquetas == c] == c).float().mean().item() for c in range(n_clases) if (etiquetas == c).any()]
    return float(np.mean(aciertos))


def main() -> None:
    """Punto de entrada desde la terminal: entrena y guarda las métricas del modelo en models/metricas.json."""
    metricas = entrenar(crear_parser().parse_args())
    # Las listas de predicciones individuales no hacen falta en el resumen del modelo publicado.
    resumen = {k: v for k, v in metricas.items() if k not in ("reales", "probabilidades")}
    CARPETA_MODELOS.mkdir(exist_ok=True)
    (CARPETA_MODELOS / "metricas.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")


def entrenar(args: argparse.Namespace) -> dict:
    """Entrena, calibra, mide en el conjunto de prueba, exporta a ONNX (salvo --no-exportar) y devuelve las métricas."""
    fijar_semilla(args.semilla)
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Dispositivo: {dispositivo}")

    # 1. Datos: si la carpeta ya trae la división por paciente (entrenamiento/validacion/prueba) se respeta,
    #    porque separar al azar puede poner fotos del mismo paciente en entrenamiento y en prueba.
    if (args.datos / "entrenamiento").is_dir():
        r_ent, e_ent, clases = listar_imagenes(args.datos / "entrenamiento")
        r_val, e_val, _ = listar_imagenes(args.datos / "validacion")
        r_pru, e_pru, _ = listar_imagenes(args.datos / "prueba")
        print(f"División predefinida: {len(r_ent)} entrenamiento, {len(r_val)} validación, {len(r_pru)} prueba.")
    else:
        # Sin división previa: estratificada al azar 70 % / 15 % / 15 %.
        rutas, etiquetas, clases = listar_imagenes(args.datos)
        r_ent, r_tmp, e_ent, e_tmp = train_test_split(rutas, etiquetas, test_size=0.30, stratify=etiquetas, random_state=args.semilla)
        r_val, r_pru, e_val, e_pru = train_test_split(r_tmp, e_tmp, test_size=0.50, stratify=e_tmp, random_state=args.semilla)
    print(f"Clases: {clases}")
    t_ent, t_eval = transformaciones()
    # Sin procesos auxiliares (num_workers=0): en Windows cada proceso reimporta PyTorch en cada época,
    # y con imágenes pequeñas en memoria cargar en el proceso principal es mucho más rápido.
    cargadores = {
        "entrenamiento": DataLoader(DatasetImagenes(r_ent, e_ent, t_ent), args.lote, shuffle=True, num_workers=0),
        "validacion": DataLoader(DatasetImagenes(r_val, e_val, t_eval), args.lote, num_workers=0),
        "prueba": DataLoader(DatasetImagenes(r_pru, e_pru, t_eval), args.lote, num_workers=0),
    }

    # 2. Red preentrenada en ImageNet con una nueva capa final para nuestras clases.
    modelo = timm.create_model(args.arquitectura, pretrained=True, num_classes=len(clases)).to(dispositivo)

    # Pesos por clase para compensar que unas clases tengan muchas más imágenes que otras.
    conteos = np.bincount(e_ent, minlength=len(clases))
    pesos = torch.tensor(len(e_ent) / (len(clases) * conteos), dtype=torch.float32, device=dispositivo)
    criterio = nn.CrossEntropyLoss(weight=pesos, label_smoothing=0.1)
    # Tasas de aprendizaje distintas: la capa final nueva aprende rápido y la red preentrenada se ajusta con
    # suavidad para no "olvidar" lo que aprendió en ImageNet con tan pocas fotos.
    params_cabeza = list(modelo.get_classifier().parameters())
    ids_cabeza = {id(p) for p in params_cabeza}
    params_base = [p for p in modelo.parameters() if id(p) not in ids_cabeza]
    optimizador = torch.optim.AdamW(
        [{"params": params_base, "lr": args.lr_base}, {"params": params_cabeza, "lr": args.lr}], weight_decay=0.05
    )
    planificador = torch.optim.lr_scheduler.CosineAnnealingLR(optimizador, T_max=args.epocas)
    # Precisión mixta bfloat16 en GPU: entrena más rápido y usa menos memoria sin perder exactitud apreciable.
    usar_amp = dispositivo.type == "cuda"

    # 3. Entrenamiento: se guarda el modelo con mejor exactitud balanceada en validación.
    mejor_exactitud, mejor_estado = 0.0, None
    for epoca in range(1, args.epocas + 1):
        modelo.train()
        perdida_total = 0.0
        for imagenes, objetivos in cargadores["entrenamiento"]:
            imagenes, objetivos = imagenes.to(dispositivo), objetivos.to(dispositivo)
            optimizador.zero_grad()
            with torch.autocast(device_type=dispositivo.type, dtype=torch.bfloat16, enabled=usar_amp):
                perdida = criterio(modelo(imagenes), objetivos)
            perdida.backward()
            optimizador.step()
            perdida_total += perdida.item() * len(objetivos)
        planificador.step()
        logits_val, etiq_val = obtener_logits(modelo, cargadores["validacion"], dispositivo)
        exactitud = exactitud_balanceada(logits_val, etiq_val, len(clases))
        print(f"Época {epoca:2d}/{args.epocas}  pérdida {perdida_total / len(e_ent):.4f}  exactitud balanceada val {exactitud:.3f}", flush=True)
        if exactitud > mejor_exactitud:
            mejor_exactitud = exactitud
            mejor_estado = {k: v.detach().clone() for k, v in modelo.state_dict().items()}
    modelo.load_state_dict(mejor_estado)

    # 4. Calibración de la confianza con el conjunto de validación.
    logits_val, etiq_val = obtener_logits(modelo, cargadores["validacion"], dispositivo)
    temperatura = calibrar_temperatura(logits_val, etiq_val)
    print(f"Temperatura calibrada: {temperatura:.3f}")

    # 5. Métricas finales en el conjunto de prueba, que el modelo nunca vio.
    logits_pru, etiq_pru = obtener_logits(modelo, cargadores["prueba"], dispositivo)
    predicciones = logits_pru.argmax(1).numpy()
    reales = etiq_pru.numpy()
    reporte = classification_report(reales, predicciones, target_names=clases, output_dict=True, zero_division=0)
    matriz = confusion_matrix(reales, predicciones).tolist()
    print(classification_report(reales, predicciones, target_names=clases, zero_division=0))
    objetivo = clases.index(args.clase_objetivo)
    es_obj, pred_obj = reales == objetivo, predicciones == objetivo
    sensibilidad = float((es_obj & pred_obj).sum() / max(es_obj.sum(), 1))
    especificidad = float((~es_obj & ~pred_obj).sum() / max((~es_obj).sum(), 1))
    print(f"{args.clase_objetivo}: sensibilidad {sensibilidad:.3f}, especificidad {especificidad:.3f}")

    # Probabilidades calibradas de prueba: sirven para medir el efecto del umbral de confianza.
    probabilidades = torch.softmax(logits_pru / temperatura, dim=1).numpy()
    metricas = {
        "datos": str(args.datos), "clases": clases,
        "imagenes": {"entrenamiento": len(r_ent), "validacion": len(r_val), "prueba": len(r_pru)},
        "arquitectura": args.arquitectura, "exactitud_balanceada_validacion": mejor_exactitud, "temperatura": temperatura,
        "reporte_prueba": reporte, "matriz_confusion": matriz,
        "sensibilidad_objetivo": sensibilidad, "especificidad_objetivo": especificidad,
        "reales": reales.tolist(), "probabilidades": probabilidades.round(5).tolist(),
    }
    if args.no_exportar:
        return metricas

    # 6. Exportación a ONNX y metadatos que necesita la aplicación.
    CARPETA_MODELOS.mkdir(exist_ok=True)
    modelo.cpu().eval()
    torch.onnx.export(
        modelo, torch.randn(1, 3, TAMANO, TAMANO), CARPETA_MODELOS / "varicela.onnx",
        input_names=["imagen"], output_names=["logits"], dynamic_axes={"imagen": {0: "lote"}, "logits": {0: "lote"}},
        opset_version=17, dynamo=False,
    )
    metadatos = {
        "arquitectura": args.arquitectura, "version": "vision-1.0.0", "clases": clases,
        "clase_objetivo": args.clase_objetivo, "temperatura": temperatura, "tamano": TAMANO,
        "umbral_recomendado": args.umbral,
        "media": MEDIA, "desviacion": DESVIACION,
    }
    (CARPETA_MODELOS / "varicela.json").write_text(json.dumps(metadatos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Modelo exportado en {CARPETA_MODELOS / 'varicela.onnx'}")
    return metricas


if __name__ == "__main__":
    main()
