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


if __name__ == "__main__":
    unittest.main()
