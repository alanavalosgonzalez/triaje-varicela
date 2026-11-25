"""Cuestionario de triaje paso a paso: datos del paciente, síntomas generales, erupción, signos de alarma y resultado."""

from datetime import date

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QProgressBar, QPushButton, QRadioButton,
    QScrollArea, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from app.core.modelos import Paciente
from app.core.orquestador import evaluar_triaje, guardar_triaje
from app.db import repositorio
from app.ui import estilos
from app.ui.animaciones import aparecer
from app.ui.comun import Sesion, ejecutar, etiqueta, tarjeta

# Síntomas de cada paso del cuestionario (los códigos vienen del catálogo de la base de datos).
GENERALES = ["fiebre_moderada", "malestar_general", "perdida_apetito", "cefalea"]
OPCIONES = [("Sí", True), ("No", False), ("No sé", None)]

# Lo que dice Doc en cada paso del cuestionario: (mensaje, emoción).
GUIA_PASOS = [
    ("Empecemos con unos datos básicos. Puedes usar un alias, no hace falta tu nombre.", "feliz"),
    ("¿Cómo te has sentido estos días? La fiebre y el cansancio suelen aparecer antes de la erupción.", "atento"),
    ("Ahora mira la piel con buena luz. En la varicela conviven manchas, granitos, ampollas y costras.", "atento"),
    ("Último paso: estos signos son importantes. Si tienes alguno, busca atención médica pronto.", "preocupado"),
]
# Reacción de Doc a cada dictamen: (mensaje, emoción).
REACCIONES = {
    "NEGATIVO_BAJO_RIESGO": ("¡Buenas noticias! No encuentro un patrón de varicela. Si algo cambia, vuelve a revisar.", "celebrando"),
    "SOSPECHA_INICIAL": ("Hay algunas señales compatibles. Vigila la evolución y consulta si aparecen ampollas o fiebre.", "atento"),
    "ALTA_PROBABILIDAD": ("Esto se parece bastante a la varicela. Te recomiendo que te valore un médico; ya activé el mapa.", "preocupado"),
    "DERIVAR_MEDICO": ("Por seguridad, acude con un médico lo antes posible. Te ayudo a encontrar uno cercano.", "preocupado"),
}

# Nombres legibles de fases y diagnósticos diferenciales que devuelve Prolog.
FASES = {
    "prodromica": "Pródromo (síntomas generales antes de la erupción)",
    "eruptiva_temprana": "Erupción temprana (manchas o granitos)",
    "vesicular": "Vesicular (ampollas con líquido)",
    "costras": "Costras (fase final)",
    "indeterminada": "No determinada",
}
DIFERENCIALES = {
    "sarampion_rubeola": "sarampión o rubéola",
    "picaduras_alergia": "picaduras o alergia",
    "impetigo_sobreinfeccion": "impétigo o infección bacteriana",
    "otras_vesiculares": "otras infecciones con ampollas (por ejemplo herpes zóster)",
}


class FilaPregunta(QWidget):
    """Una pregunta con tres opciones excluyentes: Sí, No y No sé."""

    def __init__(self, texto: str):
        """Crea la etiqueta y los tres botones de opción."""
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.addWidget(etiqueta(texto), 1)
        self.grupo = QButtonGroup(self)
        for indice, (nombre, _) in enumerate(OPCIONES):
            boton = QRadioButton(nombre)
            self.grupo.addButton(boton, indice)
            layout.addWidget(boton)

    def valor(self) -> tuple[bool, bool | None]:
        """Devuelve (respondida, valor) donde valor es True, False o None."""
        indice = self.grupo.checkedId()
        return (indice >= 0, OPCIONES[indice][1] if indice >= 0 else None)

    def limpiar(self) -> None:
        """Quita la selección para empezar un triaje nuevo."""
        self.grupo.setExclusive(False)
        for boton in self.grupo.buttons():
            boton.setChecked(False)
        self.grupo.setExclusive(True)


def combo_si_no() -> QComboBox:
    """Lista desplegable con las respuestas Sí, No y No sé."""
    combo = QComboBox()
    for nombre, valor in OPCIONES:
        combo.addItem(nombre, valor)
    combo.setCurrentIndex(2)
    return combo


