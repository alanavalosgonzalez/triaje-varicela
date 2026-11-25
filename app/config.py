"""Configuración central: rutas del proyecto y localización de SWI-Prolog y R."""

import glob
import os
import shutil
from pathlib import Path

# Carpeta raíz del proyecto (la que contiene app/, prolog/, r_scripts/...).
RAIZ = Path(__file__).resolve().parent.parent

# Carga el archivo .env si python-dotenv está instalado; si no, se usan las variables del sistema.
try:
    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")
except ImportError:
    pass

# Rutas de los recursos del proyecto.
ESQUEMA_SQL = RAIZ / "database" / "schema.sql"
SEED_INFORMACION = RAIZ / "database" / "seed_informacion.sql"
PROLOG_CLI = RAIZ / "prolog" / "cli.pl"
R_SCRIPT = RAIZ / "r_scripts" / "probabilidad.R"
DB_PATH = RAIZ / os.getenv("DB_PATH", "data/triaje_varicela.db")


ARCHIVO_ENV = RAIZ / ".env"


def guardar_en_env(nombre: str, valor: str, archivo: Path = ARCHIVO_ENV) -> None:
    """Guarda o reemplaza una variable en el archivo .env (conservando las demás líneas) y la activa en esta sesión."""
    lineas = archivo.read_text(encoding="utf-8").splitlines() if archivo.exists() else []
    nueva = f"{nombre}={valor}"
    for i, linea in enumerate(lineas):
        if linea.strip().startswith(f"{nombre}="):
            lineas[i] = nueva
            break
    else:
        lineas.append(nueva)
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.environ[nombre] = valor


def _buscar_ejecutable(variable_entorno: str, nombre: str, patrones_windows: list[str]) -> str | None:
    """Busca un ejecutable: primero en la variable de entorno, luego en el PATH y al final en rutas típicas de Windows."""
    ruta = os.getenv(variable_entorno)
    if ruta and Path(ruta).is_file():
        return ruta
    ruta = shutil.which(nombre)
    if ruta:
        return ruta
    for patron in patrones_windows:
        # Se ordena al revés para preferir la versión más reciente (por ejemplo R-4.6.2 sobre R-4.5.0).
        encontrados = sorted(glob.glob(patron), reverse=True)
        if encontrados:
            return encontrados[0]
    return None


def ruta_swipl() -> str | None:
    """Devuelve la ruta de swipl o None si SWI-Prolog no está instalado."""
    return _buscar_ejecutable("SWIPL_PATH", "swipl", [r"C:\Program Files\swipl\bin\swipl.exe"])


def ruta_rscript() -> str | None:
    """Devuelve la ruta de Rscript o None si R no está instalado."""
    return _buscar_ejecutable("RSCRIPT_PATH", "Rscript", [r"C:\Program Files\R\R-*\bin\Rscript.exe"])
