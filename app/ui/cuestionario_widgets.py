"""Componentes visuales del cuestionario: tarjetas de pregunta ilustradas, indicador de pasos, medidor y alertas.

Las ilustraciones se dibujan con QPainter. Las de las lesiones (mácula, pápula, vesícula, costra) ayudan al
usuario a reconocer cada fase de la erupción de varicela al responder.
"""

import math

from PySide6.QtCore import (
    QEasingCurve, QPointF, QRectF, QPropertyAnimation, Qt, Signal,
    Property, QPoint,
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.ui import estilos
from app.ui.iconos import icono

# Explicaciones breves que aparecen bajo cada pregunta para ayudar a responder con precisión.
DESCRIPCIONES = {
    "fiebre_moderada": "Temperatura entre 37.8 y 39 °C, medida con termómetro.",
    "malestar_general": "Cansancio, decaimiento o sensación de estar enfermo.",
    "perdida_apetito": "Menos ganas de comer que de costumbre.",
    "cefalea": "Dolor de cabeza en los últimos días.",
    "maculas": "Manchas rojas planas: al pasar el dedo no se sienten en relieve.",
    "papulas": "Granitos rojos que sobresalen un poco de la piel.",
    "vesiculas": "Ampollas pequeñas con líquido claro, como gotas de agua sobre piel roja.",
    "costras": "Lesiones secas de color café, cuando las ampollas se rompen y cicatrizan.",
    "lesiones_simultaneas": "A la vez hay manchas, granitos, ampollas y costras: es muy típico de la varicela.",
    "inicio_tronco": "Las primeras lesiones salieron en pecho, espalda, cara o cuero cabelludo.",
    "prurito": "Comezón fuerte que provoca ganas de rascarse.",
    "dificultad_respiratoria": "Falta de aire, respiración rápida o dolor en el pecho.",
    "fiebre_alta_persistente": "Más de 39 °C durante más de 3 días.",
    "lesiones_infectadas": "Lesiones con pus, muy rojas, calientes o hinchadas.",
    "confusion_rigidez": "Confusión, mucho sueño, convulsiones o dificultad para mover el cuello.",
}

PIEL = QColor("#F6D9C8")
PIEL_OSCURA = QColor("#E8BFA8")
ROJO_LESION = QColor("#D9566B")


# ---------------------------------------------------------------------------- Ilustraciones de síntomas.

def _piel(p: QPainter) -> None:
    """Fondo circular de piel para las ilustraciones de lesiones."""
    gradiente = QRadialGradient(QPointF(26, 24), 38)
    gradiente.setColorAt(0, PIEL)
    gradiente.setColorAt(1, PIEL_OSCURA)
    p.setPen(Qt.NoPen)
    p.setBrush(gradiente)
    p.drawEllipse(QRectF(2, 2, 60, 60))


def _papula(p: QPainter, x: float, y: float, r: float) -> None:
    """Granito en relieve: rojo con un brillo que sugiere volumen."""
    g = QRadialGradient(QPointF(x - r * 0.35, y - r * 0.35), r * 1.4)
    g.setColorAt(0, QColor("#F08A9A"))
    g.setColorAt(1, ROJO_LESION)
    p.setBrush(g)
    p.drawEllipse(QPointF(x, y), r, r)


def _vesicula(p: QPainter, x: float, y: float, r: float) -> None:
    """Ampolla: base roja con una gota transparente encima."""
    p.setBrush(QColor(217, 86, 107, 150))
    p.drawEllipse(QPointF(x, y + r * 0.25), r * 1.35, r * 1.2)
    g = QRadialGradient(QPointF(x - r * 0.3, y - r * 0.4), r * 1.2)
    g.setColorAt(0, QColor(255, 255, 255, 250))
    g.setColorAt(1, QColor(214, 236, 246, 210))
    p.setBrush(g)
    p.setPen(QPen(QColor(190, 120, 130), 0.8))
    p.drawEllipse(QPointF(x, y), r, r * 0.9)
    p.setPen(Qt.NoPen)


def _costra(p: QPainter, x: float, y: float, r: float) -> None:
    """Costra: forma irregular color café."""
    camino = QPainterPath()
    for i in range(7):
        angulo = i * 2 * math.pi / 7
        radio = r * (0.75 + 0.3 * ((i * 37) % 5) / 4)
        punto = QPointF(x + math.cos(angulo) * radio, y + math.sin(angulo) * radio)
        camino.moveTo(punto) if i == 0 else camino.lineTo(punto)
    camino.closeSubpath()
    p.setBrush(QColor("#8A5A3C"))
    p.drawPath(camino)


def _termometro(p: QPainter, nivel: float, color: QColor) -> None:
    """Termómetro con el nivel indicado (0 a 1)."""
    p.setPen(QPen(QColor("#5C6B7A"), 2))
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(27, 6, 10, 40), 5, 5)
    p.drawEllipse(QPointF(32, 50), 8, 8)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(32, 50), 5.5, 5.5)
    alto = 34 * nivel
    p.drawRoundedRect(QRectF(29.5, 46 - alto, 5, alto + 2), 2.5, 2.5)


