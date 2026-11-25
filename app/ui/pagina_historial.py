"""Historial de consultas guardadas en este equipo, con opción de borrar una consulta."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.core.orquestador import _pct
from app.db import repositorio
from app.ui import estilos
from app.ui.comun import Sesion, etiqueta

ESTADOS = {"ABIERTA": "Abierta", "FINALIZADA": "Finalizada", "DERIVADA": "Derivada al médico"}
IMAGEN = {"COMPATIBLE": "Compatible", "NO_COMPATIBLE": "No compatible", "INDETERMINADO": "Indeterminado"}
COLUMNAS = ["Fecha", "Alias", "Dictamen del triaje", "Probabilidad", "Imagen", "Mensajes", "Estado"]


class PaginaHistorial(QWidget):
    """Tabla de consultas; se actualiza cada vez que se abre la página."""

    def __init__(self, sesion: Sesion):
        """Construye la tabla y los botones."""
        super().__init__()
        self.sesion = sesion
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(etiqueta("Historial de consultas", "titulo"))
        layout.addWidget(etiqueta("Las consultas se guardan solo en este equipo. Puedes borrar las que no quieras conservar.", "nota"))
        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla, 1)
        botones = QHBoxLayout()
        self.total = etiqueta("", "nota")
        self.boton_borrar = QPushButton("Borrar consulta seleccionada")
        self.boton_borrar.setObjectName("secundario")
        self.boton_borrar.clicked.connect(self._borrar)
        botones.addWidget(self.total, 1)
        botones.addWidget(self.boton_borrar)
        layout.addLayout(botones)

    def showEvent(self, evento) -> None:
        """Recarga los datos al mostrar la página, así incluye las consultas recién hechas."""
        self.actualizar()
        super().showEvent(evento)

    def actualizar(self) -> None:
        """Llena la tabla con las consultas más recientes."""
        filas = repositorio.historial_general(self.sesion.conexion)
        self.tabla.setRowCount(len(filas))
        for i, f in enumerate(filas):
            dictamen = f["dictamen_final"]
            valores = [
                f["fecha_local"], f["alias"],
                estilos.ETIQUETAS_DICTAMEN.get(dictamen, "Sin cuestionario"),
                _pct(f["probabilidad_r"]) if f["probabilidad_r"] is not None else "—",
                IMAGEN.get(f["imagen"], "—"), str(f["mensajes"]) if f["mensajes"] else "—",
                ESTADOS.get(f["estado"], f["estado"]),
            ]
            for j, valor in enumerate(valores):
                celda = QTableWidgetItem(valor)
                if j == 0:
                    celda.setData(Qt.UserRole, f["id"])  # El id de la consulta se guarda oculto en la primera celda.
                if j == 2 and dictamen in estilos.COLORES_DICTAMEN:
                    celda.setForeground(Qt.GlobalColor.black)
                    celda.setBackground(QColor(estilos.COLORES_DICTAMEN[dictamen][1]))
                self.tabla.setItem(i, j, celda)
        self.total.setText(f"{len(filas)} consulta" + ("" if len(filas) == 1 else "s"))

    def _borrar(self) -> None:
        """Pide confirmación y borra la consulta seleccionada con todos sus datos."""
        fila = self.tabla.currentRow()
        if fila < 0:
            self.total.setText("Selecciona primero una consulta de la tabla.")
            return
        consulta_id = self.tabla.item(fila, 0).data(Qt.UserRole)
        confirmacion = QMessageBox.question(
            self, "Borrar consulta",
            "Se borrarán la consulta, sus respuestas, resultados, mensajes del chat y análisis de imagen. "
            "Esta acción no se puede deshacer. ¿Continuar?")
        if confirmacion != QMessageBox.Yes:
            return
        repositorio.eliminar_consulta(self.sesion.conexion, consulta_id)
        if self.sesion.consulta_id == consulta_id:
            self.sesion.consulta_id = None  # La próxima acción abrirá una consulta nueva.
        self.actualizar()

