"""Componentes interactivos del Centro Informativo.

- TarjetaArticulo: artículo desplegable con viñetas visuales (recomendado, evitar, alarma).
- LineaFases: línea de tiempo de las fases de la varicela con la ilustración de cada lesión.
- MedidorContagio: control deslizante de días que indica si la persona contagia.
- TarjetaQuiz: tarjeta de "¿Mito o realidad?" que se voltea al responder.
"""

import re

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy, QStackedWidget, QVBoxLayout,
    QWidget,
)

from app.ui import estilos
from app.ui.animaciones import aparecer
from app.ui.cuestionario_widgets import Ilustracion
from app.ui.iconos import icono

# Palabras con las que empiezan las recomendaciones negativas ("evita…", "nunca…").
INICIOS_NEGATIVOS = ("nunca", "evita", "no ", "no asistir", "no compartir")


def _en_linea(texto: str) -> str:
    """Convierte el formato básico de Markdown en línea (**negrita**, *cursiva*) a HTML."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", texto)


def bloques_markdown(texto: str) -> list[tuple[str, str]]:
    """Divide el Markdown en bloques: ("parrafo", html), ("vineta", html) o ("numero", html)."""
    bloques: list[tuple[str, str]] = []
    parrafo: list[str] = []

    def cerrar_parrafo():
        """Agrega el párrafo acumulado como un bloque."""
        if parrafo:
            bloques.append(("parrafo", _en_linea(" ".join(parrafo))))
            parrafo.clear()

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            cerrar_parrafo()
        elif linea.startswith("- "):
            cerrar_parrafo()
            bloques.append(("vineta", _en_linea(linea[2:])))
        elif re.match(r"^\d+\.\s", linea):
            cerrar_parrafo()
            bloques.append(("numero", _en_linea(re.sub(r"^\d+\.\s", "", linea))))
        else:
            parrafo.append(linea)
    cerrar_parrafo()
    return bloques


def tipo_vineta(html: str, modo_alarma: bool) -> str:
    """Decide el ícono de una viñeta: alarma, evitar (rechazar) o recomendado (aceptar)."""
    if modo_alarma:
        return "alerta"
    plano = re.sub(r"<[^>]+>", "", html).strip().lower()
    return "rechazar" if plano.startswith(INICIOS_NEGATIVOS) else "aceptar"


# ---------------------------------------------------------------------------- Artículo desplegable.

class EncabezadoClicable(QFrame):
    """Marco que funciona como botón: a diferencia de QPushButton, su altura se adapta a lo que contiene."""

    clicked = Signal()

    def __init__(self, parent=None):
        """Muestra la mano al pasar el mouse."""
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Avisa del clic."""
        self.clicked.emit()


