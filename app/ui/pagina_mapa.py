"""Mapa de centros de salud cercanos; solo se habilita cuando algún módulo detecta sospecha alta o necesidad de atención."""

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from app.db import repositorio
from app.geo import ubicacion as geo_ubicacion
from app.geo.centros import buscar_centros
from app.geo.mapa import mapa_html
from app.ui.comun import Sesion, ejecutar, etiqueta

AVISO_IP = ("Para estimar tu ubicación se enviará tu dirección IP a un servicio externo (ipapi.co). "
            "La precisión suele ser solo a nivel de ciudad. ¿Deseas continuar?")


def buscar(modo: str, texto: str):
    """Obtiene la ubicación (por dirección o por IP) y los centros cercanos; se ejecuta en segundo plano."""
    lugar = geo_ubicacion.desde_ip() if modo == "ip" else geo_ubicacion.desde_direccion(texto)
    return lugar, buscar_centros(lugar.latitud, lugar.longitud)


class PaginaMapa(QWidget):
    """Busca la ubicación del usuario, consulta OpenStreetMap y muestra mapa y tabla de centros."""

    def __init__(self, sesion: Sesion):
        """Construye los controles de búsqueda, el visor web y la tabla."""
        super().__init__()
        self.sesion = sesion
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(etiqueta("Centros de salud cercanos", "titulo"))
        self.nota = etiqueta("Escribe tu dirección o colonia y ciudad para ver hospitales, clínicas y consultorios "
                             "cercanos. En una emergencia llama al número de emergencias de tu país (en México, 911).", "nota")
        layout.addWidget(self.nota)
        fila = QHBoxLayout()
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Ej.: Av. Juárez 10, Centro, Ciudad de México")
        self.boton_buscar = QPushButton("Buscar")
        self.boton_ip = QPushButton("Usar ubicación aproximada")
        self.boton_ip.setObjectName("secundario")
        fila.addWidget(self.campo, 1)
        fila.addWidget(self.boton_buscar)
        fila.addWidget(self.boton_ip)
        layout.addLayout(fila)

        divisor = QSplitter(Qt.Vertical)
        self.mapa = QWebEngineView()
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Tipo", "Distancia", "Teléfono", "Urgencias"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.verticalHeader().setVisible(False)
        self.mapa.setHtml("<body style='font-family:Segoe UI;color:#64748B;display:flex;align-items:center;"
                          "justify-content:center;height:90vh'>El mapa aparecerá aquí después de buscar.</body>")
        divisor.addWidget(self.mapa)
        divisor.addWidget(self.tabla)
        divisor.setSizes([420, 180])
        layout.addWidget(divisor, 1)

        self.campo.returnPressed.connect(lambda: self._buscar("direccion"))
        self.boton_buscar.clicked.connect(lambda: self._buscar("direccion"))
        self.boton_ip.clicked.connect(lambda: self._buscar("ip"))

    def _buscar(self, modo: str) -> None:
        """Valida la entrada, pide consentimiento para la IP y lanza la búsqueda en segundo plano."""
        texto = self.campo.text().strip()
        if modo == "direccion" and not texto:
            self.nota.setText("Escribe una dirección, colonia o código postal con la ciudad.")
            return
        if modo == "ip" and QMessageBox.question(self, "Ubicación aproximada", AVISO_IP) != QMessageBox.Yes:
            return
        self.boton_buscar.setEnabled(False)
        self.boton_ip.setEnabled(False)
        self.nota.setText("Buscando centros de salud en OpenStreetMap…")
        ejecutar(buscar, self._mostrar, self._fallo, modo, texto)

    def _fallo(self, mensaje: str) -> None:
        """Muestra el error de red o de dirección no encontrada."""
        self._listo()
        self.nota.setText(f"No se pudo completar la búsqueda: {mensaje}")

    def _mostrar(self, datos) -> None:
        """Pinta el mapa, llena la tabla y guarda los centros mostrados."""
        self._listo()
        lugar, centros = datos
        precision = " (aproximada)" if lugar.precision == "ip" else ""
        self.nota.setText(f"Ubicación{precision}: {lugar.descripcion}. {len(centros)} centros encontrados. "
                          "Los datos provienen de OpenStreetMap; confirma por teléfono antes de acudir.")
        # Se usa una URL base https para que el mapa pueda cargar sus librerías y mosaicos desde internet.
        self.mapa.setHtml(mapa_html(lugar, centros), QUrl("https://triaje-varicela.local/"))
        self.tabla.setRowCount(len(centros))
        for fila, c in enumerate(centros):
            valores = [c.nombre, c.tipo, f"{c.distancia_km:.1f} km", c.telefono or "—", "Sí" if c.urgencias else "—"]
            for columna, valor in enumerate(valores):
                self.tabla.setItem(fila, columna, QTableWidgetItem(valor))
        if centros:
            repositorio.guardar_derivaciones(self.sesion.conexion, self.sesion.asegurar_consulta(),
                                             self.sesion.origen_derivacion or "TRIAJE", centros)

    def _listo(self) -> None:
        """Vuelve a habilitar los botones de búsqueda."""
        self.boton_buscar.setEnabled(True)
        self.boton_ip.setEnabled(True)
