# Triaje Varicela

Aplicación de escritorio para el pre-diagnóstico, triaje y orientación sobre la varicela. Combina un motor lógico en **Prolog**, análisis estadístico en **R**, un asistente conversacional con IA, visión artificial y un mapa de centros de salud cercanos.

> ⚠️ **Aviso médico:** esta herramienta es solo de apoyo orientativo. **No sustituye una consulta médica presencial.** Ante dificultad para respirar, fiebre alta persistente, lesiones infectadas o cualquier duda, acude de inmediato a un profesional de la salud.

## Estado del proyecto

- [x] Fase 1 — Arquitectura, base de datos y estructura
- [x] Fase 2 — Prolog (reglas) y R (estadística)
- [x] Fase 3 — Núcleo Python y base de datos
- [x] Fase 4 — Asistente IA y visión artificial ([método y resultados del modelo](docs/VISION.md))
- [x] Fase 5 — Interfaz gráfica y mapa

## Instalación rápida (Windows 10/11)

1. Descarga el proyecto (botón verde **Code → Download ZIP** o `git clone`) y colócalo en una ruta corta, por ejemplo `Documentos\triaje-varicela`.
2. Abre PowerShell en esa carpeta y ejecuta:

   ```powershell
   powershell -ExecutionPolicy Bypass -File instalar.ps1
   ```

   El script instala lo que falte (Python, SWI-Prolog y R con `winget`), prepara las librerías, descarga el modelo de imagen,
   comprueba todo con las pruebas automáticas y crea el acceso directo **Triaje Varicela** en el escritorio.
3. Abre la app con ese acceso directo (o con `iniciar.cmd`).
4. Para usar el asistente virtual, pulsa **Configurar asistente** y pega tu clave gratuita de
   [Google AI Studio](https://aistudio.google.com/apikey). Cada persona usa su propia clave; nunca la compartas.

La barra inferior de la app indica con ✓ / ✗ qué componentes están listos.

## Instalación manual

Requisitos: Python 3.11+, [SWI-Prolog 9+](https://www.swi-prolog.org/download/stable) y [R 4+](https://cran.r-project.org/).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### Modelo de visión

El archivo del modelo (`varicela.onnx`, 28 MB) no se guarda en git. Descárgalo de la sección
[Releases](https://github.com/alanavalosgonzalez/triaje-varicela/releases) y colócalo en la carpeta `models/`
(junto a `models/varicela.json`, que sí está en el repositorio). Sin él, la app funciona igual, excepto el análisis de imagen.

## Pruebas

```powershell
& "C:\Program Files\swipl\bin\swipl.exe" -g run_tests -t halt prolog/test_varicela.pl
& "C:\Program Files\R\R-4.6.2\bin\Rscript.exe" r_scripts/test_probabilidad.R
```

(Si `swipl` y `Rscript` están en tu PATH, basta con escribir su nombre.)

```powershell
python -m unittest -v
```

## Ejecutar la aplicación

```powershell
python -m app
```

## Demo en consola

```powershell
python -m app.demo_triaje
python -m app.demo_chat      # Requiere GEMINI_API_KEY en .env.
```

## Estructura

```
triaje-varicela/
├── app/                 Código Python de la aplicación.
│   ├── core/            Orquestador y puentes con Prolog y R.
│   ├── db/              Acceso a la base de datos SQLite.
│   ├── ai/              Asistente conversacional (LLM).
│   ├── vision/          Análisis de imágenes de la erupción.
│   ├── geo/             Geolocalización y búsqueda de centros.
│   └── ui/              Ventanas y componentes PySide6.
├── prolog/              Base de conocimientos y reglas (.pl).
├── r_scripts/           Scripts estadísticos (.R).
├── database/            Esquema SQL.
├── models/              Pesos del modelo de visión (no se suben a Git).
├── data/                Base de datos local (no se sube a Git).
├── tests/               Pruebas automatizadas.
└── docs/                Documentación de arquitectura.
```

Más detalle en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).
