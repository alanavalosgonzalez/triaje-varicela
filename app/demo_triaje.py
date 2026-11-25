"""Demostración en consola del triaje completo (Prolog + R + SQLite) antes de tener interfaz gráfica.

Ejecutar desde la raíz del proyecto: python -m app.demo_triaje
"""

from datetime import date

from app import config
from app.core.orquestador import evaluar_triaje
from app.core.modelos import Paciente
from app.db import repositorio

# Textos amigables para cada dictamen.
ETIQUETAS = {
    "NEGATIVO_BAJO_RIESGO": "Negativo / Bajo riesgo",
    "SOSPECHA_INICIAL": "Sospecha inicial",
    "ALTA_PROBABILIDAD": "Alta probabilidad de varicela",
    "DERIVAR_MEDICO": "Acude con un médico lo antes posible",
}


def preguntar(texto: str) -> bool | None:
    """Hace una pregunta de sí/no/no sé y devuelve True, False o None."""
    while True:
        respuesta = input(f"  {texto} [s/n/?]: ").strip().lower()
        if respuesta in ("s", "si", "sí"):
            return True
        if respuesta in ("n", "no"):
            return False
        if respuesta in ("?", "no se", "no sé"):
            return None
        print("    Responde s (sí), n (no) o ? (no sé).")


def main() -> None:
    """Recorre el cuestionario, ejecuta el triaje, lo guarda en la base y muestra el dictamen."""
    print("=" * 70)
    print("TRIAJE VARICELA - demostración en consola")
    print("Aviso: herramienta orientativa. No sustituye una consulta médica.")
    print("=" * 70)

    conexion = repositorio.conectar()
    alias = input("Alias del paciente: ").strip() or "anonimo"
    anio = input("Año de nacimiento (Enter si prefieres no decirlo): ").strip()
    paciente = Paciente(
        alias=alias,
        fecha_nacimiento=date(int(anio), 1, 1) if anio.isdigit() else None,
        vacunado_varicela=preguntar("¿Está vacunado contra la varicela?"),
        antecedente_varicela=preguntar("¿Ya tuvo varicela antes?"),
        embarazo=bool(preguntar("¿Está embarazada?")),
        inmunocompromiso=bool(preguntar("¿Tiene defensas bajas (tratamiento, enfermedad crónica)?")),
    )
    contacto = preguntar("¿Tuvo contacto con alguien con varicela en las últimas 3 semanas?")

    print("\nSíntomas:")
    respuestas = {
        fila["codigo"]: preguntar(fila["nombre"]) for fila in repositorio.catalogo_sintomas(conexion)
    }

    print("\nAnalizando con Prolog y R...")
    resultado = evaluar_triaje(paciente, respuestas, contacto, conexion)

    print("\n" + "=" * 70)
    print(f"DICTAMEN: {ETIQUETAS[resultado.dictamen_final]}")
    for motivo in resultado.motivos:
        print(f"  - {motivo}")
    print(f"Fase estimada: {resultado.prolog.fase}")
    if resultado.prolog.diferenciales:
        print(f"Otras causas a descartar: {', '.join(resultado.prolog.diferenciales)}")
    print(f"Riesgo de complicaciones: {resultado.r.riesgo_ponderado}")
    if resultado.habilitar_mapa:
        print("Se habilitará el mapa de centros de salud cercanos (Fase 5).")
    print(f"\nGuardado como consulta #{resultado.consulta_id} en {config.DB_PATH.name}.")
    conexion.close()


if __name__ == "__main__":
    main()
