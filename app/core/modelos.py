"""Estructuras de datos que viajan entre la interfaz, los motores y la base de datos."""

from dataclasses import dataclass, field
from datetime import date

# Orden de gravedad de los dictámenes; sirve para elegir el más conservador.
GRAVEDAD = {
    "NEGATIVO_BAJO_RIESGO": 0,
    "SOSPECHA_INICIAL": 1,
    "ALTA_PROBABILIDAD": 2,
    "DERIVAR_MEDICO": 3,
}


@dataclass
class Paciente:
    """Datos del paciente que influyen en el riesgo; None significa "no sabe"."""

    alias: str
    fecha_nacimiento: date | None = None
    sexo: str | None = None
    embarazo: bool = False
    inmunocompromiso: bool = False
    vacunado_varicela: bool | None = None
    antecedente_varicela: bool | None = None
    id: int | None = None

    def edad(self, hoy: date | None = None) -> int | None:
        """Calcula la edad en años cumplidos a partir de la fecha de nacimiento."""
        if self.fecha_nacimiento is None:
            return None
        hoy = hoy or date.today()
        cumplio = (hoy.month, hoy.day) >= (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        return hoy.year - self.fecha_nacimiento.year - (0 if cumplio else 1)


@dataclass
class ResultadoProlog:
    """Respuesta del motor lógico."""

    dictamen: str
    razones: list[str]
    fase: str
    diferenciales: list[str]
    version: str


@dataclass
class ResultadoR:
    """Respuesta del motor estadístico."""

    probabilidad: float
    ic_inferior: float
    ic_superior: float
    categoria: str
    indice_coherencia: float
    respuestas_desconocidas: int
    riesgo_ponderado: str
    banderas_alarma: list[str]
    version: str


@dataclass
class ResultadoTriaje:
    """Dictamen final combinado que se muestra al usuario y se guarda en la base."""

    dictamen_final: str
    motivos: list[str]
    prolog: ResultadoProlog
    r: ResultadoR
    habilitar_mapa: bool
    consulta_id: int | None = None
    advertencias: list[str] = field(default_factory=list)
