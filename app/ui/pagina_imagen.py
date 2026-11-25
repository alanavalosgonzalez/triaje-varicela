"""Carga y análisis de una foto de la erupción con el modelo de visión."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.db import repositorio
from app.ui import estilos
from app.ui.comun import Sesion, ejecutar, etiqueta, tarjeta

# Nombres legibles de las clases del modelo.
CLASES = {
    "varicela": "varicela", "sarampion": "sarampión", "mpox": "mpox (viruela símica)",
    "viruela_bovina": "viruela bovina", "mano_pie_boca": "enfermedad de mano, pie y boca", "sana": "piel sana",
}
DECISIONES = {
    "COMPATIBLE": ("Compatible con varicela", estilos.ROJO, estilos.ROJO_FONDO),
    "NO_COMPATIBLE": ("No parece varicela", estilos.TEAL, estilos.TEAL_FONDO),
    "INDETERMINADO": ("Resultado no concluyente", estilos.AMBAR, estilos.AMBAR_FONDO),
}
CONSEJOS = ("Consejos para la foto: luz natural sin flash, enfoca de cerca (10 a 20 cm) varias lesiones, "
            "sin filtros ni maquillaje. La foto se analiza en tu equipo y no se envía a internet.")


class PaginaImagen(QWidget):
    """Permite elegir una foto, la analiza en segundo plano y explica el resultado con su confianza."""

    def __init__(self, sesion: Sesion):
        """Construye la vista previa y los controles."""
        super().__init__()
        self.sesion = sesion
        self.analizador = None
        self.ruta: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(etiqueta("Análisis de la erupción por imagen", "titulo"))
        layout.addWidget(etiqueta(CONSEJOS, "nota"))
        cuerpo = QHBoxLayout()
        marco_foto, capa_foto = tarjeta()
        self.vista = QLabel("Ninguna foto seleccionada")
        self.vista.setAlignment(Qt.AlignCenter)
        self.vista.setMinimumSize(360, 300)
        capa_foto.addWidget(self.vista, 1)
        botones = QHBoxLayout()
        self.boton_elegir = QPushButton("Elegir foto…")
        self.boton_elegir.setObjectName("secundario")
        self.boton_analizar = QPushButton("Analizar")
        self.boton_analizar.setEnabled(False)
        botones.addWidget(self.boton_elegir)
        botones.addWidget(self.boton_analizar)
        capa_foto.addLayout(botones)
        marco_res, capa_res = tarjeta()
        self.caja = etiqueta("")
        self.caja.setAlignment(Qt.AlignCenter)
        self.detalle = etiqueta("Elige una foto y pulsa «Analizar».", "nota")
        self.detalle.setTextFormat(Qt.RichText)
        self.detalle.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        capa_res.addWidget(self.caja)
        capa_res.addWidget(self.detalle, 1)
        cuerpo.addWidget(marco_foto, 1)
        cuerpo.addWidget(marco_res, 1)
        layout.addLayout(cuerpo, 1)

        self.boton_elegir.clicked.connect(self._elegir)
        self.boton_analizar.clicked.connect(self._analizar)

    def _elegir(self) -> None:
        """Abre el selector de archivos y muestra la vista previa."""
        ruta, _ = QFileDialog.getOpenFileName(self, "Elegir foto", "", "Imágenes (*.jpg *.jpeg *.png *.bmp *.webp)")
        if not ruta:
            return
        self.ruta = ruta
        imagen = QPixmap(ruta)
        self.vista.setPixmap(imagen.scaled(self.vista.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.boton_analizar.setEnabled(True)
        self.caja.clear()
        self.caja.setStyleSheet("")
        self.detalle.setText("Pulsa «Analizar».")

    def _analizar(self) -> None:
        """Carga el modelo la primera vez y analiza la foto en segundo plano."""
        from app.vision.analizador import AnalizadorImagen, ErrorVision  # Importación tardía: onnxruntime tarda en cargar.

        if self.analizador is None:
            try:
                self.analizador = AnalizadorImagen()
            except ErrorVision as error:
                self.detalle.setText(f"El análisis de imagen no está disponible: {error}")
                return
        self.boton_analizar.setEnabled(False)
        self.detalle.setText("Analizando…")
        ejecutar(self.analizador.analizar, self._mostrar, self._fallo, self.ruta)

    def _fallo(self, mensaje: str) -> None:
        """Muestra el error de lectura de la imagen."""
        self.boton_analizar.setEnabled(True)
        self.detalle.setText(f"No se pudo analizar la foto: {mensaje}")

    def _mostrar(self, resultado) -> None:
        """Muestra la decisión, las clases más probables y guarda el análisis."""
        self.boton_analizar.setEnabled(True)
        titulo, color, fondo = DECISIONES[resultado.decision]
        self.caja.setText(titulo)
        self.caja.setStyleSheet(estilos.caja_resultado(color, fondo))
        principales = sorted(resultado.probabilidades.items(), key=lambda par: -par[1])[:3]
        lista = "".join(f"<li>{CLASES.get(c, c)}: {p:.0%}</li>" for c, p in principales)
        self.detalle.setText(
            f"<p>{resultado.motivo}</p>"
            + (f"<p><b>Clases más probables:</b></p><ul>{lista}</ul>" if lista else "")
            + f"<p style='color:{estilos.PIZARRA_SUAVE}'>El modelo solo afirma algo si su confianza supera el "
            f"{resultado.umbral:.0%}. Una foto no basta para diagnosticar: confirma siempre con un médico.</p>"
        )
        repositorio.guardar_analisis_imagen(self.sesion.conexion, self.sesion.asegurar_consulta(), self.ruta, resultado)
        if resultado.decision == "COMPATIBLE":
            self.sesion.activar_derivacion("IMAGEN")
