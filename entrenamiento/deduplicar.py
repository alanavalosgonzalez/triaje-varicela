"""Quita de un dataset extra las imágenes casi idénticas a las del dataset de evaluación (o repetidas entre sí).

Uso:
    python -m entrenamiento.deduplicar datasets/msld/fold1 datasets/msid datasets/msid_limpio

Por qué: si una misma foto estuviera en el conjunto extra (entrenamiento) y en la prueba de MSLD, el modelo
la "recordaría" y las métricas saldrían infladas. Se usa dHash (hash por diferencias, 64 bits) comparado
también contra la versión en espejo, y se consideran duplicadas las que difieren en pocos bits.
"""

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def dhash(imagen: Image.Image, lado: int = 8) -> int:
    """Huella de 64 bits: compara el brillo de cada píxel con su vecino derecho en una miniatura de 9x8."""
    gris = np.asarray(imagen.convert("L").resize((lado + 1, lado), Image.LANCZOS), dtype=np.int16)
    bits = (gris[:, 1:] > gris[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def huellas(ruta: Path) -> tuple[int, int]:
    """Huella de la imagen y de su versión en espejo horizontal."""
    imagen = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    return dhash(imagen), dhash(ImageOps.mirror(imagen))


def distancia(a: int, b: int) -> int:
    """Número de bits distintos entre dos huellas (distancia de Hamming)."""
    return bin(a ^ b).count("1")


def main() -> None:
    """Copia al destino solo las imágenes extra que no se parecen a ninguna de referencia ni a otra ya aceptada."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("referencia", type=Path, help="Dataset que no debe filtrarse al entrenamiento (por ejemplo MSLD).")
    parser.add_argument("extra", type=Path, help="Dataset extra con una subcarpeta por clase.")
    parser.add_argument("destino", type=Path)
    parser.add_argument("--umbral", type=int, default=8, help="Bits distintos (de 64) por debajo de los cuales son duplicadas.")
    args = parser.parse_args()

    referencia = [h for r in args.referencia.rglob("*") if r.suffix.lower() in EXTENSIONES for h in huellas(r)]
    print(f"{len(referencia) // 2} imágenes de referencia")
    aceptadas: list[int] = []
    resumen: dict[str, list[int]] = {}
    for ruta in sorted(p for p in args.extra.rglob("*") if p.suffix.lower() in EXTENSIONES):
        clase = ruta.parent.name
        h, h_espejo = huellas(ruta)
        contra_ref = min(min(distancia(h, r), distancia(h_espejo, r)) for r in referencia)
        contra_propias = min((distancia(h, a) for a in aceptadas), default=64)
        estado = resumen.setdefault(clase, [0, 0, 0])  # [aceptadas, duplicadas de referencia, repetidas internas].
        if contra_ref <= args.umbral:
            estado[1] += 1
        elif contra_propias <= args.umbral:
            estado[2] += 1
        else:
            estado[0] += 1
            aceptadas.append(h)
            destino = args.destino / clase / ruta.name
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ruta, destino)
    for clase, (ok, dup_ref, dup_int) in sorted(resumen.items()):
        print(f"{clase:10s} aceptadas {ok:4d} | iguales a la referencia {dup_ref:4d} | repetidas internas {dup_int:3d}")


if __name__ == "__main__":
    main()
