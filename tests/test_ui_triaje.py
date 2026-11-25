"""Pruebas de la página del cuestionario: escribir el año de nacimiento y avanzar de paso.

Se ejecutan sin mostrar ventanas (Qt offscreen) y con una base de datos temporal.
"""

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # Sin ventanas visibles durante las pruebas.

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app import config  # noqa: E402
from app.ui.comun import Sesion  # noqa: E402
from app.ui.pagina_triaje import PaginaTriaje  # noqa: E402


class PruebasAnioNacimiento(unittest.TestCase):
    """Comprueba que el año se puede escribir directamente y que se valida."""

    @classmethod
    def setUpClass(cls):
        """Crea la aplicación Qt una sola vez."""
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        """Crea la página con una base temporal."""
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta_original = config.DB_PATH
        config.DB_PATH = Path(self.carpeta.name) / "prueba.db"
        self.sesion = Sesion()
        self.pagina = PaginaTriaje(self.sesion)

    def tearDown(self):
        """Restaura la configuración y borra la base temporal."""
        self.sesion.conexion.close()
        config.DB_PATH = self.ruta_original
        self.carpeta.cleanup()

    def escribir(self, texto: str) -> None:
        """Teclea en el campo como lo haría el usuario."""
        self.pagina.campo_anio.clear()
        QTest.keyClicks(self.pagina.campo_anio, texto)

    def test_escribir_anio_directamente(self):
        """Se puede escribir el año sin usar flechas."""
        self.escribir("2018")
        self.assertEqual(self.pagina.campo_anio.text(), "2018")
        self.assertEqual(self.pagina.anio_nacimiento(), 2018)

    def test_vacio_es_opcional(self):
        """Sin año se puede avanzar: el dato es opcional."""
        self.pagina._siguiente()
        self.assertEqual(self.pagina.pasos.currentIndex(), 1)

    def test_anio_incompleto_no_avanza(self):
        """Un año a medias se señala y no deja avanzar."""
        self.escribir("20")
        self.pagina._siguiente()
        self.assertEqual(self.pagina.pasos.currentIndex(), 0)
        self.assertIn("año de nacimiento completo", self.pagina.mensaje.text())

    def test_no_acepta_letras_ni_anios_futuros(self):
        """El validador rechaza letras y años posteriores al actual."""
        self.escribir("20a1")
        self.assertNotIn("a", self.pagina.campo_anio.text())
        self.escribir(str(date.today().year + 1))
        self.assertIsNone(self.pagina.anio_nacimiento())


if __name__ == "__main__":
    unittest.main()
