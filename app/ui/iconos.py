"""Íconos de línea dibujados con QPainter: sustituyen a los emojis con un estilo sobrio y profesional."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

AZUL = "#0F4C81"


def _lienzo(tamano: int) -> tuple[QPixmap, QPainter]:
    """Crea un lienzo transparente al doble de resolución (se ve nítido en pantallas de alta densidad)."""
    pixmap = QPixmap(tamano * 2, tamano * 2)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(2)
    pintor = QPainter(pixmap)
    pintor.setRenderHint(QPainter.Antialiasing)
    pintor.scale(tamano / 24, tamano / 24)  # Todos los íconos se dibujan en una cuadrícula de 24 x 24.
    return pixmap, pintor


def icono(nombre: str, color: str = AZUL, tamano: int = 20, punto: str | None = None) -> QIcon:
    """Devuelve el ícono pedido; `punto` agrega un pequeño círculo de aviso en la esquina (por ejemplo, ámbar)."""
    pixmap, p = _lienzo(tamano)
    p.setPen(QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    DIBUJOS[nombre](p)
    if punto:
        p.setPen(QPen(QColor("#FFFFFF"), 1.5))
        p.setBrush(QColor(punto))
        p.drawEllipse(QPointF(19.5, 4.5), 4, 4)
    p.end()
    return QIcon(pixmap)


def _cuestionario(p: QPainter) -> None:
    """Portapapeles con una marca de verificación."""
    p.drawRoundedRect(QRectF(5, 4, 14, 17), 2, 2)
    p.drawRoundedRect(QRectF(9, 2.5, 6, 3.5), 1, 1)
    p.drawPolyline([QPointF(8.5, 13), QPointF(11, 15.5), QPointF(15.5, 10.5)])


def _chat(p: QPainter) -> None:
    """Globo de conversación con tres puntos."""
    camino = QPainterPath(QPointF(4, 6))
    camino.addRoundedRect(QRectF(3, 4, 18, 13), 4, 4)
    p.drawPath(camino)
    p.drawPolyline([QPointF(8, 17), QPointF(7, 21), QPointF(12, 17)])
    for x in (8.5, 12, 15.5):
        p.drawPoint(QPointF(x, 10.5))


def _imagen(p: QPainter) -> None:
    """Cámara fotográfica."""
    p.drawRoundedRect(QRectF(3, 7, 18, 13), 2.5, 2.5)
    p.drawPolyline([QPointF(8, 7), QPointF(9.5, 4.5), QPointF(14.5, 4.5), QPointF(16, 7)])
    p.drawEllipse(QPointF(12, 13.5), 3.8, 3.8)


def _informacion(p: QPainter) -> None:
    """Libro abierto."""
    p.drawPolyline([QPointF(12, 6), QPointF(7, 4.5), QPointF(3, 5), QPointF(3, 19), QPointF(7, 18.5), QPointF(12, 20)])
    p.drawPolyline([QPointF(12, 6), QPointF(17, 4.5), QPointF(21, 5), QPointF(21, 19), QPointF(17, 18.5), QPointF(12, 20)])
    p.drawLine(QPointF(12, 6), QPointF(12, 20))


def _mapa(p: QPainter) -> None:
    """Marcador de ubicación."""
    # Arco superior de 240 grados y dos líneas que se unen en la punta.
    p.drawArc(QRectF(5.5, 3, 13, 13), -30 * 16, 240 * 16)
    p.drawLine(QPointF(17.63, 12.75), QPointF(12, 21.5))
    p.drawLine(QPointF(6.37, 12.75), QPointF(12, 21.5))
    p.drawEllipse(QPointF(12, 9.5), 2.6, 2.6)


def _historial(p: QPainter) -> None:
    """Reloj."""
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    p.drawPolyline([QPointF(12, 7), QPointF(12, 12), QPointF(15.5, 14)])


def _configuracion(p: QPainter) -> None:
    """Engrane de ocho dientes."""
    for i in range(8):
        angulo = i * math.pi / 4
        p.drawLine(QPointF(12 + math.cos(angulo) * 7, 12 + math.sin(angulo) * 7),
                   QPointF(12 + math.cos(angulo) * 9.5, 12 + math.sin(angulo) * 9.5))
    p.drawEllipse(QPointF(12, 12), 6.5, 6.5)
    p.drawEllipse(QPointF(12, 12), 2.5, 2.5)


def _cruz(p: QPainter) -> None:
    """Cruz médica."""
    camino = QPainterPath()
    camino.addRoundedRect(QRectF(9, 3, 6, 18), 1.5, 1.5)
    camino.addRoundedRect(QRectF(3, 9, 18, 6), 1.5, 1.5)
    p.drawPath(camino.simplified())


def _alerta(p: QPainter) -> None:
    """Triángulo de advertencia."""
    p.drawPolygon([QPointF(12, 3.5), QPointF(21.5, 20), QPointF(2.5, 20)])
    p.drawLine(QPointF(12, 9.5), QPointF(12, 14))
    p.drawPoint(QPointF(12, 17))


def _verificado(p: QPainter) -> None:
    """Círculo con marca de verificación."""
    p.drawEllipse(QPointF(12, 12), 9, 9)
    p.drawPolyline([QPointF(8, 12.5), QPointF(11, 15.5), QPointF(16.5, 9.5)])


DIBUJOS = {
    "cuestionario": _cuestionario, "chat": _chat, "imagen": _imagen, "informacion": _informacion,
    "mapa": _mapa, "historial": _historial, "configuracion": _configuracion, "cruz": _cruz,
    "alerta": _alerta, "verificado": _verificado,
}
