"""Puentes con los motores externos: SWI-Prolog y R se ejecutan como procesos y responden JSON."""

import json
import subprocess

from app import config
from app.core.modelos import ResultadoProlog, ResultadoR

# Tiempo máximo de espera por cada motor, en segundos.
TIEMPO_LIMITE = 60


class ErrorMotor(RuntimeError):
    """Error al ejecutar Prolog o R (no instalado, fallo del script o respuesta inválida)."""


def _ejecutar(comando: list[str]) -> dict:
    """Ejecuta un comando, comprueba que terminó bien y devuelve su salida JSON como diccionario."""
    try:
        proceso = subprocess.run(
            comando, capture_output=True, text=True, encoding="utf-8", timeout=TIEMPO_LIMITE
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ErrorMotor(f"No se pudo ejecutar {comando[0]}: {error}") from error
    if proceso.returncode != 0:
        raise ErrorMotor(f"{comando[0]} terminó con código {proceso.returncode}: {proceso.stderr.strip()}")
    # Se toma la última línea no vacía para ignorar avisos que el motor escriba antes.
    lineas = [linea for linea in proceso.stdout.splitlines() if linea.strip()]
    if not lineas:
        raise ErrorMotor(f"{comando[0]} no devolvió ninguna respuesta.")
    try:
        return json.loads(lineas[-1])
    except json.JSONDecodeError as error:
        raise ErrorMotor(f"Respuesta JSON inválida de {comando[0]}: {lineas[-1]}") from error


def _valor_prolog(valor: bool | None) -> str:
    """Traduce True/False/None a los átomos si/no/desconoce de Prolog."""
    return "desconoce" if valor is None else ("si" if valor else "no")


def _valor_r(valor) -> str:
    """Traduce True/False/None y números al formato 1/0/NA de R."""
    if valor is None:
        return "NA"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    return str(valor)


def evaluar_prolog(respuestas: dict[str, bool | None]) -> ResultadoProlog:
    """Envía las respuestas al motor lógico y devuelve su dictamen."""
    swipl = config.ruta_swipl()
    if swipl is None:
        raise ErrorMotor("No se encontró SWI-Prolog. Instálalo o define SWIPL_PATH en .env.")
    argumentos = [f"{codigo}={_valor_prolog(valor)}" for codigo, valor in respuestas.items()]
    datos = _ejecutar([swipl, str(config.PROLOG_CLI), *argumentos])
    return ResultadoProlog(
        dictamen=datos["dictamen"],
        razones=datos["razones"],
        fase=datos["fase"],
        diferenciales=datos["diferenciales"],
        version=datos["version_reglas"],
    )


def evaluar_r(variables: dict[str, object]) -> ResultadoR:
    """Envía síntomas y datos del paciente al motor estadístico y devuelve la probabilidad."""
    rscript = config.ruta_rscript()
    if rscript is None:
        raise ErrorMotor("No se encontró Rscript. Instala R o define RSCRIPT_PATH en .env.")
    argumentos = [f"{clave}={_valor_r(valor)}" for clave, valor in variables.items()]
    datos = _ejecutar([rscript, str(config.R_SCRIPT), *argumentos])
    return ResultadoR(
        probabilidad=datos["probabilidad"],
        ic_inferior=datos["ic_inferior"],
        ic_superior=datos["ic_superior"],
        categoria=datos["categoria"],
        indice_coherencia=datos["indice_coherencia"],
        respuestas_desconocidas=datos["respuestas_desconocidas"],
        riesgo_ponderado=datos["riesgo_ponderado"],
        banderas_alarma=datos["banderas_alarma"],
        version=datos["version_modelo"],
    )
