"""Mapa de centros de salud cercanos; solo se habilita cuando algún módulo detecta sospecha alta o necesidad de atención."""

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.db import repositorio
from app.geo import ubicacion as geo_ubicacion
from app.geo.centros import buscar_centros
from app.geo.mapa import interpretar_clic, mapa_html, mapa_seleccion_html
from app.geo.ubicacion import Ubicacion
from app.ui.comun import Sesion, ejecutar, etiqueta

# URL base https para que los mapas puedan cargar sus librerías y mosaicos desde internet.
URL_BASE = QUrl("https://triaje-varicela.local/")


def buscar(modo: str, texto: str, punto: tuple[float, float] | None = None):
    """Obtiene la ubicación (Windows, dirección o punto elegido en el mapa) y los centros cercanos, en segundo plano."""
    if modo == "windows":
        lugar = geo_ubicacion.desde_windows()
    elif modo == "punto":
        lugar = Ubicacion(punto[0], punto[1], "punto elegido en el mapa", "mapa")
    else:
        lugar = geo_ubicacion.desde_direccion(texto)
    return lugar, buscar_centros(lugar.latitud, lugar.longitud)


class PaginaWebMapa(QWebEnginePage):
    """Página web del mapa que escucha los mensajes de clic que envía el código del mapa."""

    clic = Signal(float, float)

    def javaScriptConsoleMessage(self, nivel, mensaje, linea, origen) -> None:  # noqa: N802 (nombre de Qt).
        """Convierte los mensajes de clic del mapa en la señal `clic` e ignora el resto."""
        punto = interpretar_clic(mensaje)
        if punto:
            self.clic.emit(*punto)


class PaginaMapa(QWidget):
    """Busca la ubicación del usuario, consulta OpenStreetMap y muestra mapa y tabla de centros."""

    def __init__(self, sesion: Sesion):
        """Construye los controles de búsqueda, el visor web y la tabla."""
        super().__init__()
        self.sesion = sesion
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(etiqueta("Centros de salud cercanos", "titulo"))
        self.nota = etiqueta("Usa la ubicación de tu equipo o escribe tu dirección para ver hospitales, clínicas y "
                             "consultorios cercanos. En una emergencia llama al número de emergencias de tu país (en México, 911).", "nota")
        layout.addWidget(self.nota)
        fila = QHBoxLayout()
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Ej.: Av. Juárez 10, Centro, Ciudad de México")
        self.boton_buscar = QPushButton("Buscar dirección")
        self.boton_windows = QPushButton("Usar mi ubicación")
        self.boton_elegir = QPushButton("Elegir en el mapa")
        self.boton_elegir.setObjectName("secundario")
        self.boton_elegir.setToolTip("Haz clic en el mapa en el lugar donde estás.")
        fila.addWidget(self.campo, 1)
        fila.addWidget(self.boton_buscar)
        fila.addWidget(self.boton_windows)
        fila.addWidget(self.boton_elegir)
        layout.addLayout(fila)

        divisor = QSplitter(Qt.Vertical)
        self.mapa = QWebEngineView()
        self.pagina_web = PaginaWebMapa(self.mapa)
        self.mapa.setPage(self.pagina_web)
        self.pagina_web.clic.connect(self._clic_en_mapa)
        self._ultimo_punto: tuple[float, float] | None = None
        self._buscando = False
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
        self.boton_elegir.clicked.connect(self._mostrar_mapa_para_elegir)
        self.boton_windows.clicked.connect(lambda: self._buscar("windows"))

    def _mostrar_mapa_para_elegir(self) -> None:
        """Muestra un mapa vacío para que el usuario haga clic donde está."""
        self.mapa.setHtml(mapa_seleccion_html(self._ultimo_punto), URL_BASE)
        self.nota.setText("Acércate con la rueda del mouse y haz clic en el lugar donde estás; "
                          "buscaré los centros de salud cercanos a ese punto.")
        self.sesion.guiar("Haz clic en el mapa donde estás y busco los centros más cercanos a ese punto.", "atento")

    def _clic_en_mapa(self, latitud: float, longitud: float) -> None:
        """Al hacer clic en cualquier mapa, busca los centros cercanos a ese punto."""
        if not self._buscando:
            self._buscar("punto", (latitud, longitud))

    def _buscar(self, modo: str, punto: tuple[float, float] | None = None) -> None:
        """Valida la entrada y lanza la búsqueda en segundo plano."""
        texto = self.campo.text().strip()
        if modo == "direccion" and not texto:
            self.nota.setText("Escribe una dirección, colonia o código postal con la ciudad.")
            return
        self._buscando = True
        self._habilitar(False)
        self.nota.setText("Obteniendo tu ubicación…" if modo == "windows" else "Buscando centros de salud en OpenStreetMap…")
        self.sesion.guiar("Buscando hospitales y clínicas cerca de ti…", "pensando")
        ejecutar(buscar, self._mostrar, self._fallo, modo, texto, punto)

    def _fallo(self, mensaje: str) -> None:
        """Muestra el error de red o de dirección no encontrada."""
        self._listo()
        self.nota.setText(f"No se pudo completar la búsqueda: {mensaje}")
        self.sesion.guiar("No pude completar la búsqueda. Prueba escribiendo tu dirección.", "preocupado")

    def _mostrar(self, datos) -> None:
        """Pinta el mapa, llena la tabla y guarda los centros mostrados."""
        self._listo()
        lugar, centros = datos
        self._ultimo_punto = (lugar.latitud, lugar.longitud)
        self.nota.setText(f"Búsqueda desde: {lugar.descripcion}. {len(centros)} centros encontrados. "
                          "¿No es tu ubicación? Haz clic en el mapa para buscar desde otro punto. "
                          "Los datos provienen de OpenStreetMap; confirma por teléfono antes de acudir.")
        self.mapa.setHtml(mapa_html(lugar, centros), URL_BASE)
        self.tabla.setRowCount(len(centros))
        for fila, c in enumerate(centros):
            valores = [c.nombre, c.tipo, f"{c.distancia_km:.1f} km", c.telefono or "—", "Sí" if c.urgencias else "—"]
            for columna, valor in enumerate(valores):
                self.tabla.setItem(fila, columna, QTableWidgetItem(valor))
        if centros:
            self.sesion.guiar(f"Encontré {len(centros)} centros. El más cercano está a {centros[0].distancia_km:.1f} km.", "feliz")
        else:
            self.sesion.guiar("No encontré centros cerca. Prueba con otra dirección.", "atento")
        if centros:
            repositorio.guardar_derivaciones(self.sesion.conexion, self.sesion.asegurar_consulta(),
                                             self.sesion.origen_derivacion or "TRIAJE", centros)

    def _listo(self) -> None:
        """Vuelve a habilitar los botones de búsqueda."""
        self._buscando = False
        self._habilitar(True)

    def _habilitar(self, activo: bool) -> None:
        """Activa o desactiva los tres botones de búsqueda a la vez."""
        for boton in (self.boton_buscar, self.boton_windows, self.boton_elegir):
            boton.setEnabled(activo)
