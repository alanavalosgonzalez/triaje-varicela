"""Pruebas del asistente médico sin conexión a internet, usando un proveedor falso en lugar de Gemini.

Ejecutar desde la raíz del proyecto: python -m unittest -v
"""

import unittest

from app.ai import seguridad
from app.ai.asistente import AsistenteMedico
from app.ai.proveedores import Mensaje
from app.core.modelos import Paciente
from app.db import repositorio


class ProveedorFalso:
    """Imita a un proveedor LLM: devuelve respuestas predefinidas y cuenta cuántas veces se le llamó."""

    nombre_modelo = "falso-1"

    def __init__(self, respuestas: list[str]):
        """Guarda la lista de respuestas que irá devolviendo en orden."""
        self.respuestas = list(respuestas)
        self.llamadas: list[list[Mensaje]] = []

    def responder(self, instrucciones: str, historial: list[Mensaje]) -> str:
        """Registra la llamada y devuelve la siguiente respuesta predefinida."""
        self.llamadas.append(list(historial))
        return self.respuestas.pop(0)


class PruebasDeteccionAlarmas(unittest.TestCase):
    """Comprueba que el filtro reconoce signos de alarma escritos en lenguaje natural."""

    def test_respiracion(self):
        """Detecta dificultad respiratoria aunque se escriba sin acentos o con mayúsculas."""
        self.assertIn("dificultad_respiratoria", seguridad.detectar_alarmas("Mi hijo NO PUEDE RESPIRAR bien"))
        self.assertIn("dificultad_respiratoria", seguridad.detectar_alarmas("siento que me falta el aire"))
        self.assertIn("dificultad_respiratoria", seguridad.detectar_alarmas("me ahogo al caminar"))

    def test_fiebre_muy_alta(self):
        """Detecta fiebre de 39.5 °C o más y no la de 38 °C."""
        self.assertIn("fiebre_muy_alta", seguridad.detectar_alarmas("tiene 40 grados de fiebre"))
        self.assertIn("fiebre_muy_alta", seguridad.detectar_alarmas("el termómetro marca 39,8 °C"))
        self.assertNotIn("fiebre_muy_alta", seguridad.detectar_alarmas("tuvo 38 grados ayer"))

    def test_infeccion_y_ojos(self):
        """Detecta lesiones con pus y lesiones en los ojos."""
        self.assertIn("lesiones_infectadas", seguridad.detectar_alarmas("una ampolla tiene pus"))
        self.assertIn("lesion_ocular", seguridad.detectar_alarmas("le salió una en el ojo"))

    def test_mensaje_normal(self):
        """Un mensaje típico de varicela leve no activa ninguna alarma."""
        texto = "Tengo granitos con comezón en la espalda y 38 grados desde ayer"
        self.assertEqual(seguridad.detectar_alarmas(texto), [])


class PruebasAsistente(unittest.TestCase):
    """Comprueba el flujo de conversación y su registro en la base de datos."""

    def setUp(self):
        """Crea una base en memoria con un paciente y una consulta abierta."""
        self.conexion = repositorio.conectar(":memory:")
        paciente_id = repositorio.crear_paciente(self.conexion, Paciente(alias="Prueba"))
        self.consulta_id = repositorio.crear_consulta(self.conexion, paciente_id, None)

    def tearDown(self):
        """Cierra la base."""
        self.conexion.close()

    def test_conversacion_normal(self):
        """Una respuesta sin marca se entrega tal cual y se guardan los dos mensajes."""
        proveedor = ProveedorFalso(["¿Desde cuándo tienes la erupción?"])
        asistente = AsistenteMedico(proveedor, self.conexion, self.consulta_id)
        respuesta = asistente.enviar("Me salieron granitos que pican")
        self.assertFalse(respuesta.derivar)
        self.assertEqual(respuesta.texto, "¿Desde cuándo tienes la erupción?")
        filas = self.conexion.execute("SELECT rol FROM mensajes_chat ORDER BY id").fetchall()
        self.assertEqual([f["rol"] for f in filas], ["usuario", "asistente"])

    def test_urgencia_no_consulta_al_modelo(self):
        """Ante un signo de alarma se responde con el mensaje fijo y el modelo nunca se llama."""
        proveedor = ProveedorFalso([])
        asistente = AsistenteMedico(proveedor, self.conexion, self.consulta_id)
        respuesta = asistente.enviar("Tiene varicela y ahora le cuesta respirar")
        self.assertTrue(respuesta.urgencia)
        self.assertTrue(asistente.derivado)
        self.assertEqual(proveedor.llamadas, [])
        estado = self.conexion.execute("SELECT estado FROM consultas").fetchone()["estado"]
        self.assertEqual(estado, "DERIVADA")

    def test_marca_de_duda_del_modelo(self):
        """Si el modelo escribe la marca, se quita del texto, se añade la nota y se activa la derivación."""
        proveedor = ProveedorFalso([f"Tus respuestas no son concluyentes.\n{seguridad.MARCA_DERIVAR}"])
        asistente = AsistenteMedico(proveedor, self.conexion, self.consulta_id)
        respuesta = asistente.enviar("No sé, a veces sí y a veces no")
        self.assertTrue(respuesta.derivar)
        self.assertNotIn(seguridad.MARCA_DERIVAR, respuesta.texto)
        self.assertIn(seguridad.NOTA_DERIVACION, respuesta.texto)

    def test_historial_se_envia_completo(self):
        """En el segundo turno el modelo recibe los tres mensajes anteriores."""
        proveedor = ProveedorFalso(["Pregunta 1", "Pregunta 2"])
        asistente = AsistenteMedico(proveedor)
        asistente.enviar("Hola")
        asistente.enviar("Tengo comezón")
        self.assertEqual(len(proveedor.llamadas[1]), 3)


