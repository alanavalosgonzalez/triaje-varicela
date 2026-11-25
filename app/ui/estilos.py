"""Paleta clínica y hoja de estilos (QSS) de la aplicación."""

# Paleta: blancos, gris pizarra, azul clínico y verde azulado; ámbar y rojo solo para advertencias médicas.
BLANCO = "#FFFFFF"
FONDO = "#F5F7FA"
BORDE = "#D9E1EA"
PIZARRA = "#334155"
PIZARRA_SUAVE = "#64748B"
AZUL_CLINICO = "#0F4C81"
AZUL_OSCURO = "#0B3A63"
TEAL = "#008080"
TEAL_FONDO = "#E6F4F4"
AMBAR = "#B45309"
AMBAR_FONDO = "#FEF3C7"
ROJO = "#B91C1C"
ROJO_FONDO = "#FEE2E2"

# Colores de texto y fondo para cada dictamen del triaje.
COLORES_DICTAMEN = {
    "NEGATIVO_BAJO_RIESGO": (TEAL, TEAL_FONDO),
    "SOSPECHA_INICIAL": (AMBAR, AMBAR_FONDO),
    "ALTA_PROBABILIDAD": (ROJO, ROJO_FONDO),
    "DERIVAR_MEDICO": (ROJO, ROJO_FONDO),
}

# Textos de cada dictamen para el usuario.
ETIQUETAS_DICTAMEN = {
    "NEGATIVO_BAJO_RIESGO": "Negativo / Bajo riesgo",
    "SOSPECHA_INICIAL": "Sospecha inicial",
    "ALTA_PROBABILIDAD": "Alta probabilidad de varicela",
    "DERIVAR_MEDICO": "Acude con un médico lo antes posible",
}

HOJA_ESTILOS = f"""
QWidget {{
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
    color: {PIZARRA};
    background: {FONDO};
}}
QLabel#titulo {{ font-size: 15pt; font-weight: 600; color: {AZUL_CLINICO}; }}
QLabel#subtitulo {{ font-size: 11pt; font-weight: 600; color: {PIZARRA}; }}
QLabel#nota {{ color: {PIZARRA_SUAVE}; }}
QFrame#encabezado {{ background: {AZUL_CLINICO}; }}
QFrame#encabezado QLabel {{ background: transparent; color: {BLANCO}; }}
QLabel#aviso {{
    background: {AMBAR_FONDO}; color: {AMBAR}; border: 1px solid #F5D08A;
    padding: 6px 12px; font-size: 9pt;
}}
QFrame#tarjeta {{ background: {BLANCO}; border: 1px solid {BORDE}; border-radius: 6px; }}
QFrame#tarjeta QLabel, QFrame#tarjeta QRadioButton, QFrame#tarjeta QCheckBox {{ background: transparent; }}
QListWidget#navegacion {{
    background: {BLANCO}; border: none; border-right: 1px solid {BORDE}; padding-top: 8px; outline: 0;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 14px; height: 14px; border: 1px solid {PIZARRA_SUAVE}; background: {BLANCO};
}}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator {{ border-radius: 3px; }}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {{ border: 1px solid {TEAL}; }}
QRadioButton::indicator:checked {{
    border: 1px solid {TEAL};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                stop:0 {TEAL}, stop:0.55 {TEAL}, stop:0.65 {BLANCO}, stop:1 {BLANCO});
}}
QCheckBox::indicator:checked {{ border: 1px solid {TEAL}; background: {TEAL}; }}
QRadioButton {{ spacing: 6px; padding-right: 8px; }}
QListWidget#navegacion::item {{ padding: 10px 14px; border-left: 3px solid transparent; }}
QListWidget#navegacion::item:selected {{
    background: {TEAL_FONDO}; color: {AZUL_OSCURO}; border-left: 3px solid {TEAL};
}}
QListWidget#navegacion::item:disabled {{ color: #A0AEC0; }}
QPushButton {{
    background: {AZUL_CLINICO}; color: {BLANCO}; border: none; border-radius: 4px; padding: 7px 16px;
}}
QPushButton:hover {{ background: {AZUL_OSCURO}; }}
QPushButton:disabled {{ background: #A0AEC0; }}
QPushButton#secundario {{ background: {BLANCO}; color: {AZUL_CLINICO}; border: 1px solid {AZUL_CLINICO}; }}
QPushButton#secundario:hover {{ background: {TEAL_FONDO}; }}
QLineEdit, QComboBox, QSpinBox, QTextBrowser, QTableWidget {{
    background: {BLANCO}; border: 1px solid {BORDE}; border-radius: 4px; padding: 5px;
}}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {TEAL}; }}
QTabWidget::pane {{ border: 1px solid {BORDE}; background: {BLANCO}; }}
QTabBar::tab {{ background: {FONDO}; padding: 8px 16px; border: 1px solid {BORDE}; border-bottom: none; }}
QTabBar::tab:selected {{ background: {BLANCO}; color: {AZUL_CLINICO}; font-weight: 600; }}
QHeaderView::section {{ background: {FONDO}; border: none; border-bottom: 1px solid {BORDE}; padding: 6px; font-weight: 600; }}
QStatusBar {{ background: {BLANCO}; border-top: 1px solid {BORDE}; color: {PIZARRA_SUAVE}; }}
"""


def caja_resultado(color: str, fondo: str) -> str:
    """Estilo de un recuadro de resultado coloreado según su gravedad."""
    return (f"background: {fondo}; color: {color}; border: 1px solid {color}; border-radius: 6px; "
            "padding: 12px; font-size: 13pt; font-weight: 600;")
