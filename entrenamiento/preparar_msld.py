"""Extrae las imágenes originales del dataset MSLD v2.0 y las organiza por pliegue, partición y clase en español.

Uso:
    python -m entrenamiento.preparar_msld "C:/Users/<usuario>/Downloads/archive (1).zip"

Resultado: datasets/msld/fold1..fold5/{entrenamiento,validacion,prueba}/<clase>/*.jpg
Se ignoran las imágenes aumentadas del zip porque son copias de las originales.
"""

import sys
import zipfile
from pathlib import Path, PurePosixPath

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "datasets" / "msld"
PREFIJO = "Original Images/Original Images/FOLDS/"

# Traducción de los nombres de clase del dataset a los que usa la aplicación.
CLASES = {
    "Chickenpox": "varicela",
    "Measles": "sarampion",
    "Monkeypox": "mpox",
    "Cowpox": "viruela_bovina",
    "HFMD": "mano_pie_boca",
    "Healthy": "sana",
}

# Traducción de los nombres de partición.
PARTICIONES = {"Train": "entrenamiento", "Valid": "validacion", "Test": "prueba"}


def main() -> None:
    """Recorre el zip y copia cada imagen original a su carpeta de destino."""
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    contador: dict[str, int] = {}
    with zipfile.ZipFile(sys.argv[1]) as archivo:
        for nombre in archivo.namelist():
            if not nombre.startswith(PREFIJO) or nombre.endswith("/"):
                continue
            partes = PurePosixPath(nombre[len(PREFIJO):]).parts  # (fold1, Train, Chickenpox, imagen.jpg).
            if len(partes) != 4 or partes[1] not in PARTICIONES or partes[2] not in CLASES:
                continue
            pliegue, particion, clase, archivo_img = partes
            # Solo se usa el nombre base del archivo, así ninguna ruta del zip puede salir de DESTINO.
            destino = DESTINO / pliegue / PARTICIONES[particion] / CLASES[clase] / Path(archivo_img).name
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(archivo.read(nombre))
            clave = f"{pliegue}/{PARTICIONES[particion]}"
            contador[clave] = contador.get(clave, 0) + 1
    for clave in sorted(contador):
        print(f"{contador[clave]:4d} imágenes en {clave}")
    print(f"Listo: {sum(contador.values())} imágenes en {DESTINO}")


if __name__ == "__main__":
    main()
