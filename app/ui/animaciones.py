"""Animaciones reutilizables: aparición suave, transiciones entre pantallas y sombras."""

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QStackedWidget, QWidget

# Referencias a las animaciones en curso: sin ellas Python las destruiría antes de terminar.
_ACTIVAS: set = set()


def _conservar(animacion) -> None:
    """Mantiene viva la animación hasta que termina."""
    _ACTIVAS.add(animacion)
    animacion.finished.connect(lambda: _ACTIVAS.discard(animacion))


def aparecer(widget: QWidget, duracion: int = 350, desplazamiento: int = 0, horizontal: int = 0) -> None:
    """Hace aparecer un widget con un fundido y, opcionalmente, deslizándolo (hacia arriba o de lado)."""
    if getattr(widget, "sin_animacion", False):
        return
    efecto = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(efecto)
    grupo = QParallelAnimationGroup(widget)
    fundido = QPropertyAnimation(efecto, b"opacity")
    fundido.setDuration(duracion)
    fundido.setStartValue(0.0)
    fundido.setEndValue(1.0)
    fundido.setEasingCurve(QEasingCurve.OutCubic)
    grupo.addAnimation(fundido)
    if desplazamiento or horizontal:
        destino = widget.pos()
        movimiento = QPropertyAnimation(widget, b"pos")
        movimiento.setDuration(duracion)
        movimiento.setStartValue(destino + QPoint(horizontal, desplazamiento))
        movimiento.setEndValue(destino)
        movimiento.setEasingCurve(QEasingCurve.OutCubic)
        grupo.addAnimation(movimiento)
    # Al terminar se quita el efecto: un widget solo admite un efecto, y así no interfiere con otros (como sombras).
    grupo.finished.connect(lambda: widget.setGraphicsEffect(None))
    _conservar(grupo)
    grupo.start()


def sombra(widget: QWidget, desenfoque: int = 24, opacidad: int = 28, vertical: int = 4) -> None:
    """Agrega una sombra suave que hace que las tarjetas parezcan "flotar" sobre el fondo."""
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(desenfoque)
    efecto.setOffset(0, vertical)
    efecto.setColor(QColor(15, 76, 129, opacidad))
    widget.setGraphicsEffect(efecto)


class PilaAnimada(QStackedWidget):
    """QStackedWidget que, al cambiar de página, la muestra con un fundido y un pequeño deslizamiento."""

    def setCurrentIndex(self, indice: int) -> None:  # noqa: N802 (nombre de Qt).
        """Cambia de página y anima la entrada de la nueva."""
        if indice == self.currentIndex():
            return
        super().setCurrentIndex(indice)
        pagina = self.currentWidget()
        if pagina is not None:
            aparecer(pagina, duracion=300, desplazamiento=12)
