"""Ventana para configurar la clave de Gemini sin editar archivos a mano."""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout

from app import config
from app.ui.comun import ejecutar, etiqueta

URL_CLAVE = "https://aistudio.google.com/apikey"
EXPLICACION = (
    "El asistente virtual usa Google Gemini. Para activarlo necesitas una clave de API personal y gratuita: "
    f"créala en <a href='{URL_CLAVE}' style='color:#0F4C81'>aistudio.google.com/apikey</a> y pégala aquí.<br><br>"
    "La clave se guarda solo en este equipo (archivo .env). No la compartas ni la publiques."
)


def probar_clave(clave: str) -> int:
    """Comprueba la clave pidiendo la lista de modelos; devuelve cuántos modelos de texto están disponibles."""
    from google import genai

    cliente = genai.Client(api_key=clave)
    return sum(1 for m in cliente.models.list() if "generateContent" in (m.supported_actions or []))


class DialogoClave(QDialog):
    """Pide la clave, la verifica con Google y la guarda en .env si es válida."""

    def __init__(self, padre=None):
        """Construye el campo (oculto como contraseña) y los botones."""
        super().__init__(padre)
        self.setWindowTitle("Configurar asistente virtual")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.addWidget(etiqueta("Clave de Google Gemini", "subtitulo"))
        texto = etiqueta(EXPLICACION)
        texto.setTextFormat(Qt.RichText)
        texto.setOpenExternalLinks(True)
        layout.addWidget(texto)

        fila = QHBoxLayout()
        self.campo = QLineEdit()
        self.campo.setEchoMode(QLineEdit.Password)  # La clave no se muestra en pantalla.
        self.campo.setPlaceholderText("Pega aquí tu clave")
        self.campo.setText(os.getenv("GEMINI_API_KEY", ""))
        self.boton_ver = QPushButton("Mostrar")
        self.boton_ver.setObjectName("secundario")
        self.boton_ver.setCheckable(True)
        self.boton_ver.toggled.connect(self._alternar_visibilidad)
        fila.addWidget(self.campo, 1)
        fila.addWidget(self.boton_ver)
        layout.addLayout(fila)

        self.estado = etiqueta("", "nota")
        layout.addWidget(self.estado)
        botones = QHBoxLayout()
        botones.addStretch()
        self.boton_cancelar = QPushButton("Cancelar")
        self.boton_cancelar.setObjectName("secundario")
        self.boton_guardar = QPushButton("Verificar y guardar")
        botones.addWidget(self.boton_cancelar)
        botones.addWidget(self.boton_guardar)
        layout.addLayout(botones)
        self.boton_cancelar.clicked.connect(self.reject)
        self.boton_guardar.clicked.connect(self._verificar)

    def _alternar_visibilidad(self, visible: bool) -> None:
        """Muestra u oculta la clave para que el usuario pueda revisarla."""
        self.campo.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.boton_ver.setText("Ocultar" if visible else "Mostrar")

    def _verificar(self) -> None:
        """Valida el formato básico y prueba la clave con Google en segundo plano."""
        clave = self.campo.text().strip().strip('"').strip("'")
        if len(clave) < 20 or " " in clave:
            self.estado.setText("Esa clave no parece válida. Cópiala completa desde Google AI Studio.")
            return
        self.boton_guardar.setEnabled(False)
        self.estado.setText("Verificando la clave con Google…")
        ejecutar(probar_clave, lambda n: self._guardar(clave, n), self._fallo, clave)

    def _guardar(self, clave: str, modelos: int) -> None:
        """Guarda la clave verificada y cierra la ventana."""
        config.guardar_en_env("GEMINI_API_KEY", clave)
        self.estado.setText(f"Clave válida ({modelos} modelos disponibles). Guardada.")
        self.accept()

    def _fallo(self, mensaje: str) -> None:
        """Explica por qué no se aceptó la clave."""
        self.boton_guardar.setEnabled(True)
        invalida = "API_KEY_INVALID" in mensaje or "API key not valid" in mensaje or "400" in mensaje
        self.estado.setText("Google rechazó la clave: revisa que esté completa y activa." if invalida
                            else f"No se pudo verificar (¿hay conexión a internet?): {mensaje[:150]}")
