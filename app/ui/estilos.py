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
QLabel#titulo {{ font-size: 16pt; font-weight: 600; color: {AZUL_CLINICO}; }}
QLabel#subtitulo {{ font-size: 11.5pt; font-weight: 600; color: {AZUL_OSCURO}; }}
QLabel#nota {{ color: {PIZARRA_SUAVE}; }}
QFrame#encabezado {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {AZUL_CLINICO}, stop:0.65 #136A8F, stop:1 {TEAL});
}}
QFrame#encabezado QLabel {{ background: transparent; color: {BLANCO}; }}
QFrame#aviso {{ background: {AMBAR_FONDO}; border: none; border-bottom: 1px solid #F5D08A; }}
QFrame#aviso QLabel {{ background: transparent; color: {AMBAR}; font-size: 9pt; }}
QFrame#tarjeta {{ background: {BLANCO}; border: 1px solid #E3EAF2; border-radius: 14px; }}
QFrame#tarjeta QLabel, QFrame#tarjeta QRadioButton, QFrame#tarjeta QCheckBox {{ background: transparent; }}
QFrame#lateral {{ background: {BLANCO}; border-right: 1px solid {BORDE}; }}
QFrame#lateral QWidget {{ background: transparent; }}
QListWidget#navegacion {{ background: transparent; border: none; padding: 10px 8px 0 8px; outline: 0; }}
QListWidget#navegacion::item {{ padding: 10px 12px; margin: 2px 0; border-radius: 10px; }}
QListWidget#navegacion::item:hover {{ background: #EEF5FB; }}
QListWidget#navegacion::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {TEAL_FONDO}, stop:1 #E8F1FA);
    color: {AZUL_OSCURO}; font-weight: 600;
}}
QListWidget#navegacion::item:disabled {{ color: #A0AEC0; }}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid {PIZARRA_SUAVE}; background: {BLANCO};
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator:hover, QCheckBox::indicator:hover {{ border: 1px solid {TEAL}; background: {TEAL_FONDO}; }}
QRadioButton::indicator:checked {{
    border: 1px solid {TEAL};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                stop:0 {TEAL}, stop:0.55 {TEAL}, stop:0.65 {BLANCO}, stop:1 {BLANCO});
}}
QCheckBox::indicator:checked {{ border: 1px solid {TEAL}; background: {TEAL}; }}
QRadioButton {{ spacing: 6px; padding: 3px 10px 3px 4px; border-radius: 8px; }}
QRadioButton:hover {{ background: {TEAL_FONDO}; }}
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1663A3, stop:1 {AZUL_CLINICO});
    color: {BLANCO}; border: none; border-radius: 10px; padding: 9px 20px; font-weight: 600;
}}
QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1B76BF, stop:1 #136A8F); }}
QPushButton:pressed {{ background: {AZUL_OSCURO}; padding-top: 10px; padding-bottom: 8px; }}
QPushButton:disabled {{ background: #B8C4D2; }}
QPushButton#encabezado {{
    background: rgba(255, 255, 255, 0.14); color: {BLANCO}; border: 1px solid rgba(255, 255, 255, 0.6);
    padding: 6px 14px; border-radius: 14px;
}}
QPushButton#encabezado:hover {{ background: rgba(255, 255, 255, 0.26); }}
QPushButton#secundario {{ background: {BLANCO}; color: {AZUL_CLINICO}; border: 1px solid #B9CDE3; }}
QPushButton#secundario:hover {{ background: {TEAL_FONDO}; border: 1px solid {TEAL}; }}
QLineEdit, QComboBox, QSpinBox, QTextBrowser, QTableWidget {{
    background: {BLANCO}; border: 1px solid {BORDE}; border-radius: 10px; padding: 7px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {TEAL}; padding: 6px; }}
QProgressBar {{ background: #E6EEF6; border: none; border-radius: 4px; max-height: 8px; }}
QProgressBar::chunk {{
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {TEAL}, stop:1 #3DB4C9);
}}
QTabWidget::pane {{ border: 1px solid #E3EAF2; background: {BLANCO}; border-radius: 12px; top: -1px; }}
QTabBar::tab {{
    background: transparent; padding: 9px 18px; margin-right: 4px; border: none; border-bottom: 3px solid transparent;
    color: {PIZARRA_SUAVE};
}}
QTabBar::tab:hover {{ color: {AZUL_CLINICO}; }}
QTabBar::tab:selected {{ color: {AZUL_CLINICO}; font-weight: 600; border-bottom: 3px solid {TEAL}; }}
QHeaderView::section {{ background: #F0F5FA; border: none; border-bottom: 1px solid {BORDE}; padding: 7px; font-weight: 600; }}
QStatusBar {{ background: {BLANCO}; border-top: 1px solid {BORDE}; color: {PIZARRA_SUAVE}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C9D6E3; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #A9BCD0; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QFrame#pregunta {{ background: {BLANCO}; border: 1px solid #E3EAF2; border-radius: 14px; }}
QFrame#pregunta:hover {{ border: 1px solid #B9D7E0; background: #FBFDFF; }}
QFrame#pregunta[estado="respondida"] {{ border: 1px solid #8FD0CE; background: #F5FBFB; }}
QFrame#pregunta[estado="alarma"] {{ border: 2px solid {ROJO}; background: {ROJO_FONDO}; }}
QFrame#pregunta[estado="faltante"] {{ border: 2px solid #E3A13B; background: #FFFBF1; }}
QFrame#pregunta QLabel {{ background: transparent; }}
QLabel#pregunta_titulo {{ font-size: 10.5pt; font-weight: 600; color: {AZUL_OSCURO}; }}
QLabel#pregunta_ayuda {{ color: {PIZARRA_SUAVE}; font-size: 9pt; }}
QPushButton#opcion {{
    background: {BLANCO}; color: {PIZARRA}; border: 1px solid #C9D6E3; border-radius: 16px;
    padding: 7px 14px; font-weight: 600;
}}
QPushButton#opcion:hover {{ border: 1px solid {TEAL}; background: {TEAL_FONDO}; }}
QPushButton#opcion[tipo="si"]:checked {{ background: {TEAL}; color: {BLANCO}; border: 1px solid {TEAL}; }}
QPushButton#opcion[tipo="si_alarma"]:checked {{ background: {ROJO}; color: {BLANCO}; border: 1px solid {ROJO}; }}
QPushButton#opcion[tipo="no"]:checked {{ background: {AZUL_CLINICO}; color: {BLANCO}; border: 1px solid {AZUL_CLINICO}; }}
QPushButton#opcion[tipo="nose"]:checked {{ background: #E3A13B; color: {BLANCO}; border: 1px solid #E3A13B; }}
QFrame#aviso_alarma {{ background: {ROJO_FONDO}; border: 1px solid {ROJO}; border-radius: 12px; }}
QFrame#aviso_alarma QLabel {{ background: transparent; color: {ROJO}; font-weight: 600; }}
QLabel#contador {{ color: {TEAL}; font-weight: 600; }}
QLabel#globo {{
    background: {BLANCO}; color: {AZUL_OSCURO}; border: 1px solid #CFE3EE; border-radius: 14px; padding: 10px 12px;
}}
"""


def caja_resultado(color: str, fondo: str) -> str:
    """Estilo de un recuadro de resultado coloreado según su gravedad."""
    return (f"background: {fondo}; color: {color}; border: 1px solid {color}; border-radius: 14px; "
            "padding: 14px; font-size: 14pt; font-weight: 600;")
