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
    parser.add_argument("--extra", default=None, help="Dataset adicional solo para entrenamiento.")
    parser.add_argument("--sufijo", default="", help="Texto añadido al nombre del archivo de resultados.")
    parser.add_argument("--semillas", type=int, default=1,
                        help="Modelos por pliegue con distinta semilla; si es más de 1 se promedian (conjunto o ensemble).")
    args = parser.parse_args()

    por_pliegue, clases = [], None
    for pliegue in sorted(p for p in args.carpeta.iterdir() if p.is_dir()):
        probabilidades_modelos = []
        for semilla in range(42, 42 + args.semillas):
            print(f"\n{'=' * 30} {args.arquitectura} {pliegue.name} semilla {semilla} {'=' * 30}", flush=True)
            argumentos = crear_parser().parse_args([
                "--datos", str(pliegue), "--epocas", str(args.epocas), "--arquitectura", args.arquitectura,
                "--lr", args.lr, "--lr-base", args.lr_base, "--semilla", str(semilla), "--no-exportar",
                *(["--extra", args.extra] if args.extra else []),
            ])
            resultado = entrenar(argumentos)
            clases = resultado["clases"]
            probabilidades_modelos.append(np.array(resultado["probabilidades"]))
        # Conjunto: promedio de las probabilidades calibradas de todos los modelos del pliegue.
        por_pliegue.append((np.array(resultado["reales"]), np.mean(probabilidades_modelos, axis=0)))

    descripcion = {"arquitectura": args.arquitectura, "dataset_extra": args.extra, "epocas": args.epocas,
                   "lr": args.lr, "lr_base": args.lr_base, "modelos_por_pliegue": args.semillas}
    sufijo = args.sufijo or (f"_conjunto{args.semillas}" if args.semillas > 1 else "")
    resumir(por_pliegue, clases, descripcion, f"validacion_cruzada_{args.arquitectura.replace('.', '_')}{sufijo}.json")


def resumir(por_pliegue: list[tuple[np.ndarray, np.ndarray]], clases: list[str], descripcion: dict, nombre_archivo: str) -> dict:
    """Calcula las métricas combinadas a partir de (etiquetas reales, probabilidades) de cada pliegue, las guarda y las imprime."""
    objetivo = clases.index("varicela")
    reales = np.concatenate([r for r, _ in por_pliegue])
    probabilidades = np.concatenate([p for _, p in por_pliegue])
    predicciones = probabilidades.argmax(1)
    sensibilidades, especificidades = [], []
    for r, p in por_pliegue:
        es_obj, pred_obj = r == objetivo, p.argmax(1) == objetivo
        sensibilidades.append(float((es_obj & pred_obj).sum() / max(es_obj.sum(), 1)))
        especificidades.append(float((~es_obj & ~pred_obj).sum() / max((~es_obj).sum(), 1)))

    resumen = {
        **descripcion,
        "exactitud_balanceada": float(np.mean([(predicciones[reales == c] == c).mean() for c in range(len(clases))])),
        "pliegues": len(por_pliegue),
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
    # Un archivo por variante para poder compararlas.
    (CARPETA_MODELOS / nombre_archivo).write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 70}\nRESUMEN DE VALIDACIÓN CRUZADA ({len(por_pliegue)} pliegues) -> {nombre_archivo}")
    print(classification_report(reales, predicciones, target_names=clases, zero_division=0))
    print(f"Varicela: sensibilidad {np.mean(sensibilidades):.3f} ± {np.std(sensibilidades):.3f}, "
          f"especificidad {np.mean(especificidades):.3f} ± {np.std(especificidades):.3f}")
    print("\nEfecto del umbral de confianza:")
    for fila in resumen["efecto_umbral"]:
        print(f"  umbral {fila['umbral']:.2f}: {fila['indeterminadas']:.0%} indeterminadas, "
              f"sensibilidad {fila['sensibilidad']:.3f}, especificidad {fila['especificidad']:.3f}")
    return resumen


if __name__ == "__main__":
    main()