def dibujar_ilustracion(codigo: str, p: QPainter) -> None:
    """Dibuja la ilustración del síntoma en un área de 64 x 64."""
    p.setPen(Qt.NoPen)
    if codigo == "maculas":
        _piel(p)
        p.setBrush(QColor(217, 86, 107, 170))
        for x, y, r in ((22, 24, 6), (40, 20, 5), (30, 40, 7), (46, 38, 4.5)):
            p.drawEllipse(QPointF(x, y), r, r * 0.85)
    elif codigo == "papulas":
        _piel(p)
        for x, y, r in ((22, 24, 5.5), (40, 22, 4.5), (30, 40, 6), (46, 40, 4)):
            _papula(p, x, y, r)
    elif codigo == "vesiculas":
        _piel(p)
        for x, y, r in ((24, 26, 7), (42, 24, 5.5), (32, 42, 6.5)):
            _vesicula(p, x, y, r)
    elif codigo == "costras":
        _piel(p)
        for x, y, r in ((24, 26, 6.5), (42, 24, 5), (33, 42, 7)):
            _costra(p, x, y, r)
    elif codigo == "lesiones_simultaneas":
        _piel(p)
        p.setBrush(QColor(217, 86, 107, 170))
        p.drawEllipse(QPointF(20, 22), 5.5, 4.8)
        _papula(p, 42, 20, 5)
        _vesicula(p, 22, 42, 6)
        _costra(p, 43, 42, 6)
    elif codigo == "inicio_tronco":
        p.setPen(QPen(QColor("#5C6B7A"), 1.6))
        p.setBrush(QColor("#E8EEF4"))
        p.drawEllipse(QPointF(32, 13), 8, 8)
        cuerpo = QPainterPath()
        cuerpo.addRoundedRect(QRectF(20, 22, 24, 26), 8, 8)
        p.drawPath(cuerpo)
        p.drawRoundedRect(QRectF(12, 24, 7, 22), 3.5, 3.5)
        p.drawRoundedRect(QRectF(45, 24, 7, 22), 3.5, 3.5)
        p.drawRoundedRect(QRectF(23, 48, 7, 13), 3.5, 3.5)
        p.drawRoundedRect(QRectF(34, 48, 7, 13), 3.5, 3.5)
        p.setPen(Qt.NoPen)
        p.setBrush(ROJO_LESION)
        for x, y in ((28, 30), (36, 33), (31, 39), (38, 42), (26, 44), (30, 11), (35, 15)):
            p.drawEllipse(QPointF(x, y), 1.8, 1.8)
    elif codigo == "prurito":
        _piel(p)
        _papula(p, 24, 36, 4)
        _papula(p, 40, 40, 3.5)
        p.setPen(QPen(QColor(205, 90, 100, 200), 2.2, Qt.SolidLine, Qt.RoundCap))
        for dx in (0, 6, 12):
            p.drawLine(QPointF(20 + dx, 14), QPointF(30 + dx, 30))
    elif codigo == "fiebre_moderada":
        _termometro(p, 0.55, QColor("#E3A13B"))
    elif codigo == "fiebre_alta_persistente":
        _termometro(p, 0.95, QColor("#C0392B"))
        p.setPen(QPen(QColor("#C0392B"), 1.8, Qt.SolidLine, Qt.RoundCap))
        for y in (12, 20, 28):
            p.drawLine(QPointF(44, y), QPointF(52, y - 3))
    elif codigo == "malestar_general":
        p.setPen(QPen(QColor("#5C6B7A"), 2))
        p.setBrush(QColor("#FCE9B8"))
        p.drawEllipse(QRectF(10, 10, 44, 44))
        p.drawArc(QRectF(19, 26, 9, 6), 200 * 16, 140 * 16)
        p.drawArc(QRectF(36, 26, 9, 6), 200 * 16, 140 * 16)
        p.drawLine(QPointF(26, 42), QPointF(38, 42))
    elif codigo == "perdida_apetito":
        p.setPen(QPen(QColor("#5C6B7A"), 2))
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(10, 14, 38, 38))
        p.drawEllipse(QRectF(18, 22, 22, 22))
        p.drawLine(QPointF(54, 14), QPointF(54, 52))
        for x in (51, 54, 57):
            p.drawLine(QPointF(x, 14), QPointF(x, 22))
    elif codigo == "cefalea":
        p.setPen(QPen(QColor("#5C6B7A"), 2))
        p.setBrush(QColor("#E8EEF4"))
        p.drawEllipse(QRectF(14, 14, 32, 36))
        p.setPen(QPen(QColor("#D9566B"), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(44, 10), QPointF(49, 16), QPointF(46, 19), QPointF(53, 25)])
        p.drawPolyline([QPointF(8, 14), QPointF(13, 19), QPointF(9, 22)])
    elif codigo == "dificultad_respiratoria":
        p.setPen(QPen(QColor("#B03A48"), 2))
        p.setBrush(QColor("#F4C7CE"))
        izquierdo = QPainterPath(QPointF(29, 18))
        izquierdo.cubicTo(QPointF(14, 18), QPointF(9, 44), QPointF(14, 52))
        izquierdo.cubicTo(QPointF(20, 56), QPointF(29, 50), QPointF(29, 18))
        p.drawPath(izquierdo)
        derecho = QPainterPath(QPointF(35, 18))
        derecho.cubicTo(QPointF(50, 18), QPointF(55, 44), QPointF(50, 52))
        derecho.cubicTo(QPointF(44, 56), QPointF(35, 50), QPointF(35, 18))
        p.drawPath(derecho)
        p.drawLine(QPointF(32, 6), QPointF(32, 20))
    elif codigo == "lesiones_infectadas":
        _piel(p)
        p.setBrush(QColor(217, 60, 80, 120))
        p.drawEllipse(QPointF(32, 32), 18, 16)
        p.setBrush(ROJO_LESION)
        p.drawEllipse(QPointF(32, 32), 10, 9)
        p.setBrush(QColor("#F2D15C"))
        p.drawEllipse(QPointF(32, 31), 5, 4.5)
    elif codigo == "confusion_rigidez":
        p.setPen(QPen(QColor("#5C6B7A"), 2))
        p.setBrush(QColor("#E8EEF4"))
        p.drawEllipse(QRectF(14, 10, 36, 38))
        p.setPen(QPen(QColor("#7A5CB0"), 2, Qt.SolidLine, Qt.RoundCap))
        espiral = QPainterPath(QPointF(32, 29))
        for i in range(1, 40):
            angulo, radio = i * 0.42, i * 0.28
            espiral.lineTo(QPointF(32 + math.cos(angulo) * radio, 29 + math.sin(angulo) * radio))
        p.setBrush(Qt.NoBrush)
        p.drawPath(espiral)
        p.setPen(QPen(QColor("#5C6B7A"), 2))
        p.drawLine(QPointF(26, 48), QPointF(26, 58))
        p.drawLine(QPointF(38, 48), QPointF(38, 58))


