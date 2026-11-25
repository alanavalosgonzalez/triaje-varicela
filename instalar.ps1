# ==========================================================================
# Instalador de Triaje Varicela para Windows 10/11.
# Uso, desde la carpeta del proyecto:
#     powershell -ExecutionPolicy Bypass -File instalar.ps1
# Revisa e instala lo que falte (Python, SWI-Prolog, R), crea el entorno virtual,
# instala las librerías, descarga el modelo de imagen, prueba todo y crea un acceso directo.
# Se puede ejecutar varias veces: lo que ya está instalado se omite.
# Opción: -SinAccesoDirecto evita crear el acceso directo en el escritorio.
# ==========================================================================

param([switch]$SinAccesoDirecto)

# 'Continue': los programas externos (pip, python, winget) escriben avisos en el canal de errores aunque terminen bien;
# por eso cada paso comprueba su código de salida ($LASTEXITCODE) en lugar de detenerse con cualquier aviso.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$URL_MODELO = 'https://github.com/alanavalosgonzalez/triaje-varicela/releases/latest/download/varicela.onnx'

# Funciones para mostrar el avance con colores.
function Paso($texto)  { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Listo($texto) { Write-Host "    OK: $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "    AVISO: $texto" -ForegroundColor Yellow }

# Recarga el PATH para que se vean los programas recién instalados sin cerrar la terminal.
function Actualizar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

# Instala un programa con winget (el instalador de paquetes de Windows) si está disponible.
function Instalar-ConWinget($id, $nombre) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "No se encontró winget. Instala $nombre manualmente y vuelve a ejecutar este script."
    }
    Write-Host "    Instalando $nombre con winget (puede pedir permisos de administrador)..."
    winget install --id $id -e
    if ($LASTEXITCODE -ne 0) { throw "winget no pudo instalar $nombre (código $LASTEXITCODE)." }
    Actualizar-Path
}

# Devuelve el comando de un Python 3.11 o superior que funcione, o $null si no hay.
function Buscar-Python {
    foreach ($candidato in @(@('py', '-3'), @('python'))) {
        $exe = $candidato[0]; $argumentos = @($candidato | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $ok = & $exe @argumentos -c "import sys; print(sys.version_info >= (3, 11))" 2>$null
            if ($ok -eq 'True') { return ,$candidato }
        } catch { }
    }
    return $null
}

# 1. Python.
Paso 'Buscando Python 3.11 o superior'
$python = Buscar-Python
if (-not $python) {
    Instalar-ConWinget 'Python.Python.3.13' 'Python 3.13'
    $python = Buscar-Python
    if (-not $python) { throw 'Python se instaló pero no se encuentra. Cierra esta terminal, abre una nueva y vuelve a ejecutar el script.' }
}
Listo ((& $python[0] @($python | Select-Object -Skip 1) --version) -join '')

# 2. SWI-Prolog (motor lógico del cuestionario).
Paso 'Buscando SWI-Prolog'
if ((Get-Command swipl -ErrorAction SilentlyContinue) -or (Test-Path 'C:\Program Files\swipl\bin\swipl.exe')) {
    Listo 'SWI-Prolog ya está instalado.'
} else {
    Instalar-ConWinget 'SWI-Prolog.SWI-Prolog' 'SWI-Prolog'
    Listo 'SWI-Prolog instalado.'
}

# 3. R (motor estadístico del cuestionario).
Paso 'Buscando R'
if ((Get-Command Rscript -ErrorAction SilentlyContinue) -or (Get-ChildItem 'C:\Program Files\R\R-*\bin\Rscript.exe' -ErrorAction SilentlyContinue)) {
    Listo 'R ya está instalado.'
} else {
    Instalar-ConWinget 'RProject.R' 'R'
    Listo 'R instalado.'
}

