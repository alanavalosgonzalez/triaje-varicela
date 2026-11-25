"""Ventana principal: encabezado, aviso médico permanente, menú lateral con el asistente animado y páginas."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from app.core import diagnostico
from app.ui import estilos
from app.ui.animaciones import PilaAnimada
from app.ui.asistente_animado import PanelAsistente
from app.ui.comun import Sesion
from app.ui.dialogo_clave import DialogoClave
from app.ui.pagina_chat import PaginaChat
from app.ui.pagina_historial import PaginaHistorial
from app.ui.pagina_imagen import PaginaImagen
from app.ui.pagina_info import PaginaInfo
from app.ui.pagina_mapa import PaginaMapa
from app.ui.pagina_triaje import PaginaTriaje

AVISO_MEDICO = ("⚠  Herramienta de apoyo orientativo. NO sustituye una consulta médica presencial. "
                "Ante dificultad para respirar, fiebre muy alta, lesiones infectadas o cualquier duda, acude a un médico.")
ORIGENES = {"TRIAJE": "el cuestionario", "CHAT": "el asistente virtual", "IMAGEN": "el análisis de imagen"}

# Lo que dice Doc al entrar a cada sección: (mensaje, emoción, consejos que muestra al hacerle clic).
GUIA_SECCIONES = [
    ("¡Hola! Soy Doc. Contesta el cuestionario paso a paso y te diré qué tan probable es la varicela.", "feliz",
     ["Si no sabes una respuesta, elige «No sé»: es mejor que adivinar.",
      "Revisa la piel con buena luz antes de responder sobre la erupción.",
      "Ante dificultad para respirar o fiebre muy alta, acude a urgencias sin esperar."]),
    ("Cuéntame tus síntomas con tus palabras. Te haré preguntas para orientarte mejor.", "atento",
     ["Dime desde cuándo tienes los síntomas y si hubo fiebre.",
      "Si mencionas un signo de alarma, te indicaré acudir al médico de inmediato."]),
    ("Sube una foto de la erupción con buena luz y de cerca. La analizo aquí mismo, sin enviarla a internet.", "atento",
     ["Usa luz natural y evita el flash.", "Enfoca varias lesiones a unos 10 a 20 cm.",
      "Una foto ayuda, pero el diagnóstico siempre lo confirma un médico."]),
    ("Aquí tienes información confiable sobre la varicela: fases, cuidados, contagio y mitos.", "feliz",
     ["¿Sabías que la aspirina está contraindicada en niños con varicela?",
      "La varicela contagia desde 1 o 2 días antes de la erupción hasta que todo es costra."]),
    ("Busco hospitales y clínicas cerca de ti. Usa tu ubicación o escribe tu dirección.", "atento",
     ["Llama antes de ir para confirmar horarios.", "En una emergencia, llama al número de emergencias de tu país."]),
    ("Este es tu historial. Todo se guarda solo en este equipo.", "feliz",
     ["Puedes borrar una consulta seleccionándola en la tabla."]),
]


class VentanaPrincipal(QMainWindow):
    """Contiene la navegación entre módulos y reacciona cuando alguno indica derivar al médico."""

    def __init__(self):
        """Crea la sesión, el menú lateral con Doc y todas las páginas."""
        super().__init__()
        self.setWindowTitle("Triaje Varicela — Orientación médica")
        self.resize(1240, 820)
        self.sesion = Sesion()

        central = QWidget()
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._crear_encabezado())
        aviso = QLabel(AVISO_MEDICO)
        aviso.setObjectName("aviso")
        aviso.setWordWrap(True)
        raiz.addWidget(aviso)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        lateral = QFrame()
        lateral.setObjectName("lateral")
        lateral.setFixedWidth(240)
        capa_lateral = QVBoxLayout(lateral)
        capa_lateral.setContentsMargins(0, 0, 0, 6)
        self.menu = QListWidget()
        self.menu.setObjectName("navegacion")
        self.asistente = PanelAsistente()
        capa_lateral.addWidget(self.menu, 1)
        capa_lateral.addWidget(self.asistente)

        self.paginas = PilaAnimada()
        self.pagina_triaje = PaginaTriaje(self.sesion)
        self.pagina_mapa = PaginaMapa(self.sesion)
        self.pagina_mapa.sin_animacion = True  # El visor web del mapa no admite efectos de opacidad.
        self.pagina_chat = PaginaChat(self.sesion)
        for nombre, pagina in [
            ("📋   Cuestionario", self.pagina_triaje),
            ("💬   Asistente virtual", self.pagina_chat),
            ("📷   Análisis de imagen", PaginaImagen(self.sesion)),
            ("📘   Centro Informativo", PaginaInfo(self.sesion)),
            ("📍   Centros cercanos", self.pagina_mapa),
            ("🕘   Historial", PaginaHistorial(self.sesion)),
        ]:
            self.menu.addItem(QListWidgetItem(nombre))
            self.paginas.addWidget(pagina)
        cuerpo.addWidget(lateral)
        cuerpo.addWidget(self.paginas, 1)
        raiz.addLayout(cuerpo, 1)
        self.setCentralWidget(central)

        # El mapa queda bloqueado hasta que un módulo indique sospecha alta o necesidad de atención.
        self.item_mapa = self.menu.item(4)
        self.item_mapa.setFlags(self.item_mapa.flags() & ~Qt.ItemIsEnabled)
        self.item_mapa.setToolTip("Se habilita si el triaje, el asistente o el análisis de imagen recomiendan atención médica.")

        self.menu.currentRowChanged.connect(self._cambiar_seccion)
        self.sesion.guia.connect(self.asistente.decir)
        self.pagina_triaje.ver_mapa.connect(lambda: self.menu.setCurrentRow(4))
        self.sesion.derivacion.connect(self._habilitar_mapa)
        self.pagina_chat.solicitar_clave.connect(self.configurar_clave)
        self.statusBar().showMessage("Datos guardados solo en este equipo.")
        self.indicador = QLabel()
        self.statusBar().addPermanentWidget(self.indicador)
        self._mostrar_diagnostico()
        self.menu.setCurrentRow(0)

    def _crear_encabezado(self) -> QFrame:
        """Barra superior con degradado, título y botón de configuración."""
        encabezado = QFrame()
        encabezado.setObjectName("encabezado")
        capa = QHBoxLayout(encabezado)
        capa.setContentsMargins(22, 12, 22, 12)
        titulo = QLabel("🩺  Triaje Varicela")
        titulo.setStyleSheet("font-size: 16pt; font-weight: 600;")
        subtitulo = QLabel("Pre-diagnóstico y orientación")
        subtitulo.setStyleSheet("color: rgba(255,255,255,0.85);")
        capa.addWidget(titulo)
        capa.addStretch()
        capa.addWidget(subtitulo)
        boton_config = QPushButton("⚙  Configurar asistente")
        boton_config.setObjectName("encabezado")
        boton_config.clicked.connect(self.configurar_clave)
        capa.addSpacing(16)
        capa.addWidget(boton_config)
        return encabezado

    def _cambiar_seccion(self, indice: int) -> None:
        """Muestra la página elegida y Doc presenta la sección."""
        self.paginas.setCurrentIndex(indice)
        if 0 <= indice < len(GUIA_SECCIONES):
            texto, emocion, consejos = GUIA_SECCIONES[indice]
            self.asistente.decir(texto, emocion, consejos)

    def _mostrar_diagnostico(self) -> None:
        """Muestra en la barra inferior qué componentes están disponibles; el detalle aparece al pasar el mouse."""
        componentes = diagnostico.revisar()
        self.indicador.setText("   ".join(f"{'✓' if c.disponible else '✗'} {c.nombre}" for c in componentes))
        self.indicador.setToolTip("\n".join(f"{c.nombre}: {c.detalle}" for c in componentes))
        completo = all(c.disponible for c in componentes)
        self.indicador.setStyleSheet("" if completo else f"color: {estilos.AMBAR}; font-weight: 600;")

    def configurar_clave(self) -> None:
        """Abre la ventana de la clave de Gemini y, si se guardó, reinicia el asistente con la clave nueva."""
        if DialogoClave(self).exec():
            self.pagina_chat.reiniciar_asistente()
            self._mostrar_diagnostico()
            self.statusBar().showMessage("Clave de Gemini guardada. El asistente virtual está listo.", 6000)
            self.asistente.decir("¡Listo! Ya puedo conversar contigo en el asistente virtual.", "celebrando")

    def _habilitar_mapa(self, origen: str) -> None:
        """Desbloquea el mapa y avisa una sola vez de forma visible."""
        if self.item_mapa.flags() & Qt.ItemIsEnabled:
            return
        self.item_mapa.setFlags(self.item_mapa.flags() | Qt.ItemIsEnabled)
        self.item_mapa.setText("📍   Centros cercanos  ●")
        self.statusBar().showMessage(f"Se recomienda valoración médica (según {ORIGENES.get(origen, origen)}).")
        if origen != "TRIAJE":  # En el triaje el botón del resultado ya lo indica.
            # Se muestra un instante después para que primero se vea la respuesta del módulo.
            QTimer.singleShot(600, lambda: QMessageBox.information(
                self, "Valoración médica recomendada",
                f"Según {ORIGENES.get(origen, origen)}, conviene que te valore un médico. "
                "Ya puedes ver los centros de salud cercanos en el menú «Centros cercanos»."))

    def closeEvent(self, evento) -> None:
        """Cierra la base de datos al salir."""
        self.sesion.conexion.close()
        super().closeEvent(evento)