class Ilustracion(QWidget):
    """Muestra la ilustración de un síntoma; hace un pequeño "rebote" al responder."""

    def __init__(self, codigo: str, parent=None):
        """Guarda el código del síntoma y prepara la animación de escala."""
        super().__init__(parent)
        self.codigo = codigo
        self._escala = 1.0
        self.setFixedSize(68, 68)
        self._rebote = QPropertyAnimation(self, b"escala", self)
        self._rebote.setDuration(420)
        self._rebote.setKeyValueAt(0, 1.0)
        self._rebote.setKeyValueAt(0.4, 1.14)
        self._rebote.setKeyValueAt(1, 1.0)
        self._rebote.setEasingCurve(QEasingCurve.OutCubic)

    def _leer_escala(self) -> float:
        """Escala actual del dibujo."""
        return self._escala

    def _poner_escala(self, valor: float) -> None:
        """Cambia la escala y redibuja."""
        self._escala = valor
        self.update()

    escala = Property(float, _leer_escala, _poner_escala)

    def rebotar(self) -> None:
        """Reproduce el rebote."""
        self._rebote.start()

    def paintEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Dibuja la ilustración centrada con la escala actual."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.translate(34, 34)
        p.scale(self._escala, self._escala)
        p.translate(-32, -32)
        dibujar_ilustracion(self.codigo, p)
        p.end()