class PaginaTriaje(QWidget):
    """Asistente de varios pasos que envía las respuestas a Prolog y R y muestra el dictamen."""

    ver_mapa = Signal()

    def __init__(self, sesion: Sesion):
        """Construye los cinco pasos del cuestionario."""
        super().__init__()
        self.sesion = sesion
        self.filas: dict[str, FilaPregunta] = {}
        catalogo = repositorio.catalogo_sintomas(sesion.conexion)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        raiz.addWidget(etiqueta("Cuestionario de detección temprana", "titulo"))
        self.indicador = etiqueta("", "nota")
        raiz.addWidget(self.indicador)
        self.progreso = QProgressBar()
        self.progreso.setRange(0, 1000)
        self.progreso.setTextVisible(False)
        raiz.addWidget(self.progreso)
        self._animacion_progreso = QPropertyAnimation(self.progreso, b"value", self)
        self._animacion_progreso.setDuration(450)
        self._animacion_progreso.setEasingCurve(QEasingCurve.OutCubic)

        self.pasos = QStackedWidget()
        self.pasos.addWidget(self._paso_datos())
        self.pasos.addWidget(self._paso_sintomas(
            "Síntomas generales", "¿Ha tenido alguno de estos síntomas en los últimos días?",
            [f for f in catalogo if f["codigo"] in GENERALES]))
        self.pasos.addWidget(self._paso_sintomas(
            "La erupción en la piel", "Observa la piel con buena luz. ¿Qué tipo de lesiones hay?",
            [f for f in catalogo if f["tipo"] != "ALARMA" and f["codigo"] not in GENERALES]))
        self.pasos.addWidget(self._paso_sintomas(
            "Signos de alarma", "Estos signos requieren atención médica inmediata. ¿Presenta alguno?",
            [f for f in catalogo if f["tipo"] == "ALARMA"]))
        self.pasos.addWidget(self._paso_resultado())
        raiz.addWidget(self.pasos, 1)

        navegacion = QHBoxLayout()
        self.boton_anterior = QPushButton("Anterior")
        self.boton_anterior.setObjectName("secundario")
        self.boton_siguiente = QPushButton("Siguiente")
        self.mensaje = etiqueta("", "nota")
        navegacion.addWidget(self.mensaje, 1)
        navegacion.addWidget(self.boton_anterior)
        navegacion.addWidget(self.boton_siguiente)
        raiz.addLayout(navegacion)
        self.boton_anterior.clicked.connect(self._anterior)
        self.boton_siguiente.clicked.connect(self._siguiente)
        self._actualizar_navegacion()

    # ---------------------------------------------------------------- Construcción de los pasos.

    def _paso_datos(self) -> QWidget:
        """Paso 1: datos del paciente que modifican el riesgo."""
        marco, layout = tarjeta()
        layout.addWidget(etiqueta("Datos del paciente", "subtitulo"))
        layout.addWidget(etiqueta("No es necesario dar tu nombre real: basta con un alias.", "nota"))
        formulario = QFormLayout()
        self.campo_alias = QLineEdit()
        self.campo_alias.setPlaceholderText("Por ejemplo: Mi hijo")
        self.campo_anio = QSpinBox()
        self.campo_anio.setRange(1900, date.today().year)
        self.campo_anio.setSpecialValueText("Prefiero no decirlo")
        self.campo_anio.setMinimum(1899)
        self.campo_anio.setValue(1899)
        self.campo_vacunado = combo_si_no()
        self.campo_antecedente = combo_si_no()
        self.campo_contacto = combo_si_no()
        self.campo_embarazo = QCheckBox("Embarazo")
        self.campo_inmuno = QCheckBox("Defensas bajas (cáncer, VIH, trasplante, corticoides…)")
        formulario.addRow("Alias:", self.campo_alias)
        formulario.addRow("Año de nacimiento:", self.campo_anio)
        formulario.addRow("¿Vacunado contra varicela?", self.campo_vacunado)
        formulario.addRow("¿Ya tuvo varicela antes?", self.campo_antecedente)
        formulario.addRow("¿Contacto con un caso en las últimas 3 semanas?", self.campo_contacto)
        formulario.addRow("", self.campo_embarazo)
        formulario.addRow("", self.campo_inmuno)
        layout.addLayout(formulario)
        layout.addStretch()
        return marco

    def _paso_sintomas(self, titulo: str, descripcion: str, filas_catalogo) -> QWidget:
        """Pasos 2 a 4: una fila Sí/No/No sé por síntoma."""
        marco, layout = tarjeta()
        layout.addWidget(etiqueta(titulo, "subtitulo"))
        layout.addWidget(etiqueta(descripcion, "nota"))
        for fila in filas_catalogo:
            pregunta = FilaPregunta(fila["nombre"])
            self.filas[fila["codigo"]] = pregunta
            layout.addWidget(pregunta)
        layout.addStretch()
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QScrollArea.NoFrame)
        desplazable.setWidget(marco)
        return desplazable

    def _paso_resultado(self) -> QWidget:
        """Paso 5: dictamen combinado y explicación."""
        marco, layout = tarjeta()
        self.caja_dictamen = etiqueta("", ajustar=True)
        self.caja_dictamen.setAlignment(Qt.AlignCenter)
        self.detalle = etiqueta("")
        self.detalle.setTextFormat(Qt.RichText)
        self.detalle.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.boton_mapa = QPushButton("Ver centros de salud cercanos")
        self.boton_mapa.clicked.connect(self.ver_mapa.emit)
        self.boton_nuevo = QPushButton("Nuevo triaje")
        self.boton_nuevo.setObjectName("secundario")
        self.boton_nuevo.clicked.connect(self._reiniciar)
        layout.addWidget(self.caja_dictamen)
        layout.addWidget(self.detalle, 1)
        botones = QHBoxLayout()
        botones.addStretch()
        botones.addWidget(self.boton_nuevo)
        botones.addWidget(self.boton_mapa)
        layout.addLayout(botones)
        return marco

    # ---------------------------------------------------------------- Navegación.

    def _codigos_del_paso(self, indice: int) -> list[str]:
        """Códigos de síntomas que pertenecen a un paso del cuestionario."""
        widget = self.pasos.widget(indice)
        return [c for c, fila in self.filas.items() if widget.isAncestorOf(fila)]

    def _actualizar_navegacion(self) -> None:
        """Ajusta botones e indicador según el paso actual."""
        paso = self.pasos.currentIndex()
        ultimo_pregunta = self.pasos.count() - 2
        self.indicador.setText(f"Paso {min(paso + 1, ultimo_pregunta + 1)} de {ultimo_pregunta + 1}"
                               if paso <= ultimo_pregunta else "Resultado")
        self.boton_anterior.setVisible(0 < paso <= ultimo_pregunta)
        self.boton_siguiente.setVisible(paso <= ultimo_pregunta)
        self.boton_siguiente.setText("Evaluar ✓" if paso == ultimo_pregunta else "Siguiente →")
        self.mensaje.setText("")
        # La barra avanza suavemente: cada paso completado suma una parte.
        self._animacion_progreso.stop()
        self._animacion_progreso.setStartValue(self.progreso.value())
        self._animacion_progreso.setEndValue(int(1000 * min(paso, ultimo_pregunta + 1) / (ultimo_pregunta + 1)))
        self._animacion_progreso.start()
        if paso < len(GUIA_PASOS) and self.isVisible():
            self.sesion.guiar(*GUIA_PASOS[paso])

    def _anterior(self) -> None:
        """Vuelve al paso anterior."""
        self.pasos.setCurrentIndex(self.pasos.currentIndex() - 1)
        self._actualizar_navegacion()

    def _siguiente(self) -> None:
        """Avanza si todas las preguntas del paso están respondidas; en el último paso lanza la evaluación."""
        paso = self.pasos.currentIndex()
        sin_responder = [c for c in self._codigos_del_paso(paso) if not self.filas[c].valor()[0]]
        if sin_responder:
            self.mensaje.setText("Responde todas las preguntas (puedes elegir «No sé»).")
            return
        if paso == self.pasos.count() - 2:
            self._evaluar()
            return
        self.pasos.setCurrentIndex(paso + 1)
        self._actualizar_navegacion()

    # ---------------------------------------------------------------- Evaluación.

    def _evaluar(self) -> None:
        """Arma el paciente y las respuestas y ejecuta Prolog y R en segundo plano."""
        anio = self.campo_anio.value()
        self.paciente = Paciente(
            alias=self.campo_alias.text().strip() or "anónimo",
            fecha_nacimiento=date(anio, 7, 1) if anio > 1899 else None,  # Mitad de año: edad aproximada.
            embarazo=self.campo_embarazo.isChecked(),
            inmunocompromiso=self.campo_inmuno.isChecked(),
            vacunado_varicela=self.campo_vacunado.currentData(),
            antecedente_varicela=self.campo_antecedente.currentData(),
        )
        self.respuestas = {codigo: fila.valor()[1] for codigo, fila in self.filas.items()}
        self.contacto = self.campo_contacto.currentData()
        self.boton_siguiente.setEnabled(False)
        self.mensaje.setText("Analizando con el motor lógico (Prolog) y el estadístico (R)…")
        self.sesion.guiar("Dame un momento: estoy revisando tus respuestas con mis dos motores de análisis…", "pensando")
        ejecutar(evaluar_triaje, self._mostrar_resultado, self._mostrar_error, self.paciente, self.respuestas, self.contacto)

    def _mostrar_error(self, mensaje: str) -> None:
        """Informa del fallo sin perder las respuestas."""
        self.boton_siguiente.setEnabled(True)
        self.mensaje.setText(f"No se pudo completar el análisis: {mensaje}")
        self.sesion.guiar("Ups, no pude terminar el análisis. Revisa el mensaje de abajo e inténtalo de nuevo.", "preocupado")

    def _mostrar_resultado(self, resultado) -> None:
        """Guarda el resultado en la base (hilo principal) y lo muestra."""
        self.boton_siguiente.setEnabled(True)
        guardar_triaje(self.sesion.conexion, self.paciente, self.respuestas, self.contacto, resultado)
        self.sesion.paciente, self.sesion.consulta_id, self.sesion.ultimo_triaje = self.paciente, resultado.consulta_id, resultado

        color, fondo = estilos.COLORES_DICTAMEN[resultado.dictamen_final]
        self.caja_dictamen.setText(estilos.ETIQUETAS_DICTAMEN[resultado.dictamen_final])
        self.caja_dictamen.setStyleSheet(estilos.caja_resultado(color, fondo))
        r = resultado.r
        motivos = "".join(f"<li>{m}</li>" for m in resultado.motivos)
        diferenciales = ", ".join(DIFERENCIALES.get(d, d) for d in resultado.prolog.diferenciales)
        self.detalle.setText(
            f"<p><b>Por qué:</b></p><ul>{motivos}</ul>"
            f"<p><b>Fase estimada:</b> {FASES.get(resultado.prolog.fase, resultado.prolog.fase)}</p>"
            + (f"<p><b>Otras causas a descartar:</b> {diferenciales}</p>" if diferenciales else "")
            + f"<p><b>Riesgo de complicaciones:</b> {r.riesgo_ponderado.lower()}</p>"
            f"<p style='color:{estilos.PIZARRA_SUAVE}'>Este resultado es orientativo y no sustituye la valoración de un médico. "
            "Puedes resolver dudas con el asistente virtual o consultar el Centro Informativo.</p>"
        )
        self.boton_mapa.setVisible(resultado.habilitar_mapa)
        self.pasos.setCurrentIndex(self.pasos.count() - 1)
        self._actualizar_navegacion()
        aparecer(self.caja_dictamen, duracion=500, desplazamiento=16)
        self.sesion.guiar(*REACCIONES[resultado.dictamen_final])
        self.sesion.triaje_completado.emit(resultado)
        if resultado.habilitar_mapa:
            self.sesion.activar_derivacion("TRIAJE")

    def _reiniciar(self) -> None:
        """Limpia el formulario para un triaje nuevo (de otra persona o en otro momento)."""
        for fila in self.filas.values():
            fila.limpiar()
        self.campo_alias.clear()
        self.campo_anio.setValue(1899)
        for combo in (self.campo_vacunado, self.campo_antecedente, self.campo_contacto):
            combo.setCurrentIndex(2)
        self.campo_embarazo.setChecked(False)
        self.campo_inmuno.setChecked(False)
        self.sesion.paciente = None
        self.sesion.consulta_id = None
        self.pasos.setCurrentIndex(0)
        self._actualizar_navegacion()
