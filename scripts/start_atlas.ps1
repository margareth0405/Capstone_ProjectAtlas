[CmdletBinding()]
param(
    [switch]$PrepareOnly,
    [string]$Address = "127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvDirectory = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvDirectory "Scripts\python.exe"
$activateScript = Join-Path $venvDirectory "Scripts\Activate.ps1"
$requirementsFile = Join-Path $projectRoot "requirements.txt"
$requirementsMarker = Join-Path $venvDirectory ".atlas-requirements.sha256"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating the ATLAS virtual environment..." -ForegroundColor Cyan

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Install Python 3.12 or newer and make it available as 'python'."
    }

    & $pythonCommand.Source -m venv $venvDirectory
    if ($LASTEXITCODE -ne 0) {
        throw "Python could not create the virtual environment."
    }
}

$currentRequirementsHash = (Get-FileHash -LiteralPath $requirementsFile -Algorithm SHA256).Hash
$installedRequirementsHash = if (Test-Path -LiteralPath $requirementsMarker) {
    (Get-Content -LiteralPath $requirementsMarker -Raw).Trim()
} else {
    ""
}

if ($currentRequirementsHash -ne $installedRequirementsHash) {
    Write-Host "Installing ATLAS dependencies..." -ForegroundColor Cyan
    & $venvPython -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed. Check the pip output above."
    }

    Set-Content -LiteralPath $requirementsMarker -Value $currentRequirementsHash -NoNewline
}

# Activate the environment for this terminal task. Calling its Python executable
# directly above also guarantees setup uses the same environment.
. $activateScript
$env:PYTHONUNBUFFERED = "1"

Write-Host "Using $(& $venvPython --version) from $venvDirectory" -ForegroundColor Green

if ($PrepareOnly) {
    Write-Host "ATLAS environment is ready." -ForegroundColor Green
    exit 0
}

Write-Host "Checking the Django configuration..." -ForegroundColor Cyan
& $venvPython manage.py check
if ($LASTEXITCODE -ne 0) {
    throw "Django's configuration check failed."
}

Write-Host "Starting ATLAS at http://$Address/" -ForegroundColor Green
Write-Host "Applying database migrations..." -ForegroundColor Cyan
& $venvPython manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    throw "Database migration failed."
}

& $venvPython manage.py runserver $Address
exit $LASTEXITCODE
