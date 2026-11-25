"""Centro Informativo interactivo: secciones con portada, línea de fases, medidor de contagio y juego de mitos.

El contenido viene de la base de datos (catalogo_informacion); esta página solo decide cómo presentarlo.
Doc acompaña cada interacción con un comentario breve.
"""

import random

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.db import repositorio
from app.ui import estilos
from app.ui.animaciones import PilaAnimada, aparecer, sombra
from app.ui.comun import Sesion, etiqueta
from app.ui.iconos import icono
from app.ui.info_widgets import JuegoMitos, LineaFases, MedidorContagio, TarjetaArticulo

# Secciones: (código en la base, título, descripción corta, ícono, color de acento).
SECCIONES = [
    ("QUE_ES", "¿Qué es la varicela?", "Causa, fases y quién tiene más riesgo", "lupa", estilos.AZUL_CLINICO),
    ("CUIDADOS", "Cuidados en casa", "Qué hacer, qué evitar y cuándo ir al médico", "casa", estilos.TEAL),
    ("AISLAMIENTO", "Contagio y aislamiento", "Cuándo contagia y cómo proteger a otros", "escudo", "#4B5FB8"),
    ("MITOS", "¿Mito o realidad?", "Pon a prueba lo que sabes", "pregunta", estilos.AMBAR),
]

# Ícono de cada artículo según su título.
ICONOS_ARTICULO = {
    "¿Qué es la varicela?": "lupa",
    "¿Quién tiene más riesgo de complicaciones?": "alerta",
    "Prevención: la vacuna": "escudo",
    "Para la fiebre y el malestar": "cruz",
    "Para la comezón y la piel": "casa",
    "Cuándo acudir al médico de inmediato": "alerta",
    "¿Cuándo se contagia?": "historial",
    "Medidas en casa": "casa",
    "Protege a las personas de riesgo": "escudo",
}

# Lo que comenta Doc al abrir cada artículo.
DATOS_CLAVE = {
    "¿Qué es la varicela?": "Dato clave: el mismo virus puede despertar años después como herpes zóster.",
    "¿Quién tiene más riesgo de complicaciones?": "Si eres de un grupo de riesgo, el antiviral funciona mejor en las primeras 24 horas.",
    "Prevención: la vacuna": "La vacuna aplicada en los 3 a 5 días tras el contacto puede evitar o suavizar la enfermedad.",
    "Para la fiebre y el malestar": "Recuerda: paracetamol sí, aspirina nunca en niños ni adolescentes.",
    "Para la comezón y la piel": "Las uñas cortas evitan infecciones y cicatrices. ¡Un baño tibio también ayuda!",
    "Cuándo acudir al médico de inmediato": "Si ves cualquiera de estos signos, no esperes: acude a urgencias.",
    "¿Cuándo se contagia?": "Prueba el control de días de arriba para verlo de forma visual.",
    "Medidas en casa": "Lavarse las manos con frecuencia es de las medidas más eficaces.",
    "Protege a las personas de riesgo": "Embarazadas, bebés y personas con defensas bajas deben evitar el contacto.",
}

# Comentario de Doc al elegir cada fase en la línea de tiempo.
COMENTARIOS_FASE = [
    "En la incubación no hay síntomas: por eso conviene vigilar 3 semanas tras un contacto.",
    "El pródromo parece un resfriado: fiebre y cansancio antes de las ronchas.",
    "Esta es la fase más reconocible: lesiones en distintas etapas a la vez.",
    "Cuando todo es costra, ya no contagia. ¡Falta poco!",
]


def preguntas_quiz(articulos) -> list[tuple[str, bool, str, str]]:
    """Convierte los artículos 'Mito: "..."' y 'Realidad: "..."' en preguntas del juego, mezcladas."""
    preguntas = []
    for a in articulos:
        titulo = a["titulo"]
        if ":" not in titulo:
            continue
        tipo, afirmacion = titulo.split(":", 1)
        preguntas.append((afirmacion.strip().strip('"'), tipo.strip().lower() == "mito", a["contenido_md"], a["fuente"]))
    random.Random(7).shuffle(preguntas)  # Orden fijo pero mezclado, para no tener todos los mitos juntos.
    return preguntas


