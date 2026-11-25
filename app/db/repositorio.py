"""Acceso a la base de datos SQLite: crea el esquema y guarda pacientes, consultas y resultados."""

import json
import sqlite3
from pathlib import Path

from app import config
from app.core.modelos import Paciente, ResultadoTriaje


def conectar(ruta: Path | str | None = None) -> sqlite3.Connection:
    """Abre la base (la crea si no existe), activa las claves foráneas y aplica el esquema."""
    ruta = config.DB_PATH if ruta is None else ruta
    if str(ruta) != ":memory:":
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.row_factory = sqlite3.Row  # Permite leer columnas por nombre: fila["alias"].
    conexion.execute("PRAGMA foreign_keys = ON")
    # El esquema usa CREATE TABLE IF NOT EXISTS, así que aplicarlo varias veces es seguro.
    conexion.executescript(config.ESQUEMA_SQL.read_text(encoding="utf-8"))
    return conexion


def _bool_a_int(valor: bool | None) -> int | None:
    """Convierte True/False/None al 1/0/NULL que guarda SQLite."""
    return None if valor is None else int(valor)


def crear_paciente(conexion: sqlite3.Connection, paciente: Paciente) -> int:
    """Inserta un paciente y devuelve su id."""
    with conexion:  # El bloque with confirma la transacción o la deshace si hay error.
        cursor = conexion.execute(
            """INSERT INTO pacientes (alias, fecha_nacimiento, sexo, embarazo, inmunocompromiso,
                                      vacunado_varicela, antecedente_varicela)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                paciente.alias,
                paciente.fecha_nacimiento.isoformat() if paciente.fecha_nacimiento else None,
                paciente.sexo,
                int(paciente.embarazo),
                int(paciente.inmunocompromiso),
                _bool_a_int(paciente.vacunado_varicela),
                _bool_a_int(paciente.antecedente_varicela),
            ),
        )
    paciente.id = cursor.lastrowid
    return paciente.id


def crear_consulta(conexion: sqlite3.Connection, paciente_id: int, contacto_previo: bool | None) -> int:
    """Abre una nueva consulta para el paciente y devuelve su id."""
    with conexion:
        cursor = conexion.execute(
            "INSERT INTO consultas (paciente_id, contacto_previo) VALUES (?, ?)",
            (paciente_id, _bool_a_int(contacto_previo)),
        )
    return cursor.lastrowid


def catalogo_sintomas(conexion: sqlite3.Connection) -> list[sqlite3.Row]:
    """Devuelve el catálogo de síntomas en el orden en que se preguntan."""
    return conexion.execute(
        "SELECT id, codigo, nombre, tipo FROM catalogo_sintomas ORDER BY orden"
    ).fetchall()


def guardar_respuestas(conexion: sqlite3.Connection, consulta_id: int, respuestas: dict[str, bool | None]) -> None:
    """Guarda las respuestas del cuestionario; ignora códigos que no estén en el catálogo."""
    ids = {fila["codigo"]: fila["id"] for fila in catalogo_sintomas(conexion)}
    with conexion:
        conexion.executemany(
            "INSERT INTO respuestas_triaje (consulta_id, sintoma_id, presente) VALUES (?, ?, ?)",
            [
                (consulta_id, ids[codigo], _bool_a_int(valor))
                for codigo, valor in respuestas.items()
                if codigo in ids
            ],
        )


def guardar_resultado(conexion: sqlite3.Connection, consulta_id: int, resultado: ResultadoTriaje) -> int:
    """Guarda el dictamen combinado y marca la consulta como finalizada o derivada."""
    estado = "DERIVADA" if resultado.dictamen_final == "DERIVAR_MEDICO" else "FINALIZADA"
    with conexion:
        cursor = conexion.execute(
            """INSERT INTO resultados_triaje
                   (consulta_id, dictamen_prolog, reglas_activadas, probabilidad_r, ic_inferior,
                    ic_superior, riesgo_ponderado, banderas_alarma, dictamen_final, version_motor)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                consulta_id,
                resultado.prolog.dictamen,
                json.dumps(resultado.prolog.razones, ensure_ascii=False),
                resultado.r.probabilidad,
                resultado.r.ic_inferior,
                resultado.r.ic_superior,
                resultado.r.riesgo_ponderado,
                json.dumps(resultado.r.banderas_alarma, ensure_ascii=False),
                resultado.dictamen_final,
                f"{resultado.prolog.version}+{resultado.r.version}",
            ),
        )
        conexion.execute(
            "UPDATE consultas SET estado = ?, finalizada_en = datetime('now') WHERE id = ?",
            (estado, consulta_id),
        )
    return cursor.lastrowid


def guardar_mensaje(
    conexion: sqlite3.Connection,
    consulta_id: int,
    rol: str,
    contenido: str,
    umbral_duda: bool = False,
    modelo_llm: str | None = None,
) -> int:
    """Guarda un mensaje del chat; rol es usuario, asistente o sistema."""
    with conexion:
        cursor = conexion.execute(
            """INSERT INTO mensajes_chat (consulta_id, rol, contenido, umbral_duda, modelo_llm)
               VALUES (?, ?, ?, ?, ?)""",
            (consulta_id, rol, contenido, int(umbral_duda), modelo_llm),
        )
        if umbral_duda:
            conexion.execute("UPDATE consultas SET estado = 'DERIVADA' WHERE id = ?", (consulta_id,))
    return cursor.lastrowid


def historial(conexion: sqlite3.Connection, paciente_id: int) -> list[sqlite3.Row]:
    """Devuelve las consultas del paciente con su dictamen, de la más reciente a la más antigua."""
    return conexion.execute(
        """SELECT c.id, c.iniciada_en, c.estado, r.dictamen_final, r.probabilidad_r
           FROM consultas c
           LEFT JOIN resultados_triaje r ON r.consulta_id = c.id
           WHERE c.paciente_id = ?
           ORDER BY c.iniciada_en DESC, c.id DESC""",
        (paciente_id,),
    ).fetchall()
