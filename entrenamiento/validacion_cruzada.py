"""Validación cruzada en los 5 pliegues de MSLD v2.0: estima la precisión real del modelo con todas las fotos de prueba.

Uso:
    python -m entrenamiento.validacion_cruzada --epocas 20

Entrena un modelo por pliegue (sin exportarlo), junta las predicciones de prueba de los cinco y guarda
el resumen en models/validacion_cruzada.json. El modelo que usa la app se entrena aparte con entrenar_vision.py.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

from entrenamiento.entrenar_vision import CARPETA_MODELOS, RAIZ, crear_parser, entrenar

UMBRALES = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9]


def efecto_umbral(reales: np.ndarray, probabilidades: np.ndarray, objetivo: int) -> list[dict]:
    """Para cada umbral, mide cuántas fotos quedan INDETERMINADAS y la sensibilidad y especificidad en las decididas."""
    filas = []
    for umbral in UMBRALES:
        confianza = probabilidades.max(1)
        prediccion = probabilidades.argmax(1)
        decididas = confianza >= umbral
        es_obj, pred_obj = reales[decididas] == objetivo, prediccion[decididas] == objetivo
        filas.append({
            "umbral": umbral,
            "indeterminadas": float(1 - decididas.mean()),
            "sensibilidad": float((es_obj & pred_obj).sum() / max(es_obj.sum(), 1)),
            "especificidad": float((~es_obj & ~pred_obj).sum() / max((~es_obj).sum(), 1)),
            "varicelas_decididas": int(es_obj.sum()),
        })
    return filas


def main() -> None:
    """Ejecuta el entrenamiento en cada pliegue y resume los resultados combinados."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--epocas", type=int, default=20)
    parser.add_argument("--carpeta", type=Path, default=RAIZ / "datasets" / "msld")
    parser.add_argument("--arquitectura", default="efficientnet_b0")
    parser.add_argument("--lr", default="1e-3")
    parser.add_argument("--lr-base", default="1e-4")
    args = parser.parse_args()

    resultados = []
    for pliegue in sorted(p for p in args.carpeta.iterdir() if p.is_dir()):
        print(f"\n{'=' * 30} {args.arquitectura} {pliegue.name} {'=' * 30}", flush=True)
        argumentos = crear_parser().parse_args([
            "--datos", str(pliegue), "--epocas", str(args.epocas), "--arquitectura", args.arquitectura,
            "--lr", args.lr, "--lr-base", args.lr_base, "--no-exportar",
        ])
        resultados.append(entrenar(argumentos))

    clases = resultados[0]["clases"]
    objetivo = clases.index("varicela")
    reales = np.concatenate([r["reales"] for r in resultados])
    probabilidades = np.concatenate([r["probabilidades"] for r in resultados])
    predicciones = probabilidades.argmax(1)
    sensibilidades = [r["sensibilidad_objetivo"] for r in resultados]
    especificidades = [r["especificidad_objetivo"] for r in resultados]

    resumen = {
        "arquitectura": args.arquitectura, "epocas": args.epocas, "lr": args.lr, "lr_base": args.lr_base,
        "exactitud_balanceada": float(np.mean([(predicciones[reales == c] == c).mean() for c in range(len(clases))])),
        "pliegues": len(resultados),
        "imagenes_prueba_totales": int(len(reales)),
        "varicelas_prueba_totales": int((reales == objetivo).sum()),
        "exactitud_global": float((predicciones == reales).mean()),
        "sensibilidad_varicela": {"media": float(np.mean(sensibilidades)), "desviacion": float(np.std(sensibilidades)),
                                  "por_pliegue": sensibilidades},
        "especificidad_varicela": {"media": float(np.mean(especificidades)), "desviacion": float(np.std(especificidades)),
                                   "por_pliegue": especificidades},
        "reporte_combinado": classification_report(reales, predicciones, target_names=clases, output_dict=True, zero_division=0),
        "matriz_confusion_combinada": confusion_matrix(reales, predicciones).tolist(),
        "clases": clases,
        "efecto_umbral": efecto_umbral(reales, probabilidades, objetivo),
    }
    CARPETA_MODELOS.mkdir(exist_ok=True)
    # Un archivo por arquitectura para poder comparar las variantes; el punto del nombre se reemplaza.
    salida = CARPETA_MODELOS / f"validacion_cruzada_{args.arquitectura.replace('.', '_')}.json"
    salida.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 70}\nRESUMEN DE VALIDACIÓN CRUZADA ({len(resultados)} pliegues)")
    print(classification_report(reales, predicciones, target_names=clases, zero_division=0))
    print(f"Varicela: sensibilidad {np.mean(sensibilidades):.3f} ± {np.std(sensibilidades):.3f}, "
          f"especificidad {np.mean(especificidades):.3f} ± {np.std(especificidades):.3f}")
    print("\nEfecto del umbral de confianza:")
    for fila in resumen["efecto_umbral"]:
        print(f"  umbral {fila['umbral']:.2f}: {fila['indeterminadas']:.0%} indeterminadas, "
              f"sensibilidad {fila['sensibilidad']:.3f}, especificidad {fila['especificidad']:.3f}")


if __name__ == "__main__":
    main()
