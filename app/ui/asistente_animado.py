"""Asistente animado "Doc": un personaje dibujado con QPainter que acompaña y guía al usuario.

Flota suavemente, parpadea, saluda y cambia de expresión según lo que ocurre en la aplicación.
Todo se dibuja con código (sin imágenes), usando la paleta clínica de la app.
"""

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

# Expresiones disponibles; las páginas eligen una al hablar.
EMOCIONES = ("feliz", "atento", "pensando", "preocupado", "celebrando")

# Colores del personaje: verde azulado clínico con detalles suaves.
CUERPO_CLARO = QColor("#7ED7D3")
CUERPO_OSCURO = QColor("#1F9AA6")
PANZA = QColor("#F4FBFB")
CONTORNO = QColor("#167C88")
OJOS = QColor("#16324F")
MEJILLAS = QColor(255, 128, 150, 170)
METAL = QColor("#C9D3DD")
ESTETOSCOPIO = QColor("#3B4A5A")


class MascotaDoc(QWidget):
    """Personaje animado. Se redibuja unas 30 veces por segundo según su estado y el tiempo."""

    clic = Signal()

    def __init__(self, parent=None):
        """Prepara el reloj de animación y el primer parpadeo."""
        super().__init__(parent)
        self.setFixedSize(150, 160)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Soy Doc, tu asistente. Haz clic para que te salude.")
        self.emocion = "feliz"
        self.t = 0.0
        self._siguiente_parpadeo = 2.0
        self._parpadeo_hasta = 0.0
        self._saludo_hasta = 1.6  # Saluda al abrir la app.
        self._celebracion_hasta = 0.0
        self._reloj = QTimer(self)
        self._reloj.timeout.connect(self._avanzar)
        self._reloj.start(33)

    # ------------------------------------------------------------------ Control desde fuera.

    def cambiar_emocion(self, emocion: str) -> None:
        """Cambia la expresión; "celebrando" además hace saltar al personaje unos segundos."""
        self.emocion = emocion if emocion in EMOCIONES else "feliz"
        if self.emocion == "celebrando":
            self._celebracion_hasta = self.t + 2.2

    def saludar(self) -> None:
        """Agita la mano durante un momento."""
        self._saludo_hasta = self.t + 1.6

    def mousePressEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Al hacer clic, saluda y avisa al panel."""
        self.saludar()
        self.clic.emit()

    # ------------------------------------------------------------------ Animación.

    def _avanzar(self) -> None:
        """Avanza el tiempo, programa parpadeos y pide redibujar."""
        self.t += 0.033
        if self.t >= self._siguiente_parpadeo:
            self._parpadeo_hasta = self.t + 0.14
            self._siguiente_parpadeo = self.t + random.uniform(2.5, 5.0)
        self.update()

    def _apertura_ojos(self) -> float:
        """1 = ojos abiertos, 0 = cerrados (durante el parpadeo)."""
        if self.t < self._parpadeo_hasta:
            return 0.1
        return 0.55 if self.emocion == "pensando" else 1.0

    # ------------------------------------------------------------------ Dibujo.

    def paintEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Dibuja sombra, cuerpo, bata, estetoscopio, cara, brazos y efectos según la emoción."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        celebrando = self.t < self._celebracion_hasta
        velocidad = 1.2 if self.emocion == "pensando" else 2.2
        flotacion = math.sin(self.t * velocidad) * 4
        salto = abs(math.sin(self.t * 7)) * 14 if celebrando else 0
        cx, cy = 75.0, 82.0 + flotacion - salto

        # Sombra en el suelo: se achica cuando el personaje sube.
        ancho_sombra = 70 - (flotacion + salto) * 1.2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(15, 76, 129, 40))
        p.drawEllipse(QPointF(75, 150), ancho_sombra / 2, 6)

        self._pies(p, cx, cy)
        self._brazo(p, cx - 44, cy + 6, izquierdo=True, angulo=math.sin(self.t * 1.8) * 6)
        angulo_derecho = math.sin(self.t * 12) * 28 - 55 if self.t < self._saludo_hasta else math.sin(self.t * 1.8 + 1) * 6
        if celebrando:
            angulo_derecho = -70 + math.sin(self.t * 14) * 15
        self._cuerpo(p, cx, cy)
        self._brazo(p, cx + 44, cy + 6, izquierdo=False, angulo=angulo_derecho)
        self._estetoscopio(p, cx, cy)
        self._espejo_frontal(p, cx, cy)
        self._cara(p, cx, cy)
        if self.emocion == "pensando":
            self._burbujas_pensamiento(p, cx, cy)
        if celebrando:
            self._destellos(p, cx, cy)
        p.end()

    def _cuerpo(self, p: QPainter, cx: float, cy: float) -> None:
        """Cuerpo redondo con degradado, panza clara y solapas de bata de médico."""
        degradado = QRadialGradient(QPointF(cx - 18, cy - 26), 70)
        degradado.setColorAt(0, CUERPO_CLARO)
        degradado.setColorAt(1, CUERPO_OSCURO)
        p.setPen(QPen(CONTORNO, 2))
        p.setBrush(QBrush(degradado))
        p.drawEllipse(QPointF(cx, cy), 46, 50)
        # Panza clara, como una bata.
        p.setPen(Qt.NoPen)
        p.setBrush(PANZA)
        p.drawEllipse(QPointF(cx, cy + 27), 30, 22)
        # Solapas de la bata.
        p.setPen(QPen(QColor("#D5E6EA"), 2))
        p.drawLine(QPointF(cx - 12, cy + 7), QPointF(cx, cy + 20))
        p.drawLine(QPointF(cx + 12, cy + 7), QPointF(cx, cy + 20))
        # Brillo en la cabeza.
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 90))
        p.drawEllipse(QPointF(cx - 20, cy - 30), 10, 6)

    def _pies(self, p: QPainter, cx: float, cy: float) -> None:
        """Dos pies redondeados."""
        p.setPen(QPen(CONTORNO, 2))
        p.setBrush(CUERPO_OSCURO)
        for dx in (-18, 18):
            p.drawEllipse(QPointF(cx + dx, cy + 48), 12, 7)

    def _brazo(self, p: QPainter, x: float, y: float, izquierdo: bool, angulo: float) -> None:
        """Brazo ovalado que gira desde el hombro (para saludar o balancearse)."""
        p.save()
        p.translate(x, y - 10)
        p.rotate(-angulo if izquierdo else angulo)
        p.setPen(QPen(CONTORNO, 2))
        p.setBrush(CUERPO_OSCURO)
        p.drawEllipse(QRectF(-7, 0, 14, 28))
        p.restore()

    def _estetoscopio(self, p: QPainter, cx: float, cy: float) -> None:
        """Estetoscopio colgado del cuello con su campana."""
        camino = QPainterPath(QPointF(cx - 24, cy + 8))
        camino.cubicTo(QPointF(cx - 22, cy + 36), QPointF(cx + 14, cy + 40), QPointF(cx + 16, cy + 26))
        p.setPen(QPen(ESTETOSCOPIO, 3, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawPath(camino)
        p.setPen(QPen(ESTETOSCOPIO, 2))
        p.setBrush(METAL)
        p.drawEllipse(QPointF(cx + 16, cy + 23), 5, 5)

    def _espejo_frontal(self, p: QPainter, cx: float, cy: float) -> None:
        """Espejo frontal de médico con su cinta."""
        p.setPen(QPen(QColor("#2C5D7C"), 3))
        p.drawArc(QRectF(cx - 42, cy - 46, 84, 92), 40 * 16, 100 * 16)
        p.setPen(QPen(QColor("#8A99A8"), 1.5))
        p.setBrush(METAL)
        p.drawEllipse(QPointF(cx, cy - 42), 9, 9)
        p.setBrush(QColor(255, 255, 255, 200))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx - 3, cy - 45), 3, 3)

    def _cara(self, p: QPainter, cx: float, cy: float) -> None:
        """Ojos (con parpadeo y mirada), cejas, mejillas y boca según la emoción."""
        apertura = self._apertura_ojos()
        mirada = QPointF(2.5, -2.5) if self.emocion == "pensando" else QPointF(math.sin(self.t * 0.7) * 1.2, 0)
        for dx in (-16, 16):
            ojo = QPointF(cx + dx, cy - 14)
            if apertura < 0.2:
                p.setPen(QPen(OJOS, 2.5, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(ojo + QPointF(-6, 0), ojo + QPointF(6, 0))
                continue
            p.setPen(Qt.NoPen)
            p.setBrush(Qt.white)
            p.drawEllipse(ojo, 9, 11 * apertura)
            p.setBrush(OJOS)
            p.drawEllipse(ojo + mirada, 5, 6 * apertura)
            p.setBrush(Qt.white)
            p.drawEllipse(ojo + mirada + QPointF(-1.8, -2.2), 1.8, 1.8)
        # Cejas: inclinadas si está preocupado, altas si está atento.
        p.setPen(QPen(OJOS, 2.2, Qt.SolidLine, Qt.RoundCap))
        if self.emocion == "preocupado":
            # La preocupación levanta el extremo interior de las cejas (bajarlo daría cara de enojo).
            p.drawLine(QPointF(cx - 23, cy - 25), QPointF(cx - 10, cy - 30))
            p.drawLine(QPointF(cx + 23, cy - 25), QPointF(cx + 10, cy - 30))
        elif self.emocion in ("atento", "celebrando"):
            p.drawArc(QRectF(cx - 24, cy - 33, 14, 8), 30 * 16, 120 * 16)
            p.drawArc(QRectF(cx + 10, cy - 33, 14, 8), 30 * 16, 120 * 16)
        # Mejillas.
        p.setPen(Qt.NoPen)
        p.setBrush(MEJILLAS)
        for dx in (-27, 27):
            p.drawEllipse(QPointF(cx + dx, cy - 2), 6, 3.5)
        # Boca.
        p.setPen(QPen(OJOS, 2.4, Qt.SolidLine, Qt.RoundCap))
        if self.emocion == "celebrando" or (self.emocion == "feliz" and self.t < self._saludo_hasta):
            boca = QPainterPath(QPointF(cx - 9, cy - 1))
            boca.quadTo(QPointF(cx, cy + 12), QPointF(cx + 9, cy - 1))
            boca.closeSubpath()
            p.setBrush(QColor("#C2475A"))
            p.drawPath(boca)
        elif self.emocion == "preocupado":
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - 7, cy + 1, 14, 8), 20 * 16, 140 * 16)
        elif self.emocion == "pensando":
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx + 4, cy + 3), 3, 2.5)
        else:
            p.setBrush(Qt.NoBrush)
            ancho = 16 if self.emocion == "feliz" else 12
            p.drawArc(QRectF(cx - ancho / 2, cy - 6, ancho, 10), 200 * 16, 140 * 16)

    def _burbujas_pensamiento(self, p: QPainter, cx: float, cy: float) -> None:
        """Tres puntos que se encienden por turnos, como "estoy pensando…"."""
        for i in range(3):
            brillo = 0.35 + 0.65 * max(0.0, math.sin(self.t * 5 - i * 0.9))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 128, 128, int(255 * brillo)))
            p.drawEllipse(QPointF(cx + 30 + i * 11, cy - 58 - i * 3), 4 + i * 0.6, 4 + i * 0.6)

    def _destellos(self, p: QPainter, cx: float, cy: float) -> None:
        """Pequeñas estrellas que giran alrededor al celebrar."""
        p.setPen(Qt.NoPen)
        for i in range(5):
            angulo = self.t * 3 + i * (2 * math.pi / 5)
            x, y = cx + math.cos(angulo) * 62, cy - 10 + math.sin(angulo) * 48
            tamano = 3 + 2 * abs(math.sin(self.t * 6 + i))
            p.setBrush(QColor("#F6C343") if i % 2 else QColor("#3DB4C9"))
            estrella = QPainterPath()
            for k in range(8):
                radio = tamano if k % 2 == 0 else tamano / 2.5
                punto = QPointF(x + math.cos(k * math.pi / 4) * radio, y + math.sin(k * math.pi / 4) * radio)
                estrella.moveTo(punto) if k == 0 else estrella.lineTo(punto)
            estrella.closeSubpath()
            p.drawPath(estrella)


class GloboTexto(QLabel):
    """Globo de diálogo que escribe su texto letra por letra."""

    def __init__(self, parent=None):
        """Configura el estilo y el temporizador de escritura."""
        super().__init__(parent)
        self.setObjectName("globo")
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._completo = ""
        self._mostrados = 0
        self._escritura = QTimer(self)
        self._escritura.timeout.connect(self._escribir_letra)

    def escribir(self, texto: str) -> None:
        """Empieza a escribir un texto nuevo desde el principio."""
        self._completo, self._mostrados = texto, 0
        self.setText("")
        self._escritura.start(16)

    def _escribir_letra(self) -> None:
        """Muestra dos letras más por paso hasta completar el texto."""
        self._mostrados = min(len(self._completo), self._mostrados + 2)
        self.setText(self._completo[:self._mostrados])
        if self._mostrados >= len(self._completo):
            self._escritura.stop()


class PanelAsistente(QWidget):
    """Globo de texto más el personaje; las páginas le piden que diga algo con una emoción."""

    def __init__(self, parent=None):
        """Coloca el globo encima del personaje."""
        super().__init__(parent)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(10, 6, 10, 4)
        capa.setSpacing(2)
        self.globo = GloboTexto()
        self.mascota = MascotaDoc()
        capa.addWidget(self.globo)
        capa.addWidget(self.mascota, 0, Qt.AlignHCenter)
        self._consejos: list[str] = []
        self._indice_consejo = 0
        self.mascota.clic.connect(self._siguiente_consejo)

    def decir(self, texto: str, emocion: str = "feliz", consejos: list[str] | None = None) -> None:
        """Muestra un mensaje con la expresión indicada; los consejos opcionales salen al hacer clic en Doc."""
        self.mascota.cambiar_emocion(emocion)
        self.globo.escribir(texto)
        if consejos is not None:
            self._consejos, self._indice_consejo = consejos, 0

    def _siguiente_consejo(self) -> None:
        """Al hacer clic en Doc, muestra el siguiente consejo de la página actual."""
        if self._consejos:
            self.globo.escribir(self._consejos[self._indice_consejo % len(self._consejos)])
            self._indice_consejo += 1