class PaginaInfo(QWidget):
    """Portada con cuatro secciones; cada sección presenta su contenido de forma interactiva."""

    def __init__(self, sesion: Sesion):
        """Construye la portada, los botones de sección y el contenido de cada una."""
        super().__init__()
        self.sesion = sesion
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 12)
        raiz.setSpacing(12)
        raiz.addWidget(self._portada())

        fila = QHBoxLayout()
        fila.setSpacing(12)
        self.grupo = QButtonGroup(self)
        self.pila = PilaAnimada()
        self._tarjetas_por_seccion: dict[int, list[QWidget]] = {}
        for indice, (codigo, titulo, descripcion, nombre_icono, color) in enumerate(SECCIONES):
            boton = QPushButton(f"{titulo}\n{descripcion}")
            boton.setObjectName("seccion_info")
            boton.setCheckable(True)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setIcon(icono(nombre_icono, color, 28))
            boton.setIconSize(QSize(28, 28))
            boton.setStyleSheet(f"QPushButton#seccion_info:checked {{ border: 2px solid {color}; }}")
            self.grupo.addButton(boton, indice)
            fila.addWidget(boton, 1)
            self.pila.addWidget(self._seccion(indice, codigo, color))
        raiz.addLayout(fila)
        raiz.addWidget(self.pila, 1)
        self.grupo.idClicked.connect(self._mostrar_seccion)
        self.grupo.button(0).setChecked(True)

    # ------------------------------------------------------------------ Construcción.

    def _portada(self) -> QFrame:
        """Franja superior con título, subtítulo y fuentes."""
        portada = QFrame()
        portada.setObjectName("portada_info")
        capa = QHBoxLayout(portada)
        capa.setContentsMargins(24, 16, 24, 16)
        textos = QVBoxLayout()
        titulo = QLabel("Centro Informativo")
        titulo.setObjectName("portada_titulo")
        subtitulo = QLabel("Todo lo que necesitas saber sobre la varicela, explicado de forma clara. "
                           "Basado en guías de la OMS, los CDC y la Academia Americana de Pediatría.")
        subtitulo.setObjectName("portada_texto")
        subtitulo.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)
        capa.addLayout(textos, 1)
        simbolo = QLabel()
        simbolo.setPixmap(icono("informacion", "#FFFFFF", 54).pixmap(54, 54))
        capa.addWidget(simbolo)
        return portada

    def _seccion(self, indice: int, codigo: str, color: str) -> QScrollArea:
        """Construye el contenido de una sección dentro de un área desplazable."""
        contenedor = QWidget()
        capa = QVBoxLayout(contenedor)
        capa.setContentsMargins(2, 4, 10, 10)
        capa.setSpacing(12)
        tarjetas: list[QWidget] = []
        articulos = repositorio.informacion(self.sesion.conexion, codigo)

        if codigo == "QUE_ES":
            linea = LineaFases()
            linea.fase_elegida.connect(lambda i: self.sesion.guiar(COMENTARIOS_FASE[i], "atento"))
            tarjetas.append(self._interactiva("Las fases de la varicela",
                                              "Haz clic en cada fase para ver qué ocurre.", linea))
            articulos = [a for a in articulos if a["titulo"] != "Fases de la enfermedad"]  # Ya está en la línea de tiempo.
        elif codigo == "CUIDADOS":
            tarjetas.append(self._leyenda())
            articulos = sorted(articulos, key=lambda a: "acudir" not in a["titulo"])  # Primero, los signos de alarma.
        elif codigo == "AISLAMIENTO":
            medidor = MedidorContagio()
            sombra(medidor)
            medidor.cambio.connect(lambda dia, titulo: self.sesion.guiar(
                f"{titulo}. " + ("Recuerda: todas las lesiones deben ser costras." if dia >= 5 else ""),
                "preocupado" if titulo == "Contagia" else "atento"))
            tarjetas.append(medidor)
        elif codigo == "MITOS":
            juego = JuegoMitos(preguntas_quiz(articulos))
            juego.progreso.connect(self._progreso_juego)
            tarjetas.append(juego)
            articulos = []  # Los mitos se presentan solo como juego.

        for a in articulos:
            alarma = "acudir" in a["titulo"]
            tarjeta = TarjetaArticulo(a["titulo"], a["contenido_md"], a["fuente"],
                                      ICONOS_ARTICULO.get(a["titulo"], "informacion"),
                                      estilos.ROJO if alarma else color, alarma=alarma)
            if alarma or a["titulo"] == "¿Qué es la varicela?":
                tarjeta.abrir_sin_animacion()  # Lo esencial se ve sin hacer clic.
            tarjeta.abierto.connect(self._articulo_abierto)
            sombra(tarjeta, desenfoque=18, opacidad=22, vertical=3)
            tarjetas.append(tarjeta)

        for tarjeta in tarjetas:
            capa.addWidget(tarjeta)
        capa.addStretch()
        self._tarjetas_por_seccion[indice] = tarjetas
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.NoFrame)
        area.setWidget(contenedor)
        return area

    def _interactiva(self, titulo: str, ayuda: str, contenido: QWidget) -> QFrame:
        """Tarjeta blanca con título y ayuda para un componente interactivo."""
        marco = QFrame()
        marco.setObjectName("tarjeta_interactiva")
        sombra(marco)
        capa = QVBoxLayout(marco)
        capa.setContentsMargins(20, 16, 20, 16)
        capa.addWidget(etiqueta(titulo, "subtitulo"))
        capa.addWidget(etiqueta(ayuda, "nota"))
        capa.addWidget(contenido)
        return marco

    def _leyenda(self) -> QFrame:
        """Explica el significado de los íconos de las viñetas."""
        marco = QFrame()
        marco.setObjectName("leyenda")
        capa = QHBoxLayout(marco)
        capa.setContentsMargins(14, 8, 14, 8)
        for nombre, color, texto in (("aceptar", estilos.TEAL, "Recomendado"), ("rechazar", estilos.ROJO, "Evitar"),
                                     ("alerta", estilos.ROJO, "Signo de alarma")):
            simbolo = QLabel()
            simbolo.setPixmap(icono(nombre, color, 16).pixmap(16, 16))
            capa.addWidget(simbolo)
            capa.addWidget(QLabel(texto))
            capa.addSpacing(18)
        capa.addStretch()
        return marco

    # ------------------------------------------------------------------ Interacción.

    def _mostrar_seccion(self, indice: int) -> None:
        """Cambia de sección y hace aparecer sus tarjetas una tras otra."""
        self.pila.setCurrentIndex(indice)
        for orden, tarjeta in enumerate(self._tarjetas_por_seccion.get(indice, [])):
            QTimer.singleShot(90 * orden, lambda t=tarjeta: aparecer(t, duracion=320, desplazamiento=14))
        mensajes = [
            "Empecemos por lo básico. Haz clic en las fases para ver cómo evoluciona la varicela.",
            "Aquí verás qué hacer en casa. Lo rojo es lo que debes evitar.",
            "Mueve el control de días para ver cuándo contagia la varicela.",
            "¡Juguemos! Lee cada frase y dime si es mito o realidad.",
        ]
        self.sesion.guiar(mensajes[indice], "celebrando" if indice == 3 else "feliz")

    def _articulo_abierto(self, titulo: str) -> None:
        """Doc comenta el dato clave del artículo que se acaba de abrir."""
        self.sesion.guiar(DATOS_CLAVE.get(titulo, "Si te queda alguna duda, pregúntame en el asistente virtual."),
                          "preocupado" if "acudir" in titulo else "atento")

    def _progreso_juego(self, aciertos: int, respondidas: int, total: int, acierto: bool) -> None:
        """Doc reacciona a cada respuesta del juego y felicita al terminar."""
        if respondidas == total:
            calificacion = aciertos / total
            mensaje = (f"¡Terminaste! Acertaste {aciertos} de {total}. "
                       + ("¡Excelente, sabes mucho de varicela!" if calificacion >= 0.8
                          else "Revisa las explicaciones: así se evitan riesgos reales."))
            self.sesion.guiar(mensaje, "celebrando" if calificacion >= 0.8 else "atento")
        elif acierto:
            self.sesion.guiar(f"¡Correcto! Llevas {aciertos} de {respondidas}.", "celebrando")
        else:
            self.sesion.guiar("Casi. Lee la explicación de la tarjeta: es un error muy común.", "atento")
