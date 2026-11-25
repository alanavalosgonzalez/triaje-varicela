"""Pruebas de la lógica de visión que no requieren el modelo entrenado: calidad de imagen y decisión con umbral.

Ejecutar desde la raíz del proyecto: python -m unittest -v
"""

import unittest

import numpy as np
from PIL import Image

from app.vision.analizador import calidad_imagen, decidir


def imagen_ruido(lado: int = 300, brillo: int = 128, semilla: int = 0) -> Image.Image:
    """Crea una imagen con textura aleatoria (nítida) del brillo medio indicado."""
    generador = np.random.default_rng(semilla)
    datos = np.clip(generador.normal(brillo, 40, (lado, lado, 3)), 0, 255).astype(np.uint8)
    return Image.fromarray(datos)


class PruebasCalidad(unittest.TestCase):
    """Comprueba que las fotos inservibles se rechazan antes de analizarlas."""

    def test_imagen_aceptable(self):
        """Una imagen nítida, bien iluminada y grande pasa el control."""
        self.assertIsNone(calidad_imagen(imagen_ruido()))

    def test_muy_pequena(self):
        """Una imagen menor de 100 píxeles se rechaza."""
        self.assertIn("pequeña", calidad_imagen(imagen_ruido(lado=64)))

    def test_oscura(self):
        """Una imagen casi negra se rechaza por oscura."""
        self.assertIn("oscura", calidad_imagen(Image.new("RGB", (300, 300), (10, 10, 10))))

    def test_borrosa(self):
        """Una imagen lisa, sin bordes, se rechaza por borrosa."""
        self.assertIn("borrosa", calidad_imagen(Image.new("RGB", (300, 300), (150, 120, 110))))


class PruebasDecision(unittest.TestCase):
    """Comprueba que el modelo solo afirma algo cuando supera el umbral de confianza."""

    def test_compatible(self):
        """Varicela con confianza alta es COMPATIBLE."""
        decision, clase, _, _ = decidir({"varicela": 0.92, "sarampion": 0.05, "sana": 0.03}, "varicela", 0.85)
        self.assertEqual((decision, clase), ("COMPATIBLE", "varicela"))

    def test_no_compatible(self):
        """Otra clase con confianza alta es NO_COMPATIBLE."""
        decision, clase, _, _ = decidir({"varicela": 0.04, "sarampion": 0.90, "sana": 0.06}, "varicela", 0.85)
        self.assertEqual((decision, clase), ("NO_COMPATIBLE", "sarampion"))

    def test_otra_enfermedad_requiere_medico(self):
        """Si la foto parece otra enfermedad (no piel sana), el resultado recomienda consulta médica."""
        from app.vision.analizador import ResultadoImagen, requiere_medico

        decision, clase, confianza, motivo = decidir({"varicela": 0.04, "mpox": 0.93, "sana": 0.03}, "varicela", 0.6)
        self.assertEqual(decision, "NO_COMPATIBLE")
        self.assertIn("valoración médica", motivo)
        resultado = ResultadoImagen(decision, clase, confianza, {}, 0.6, motivo, "x", "v")
        self.assertTrue(requiere_medico(resultado))

    def test_piel_sana_no_requiere_medico(self):
        """Piel sana con confianza alta no activa la recomendación de consulta."""
        from app.vision.analizador import ResultadoImagen, requiere_medico

        decision, clase, confianza, motivo = decidir({"varicela": 0.05, "sana": 0.90, "mpox": 0.05}, "varicela", 0.6)
        resultado = ResultadoImagen(decision, clase, confianza, {}, 0.6, motivo, "x", "v")
        self.assertFalse(requiere_medico(resultado))

    def test_indeterminado(self):
        """Si ninguna clase supera el umbral, el resultado es INDETERMINADO aunque gane varicela."""
        decision, _, confianza, _ = decidir({"varicela": 0.60, "sarampion": 0.30, "sana": 0.10}, "varicela", 0.85)
        self.assertEqual(decision, "INDETERMINADO")
        self.assertAlmostEqual(confianza, 0.60)


if __name__ == "__main__":
    unittest.main()
