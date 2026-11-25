"""Mide si analizar cada foto también en espejo (test-time augmentation) mejora al modelo, con las fotos de prueba.

Uso:
    python -m entrenamiento.evaluar_tta [carpeta_de_prueba]

Compara, con el umbral recomendado, cuántas fotos quedan indeterminadas y cuántas se aciertan, con y sin espejo.
"""

import sys
from pathlib import Path

import numpy as np

from app.vision.analizador import AnalizadorImagen

PRUEBA = Path(__file__).resolve().parent.parent / "datasets" / "msld" / "fold1" / "prueba"


def resumen(nombre: str, fotos: list[Path], resultados: list) -> None:
    """Imprime indeterminadas, exactitud en las decididas y sensibilidad/especificidad de varicela."""
    reales = [f.parent.name for f in fotos]
    decididas = [(c, r) for c, r in zip(reales, resultados) if r.decision != "INDETERMINADO"]
    aciertos = sum(r.clase_predicha == c for c, r in decididas)
    vp = sum(c == "varicela" and r.decision == "COMPATIBLE" for c, r in decididas)
    varicelas = sum(c == "varicela" for c, _ in decididas)
    fp = sum(c != "varicela" and r.decision == "COMPATIBLE" for c, r in decididas)
    otras = len(decididas) - varicelas
    exactitud_total = np.mean([r.clase_predicha == c for c, r in zip(reales, resultados)])
    print(f"{nombre:12s} indeterminadas {1 - len(decididas) / len(fotos):5.1%} | exactitud en decididas "
          f"{aciertos}/{len(decididas)} | exactitud total {exactitud_total:.1%} | varicela: sens {vp}/{varicelas}, "
          f"falsos positivos {fp}/{otras}")


def main() -> None:
    """Analiza todas las fotos de prueba con y sin espejo."""
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else PRUEBA
    fotos = sorted(p for p in carpeta.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    for nombre, tta in [("sin espejo", False), ("con espejo", True)]:
        analizador = AnalizadorImagen(tta=tta)
        resumen(nombre, fotos, [analizador.analizar(f) for f in fotos])


if __name__ == "__main__":
    main()
