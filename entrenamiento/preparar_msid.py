"""Extrae el Monkeypox Skin Images Dataset (MSID, Mendeley Data, CC BY 4.0) con las clases en español.

Uso:
    python -m entrenamiento.preparar_msid datasets/descargas/msid_v6.zip

Resultado: datasets/msid/<clase>/*.png (varicela, sarampion, mpox, sana).
Cita: Bala, D. y Hossain, M. S. (2023). Monkeypox Skin Images Dataset (MSID), versión 6. Mendeley Data.
DOI 10.17632/r9bfpnvyxr.6.
"""

import sys
import zipfile
from pathlib import Path, PurePosixPath

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "datasets" / "msid"

# Traducción de las carpetas del zip a las clases que usa el modelo.
CLASES = {"Chickenpox": "varicela", "Measles": "sarampion", "Monkeypox": "mpox", "Normal": "sana"}


def main() -> None:
    """Copia cada imagen a la carpeta de su clase usando solo el nombre base del archivo."""
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    conteo: dict[str, int] = {}
    with zipfile.ZipFile(sys.argv[1]) as archivo:
        for nombre in archivo.namelist():
            partes = PurePosixPath(nombre).parts
            if nombre.endswith("/") or len(partes) < 2 or partes[-2] not in CLASES:
                continue
            clase = CLASES[partes[-2]]
            destino = DESTINO / clase / Path(partes[-1]).name  # Nunca se usa la ruta del zip: no puede salir de DESTINO.
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(archivo.read(nombre))
            conteo[clase] = conteo.get(clase, 0) + 1
    for clase, total in sorted(conteo.items()):
        print(f"{total:4d} imágenes de {clase}")


if __name__ == "__main__":
    main()
