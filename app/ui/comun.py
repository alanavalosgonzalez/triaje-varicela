"""Piezas compartidas por todas las páginas: ejecución en segundo plano y estado de la sesión."""

import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.core.modelos import Paciente, ResultadoTriaje
from app.db import repositorio


class SenalesTrabajo(QObject):
    """Señales de un trabajo en segundo plano; se crean en el hilo principal, así sus respuestas llegan a él."""

    terminado = Signal(object)
    fallo = Signal(str)


class Trabajo(QRunnable):
    """Ejecuta una función en otro hilo para que la ventana no se congele mientras responde Prolog, R, Gemini o el modelo."""

    def __init__(self, funcion, *args, **kwargs):
        """Guarda la función y sus argumentos."""
        super().__init__()
        self.funcion, self.args, self.kwargs = funcion, args, kwargs
        self.senales = SenalesTrabajo()

    def run(self):
        """Llama a la función y emite el resultado o el mensaje de error."""
        try:
            resultado = self.funcion(*self.args, **self.kwargs)
        except Exception as error:  # Cualquier error se muestra al usuario en lugar de cerrar la app.
            traceback.print_exc()
            self.senales.fallo.emit(str(error))
        else:
            self.senales.terminado.emit(resultado)


# Referencias a los trabajos en curso: sin ellas Python podría destruir sus señales antes de que lleguen al hilo principal.
_TRABAJOS_ACTIVOS: set[Trabajo] = set()


def ejecutar(funcion, al_terminar, al_fallar, *args, **kwargs) -> None:
    """Lanza una función en el grupo de hilos y conecta sus respuestas."""
    trabajo = Trabajo(funcion, *args, **kwargs)
    trabajo.setAutoDelete(False)
    _TRABAJOS_ACTIVOS.add(trabajo)

    def liberar(*_):
        """Suelta la referencia cuando el trabajo ya respondió."""
        _TRABAJOS_ACTIVOS.discard(trabajo)

    trabajo.senales.terminado.connect(al_terminar)
    trabajo.senales.fallo.connect(al_fallar)
    trabajo.senales.terminado.connect(liberar)
    trabajo.senales.fallo.connect(liberar)
    QThreadPool.globalInstance().start(trabajo)


class Sesion(QObject):
    """Estado compartido entre páginas: base de datos, paciente, consulta actual y si hay que derivar al médico.

    Todas las escrituras en SQLite se hacen desde el hilo principal, porque una conexión no puede compartirse entre hilos.
    """

    derivacion = Signal(str)                 # Origen: TRIAJE, CHAT o IMAGEN.
    triaje_completado = Signal(object)       # ResultadoTriaje.
    guia = Signal(str, str, object)          # Mensaje para el asistente animado: texto, emoción y consejos opcionales.

    def __init__(self):
        """Abre la base de datos local."""
        super().__init__()
        self.conexion = repositorio.conectar()
        self.paciente: Paciente | None = None
        self.consulta_id: int | None = None
        self.ultimo_triaje: ResultadoTriaje | None = None
        self.origen_derivacion: str | None = None

    def asegurar_consulta(self) -> int:
        """Devuelve la consulta actual o crea una con un paciente anónimo si aún no se hizo el triaje."""
        if self.consulta_id is None:
            if self.paciente is None:
                self.paciente = Paciente(alias="anónimo")
            if self.paciente.id is None:
                repositorio.crear_paciente(self.conexion, self.paciente)
            self.consulta_id = repositorio.crear_consulta(self.conexion, self.paciente.id, None)
        return self.consulta_id

    def guiar(self, texto: str, emocion: str = "feliz", consejos: list[str] | None = None) -> None:
        """Pide al asistente animado (Doc) que muestre un mensaje con una expresión."""
        self.guia.emit(texto, emocion, consejos)

    def activar_derivacion(self, origen: str) -> None:
        """Registra que un módulo detectó sospecha alta o necesidad de atención y avisa a la ventana."""
        if self.origen_derivacion is None:
            self.origen_derivacion = origen
        self.derivacion.emit(origen)


def tarjeta() -> tuple[QFrame, QVBoxLayout]:
    """Crea un recuadro blanco con borde suave y devuelve el marco y su layout."""
    from app.ui.animaciones import sombra  # Importación local para evitar dependencias circulares.

    marco = QFrame()
    marco.setObjectName("tarjeta")
    sombra(marco)
    layout = QVBoxLayout(marco)
    layout.setContentsMargins(20, 18, 20, 18)
    return marco, layout


def etiqueta(texto: str, nombre: str | None = None, ajustar: bool = True) -> QLabel:
    """Crea una etiqueta con estilo opcional (titulo, subtitulo o nota)."""
    label = QLabel(texto)
    if nombre:
        label.setObjectName(nombre)
    label.setWordWrap(ajustar)
    return label