# ---------------------------------------------------------------------------- Tarjeta de pregunta.

OPCIONES = [("Sí", True), ("No", False), ("No sé", None)]


class TarjetaPregunta(QFrame):
    """Pregunta con ilustración, explicación y tres botones grandes; se ilumina al responderla."""

    respondida = Signal(str, object)  # Código del síntoma y valor (True, False o None).

    def __init__(self, codigo: str, texto: str, es_alarma: bool = False, parent=None):
        """Construye la tarjeta y sus botones de respuesta."""
        super().__init__(parent)
        self.codigo, self.es_alarma = codigo, es_alarma
        self.setObjectName("pregunta")
        self.setProperty("estado", "pendiente")
        self.setProperty("alarma", es_alarma)
        capa = QHBoxLayout(self)
        capa.setContentsMargins(12, 10, 14, 10)
        capa.setSpacing(14)
        self.ilustracion = Ilustracion(codigo)
        capa.addWidget(self.ilustracion)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        titulo = QLabel(texto)
        titulo.setObjectName("pregunta_titulo")
        titulo.setWordWrap(True)
        descripcion = QLabel(DESCRIPCIONES.get(codigo, ""))
        descripcion.setObjectName("pregunta_ayuda")
        descripcion.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(descripcion)
        capa.addLayout(textos, 1)
        self.botones: list[QPushButton] = []
        for indice, (nombre, _) in enumerate(OPCIONES):
            boton = QPushButton(nombre)
            boton.setObjectName("opcion")
            boton.setProperty("tipo", ("si_alarma" if es_alarma else "si", "no", "nose")[indice])
            boton.setCheckable(True)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setMinimumWidth(66)
            boton.clicked.connect(lambda _=False, i=indice: self.seleccionar(i))
            self.botones.append(boton)
            capa.addWidget(boton)
        self._indice = -1

    def seleccionar(self, indice: int) -> None:
        """Marca una opción, actualiza el estilo de la tarjeta y avisa con la señal `respondida`."""
        for i, boton in enumerate(self.botones):
            boton.setChecked(i == indice)
        nuevo = indice != self._indice
        self._indice = indice
        valor = OPCIONES[indice][1]
        self.setProperty("estado", "alarma" if (self.es_alarma and valor is True) else "respondida")
        self.style().unpolish(self)
        self.style().polish(self)
        if nuevo:
            self.ilustracion.rebotar()
        self.respondida.emit(self.codigo, valor)

    def valor(self) -> tuple[bool, bool | None]:
        """Devuelve (respondida, valor)."""
        return (self._indice >= 0, OPCIONES[self._indice][1] if self._indice >= 0 else None)

    def limpiar(self) -> None:
        """Quita la respuesta para empezar un triaje nuevo."""
        self._indice = -1
        for boton in self.botones:
            boton.setChecked(False)
        self.setProperty("estado", "pendiente")
        self.style().unpolish(self)
        self.style().polish(self)

    def resaltar_pendiente(self) -> None:
        """Marca la tarjeta en ámbar (hasta que se responda) y la sacude levemente para señalar que falta."""
        self.setProperty("estado", "faltante")
        self.style().unpolish(self)
        self.style().polish(self)
        inicio = self.pos()
        sacudida = QPropertyAnimation(self, b"pos", self)
        sacudida.setDuration(380)
        for paso, dx in enumerate((0, -8, 8, -5, 5, 0)):
            sacudida.setKeyValueAt(paso / 5, inicio + QPoint(dx, 0))
        sacudida.start(QPropertyAnimation.DeleteWhenStopped)


