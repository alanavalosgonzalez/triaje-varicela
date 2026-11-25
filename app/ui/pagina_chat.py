"""Chat con el asistente médico virtual (Gemini) y el filtro de seguridad clínica."""

import html

import time

from PySide6.QtCore import QTimer, Signal
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

    solicitar_clave = Signal()  # Se emite cuando falta la clave de Gemini, para abrir la ventana de configuración.

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

        # Contador visible mientras se espera la respuesta, para que se note que la app sigue trabajando.
        self._inicio_espera = 0.0
        self._contador = QTimer(self)
        self._contador.setInterval(1000)
        self._contador.timeout.connect(self._actualizar_espera)
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

    def reiniciar_asistente(self) -> None:
        """Usa la clave recién configurada conservando la conversación: solo se reemplaza la conexión con Gemini."""
        if self.asistente is None:
            return  # Se creará con la clave nueva en el próximo mensaje.
        try:
            self.asistente.proveedor = ProveedorGemini()
        except ErrorProveedor:
            self.asistente = None  # Si la clave nueva no sirve, el próximo mensaje lo explicará.

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
                if "GEMINI_API_KEY" in str(error):
                    self._agregar("asistente", "Para usar el asistente necesitas configurar tu clave de Gemini. "
                                  "Se abrirá la ventana de configuración; después vuelve a enviar tu mensaje.", alerta=True)
                    self.solicitar_clave.emit()
                else:
                    self._agregar("asistente", f"No puedo conectarme con el modelo de lenguaje: {error}", alerta=True)
                return
        self.campo.clear()
        self._agregar("usuario", texto)
        repositorio.guardar_mensaje(self.sesion.conexion, self.sesion.asegurar_consulta(), "usuario", texto)
        self.boton.setEnabled(False)
        self._inicio_espera = time.monotonic()
        self.sesion.guiar("Déjame pensar en lo que me cuentas…", "pensando")
        self._actualizar_espera()
        self._contador.start()
        # Se guardan el asistente y su proveedor de ESTE mensaje: si mientras tanto se cambia la clave y se reinicia
        # el asistente, la respuesta en camino sigue teniendo a quién referirse.
        asistente, proveedor = self.asistente, self.asistente.proveedor
        ejecutar(asistente.enviar,
                 lambda respuesta: self._recibir(respuesta, proveedor),
                 lambda mensaje: self._fallo(mensaje, asistente),
                 texto)

    def _recibir(self, respuesta, proveedor) -> None:
        """Muestra y guarda la respuesta; si hubo urgencia o duda, activa la derivación al médico."""
        self._listo()
        self._agregar("asistente", respuesta.texto, alerta=respuesta.derivar)
        modelo = "filtro_seguridad" if respuesta.urgencia else getattr(proveedor, "modelo_usado", proveedor.nombre_modelo)
        repositorio.guardar_mensaje(self.sesion.conexion, self.sesion.asegurar_consulta(), "asistente",
                                    respuesta.texto, respuesta.derivar, modelo)
        if respuesta.urgencia:
            self.sesion.guiar("Lo que describes puede ser serio. Por favor, busca atención médica ahora.", "preocupado")
        elif respuesta.derivar:
            self.sesion.guiar("Prefiero que te revise un médico. Ya puedes ver los centros cercanos.", "preocupado")
        else:
            self.sesion.guiar("Te respondí en el chat. Cuéntame más si quieres.", "feliz")
        if respuesta.derivar:
            self.sesion.activar_derivacion("CHAT")

    def _fallo(self, mensaje: str, asistente: AsistenteMedico) -> None:
        """Informa del error de red o de la API sin cerrar la conversación."""
        self._listo()
        # El historial del asistente ya incluye el mensaje del usuario sin respuesta; se quita para poder reenviarlo.
        if asistente.historial and asistente.historial[-1].rol == "usuario":
            asistente.historial.pop()
        self._agregar("asistente", f"No pude responder: {mensaje}. Intenta de nuevo en un momento.", alerta=True)
        self.sesion.guiar("No pude conectarme ahora. Inténtalo de nuevo en un momento.", "preocupado")

    def _actualizar_espera(self) -> None:
        """Muestra cuántos segundos lleva esperando la respuesta."""
        segundos = int(time.monotonic() - self._inicio_espera)
        aviso = " (el servicio está lento, probando otro modelo…)" if segundos >= 15 else ""
        self.campo.setPlaceholderText(f"El asistente está escribiendo… {segundos} s{aviso}")

    def _listo(self) -> None:
        """Vuelve a habilitar el envío."""
        self._contador.stop()
        self.boton.setEnabled(True)
        self.campo.setPlaceholderText("Escribe tu mensaje y pulsa Enter…")
        self.campo.setFocus()
