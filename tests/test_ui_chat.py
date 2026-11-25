"""Prueba de la página de chat: cambiar la clave mientras llega una respuesta no debe provocar errores.

Reproduce el fallo "NoneType object has no attribute proveedor". Se ejecuta sin mostrar ventanas (Qt offscreen).
"""

import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # Sin ventanas visibles durante las pruebas.

from PySide6.QtWidgets import QApplication  # noqa: E402

from app import config  # noqa: E402
from app.ai.asistente import AsistenteMedico  # noqa: E402
from app.ui import pagina_chat  # noqa: E402
from app.ui.comun import Sesion  # noqa: E402


class ProveedorLento:
    """Proveedor falso que tarda un poco en responder, como Gemini por internet."""

    nombre_modelo = "lento-1"

    def responder(self, instrucciones, historial):
        """Espera medio segundo y responde."""
        time.sleep(0.5)
        return "Respuesta del modelo"


class PruebasPaginaChat(unittest.TestCase):
    """Comprueba el chat con una base temporal y proveedores falsos."""

    @classmethod
    def setUpClass(cls):
        """Crea la aplicación Qt una sola vez."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Usa una base de datos temporal para no tocar la del usuario."""
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta_original = config.DB_PATH
        config.DB_PATH = Path(self.carpeta.name) / "prueba.db"
        self.sesion = Sesion()
        self.pagina = pagina_chat.PaginaChat(self.sesion)

    def tearDown(self):
        """Restaura la configuración y borra la base temporal."""
        self.sesion.conexion.close()
        config.DB_PATH = self.ruta_original
        self.carpeta.cleanup()

    def esperar_respuesta(self, segundos: float = 5) -> None:
        """Procesa eventos de Qt hasta que el botón Enviar vuelva a estar disponible."""
        limite = time.time() + segundos
        while not self.pagina.boton.isEnabled() and time.time() < limite:
            self.app.processEvents()
            time.sleep(0.02)

    def test_cambiar_clave_con_respuesta_en_camino(self):
        """Reiniciar el asistente mientras responde no falla y conserva la conversación."""
        self.pagina.asistente = AsistenteMedico(ProveedorLento())
        original = pagina_chat.ProveedorGemini
        pagina_chat.ProveedorGemini = ProveedorLento  # La "clave nueva" crea otro proveedor falso.
        try:
            self.pagina.campo.setText("Tengo granitos")
            self.pagina._enviar()
            self.pagina.reiniciar_asistente()  # Como si se guardara la clave mientras Gemini responde.
            self.esperar_respuesta()
        finally:
            pagina_chat.ProveedorGemini = original
        self.assertTrue(self.pagina.boton.isEnabled())
        self.assertIn("Respuesta del modelo", self.pagina.historial.toPlainText())
        self.assertEqual(len(self.pagina.asistente.historial), 2)  # La conversación se conservó.
        roles = [f["rol"] for f in self.sesion.conexion.execute("SELECT rol FROM mensajes_chat ORDER BY id")]
        self.assertEqual(roles, ["usuario", "asistente"])


if __name__ == "__main__":
    unittest.main()