# 4. Entorno virtual y librerías de Python.
Paso 'Preparando el entorno virtual de Python (.venv)'
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & $python[0] @($python | Select-Object -Skip 1) -m venv .venv
    Listo 'Entorno virtual creado.'
} else {
    Listo 'El entorno virtual ya existe.'
}
Paso 'Instalando librerías (puede tardar varios minutos la primera vez)'
# PySide6 incluye archivos con rutas muy largas; Windows limita las rutas a 260 caracteres salvo que se active
# la opción LongPathsEnabled. Con la carpeta del proyecto en una ruta larga, la instalación falla.
$rutasLargas = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -ErrorAction SilentlyContinue).LongPathsEnabled -eq 1
if (-not $rutasLargas -and $PSScriptRoot.Length -gt 60) {
    Aviso "La carpeta del proyecto tiene una ruta larga ($($PSScriptRoot.Length) caracteres) y Windows no tiene activadas las rutas largas."
    Aviso 'Si la instalación falla, mueve el proyecto a una ruta corta, por ejemplo C:\Users\<tu usuario>\Documents\triaje-varicela.'
}
& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw ('pip no pudo instalar las librerías. Causas habituales: sin conexión a internet, o la carpeta del proyecto ' +
           'está en una ruta demasiado larga (muévela a una ruta corta como Documents\triaje-varicela).')
}
Listo 'Librerías instaladas.'

# 5. Archivo de configuración.
Paso 'Configuración (.env)'
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env' -ErrorAction Stop
    Listo 'Se creó .env. La clave de Gemini se configura desde la app (botón "Configurar asistente").'
} else {
    Listo '.env ya existe; no se modificó.'
}

# 6. Modelo de visión (no se guarda en git: se descarga del Release de GitHub).
Paso 'Modelo de análisis de imagen'
if (Test-Path 'models\varicela.onnx') {
    Listo 'El modelo ya está en models\varicela.onnx.'
} else {
    try {
        Invoke-WebRequest $URL_MODELO -OutFile 'models\varicela.onnx' -UseBasicParsing -ErrorAction Stop
        Listo ('Modelo descargado ({0:N0} MB).' -f ((Get-Item 'models\varicela.onnx').Length / 1MB))
    } catch {
        Remove-Item 'models\varicela.onnx' -ErrorAction SilentlyContinue
        Aviso "No se pudo descargar el modelo. Descárgalo de la sección Releases de GitHub y colócalo en models\. El resto de la app funciona sin él."
    }
}

# 7. Comprobación con las pruebas automáticas.
Paso 'Comprobando la instalación con las pruebas automáticas'
$env:PYTHONIOENCODING = 'utf-8'
$salida = & .\.venv\Scripts\python.exe -m unittest -q 2>&1 | ForEach-Object { "$_" } | Where-Object { $_.Trim() -and $_ -notmatch 'RemoteException' }
$codigo = $LASTEXITCODE
$salida | Select-Object -Last 3 | ForEach-Object { Write-Host "    $_" }
if ($codigo -eq 0) { Listo 'Todas las pruebas pasaron.' } else { Aviso 'Alguna prueba falló; revisa el mensaje de arriba.' }

# 8. Acceso directo en el escritorio que abre la app sin ventana de consola.
if (-not $SinAccesoDirecto) {
    Paso 'Creando acceso directo en el escritorio'
    $acceso = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Triaje Varicela.lnk'
    $shell = New-Object -ComObject WScript.Shell
    $atajo = $shell.CreateShortcut($acceso)
    $atajo.TargetPath = Join-Path $PSScriptRoot 'iniciar.cmd'
    $atajo.WorkingDirectory = $PSScriptRoot
    $atajo.WindowStyle = 7  # Ventana minimizada: la consola del lanzador no estorba.
    $atajo.Save()
    Listo "Acceso directo creado: $acceso"
}

Write-Host "`nInstalación terminada. Abre la app con el acceso directo 'Triaje Varicela' o con iniciar.cmd." -ForegroundColor Green
