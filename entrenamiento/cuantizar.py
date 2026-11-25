"""Reduce el tamaño del modelo ONNX guardando los pesos en 8 bits (cuantización dinámica) y compara su precisión.

Uso:
    python -m entrenamiento.cuantizar

Crea models/varicela_int8.onnx y compara ambas versiones con las fotos de prueba del pliegue 1.
Si las predicciones casi no cambian, se renombra el original a varicela_fp32.onnx y el cuantizado a
varicela.onnx, que es el que carga la aplicación (en la versión 1.0: 28 MB frente a 111 MB).
"""

import time
from pathlib import Path

import numpy as np
from onnxruntime.quantization import QuantType, quantize_dynamic

from app.vision.analizador import RUTA_METADATOS, RUTA_MODELO, AnalizadorImagen

RUTA_INT8 = RUTA_MODELO.with_name("varicela_int8.onnx")
FOTOS_PRUEBA = Path(__file__).resolve().parent.parent / "datasets" / "msld" / "fold1" / "prueba"


def evaluar(ruta_modelo: Path, fotos: list[Path], umbral: float) -> tuple[list, float]:
    """Analiza todas las fotos con un modelo y devuelve los resultados y el tiempo medio por foto."""
    analizador = AnalizadorImagen(ruta_modelo, RUTA_METADATOS, umbral=umbral)
    inicio = time.perf_counter()
    resultados = [analizador.analizar(f) for f in fotos]
    return resultados, (time.perf_counter() - inicio) / len(fotos)


def resumen(nombre: str, fotos: list[Path], resultados: list, tiempo: float) -> None:
    """Imprime exactitud, decisiones y sensibilidad/especificidad de varicela en las fotos decididas."""
    reales = [f.parent.name for f in fotos]
    exactitud = np.mean([r.clase_predicha == c for c, r in zip(reales, resultados)])
    decididas = [(c, r) for c, r in zip(reales, resultados) if r.decision != "INDETERMINADO"]
    vp = sum(c == "varicela" and r.decision == "COMPATIBLE" for c, r in decididas)
    fn = sum(c == "varicela" and r.decision != "COMPATIBLE" for c, r in decididas)
    vn = sum(c != "varicela" and r.decision != "COMPATIBLE" for c, r in decididas)
    fp = sum(c != "varicela" and r.decision == "COMPATIBLE" for c, r in decididas)
    print(f"{nombre}: {ruta_tamano(nombre)}  {tiempo * 1000:.0f} ms/foto  exactitud {exactitud:.1%}  "
          f"decididas {len(decididas)}/{len(fotos)}  sens {vp}/{vp + fn}  espec {vn}/{vn + fp}")


def ruta_tamano(nombre: str) -> str:
    """Tamaño en MB del archivo del modelo indicado."""
    ruta = RUTA_INT8 if nombre == "int8" else RUTA_MODELO
    return f"{ruta.stat().st_size / 1e6:.0f} MB"


def main() -> None:
    """Cuantiza el modelo y compara ambas versiones con el umbral recomendado."""
    quantize_dynamic(str(RUTA_MODELO), str(RUTA_INT8), weight_type=QuantType.QInt8)
    fotos = sorted(FOTOS_PRUEBA.rglob("*.jpg"))
    umbral = AnalizadorImagen(RUTA_MODELO, RUTA_METADATOS).meta["umbral_recomendado"]
    print(f"Umbral: {umbral}")
    originales, t1 = evaluar(RUTA_MODELO, fotos, umbral)
    cuantizados, t2 = evaluar(RUTA_INT8, fotos, umbral)
    resumen("fp32", fotos, originales, t1)
    resumen("int8", fotos, cuantizados, t2)
    iguales = sum(a.clase_predicha == b.clase_predicha for a, b in zip(originales, cuantizados))
    diferencia = max(abs(a.confianza - b.confianza) for a, b in zip(originales, cuantizados))
    print(f"Misma clase predicha en {iguales}/{len(fotos)} fotos; diferencia máxima de confianza {diferencia:.3f}")


if __name__ == "__main__":
    main()