class TarjetaArticulo(QFrame):
    """Artículo con encabezado siempre visible y cuerpo que se despliega con animación."""

    abierto = Signal(str)  # Título del artículo al desplegarse.

    def __init__(self, titulo: str, contenido_md: str, fuente: str, nombre_icono: str,
                 color: str = estilos.AZUL_CLINICO, alarma: bool = False, parent=None):
        """Construye el encabezado clicable y el cuerpo con viñetas visuales."""
        super().__init__(parent)
        self.titulo = titulo
        self.setObjectName("articulo_alarma" if alarma else "articulo")
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)

        self.encabezado = EncabezadoClicable()
        self.encabezado.setObjectName("articulo_encabezado")
        fila = QHBoxLayout(self.encabezado)
        fila.setContentsMargins(16, 12, 16, 12)
        circulo = QLabel()
        circulo.setObjectName("articulo_icono")
        circulo.setFixedSize(40, 40)
        circulo.setAlignment(Qt.AlignCenter)
        circulo.setStyleSheet(f"background: {estilos.aclarar(color)}; border-radius: 20px;")
        circulo.setPixmap(icono(nombre_icono, color, 22).pixmap(22, 22))
        texto = QLabel(titulo)
        texto.setObjectName("articulo_titulo")
        texto.setWordWrap(True)
        self.flecha = QLabel()
        fila.addWidget(circulo)
        fila.addSpacing(10)
        fila.addWidget(texto, 1)
        fila.addWidget(self.flecha)
        capa.addWidget(self.encabezado)

        self.cuerpo = QWidget()
        self.cuerpo.setObjectName("articulo_cuerpo")
        capa_cuerpo = QVBoxLayout(self.cuerpo)
        capa_cuerpo.setContentsMargins(66, 0, 20, 16)
        capa_cuerpo.setSpacing(8)
        numero = 0
        for tipo, html in bloques_markdown(contenido_md):
            if tipo == "parrafo":
                capa_cuerpo.addWidget(self._texto(html))
                continue
            renglon = QHBoxLayout()
            renglon.setSpacing(10)
            marca = QLabel()
            marca.setFixedWidth(24)
            marca.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            if tipo == "numero":
                numero += 1
                marca.setText(str(numero))
                marca.setObjectName("articulo_numero")
                marca.setFixedSize(24, 24)
                marca.setAlignment(Qt.AlignCenter)
            else:
                nombre = tipo_vineta(html, alarma)
                color_marca = estilos.TEAL if nombre == "aceptar" else estilos.ROJO
                marca.setPixmap(icono(nombre, color_marca, 18).pixmap(18, 18))
            renglon.addWidget(marca)
            renglon.addWidget(self._texto(html), 1)
            capa_cuerpo.addLayout(renglon)
        pie = QLabel(f"Fuente: {fuente}")
        pie.setObjectName("articulo_fuente")
        pie.setWordWrap(True)
        capa_cuerpo.addWidget(pie)
        capa.addWidget(self.cuerpo)

        self._abierto = False
        self.cuerpo.setMaximumHeight(0)
        self._animacion = QPropertyAnimation(self.cuerpo, b"maximumHeight", self)
        self._animacion.setDuration(380)
        self._animacion.setEasingCurve(QEasingCurve.InOutCubic)
        self._animacion.finished.connect(self._al_terminar)
        self.encabezado.clicked.connect(self.alternar)
        self._actualizar_flecha()

    @staticmethod
    def _texto(html: str) -> QLabel:
        """Etiqueta de texto enriquecido con ajuste de línea."""
        etiqueta = QLabel(html)
        etiqueta.setTextFormat(Qt.RichText)
        etiqueta.setWordWrap(True)
        etiqueta.setObjectName("articulo_texto")
        return etiqueta

    def _actualizar_flecha(self) -> None:
        """Texto del indicador según el estado."""
        self.flecha.setText("Ocultar" if self._abierto else "Leer")
        self.flecha.setObjectName("articulo_accion")
        self.flecha.style().unpolish(self.flecha)
        self.flecha.style().polish(self.flecha)

    def alternar(self) -> None:
        """Despliega o pliega el cuerpo con animación."""
        self._abierto = not self._abierto
        self._animacion.stop()
        self._animacion.setStartValue(self.cuerpo.maximumHeight() if self.cuerpo.maximumHeight() < 5000 else self.cuerpo.height())
        self._animacion.setEndValue(self.cuerpo.sizeHint().height() if self._abierto else 0)
        self._animacion.start()
        self._actualizar_flecha()
        if self._abierto:
            self.abierto.emit(self.titulo)

    def abrir_sin_animacion(self) -> None:
        """Deja el artículo desplegado desde el inicio (por ejemplo, el de signos de alarma)."""
        self._abierto = True
        self.cuerpo.setMaximumHeight(16777215)
        self._actualizar_flecha()

    def _al_terminar(self) -> None:
        """Al terminar de abrir, quita el límite de altura para que el texto se adapte al ancho de la ventana."""
        if self._abierto:
            self.cuerpo.setMaximumHeight(16777215)


# ---------------------------------------------------------------------------- Línea de tiempo de fases.

FASES = [
    ("Incubación", "10 a 21 días", "reloj",
     "Después del contagio el virus se multiplica sin dar síntomas. Si hubo contacto con un caso, "
     "vigila la aparición de fiebre o ronchas durante tres semanas."),
    ("Pródromo", "1 a 2 días", "fiebre_moderada",
     "Fiebre moderada, cansancio, falta de apetito y dolor de cabeza. En niños pequeños a veces "
     "la erupción es la primera señal."),
    ("Erupción", "3 a 5 días de brotes", "lesiones_simultaneas",
     "Aparecen manchas rojas que se convierten en granitos y luego en ampollas con líquido claro. "
     "Lo típico es ver lesiones en distintas fases al mismo tiempo, con mucha comezón."),
    ("Costras", "1 a 2 semanas", "costras",
     "Las ampollas se secan y forman costras que caen solas. Cuando todas las lesiones son costras, "
     "la persona deja de contagiar."),
]


