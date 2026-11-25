"""Punto de entrada de la aplicación de escritorio. Ejecutar desde la raíz del proyecto: python -m app"""

import sys

# QtWebEngine debe importarse antes de crear la QApplication.
from PySide6 import QtWebEngineWidgets  # noqa: F401
from PySide6.QtWidgets import QApplication

from app.ui.estilos import HOJA_ESTILOS
from app.ui.ventana import VentanaPrincipal


def main() -> int:
    """Crea la aplicación con el estilo clínico y muestra la ventana principal."""
    aplicacion = QApplication(sys.argv)
    aplicacion.setApplicationName("Triaje Varicela")
    aplicacion.setStyle("Fusion")  # Estilo base uniforme sobre el que se aplica la hoja de estilos.
    aplicacion.setStyleSheet(HOJA_ESTILOS)
    ventana = VentanaPrincipal()
    ventana.show()
    return aplicacion.exec()


if __name__ == "__main__":
    sys.exit(main())
