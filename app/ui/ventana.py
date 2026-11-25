"""Ventana principal: encabezado, aviso médico permanente, menú lateral y páginas."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QStackedWidget,
    QVBoxLayout, QWidget,
)

from app.core import diagnostico
from app.ui import estilos
from app.ui.comun import Sesion
from app.ui.pagina_chat import PaginaChat
from app.ui.pagina_historial import PaginaHistorial
from app.ui.pagina_imagen import PaginaImagen
from app.ui.pagina_info import PaginaInfo
from app.ui.pagina_mapa import PaginaMapa
from app.ui.pagina_triaje import PaginaTriaje

AVISO_MEDICO = ("⚠  Herramienta de apoyo orientativo. NO sustituye una consulta médica presencial. "
                "Ante dificultad para respirar, fiebre muy alta, lesiones infectadas o cualquier duda, acude a un médico.")
ORIGENES = {"TRIAJE": "el cuestionario", "CHAT": "el asistente virtual", "IMAGEN": "el análisis de imagen"}


class VentanaPrincipal(QMainWindow):
    """Contiene la navegación entre módulos y reacciona cuando alguno indica derivar al médico."""

    def __init__(self):
        """Crea la sesión y todas las páginas."""
        super().__init__()
        self.setWindowTitle("Triaje Varicela — Orientación médica")
        self.resize(1180, 780)
        self.sesion = Sesion()

        central = QWidget()
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        encabezado = QFrame()
        encabezado.setObjectName("encabezado")
        capa_encabezado = QHBoxLayout(encabezado)
        capa_encabezado.setContentsMargins(20, 12, 20, 12)
        titulo = QLabel("Triaje Varicela")
        titulo.setStyleSheet("font-size: 15pt; font-weight: 600;")
        capa_encabezado.addWidget(titulo)
        capa_encabezado.addStretch()
        capa_encabezado.addWidget(QLabel("Pre-diagnóstico y orientación"))
        raiz.addWidget(encabezado)

        aviso = QLabel(AVISO_MEDICO)
        aviso.setObjectName("aviso")
        aviso.setWordWrap(True)
        raiz.addWidget(aviso)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        self.menu = QListWidget()
        self.menu.setObjectName("navegacion")
        self.menu.setFixedWidth(220)
        self.paginas = QStackedWidget()
        self.pagina_triaje = PaginaTriaje(self.sesion)
        self.pagina_mapa = PaginaMapa(self.sesion)
        for nombre, pagina in [
            ("Cuestionario de triaje", self.pagina_triaje),
            ("Asistente virtual", PaginaChat(self.sesion)),
            ("Análisis de imagen", PaginaImagen(self.sesion)),
            ("Centro Informativo", PaginaInfo(self.sesion)),
            ("Centros cercanos", self.pagina_mapa),
            ("Historial", PaginaHistorial(self.sesion)),
        ]:
            self.menu.addItem(QListWidgetItem(nombre))
            self.paginas.addWidget(pagina)
        cuerpo.addWidget(self.menu)
        cuerpo.addWidget(self.paginas, 1)
        raiz.addLayout(cuerpo, 1)
        self.setCentralWidget(central)

        # El mapa queda bloqueado hasta que un módulo indique sospecha alta o necesidad de atención.
        self.item_mapa = self.menu.item(4)
        self.item_mapa.setFlags(self.item_mapa.flags() & ~Qt.ItemIsEnabled)
        self.item_mapa.setToolTip("Se habilita si el triaje, el asistente o el análisis de imagen recomiendan atención médica.")

        self.menu.currentRowChanged.connect(self.paginas.setCurrentIndex)
        self.menu.setCurrentRow(0)
        self.pagina_triaje.ver_mapa.connect(lambda: self.menu.setCurrentRow(4))
        self.sesion.derivacion.connect(self._habilitar_mapa)
        self.statusBar().showMessage("Datos guardados solo en este equipo.")
        self._mostrar_diagnostico()

    def _mostrar_diagnostico(self) -> None:
        """Muestra en la barra inferior qué componentes están disponibles; el detalle aparece al pasar el mouse."""
        componentes = diagnostico.revisar()
        texto = "   ".join(f"{'✓' if c.disponible else '✗'} {c.nombre}" for c in componentes)
        indicador = QLabel(texto)
        indicador.setToolTip("\n".join(f"{c.nombre}: {c.detalle}" for c in componentes))
        if not all(c.disponible for c in componentes):
            indicador.setStyleSheet(f"color: {estilos.AMBAR}; font-weight: 600;")
        self.statusBar().addPermanentWidget(indicador)

    def _habilitar_mapa(self, origen: str) -> None:
        """Desbloquea el mapa y avisa una sola vez de forma visible."""
        if self.item_mapa.flags() & Qt.ItemIsEnabled:
            return
        self.item_mapa.setFlags(self.item_mapa.flags() | Qt.ItemIsEnabled)
        self.item_mapa.setText("Centros cercanos  ●")
        self.statusBar().showMessage(f"Se recomienda valoración médica (según {ORIGENES.get(origen, origen)}).")
        if origen != "TRIAJE":  # En el triaje el botón del resultado ya lo indica.
            QMessageBox.information(self, "Valoración médica recomendada",
                                    f"Según {ORIGENES.get(origen, origen)}, conviene que te valore un médico. "
                                    "Ya puedes ver los centros de salud cercanos en el menú «Centros cercanos».")

    def closeEvent(self, evento) -> None:
        """Cierra la base de datos al salir."""
        self.sesion.conexion.close()
        super().closeEvent(evento)