class _IlustracionReloj(QWidget):
    """Reloj simple para la fase de incubación (no hay lesión que mostrar)."""

    def __init__(self, parent=None):
        """Tamaño igual al de las ilustraciones de lesiones."""
        super().__init__(parent)
        self.setFixedSize(68, 68)

    def rebotar(self) -> None:
        """Compatibilidad con Ilustracion (sin animación)."""

    def paintEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Dibuja la esfera y las manecillas."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#5C6B7A"), 2.5))
        p.setBrush(QColor("#E8EEF4"))
        p.drawEllipse(QPointF(34, 34), 26, 26)
        p.setPen(QPen(QColor(estilos.AZUL_CLINICO), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(34, 34), QPointF(34, 18))
        p.drawLine(QPointF(34, 34), QPointF(46, 40))
        p.end()


class NodoFase(QFrame):
    """Una fase de la línea de tiempo: ilustración, nombre y duración; se puede elegir con un clic."""

    elegido = Signal(int)

    def __init__(self, indice: int, nombre: str, duracion: str, codigo: str, parent=None):
        """Construye el nodo clicable."""
        super().__init__(parent)
        self.indice = indice
        self.setObjectName("nodo_fase")
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("activo", False)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(10, 12, 10, 12)
        capa.setSpacing(4)
        self.ilustracion = _IlustracionReloj() if codigo == "reloj" else Ilustracion(codigo)
        capa.addWidget(self.ilustracion, 0, Qt.AlignHCenter)
        titulo = QLabel(f"{indice + 1}. {nombre}")
        titulo.setObjectName("nodo_titulo")
        titulo.setAlignment(Qt.AlignCenter)
        tiempo = QLabel(duracion)
        tiempo.setObjectName("nodo_duracion")
        tiempo.setAlignment(Qt.AlignCenter)
        capa.addWidget(titulo)
        capa.addWidget(tiempo)

    def mousePressEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Al hacer clic, avisa qué fase se eligió."""
        self.elegido.emit(self.indice)

    def activar(self, activo: bool) -> None:
        """Resalta u opaca el nodo."""
        self.setProperty("activo", activo)
        self.style().unpolish(self)
        self.style().polish(self)
        if activo:
            self.ilustracion.rebotar()


class LineaFases(QWidget):
    """Línea de tiempo con las cuatro fases; al elegir una muestra su explicación."""

    fase_elegida = Signal(int)

    def __init__(self, parent=None):
        """Construye los nodos unidos por flechas y el recuadro de explicación."""
        super().__init__(parent)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.nodos: list[NodoFase] = []
        for i, (nombre, duracion, codigo, _) in enumerate(FASES):
            nodo = NodoFase(i, nombre, duracion, codigo)
            nodo.elegido.connect(self.elegir)
            self.nodos.append(nodo)
            fila.addWidget(nodo, 1)
            if i < len(FASES) - 1:
                flecha = QLabel()
                flecha.setPixmap(_flecha().pixmap(22, 22))
                fila.addWidget(flecha)
        capa.addLayout(fila)
        self.explicacion = QLabel()
        self.explicacion.setObjectName("fase_explicacion")
        self.explicacion.setWordWrap(True)
        capa.addWidget(self.explicacion)
        self.elegir(2, avisar=False)  # Empieza en la erupción, la fase más reconocible.

    def elegir(self, indice: int, avisar: bool = True) -> None:
        """Resalta la fase elegida y muestra su explicación con una animación."""
        for nodo in self.nodos:
            nodo.activar(nodo.indice == indice)
        nombre, duracion, _, texto = FASES[indice]
        self.explicacion.setText(f"<b>{nombre} ({duracion}).</b> {texto}")
        aparecer(self.explicacion, duracion=300, desplazamiento=8)
        if avisar:
            self.fase_elegida.emit(indice)


def _flecha():
    """Flecha hacia la derecha dibujada con el mismo estilo que los íconos."""
    from PySide6.QtGui import QIcon, QPixmap

    pixmap = QPixmap(44, 44)
    pixmap.fill(Qt.transparent)
    pixmap.setDevicePixelRatio(2)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("#9FB3C8"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(4, 11), QPointF(18, 11))
    p.drawPolyline([QPointF(13, 6), QPointF(18, 11), QPointF(13, 16)])
    p.end()
    return QIcon(pixmap)


# ---------------------------------------------------------------------------- Contagio por días.

def estado_contagio(dia: int) -> tuple[str, str, str]:
    """Para un día respecto al inicio de la erupción, devuelve (título, explicación, color)."""
    if dia < -2:
        return ("Aún no contagia", "Está en incubación: el virus se multiplica sin síntomas y todavía no se transmite.",
                estilos.TEAL)
    if dia < 0:
        return ("Ya contagia, aunque no haya ronchas",
                "La varicela se transmite desde 1 a 2 días antes de la erupción: por eso se contagia tan fácilmente.",
                estilos.AMBAR)
    if dia < 5:
        return ("Contagia", "Hay ampollas sin costra. No debe ir a la escuela ni al trabajo y debe evitar a personas de riesgo.",
                estilos.ROJO)
    if dia < 8:
        return ("Contagia hasta que todo sea costra",
                "Suele dejar de contagiar entre los días 5 y 7, cuando TODAS las lesiones se han secado en costra.",
                estilos.AMBAR)
    return ("Ya no contagia", "Si todas las lesiones son costras, ya puede volver a sus actividades.", estilos.TEAL)


class BarraContagio(QWidget):
    """Barra de colores con las etapas del contagio y un marcador en el día elegido."""

    DIAS = (-4, 10)

    def __init__(self, parent=None):
        """Altura fija y día inicial."""
        super().__init__(parent)
        self.dia = 0
        self.setMinimumHeight(54)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def poner_dia(self, dia: int) -> None:
        """Mueve el marcador y redibuja."""
        self.dia = dia
        self.update()

    def _x(self, dia: float) -> float:
        """Posición horizontal de un día en la barra."""
        inicio, fin = self.DIAS
        return 12 + (self.width() - 24) * (dia - inicio) / (fin - inicio)

    def paintEvent(self, evento) -> None:  # noqa: N802 (nombre de Qt).
        """Dibuja las zonas de color, el día 0 (inicio de la erupción) y el marcador."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        zonas = [(-4, -2, estilos.TEAL), (-2, 0, estilos.AMBAR), (0, 5, estilos.ROJO), (5, 8, estilos.AMBAR), (8, 10, estilos.TEAL)]
        for inicio, fin, color in zonas:
            c = QColor(color)
            c.setAlpha(70)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRect(QRectF(self._x(inicio), 14, self._x(fin) - self._x(inicio), 14))
        fuente = QFont(self.font())
        fuente.setPointSize(8)
        p.setFont(fuente)
        p.setPen(QColor(estilos.PIZARRA_SUAVE))
        for dia in range(self.DIAS[0], self.DIAS[1] + 1, 2):
            p.drawText(QRectF(self._x(dia) - 20, 32, 40, 16), Qt.AlignCenter, f"{dia:+d}" if dia else "0")
        p.setPen(QPen(QColor(estilos.AZUL_OSCURO), 1.5, Qt.DashLine))
        p.drawLine(QPointF(self._x(0), 6), QPointF(self._x(0), 30))
        p.setPen(QColor(estilos.AZUL_OSCURO))
        p.drawText(QRectF(self._x(0) - 60, -2, 120, 12), Qt.AlignCenter, "inicio de la erupción")
        x = self._x(self.dia)
        p.setPen(QPen(QColor("#FFFFFF"), 3))
        p.setBrush(QColor(estado_contagio(self.dia)[2]))
        p.drawEllipse(QPointF(x, 21), 9, 9)
        p.end()


class MedidorContagio(QFrame):
    """Control deslizante de días con la barra de etapas y el estado del contagio."""

    cambio = Signal(int, str)  # Día y título del estado.

    def __init__(self, parent=None):
        """Construye la barra, el deslizador y el recuadro de estado."""
        super().__init__(parent)
        self.setObjectName("tarjeta_interactiva")
        capa = QVBoxLayout(self)
        capa.setContentsMargins(20, 16, 20, 16)
        titulo = QLabel("¿Contagia? Mueve el control para elegir el día")
        titulo.setObjectName("subtitulo")
        capa.addWidget(titulo)
        ayuda = QLabel("El día 0 es cuando aparecen las primeras ronchas; los días negativos son antes de que aparezcan.")
        ayuda.setObjectName("nota")
        ayuda.setWordWrap(True)
        capa.addWidget(ayuda)
        self.barra = BarraContagio()
        capa.addWidget(self.barra)
        self.deslizador = QSlider(Qt.Horizontal)
        self.deslizador.setRange(*BarraContagio.DIAS)
        self.deslizador.setValue(0)
        capa.addWidget(self.deslizador)
        self.estado = QLabel()
        self.estado.setObjectName("estado_contagio")
        self.estado.setWordWrap(True)
        capa.addWidget(self.estado)
        self.deslizador.valueChanged.connect(self._actualizar)
        self._ultimo_titulo = ""
        self._actualizar(0, avisar=False)

    def _actualizar(self, dia: int, avisar: bool = True) -> None:
        """Actualiza la barra y el recuadro; anima el recuadro cuando cambia de etapa."""
        self.barra.poner_dia(dia)
        titulo, texto, color = estado_contagio(dia)
        nombre_dia = "el día del inicio de la erupción" if dia == 0 else f"{abs(dia)} día{'s' if abs(dia) != 1 else ''} " \
                     f"{'antes' if dia < 0 else 'después'} de la erupción"
        self.estado.setText(f"<span style='font-size:12pt; font-weight:600; color:{color}'>{titulo}</span><br>"
                            f"<span style='color:{estilos.PIZARRA_SUAVE}'>{nombre_dia.capitalize()}.</span> {texto}")
        self.estado.setStyleSheet(f"border-left: 5px solid {color}; padding: 10px 14px; "
                                  f"background: {estilos.aclarar(color, 0.9)}; border-radius: 3px;")
        if titulo != self._ultimo_titulo:
            if self._ultimo_titulo:
                aparecer(self.estado, duracion=280, desplazamiento=6)
            self._ultimo_titulo = titulo
            if avisar:
                self.cambio.emit(dia, titulo)


# ---------------------------------------------------------------------------- Quiz de mitos y realidades.

class TarjetaQuiz(QFrame):
    """Afirmación con botones "Mito" y "Realidad"; al responder se voltea y explica la respuesta."""

    respondida = Signal(bool)  # True si el usuario acertó.

    def __init__(self, afirmacion: str, es_mito: bool, explicacion_md: str, fuente: str, parent=None):
        """Construye la cara de pregunta y la cara de respuesta."""
        super().__init__(parent)
        self.es_mito = es_mito
        self.setObjectName("quiz")
        self.setProperty("estado", "pregunta")
        self.setMinimumHeight(190)
        self.caras = QStackedWidget()
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.addWidget(self.caras)

        # Cara 1: la pregunta.
        frente = QWidget()
        capa_frente = QVBoxLayout(frente)
        capa_frente.setContentsMargins(18, 16, 18, 16)
        etiqueta_pregunta = QLabel("¿Mito o realidad?")
        etiqueta_pregunta.setObjectName("quiz_etiqueta")
        texto = QLabel(f"«{afirmacion}»")
        texto.setObjectName("quiz_afirmacion")
        texto.setWordWrap(True)
        botones = QHBoxLayout()
        self.boton_mito = QPushButton("Es un mito")
        self.boton_mito.setObjectName("secundario")
        self.boton_realidad = QPushButton("Es realidad")
        self.boton_realidad.setObjectName("secundario")
        for boton, respuesta in ((self.boton_mito, True), (self.boton_realidad, False)):
            boton.setCursor(Qt.PointingHandCursor)
            boton.clicked.connect(lambda _=False, r=respuesta: self.responder(r))
            botones.addWidget(boton)
        capa_frente.addWidget(etiqueta_pregunta)
        capa_frente.addWidget(texto, 1)
        capa_frente.addLayout(botones)
        self.caras.addWidget(frente)

        # Cara 2: la respuesta, con la explicación del Centro Informativo.
        reverso = QWidget()
        capa_reverso = QVBoxLayout(reverso)
        capa_reverso.setContentsMargins(18, 14, 18, 14)
        self.veredicto = QLabel()
        self.veredicto.setObjectName("quiz_veredicto")
        self.resultado = QLabel()
        self.resultado.setObjectName("quiz_resultado")
        explicacion = QLabel(" ".join(html for _, html in bloques_markdown(explicacion_md)))
        explicacion.setTextFormat(Qt.RichText)
        explicacion.setWordWrap(True)
        pie = QLabel(f"Fuente: {fuente}")
        pie.setObjectName("articulo_fuente")
        pie.setWordWrap(True)
        recordatorio = QLabel(f"«{afirmacion}»")
        recordatorio.setObjectName("quiz_recordatorio")
        recordatorio.setWordWrap(True)
        cabecera = QHBoxLayout()
        cabecera.addWidget(self.veredicto)
        cabecera.addStretch()
        cabecera.addWidget(self.resultado)
        capa_reverso.addLayout(cabecera)
        capa_reverso.addWidget(recordatorio)
        capa_reverso.addWidget(explicacion, 1)
        capa_reverso.addWidget(pie)
        self.caras.addWidget(reverso)

    def responder(self, dijo_mito: bool) -> None:
        """Voltea la tarjeta, indica si acertó y avisa con la señal `respondida`."""
        acierto = dijo_mito == self.es_mito
        self.veredicto.setText("MITO" if self.es_mito else "REALIDAD")
        self.veredicto.setProperty("tipo", "mito" if self.es_mito else "realidad")
        self.resultado.setText("¡Correcto!" if acierto else "No exactamente")
        self.resultado.setProperty("acierto", acierto)
        self.setProperty("estado", "acierto" if acierto else "error")
        for widget in (self, self.veredicto, self.resultado):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.caras.setCurrentIndex(1)
        aparecer(self.caras.currentWidget(), duracion=420, horizontal=-30)  # Efecto de "voltear" la tarjeta.
        self.respondida.emit(acierto)

    def reiniciar(self) -> None:
        """Vuelve a mostrar la pregunta."""
        self.setProperty("estado", "pregunta")
        self.style().unpolish(self)
        self.style().polish(self)
        self.caras.setCurrentIndex(0)


class JuegoMitos(QWidget):
    """Cuadrícula de tarjetas de quiz con marcador de aciertos."""

    progreso = Signal(int, int, int, bool)  # Aciertos, respondidas, total y si la última fue acierto.

    def __init__(self, preguntas: list[tuple[str, bool, str, str]], parent=None):
        """Crea una tarjeta por afirmación: (afirmación, es_mito, explicación, fuente)."""
        super().__init__(parent)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        cabecera = QHBoxLayout()
        self.marcador = QLabel()
        self.marcador.setObjectName("contador")
        boton_reiniciar = QPushButton("Volver a jugar")
        boton_reiniciar.setObjectName("secundario")
        boton_reiniciar.clicked.connect(self.reiniciar)
        cabecera.addWidget(self.marcador, 1)
        cabecera.addWidget(boton_reiniciar)
        capa.addLayout(cabecera)
        rejilla = QGridLayout()
        rejilla.setSpacing(14)
        self.tarjetas: list[TarjetaQuiz] = []
        for i, (afirmacion, es_mito, explicacion, fuente) in enumerate(preguntas):
            tarjeta = TarjetaQuiz(afirmacion, es_mito, explicacion, fuente)
            tarjeta.respondida.connect(self._al_responder)
            rejilla.addWidget(tarjeta, i // 2, i % 2)
            self.tarjetas.append(tarjeta)
        capa.addLayout(rejilla)
        self.aciertos = self.respondidas = 0
        self._mostrar_marcador()

    def _mostrar_marcador(self) -> None:
        """Texto del marcador."""
        self.marcador.setText(f"Aciertos: {self.aciertos} de {self.respondidas} respondidas "
                              f"({len(self.tarjetas) - self.respondidas} por responder)")

    def _al_responder(self, acierto: bool) -> None:
        """Suma al marcador y avisa del progreso."""
        self.respondidas += 1
        self.aciertos += int(acierto)
        self._mostrar_marcador()
        self.progreso.emit(self.aciertos, self.respondidas, len(self.tarjetas), acierto)

    def reiniciar(self) -> None:
        """Vuelve a poner todas las tarjetas boca arriba, en orden escalonado."""
        self.aciertos = self.respondidas = 0
        self._mostrar_marcador()
        for i, tarjeta in enumerate(self.tarjetas):
            tarjeta.reiniciar()
            QTimer.singleShot(i * 60, lambda t=tarjeta: aparecer(t.caras.currentWidget(), duracion=300, desplazamiento=10))
