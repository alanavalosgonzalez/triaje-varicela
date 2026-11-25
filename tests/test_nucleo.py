"""Pruebas del núcleo: base de datos, combinación de motores y triaje completo con Prolog y R reales.

Ejecutar desde la raíz del proyecto: python -m unittest -v
"""

import unittest
from datetime import date

from app import config
from app.core.modelos import Paciente, ResultadoProlog, ResultadoR
from app.core.orquestador import combinar, evaluar_triaje
from app.db import repositorio

# Las pruebas de integración se saltan si falta Prolog o R en el equipo.
MOTORES_DISPONIBLES = config.ruta_swipl() is not None and config.ruta_rscript() is not None


def resultado_r(probabilidad, categoria, ic=(0.0, 1.0), riesgo="BAJO", alarmas=None) -> ResultadoR:
    """Crea un ResultadoR de prueba sin ejecutar R."""
    return ResultadoR(probabilidad, ic[0], ic[1], categoria, 0.5, 0, riesgo, alarmas or [], "test")


def resultado_prolog(dictamen, razones=None) -> ResultadoProlog:
    """Crea un ResultadoProlog de prueba sin ejecutar Prolog."""
    return ResultadoProlog(dictamen, razones or ["prueba"], "vesicular", [], "test")


class PruebasBaseDatos(unittest.TestCase):
    """Comprueba el esquema y las operaciones del repositorio en una base en memoria."""

    def setUp(self):
        """Abre una base vacía en memoria antes de cada prueba."""
        self.conexion = repositorio.conectar(":memory:")

    def tearDown(self):
        """Cierra la base después de cada prueba."""
        self.conexion.close()

    def test_catalogo_cargado(self):
        """El esquema carga los 15 síntomas del catálogo."""
        self.assertEqual(len(repositorio.catalogo_sintomas(self.conexion)), 15)

    def test_centro_informativo(self):
        """Las cuatro secciones del Centro Informativo tienen contenido con fuente y no se duplican al reconectar."""
        conteos = {s: len(repositorio.informacion(self.conexion, s)) for s in ("QUE_ES", "CUIDADOS", "AISLAMIENTO", "MITOS")}
        self.assertTrue(all(n > 0 for n in conteos.values()), conteos)
        self.assertTrue(all(fila["fuente"] for fila in repositorio.informacion(self.conexion, "MITOS")))
        # El aviso sobre la aspirina es crítico: debe estar en Cuidados y en Mitos.
        textos = " ".join(f["contenido_md"] for s in ("CUIDADOS", "MITOS") for f in repositorio.informacion(self.conexion, s))
        self.assertGreaterEqual(textos.lower().count("aspirina"), 2)

    def test_seed_no_se_duplica(self):
        """Volver a abrir la misma base no vuelve a insertar el contenido informativo."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "prueba.db")
            for _ in range(2):
                conexion = repositorio.conectar(ruta)
                total = conexion.execute("SELECT COUNT(*) FROM catalogo_informacion").fetchone()[0]
                conexion.close()
            self.assertEqual(total, 17)

    def test_historial_general_y_borrado(self):
        """El historial reúne consultas con sus mensajes, y borrar una consulta elimina sus datos en cascada."""
        paciente_id = repositorio.crear_paciente(self.conexion, Paciente(alias="Luis"))
        consulta_id = repositorio.crear_consulta(self.conexion, paciente_id, None)
        repositorio.guardar_mensaje(self.conexion, consulta_id, "usuario", "Hola")
        filas = repositorio.historial_general(self.conexion)
        self.assertEqual((filas[0]["alias"], filas[0]["mensajes"]), ("Luis", 1))
        repositorio.eliminar_consulta(self.conexion, consulta_id)
        self.assertEqual(self.conexion.execute("SELECT COUNT(*) FROM mensajes_chat").fetchone()[0], 0)

    def test_guardar_en_env(self):
        """Guardar una variable reemplaza su línea, conserva las demás y la crea si no existía."""
        import os
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / ".env"
            archivo.write_text("# comentario\nDB_PATH=data/x.db\nPRUEBA_CLAVE=vieja\n", encoding="utf-8")
            config.guardar_en_env("PRUEBA_CLAVE", "nueva", archivo)
            config.guardar_en_env("PRUEBA_OTRA", "1", archivo)
            self.assertEqual(archivo.read_text(encoding="utf-8"),
                             "# comentario\nDB_PATH=data/x.db\nPRUEBA_CLAVE=nueva\nPRUEBA_OTRA=1\n")
            self.assertEqual(os.environ.pop("PRUEBA_CLAVE"), "nueva")
            os.environ.pop("PRUEBA_OTRA")

    def test_paciente_y_consulta(self):
        """Se puede crear un paciente, abrirle una consulta y verla en su historial."""
        paciente_id = repositorio.crear_paciente(self.conexion, Paciente(alias="Ana", vacunado_varicela=None))
        consulta_id = repositorio.crear_consulta(self.conexion, paciente_id, contacto_previo=True)
        repositorio.guardar_respuestas(self.conexion, consulta_id, {"vesiculas": True, "codigo_inexistente": True})
        historial = repositorio.historial(self.conexion, paciente_id)
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["estado"], "ABIERTA")
        filas = self.conexion.execute("SELECT COUNT(*) FROM respuestas_triaje").fetchone()[0]
        self.assertEqual(filas, 1)  # El código inexistente se ignora.


class PruebasCombinacion(unittest.TestCase):
    """Comprueba las reglas de seguridad del orquestador sin ejecutar los motores."""

    def test_prolog_pide_derivar(self):
        """Si Prolog deriva, el resultado final deriva aunque R diga bajo riesgo."""
        final, _ = combinar(resultado_prolog("derivar_medico"), resultado_r(0.05, "NEGATIVO_BAJO_RIESGO", (0.01, 0.1)))
        self.assertEqual(final, "DERIVAR_MEDICO")

    def test_motores_contradictorios(self):
        """Negativo en un motor y alta probabilidad en el otro se considera duda y deriva."""
        final, _ = combinar(resultado_prolog("negativo_bajo_riesgo"), resultado_r(0.9, "ALTA_PROBABILIDAD", (0.8, 0.95)))
        self.assertEqual(final, "DERIVAR_MEDICO")

    def test_intervalo_demasiado_ancho(self):
        """Un intervalo de confianza que va de bajo a alto se considera duda y deriva."""
        final, _ = combinar(resultado_prolog("sospecha_inicial"), resultado_r(0.5, "SOSPECHA_INICIAL", (0.1, 0.9)))
        self.assertEqual(final, "DERIVAR_MEDICO")

    def test_se_elige_el_mas_grave(self):
        """Con motores coherentes se elige el dictamen más grave de los dos."""
        final, _ = combinar(resultado_prolog("sospecha_inicial"), resultado_r(0.8, "ALTA_PROBABILIDAD", (0.7, 0.9)))
        self.assertEqual(final, "ALTA_PROBABILIDAD")

    def test_riesgo_alto_con_sospecha(self):
        """Un paciente de riesgo alto con sospecha se deriva al médico."""
        final, _ = combinar(
            resultado_prolog("sospecha_inicial"), resultado_r(0.5, "SOSPECHA_INICIAL", (0.4, 0.6), riesgo="ALTO")
        )
        self.assertEqual(final, "DERIVAR_MEDICO")


@unittest.skipUnless(MOTORES_DISPONIBLES, "SWI-Prolog o R no están instalados.")
class PruebasIntegracion(unittest.TestCase):
    """Ejecuta el triaje completo con los motores reales y lo guarda en una base en memoria."""

    def setUp(self):
        """Prepara una base en memoria y un paciente infantil sin factores de riesgo."""
        self.conexion = repositorio.conectar(":memory:")
        self.paciente = Paciente(alias="Niño", fecha_nacimiento=date(2019, 5, 1), vacunado_varicela=False)

    def tearDown(self):
        """Cierra la base."""
        self.conexion.close()

    def test_caso_tipico(self):
        """Un cuadro típico da alta probabilidad, habilita el mapa y queda guardado."""
        respuestas = {"vesiculas": True, "lesiones_simultaneas": True, "prurito": True,
                      "fiebre_moderada": True, "inicio_tronco": True, "dificultad_respiratoria": False}
        resultado = evaluar_triaje(self.paciente, respuestas, contacto_previo=True, conexion=self.conexion)
        self.assertEqual(resultado.dictamen_final, "ALTA_PROBABILIDAD")
        self.assertTrue(resultado.habilitar_mapa)
        guardado = self.conexion.execute(
            "SELECT dictamen_final FROM resultados_triaje WHERE consulta_id = ?", (resultado.consulta_id,)
        ).fetchone()
        self.assertEqual(guardado["dictamen_final"], "ALTA_PROBABILIDAD")

    def test_signo_de_alarma(self):
        """La dificultad respiratoria siempre deriva al médico y marca la consulta como DERIVADA."""
        resultado = evaluar_triaje(self.paciente, {"dificultad_respiratoria": True}, None, self.conexion)
        self.assertEqual(resultado.dictamen_final, "DERIVAR_MEDICO")
        estado = self.conexion.execute("SELECT estado FROM consultas").fetchone()["estado"]
        self.assertEqual(estado, "DERIVADA")

    def test_sin_sintomas(self):
        """Sin síntomas compatibles el resultado es negativo y no se habilita el mapa."""
        respuestas = {"cefalea": True, "vesiculas": False, "papulas": False, "maculas": False}
        resultado = evaluar_triaje(self.paciente, respuestas, contacto_previo=False)
        self.assertEqual(resultado.dictamen_final, "NEGATIVO_BAJO_RIESGO")
        self.assertFalse(resultado.habilitar_mapa)


if __name__ == "__main__":
    unittest.main()
