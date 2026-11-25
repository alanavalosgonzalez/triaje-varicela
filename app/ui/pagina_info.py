"""Centro Informativo: muestra los artículos de la base de datos organizados en pestañas."""

from PySide6.QtWidgets import QTabWidget, QTextBrowser, QVBoxLayout, QWidget

from app.db import repositorio
from app.ui.comun import Sesion, etiqueta

SECCIONES = [
    ("QUE_ES", "¿Qué es la varicela?"),
    ("CUIDADOS", "Cuidados en casa"),
    ("AISLAMIENTO", "Aislamiento y contagio"),
    ("MITOS", "Mitos y realidades"),
]


class PaginaInfo(QWidget):
    """Una pestaña por sección; el contenido se guarda en Markdown y Qt lo muestra con formato."""

    def __init__(self, sesion: Sesion):
        """Lee los artículos de cada sección y los presenta con su fuente."""
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(etiqueta("Centro Informativo", "titulo"))
        layout.addWidget(etiqueta("Información de referencia basada en guías de la OMS, los CDC y la Academia "
                                  "Americana de Pediatría. No sustituye la consulta médica.", "nota"))
        pestanas = QTabWidget()
        for codigo, nombre in SECCIONES:
            articulos = repositorio.informacion(sesion.conexion, codigo)
            texto = "\n\n---\n\n".join(
                f"## {a['titulo']}\n\n{a['contenido_md']}\n\n*Fuente: {a['fuente']} (revisado: {a['fecha_revision']})*"
                for a in articulos
            )
            vista = QTextBrowser()
            vista.setMarkdown(texto)
            vista.document().setDocumentMargin(16)
            pestanas.addTab(vista, nombre)
        layout.addWidget(pestanas, 1)