class ErrorApiFalso(Exception):
    """Imita un error de la API de Gemini con su código HTTP."""

    def __init__(self, code: int):
        """Guarda el código, como hace el SDK."""
        super().__init__(f"error {code}")
        self.code = code


class ClienteFalso:
    """Imita genai.Client: cada llamada consume la siguiente acción de la lista (un error o un texto)."""

    def __init__(self, acciones: list):
        """Guarda las acciones y registra qué modelo se pidió en cada llamada."""
        self.acciones, self.modelos_llamados = list(acciones), []
        self.models = self

    def generate_content(self, model, contents, config):
        """Lanza el error o devuelve un objeto con .text."""
        self.modelos_llamados.append(model)
        accion = self.acciones.pop(0)
        if isinstance(accion, Exception):
            raise accion
        return type("Respuesta", (), {"text": accion})()


class TimeoutFalso(Exception):
    """Imita el error de tiempo agotado de la conexión (sin código HTTP)."""


class PruebasReintentosGemini(unittest.TestCase):
    """Comprueba los reintentos ante saturación, el tiempo límite y el paso a modelos de respaldo."""

    def proveedor(self, acciones: list, respaldo=("respaldo",)):
        """Crea un ProveedorGemini con un cliente falso, sin red ni espera real."""
        from google.genai import types

        from app.ai.proveedores import ProveedorGemini

        p = object.__new__(ProveedorGemini)
        p._types, p._cliente, p._temperatura = types, ClienteFalso(acciones), 0.3
        p.nombre_modelo, p.modelos_respaldo, p.modelo_usado = "principal", list(respaldo), "principal"
        p._pausados, p._sin_razonamiento = {}, set()
        p.ahora = 1000.0
        p._reloj = lambda: p.ahora
        p.esperas = []
        p._esperar = p.esperas.append
        return p

    def responder(self, p):
        """Envía un mensaje de prueba."""
        return p.responder("sistema", [Mensaje("usuario", "hola")])

    def test_reintenta_y_responde(self):
        """Un 503 y luego éxito: responde el modelo principal tras esperar 1 segundo."""
        p = self.proveedor([ErrorApiFalso(503), "Hola"])
        self.assertEqual(self.responder(p), "Hola")
        self.assertEqual((p.modelo_usado, p.esperas), ("principal", [1]))

    def test_pasa_al_modelo_de_respaldo(self):
        """Si el principal falla en sus dos intentos, responde el modelo de respaldo."""
        p = self.proveedor([ErrorApiFalso(503)] * 2 + ["Respuesta de respaldo"])
        self.assertEqual(self.responder(p), "Respuesta de respaldo")
        self.assertEqual(p.modelo_usado, "respaldo")

    def test_tiempo_agotado_pasa_directo_al_respaldo(self):
        """Si el principal no responde a tiempo, no se le vuelve a esperar: se pasa al respaldo de inmediato."""
        p = self.proveedor([TimeoutFalso("lento"), "Rápido"])
        self.assertEqual(self.responder(p), "Rápido")
        self.assertEqual(p._cliente.modelos_llamados, ["principal", "respaldo"])

    def test_modelo_saturado_se_salta_un_tiempo(self):
        """Tras fallar, el principal se deja al final durante la pausa y se vuelve a probar cuando termina."""
        from app.ai.proveedores import PAUSA_MODELO_SATURADO

        p = self.proveedor([ErrorApiFalso(503), ErrorApiFalso(503), "uno", "dos", "tres"])
        self.responder(p)
        self.responder(p)  # Durante la pausa empieza directamente por el respaldo.
        self.assertEqual(p._cliente.modelos_llamados, ["principal", "principal", "respaldo", "respaldo"])
        p.ahora += PAUSA_MODELO_SATURADO + 1
        self.responder(p)  # Pasada la pausa, se vuelve a intentar con el principal.
        self.assertEqual(p._cliente.modelos_llamados[-1], "principal")

    def test_modelo_sin_nivel_de_razonamiento(self):
        """Si un modelo rechaza el nivel de razonamiento (400), se repite sin él y se recuerda."""
        error = ErrorApiFalso(400)
        error.args = ("400 INVALID_ARGUMENT: Thinking level is not supported",)
        p = self.proveedor([error, "Sin razonamiento"])
        self.assertEqual(self.responder(p), "Sin razonamiento")
        self.assertIn("principal", p._sin_razonamiento)

    def test_error_no_temporal_no_se_reintenta(self):
        """Un error como clave inválida (400) se informa de inmediato, sin reintentos."""
        from app.ai.proveedores import ErrorProveedor

        p = self.proveedor([ErrorApiFalso(400)])
        with self.assertRaises(ErrorProveedor):
            self.responder(p)
        self.assertEqual(p._cliente.modelos_llamados, ["principal"])


if __name__ == "__main__":
    unittest.main()
