"""Orquestador del triaje: consulta Prolog y R a la vez, combina sus resultados y aplica las reglas de seguridad."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

from app.core import motores
from app.core.modelos import GRAVEDAD, Paciente, ResultadoProlog, ResultadoR, ResultadoTriaje
from app.db import repositorio

# Dictámenes que habilitan el mapa de centros de salud cercanos.
DICTAMENES_CON_MAPA = {"ALTA_PROBABILIDAD", "DERIVAR_MEDICO"}


def _pct(valor: float) -> str:
    """Formatea una probabilidad sin mostrar 0 % o 100 %, que sugerirían una certeza que el modelo no tiene."""
    if valor > 0.99:
        return ">99 %"
    if valor < 0.01:
        return "<1 %"
    return f"{valor:.0%}".replace("%", " %")


def combinar(prolog: ResultadoProlog, r: ResultadoR) -> tuple[str, list[str]]:
    """Combina ambos motores y devuelve (dictamen_final, motivos), siempre del lado más prudente."""
    dictamen_prolog = prolog.dictamen.upper()

    # Seguridad 1: Prolog ya pidió derivar (signo de alarma o demasiadas dudas).
    if dictamen_prolog == "DERIVAR_MEDICO":
        return "DERIVAR_MEDICO", [f"Regla lógica: {razon}" for razon in prolog.razones]

    # Seguridad 2: R detectó signos de alarma.
    if r.banderas_alarma:
        return "DERIVAR_MEDICO", [f"Signo de alarma: {s}" for s in r.banderas_alarma]

    # Umbral de duda A: los motores se contradicen por completo (uno dice negativo y el otro alta).
    if abs(GRAVEDAD[dictamen_prolog] - GRAVEDAD[r.categoria]) >= 2:
        return "DERIVAR_MEDICO", [
            f"Los motores no coinciden (lógico: {dictamen_prolog}, estadístico: {r.categoria})."
        ]

    # Umbral de duda B: el intervalo de confianza abarca desde bajo riesgo hasta alta probabilidad.
    if r.ic_inferior < 0.30 and r.ic_superior >= 0.70:
        return "DERIVAR_MEDICO", [
            f"Resultado incierto: probabilidad entre {_pct(r.ic_inferior)} y {_pct(r.ic_superior)}."
        ]

    # Se elige el dictamen más grave de los dos motores (criterio conservador).
    final = max(dictamen_prolog, r.categoria, key=GRAVEDAD.__getitem__)
    motivos = [
        f"Regla lógica: {dictamen_prolog} ({', '.join(prolog.razones)}).",
        f"Probabilidad estadística: {_pct(r.probabilidad)} "
        f"(IC 95 %: {_pct(r.ic_inferior)} a {_pct(r.ic_superior)}).",
    ]

    # Paciente de riesgo alto (embarazo, inmunocompromiso, lactante) con cualquier sospecha: derivar.
    if r.riesgo_ponderado == "ALTO" and GRAVEDAD[final] >= GRAVEDAD["SOSPECHA_INICIAL"]:
        motivos.append("Riesgo de complicaciones ALTO: requiere valoración médica temprana.")
        final = "DERIVAR_MEDICO"

    return final, motivos


def _variables_r(paciente: Paciente, respuestas: dict[str, bool | None], contacto_previo: bool | None) -> dict:
    """Reúne síntomas y datos del paciente en el formato que espera el script de R."""
    return {
        **respuestas,
        "contacto_previo": contacto_previo,
        "vacunado_varicela": paciente.vacunado_varicela,
        "antecedente_varicela": paciente.antecedente_varicela,
        "embarazo": paciente.embarazo,
        "inmunocompromiso": paciente.inmunocompromiso,
        "edad": paciente.edad(),
    }


def evaluar_triaje(
    paciente: Paciente,
    respuestas: dict[str, bool | None],
    contacto_previo: bool | None,
    conexion: sqlite3.Connection | None = None,
) -> ResultadoTriaje:
    """Ejecuta el triaje completo y, si se pasa una conexión, guarda todo en la base de datos."""
    respuestas_prolog = {**respuestas, "contacto_previo": contacto_previo}

    # Prolog y R se ejecutan en paralelo para que el usuario espere solo lo que tarde el más lento.
    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        futuro_prolog = ejecutor.submit(motores.evaluar_prolog, respuestas_prolog)
        futuro_r = ejecutor.submit(motores.evaluar_r, _variables_r(paciente, respuestas, contacto_previo))
        resultado_prolog = futuro_prolog.result()
        resultado_r = futuro_r.result()

    final, motivos = combinar(resultado_prolog, resultado_r)
    resultado = ResultadoTriaje(
        dictamen_final=final,
        motivos=motivos,
        prolog=resultado_prolog,
        r=resultado_r,
        habilitar_mapa=final in DICTAMENES_CON_MAPA,
    )

    if conexion is not None:
        if paciente.id is None:
            repositorio.crear_paciente(conexion, paciente)
        consulta_id = repositorio.crear_consulta(conexion, paciente.id, contacto_previo)
        repositorio.guardar_respuestas(conexion, consulta_id, respuestas)
        repositorio.guardar_resultado(conexion, consulta_id, resultado)
        resultado.consulta_id = consulta_id

    return resultado
