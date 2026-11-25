"""Chat con el asistente médico virtual (Gemini) y el filtro de seguridad clínica."""

import html

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from app.ai.asistente import AsistenteMedico
from app.ai.prompts import SYSTEM_PROMPT, contexto_triaje
from app.ai.proveedores import ErrorProveedor, ProveedorGemini
from app.db import repositorio
from app.ui import estilos
from app.ui.comun import Sesion, ejecutar, etiqueta

SALUDO = ("Hola, soy el asistente médico virtual. Cuéntame qué síntomas tienes y desde cuándo. "
          "Recuerda que mi orientación no sustituye una consulta médica.")


class PaginaChat(QWidget):
    """Muestra la conversación; el modelo responde en segundo plano y los mensajes se guardan en la base."""

    def __init__(self, sesion: Sesion):
        """Construye el historial, el campo de texto y conecta el contexto del triaje."""
        super().__init__()
        self.sesion = sesion
        self.asistente: AsistenteMedico | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(etiqueta("Asistente médico virtual", "titulo"))
        layout.addWidget(etiqueta("Resuelve dudas sobre tus síntomas. Ante signos de alarma te indicará acudir a urgencias.", "nota"))
        self.historial = QTextBrowser()
        self.historial.setOpenExternalLinks(False)
        layout.addWidget(self.historial, 1)
        fila = QHBoxLayout()
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Escribe tu mensaje y pulsa Enter…")
        self.boton = QPushButton("Enviar")
        fila.addWidget(self.campo, 1)
        fila.addWidget(self.boton)
        layout.addLayout(fila)

        self.campo.returnPressed.connect(self._enviar)
        self.boton.clicked.connect(self._enviar)
        sesion.triaje_completado.connect(self._usar_contexto)
        self._agregar("asistente", SALUDO)

    def _agregar(self, rol: str, texto: str, alerta: bool = False) -> None:
        """Añade un mensaje con estilo de burbuja; el texto se escapa porque puede venir del usuario o del modelo."""
        contenido = html.escape(texto).replace("\n", "<br>")
        if rol == "usuario":
            bloque = (f"<table width='100%'><tr><td width='25%'></td><td style='background:{estilos.TEAL_FONDO};"
                      f"padding:8px;border-radius:6px'><b>Tú</b><br>{contenido}</td></tr></table>")
        else:
            color, fondo = (estilos.ROJO, estilos.ROJO_FONDO) if alerta else (estilos.PIZARRA, estilos.BLANCO)
            bloque = (f"<table width='100%'><tr><td style='background:{fondo};color:{color};padding:8px;"
                      f"border:1px solid {estilos.BORDE}'><b>Asistente</b><br>{contenido}</td>"
                      "<td width='25%'></td></tr></table>")
        self.historial.append(bloque)

    def _crear_asistente(self) -> AsistenteMedico:
        """Crea el asistente al primer mensaje; sin conexión a la base porque responde en otro hilo."""
        asistente = AsistenteMedico(ProveedorGemini(), triaje=self.sesion.ultimo_triaje)
        return asistente

    def _usar_contexto(self, resultado) -> None:
        """Cuando se completa un triaje, el asistente lo toma en cuenta en los siguientes mensajes."""
        if self.asistente is not None:
            self.asistente.instrucciones = SYSTEM_PROMPT + "\n\n" + contexto_triaje(
                resultado.dictamen_final, resultado.prolog.fase, resultado.r.probabilidad, resultado.motivos)

    def _enviar(self) -> None:
        """Muestra el mensaje del usuario y pide la respuesta en segundo plano."""
        texto = self.campo.text().strip()
        if not texto or not self.boton.isEnabled():
            return
        if self.asistente is None:
            try:
                self.asistente = self._crear_asistente()
            except ErrorProveedor as error:
                self._agregar("asistente", f"No puedo conectarme con el modelo de lenguaje: {error}", alerta=True)
                return
        self.campo.clear()
        self._agregar("usuario", texto)
        repositorio.guardar_mensaje(self.sesion.conexion, self.sesion.asegurar_consulta(), "usuario", texto)
        self.boton.setEnabled(False)
        self.campo.setPlaceholderText("El asistente está escribiendo…")
        ejecutar(self.asistente.enviar, self._recibir, self._fallo, texto)

    def _recibir(self, respuesta) -> None:
        """Muestra y guarda la respuesta; si hubo urgencia o duda, activa la derivación al médico."""
        self._listo()
        self._agregar("asistente", respuesta.texto, alerta=respuesta.derivar)
        modelo = "filtro_seguridad" if respuesta.urgencia else self.asistente.proveedor.nombre_modelo
        repositorio.guardar_mensaje(self.sesion.conexion, self.sesion.asegurar_consulta(), "asistente",
                                    respuesta.texto, respuesta.derivar, modelo)
        if respuesta.derivar:
            self.sesion.activar_derivacion("CHAT")

    def _fallo(self, mensaje: str) -> None:
        """Informa del error de red o de la API sin cerrar la conversación."""
        self._listo()
        # El historial del asistente ya incluye el mensaje del usuario sin respuesta; se quita para poder reenviarlo.
        if self.asistente.historial and self.asistente.historial[-1].rol == "usuario":
            self.asistente.historial.pop()
        self._agregar("asistente", f"No pude responder: {mensaje}. Intenta de nuevo en un momento.", alerta=True)

    def _listo(self) -> None:
        """Vuelve a habilitar el envío."""
        self.boton.setEnabled(True)
        self.campo.setPlaceholderText("Escribe tu mensaje y pulsa Enter…")
        self.campo.setFocus()