# ---------------------------------------------------------------------------- Indicador de pasos.

class IndicadorPasos(QWidget):
    """Círculos numerados unidos por una línea que se rellena de forma animada al avanzar."""

    def __init__(self, nombres: list[str], parent=None):
        """Guarda los nombres de los pasos y prepara la animación del avance."""
        super().__init__(parent)
        self.nombres = nombres
        self._avance = 0.0
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._animacion = QPropertyAnimation(self, b"avance", self)
        self._animacion.setDuration(550)
        self._animacion.setEasingCurve(QEasingCurve.InOutCubic)

    def _leer(self) -> float:
        """Avance actual (0 = primer paso; len(nombres) = completado)."""
        return self._avance

    def _poner(self, valor: float) -> None:
        """Actualiza el avance y redibuja."""
        self._avance = valor
        self.update()

    avance = Property(float, _leer, _poner)

    def ir_a(self, paso: int) -> None:
        """Anima la línea hasta el paso indicado."""
        self._animacion.stop()
        self._animacion.setStartValue(self._avance)
        self._animacion.setEndValue(float(paso))
        self._animacion.start()

    def paintEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Dibuja la línea base, la parte completada y cada círculo con su estado."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        n = len(self.nombres)
        margen = 64  # Deja espacio para que las etiquetas de los extremos no se corten.
        ancho = self.width() - 2 * margen
        xs = [margen + ancho * i / (n - 1) for i in range(n)]
        y = 20
        p.setPen(QPen(QColor("#DCE6F0"), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(xs[0], y), QPointF(xs[-1], y))
        hasta = min(self._avance, n - 1)
        x_fin = xs[0] + (xs[-1] - xs[0]) * hasta / (n - 1)
        degradado = QLinearGradient(QPointF(xs[0], y), QPointF(xs[-1], y))
        degradado.setColorAt(0, QColor(estilos.TEAL))
        degradado.setColorAt(1, QColor("#3DB4C9"))
        p.setPen(QPen(degradado, 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(xs[0], y), QPointF(x_fin, y))
        fuente = QFont(self.font())
        for i, (x, nombre) in enumerate(zip(xs, self.nombres)):
            completado = self._avance >= i + 1 - 0.01
            actual = not completado and self._avance >= i - 0.01
            if actual:  # Halo alrededor del paso actual.
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 128, 128, 45))
                p.drawEllipse(QPointF(x, y), 19, 19)
            p.setPen(QPen(QColor(estilos.TEAL) if (completado or actual) else QColor("#C5D3E0"), 2))
            p.setBrush(QColor(estilos.TEAL) if completado else QColor("#FFFFFF"))
            p.drawEllipse(QPointF(x, y), 13, 13)
            if completado:
                p.setPen(QPen(QColor("#FFFFFF"), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPolyline([QPointF(x - 5, y), QPointF(x - 1.5, y + 4), QPointF(x + 5.5, y - 4)])
            else:
                fuente.setBold(True)
                fuente.setPointSizeF(9.5)
                p.setFont(fuente)
                p.setPen(QColor(estilos.TEAL) if actual else QColor("#8FA3B8"))
                p.drawText(QRectF(x - 13, y - 13, 26, 26), Qt.AlignCenter, str(i + 1))
            fuente.setBold(actual)
            fuente.setPointSizeF(9)
            p.setFont(fuente)
            p.setPen(QColor(estilos.AZUL_OSCURO) if (actual or completado) else QColor("#8FA3B8"))
            p.drawText(QRectF(x - 60, y + 18, 120, 20), Qt.AlignHCenter | Qt.AlignTop, nombre)
        p.end()


# ---------------------------------------------------------------------------- Medidor de probabilidad.

class MedidorProbabilidad(QWidget):
    """Medidor semicircular con zonas de color y una aguja que avanza animada hasta la probabilidad."""

    def __init__(self, parent=None):
        """Prepara el valor y la animación de la aguja."""
        super().__init__(parent)
        self._valor = 0.0
        self.setFixedSize(260, 160)
        self._animacion = QPropertyAnimation(self, b"valor", self)
        self._animacion.setDuration(1400)
        self._animacion.setEasingCurve(QEasingCurve.OutBack)

    def _leer(self) -> float:
        """Valor mostrado (0 a 1)."""
        return self._valor

    def _poner(self, valor: float) -> None:
        """Actualiza el valor y redibuja."""
        self._valor = max(0.0, min(1.0, valor))
        self.update()

    valor = Property(float, _leer, _poner)

    def mostrar(self, probabilidad: float) -> None:
        """Lleva la aguja desde cero hasta la probabilidad indicada."""
        self._animacion.stop()
        self._animacion.setStartValue(0.0)
        self._animacion.setEndValue(float(probabilidad))
        self._animacion.start()

    def paintEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Dibuja las tres zonas (bajo, sospecha, alto), la aguja y el porcentaje."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        centro = QPointF(130, 128)
        radio = 100
        rect = QRectF(centro.x() - radio, centro.y() - radio, 2 * radio, 2 * radio)
        # Zonas con los mismos cortes que el motor estadístico: 30 % y 70 %.
        for inicio, fin, color in ((0.0, 0.30, estilos.TEAL), (0.30, 0.70, "#E3A13B"), (0.70, 1.0, estilos.ROJO)):
            p.setPen(QPen(QColor(color), 16, Qt.SolidLine, Qt.FlatCap))
            p.drawArc(rect, int((180 - inicio * 180) * 16), int(-(fin - inicio) * 180 * 16))
        angulo = math.radians(180 - self._valor * 180)
        punta = QPointF(centro.x() + math.cos(angulo) * (radio - 22), centro.y() - math.sin(angulo) * (radio - 22))
        p.setPen(QPen(QColor(estilos.AZUL_OSCURO), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(centro, punta)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(estilos.AZUL_OSCURO))
        p.drawEllipse(centro, 8, 8)
        fuente = QFont(self.font())
        fuente.setPointSize(18)
        fuente.setBold(True)
        p.setFont(fuente)
        p.setPen(QColor(estilos.AZUL_OSCURO))
        texto = ">99 %" if self._valor > 0.99 else f"{self._valor * 100:.0f} %"
        p.drawText(QRectF(0, centro.y() - 62, 260, 30), Qt.AlignHCenter, texto)
        fuente.setPointSize(8)
        fuente.setBold(False)
        p.setFont(fuente)
        p.setPen(QColor(estilos.PIZARRA_SUAVE))
        p.drawText(QRectF(0, centro.y() + 12, 260, 20), Qt.AlignHCenter, "probabilidad estadística de varicela")
        p.end()


# ---------------------------------------------------------------------------- Aviso de alarma.

class AvisoAlarma(QFrame):
    """Banda roja que aparece con animación cuando el paciente marca un signo de alarma."""

    def __init__(self, parent=None):
        """Construye la banda oculta, con su ícono y texto."""
        super().__init__(parent)
        self.setObjectName("aviso_alarma")
        capa = QHBoxLayout(self)
        capa.setContentsMargins(14, 10, 14, 10)
        simbolo = QLabel()
        simbolo.setPixmap(icono("alerta", estilos.ROJO, 22).pixmap(22, 22))
        self.texto = QLabel("Marcaste un signo de alarma: busca atención médica lo antes posible, "
                            "sin esperar al resultado del cuestionario.")
        self.texto.setWordWrap(True)
        capa.addWidget(simbolo)
        capa.addWidget(self.texto, 1)
        self.setMaximumHeight(0)
        self._altura = QPropertyAnimation(self, b"maximumHeight", self)
        self._altura.setDuration(350)
        self._altura.setEasingCurve(QEasingCurve.OutCubic)
        self.visible_alarma = False

    def mostrar(self, visible: bool) -> None:
        """Despliega u oculta la banda con una animación de altura."""
        if visible == self.visible_alarma:
            return
        self.visible_alarma = visible
        self._altura.stop()
        self._altura.setStartValue(self.maximumHeight())
        self._altura.setEndValue(90 if visible else 0)
        self._altura.start()
