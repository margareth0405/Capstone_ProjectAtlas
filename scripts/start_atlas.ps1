[CmdletBinding()]
param(
    [switch]$PrepareOnly,
    [switch]$UseSQLite,
    [switch]$OpenBrowser,
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

if ($UseSQLite) {
    $localDatabase = (Join-Path $projectRoot "db.sqlite3").Replace("\", "/")
    $env:DATABASE_URL = "sqlite:///$localDatabase"
    $env:DJANGO_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    Write-Host "Quick-start mode: using the local development database." -ForegroundColor Yellow
    Write-Host "Development email mode: verification links appear in this terminal." -ForegroundColor Yellow
}

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

$browserJob = $null
if ($OpenBrowser) {
    $browserUrl = "http://$Address/"
    $browserJob = Start-Job -ScriptBlock {
        param($TargetUrl)
        for ($attempt = 0; $attempt -lt 30; $attempt += 1) {
            try {
                Invoke-WebRequest -Uri $TargetUrl -UseBasicParsing -TimeoutSec 1 | Out-Null
                Start-Process $TargetUrl
                return
            } catch {
                Start-Sleep -Milliseconds 500
            }
        }
    } -ArgumentList $browserUrl
}

try {
    & $venvPython manage.py runserver $Address
    exit $LASTEXITCODE
} finally {
    if ($browserJob) {
        Stop-Job -Job $browserJob -ErrorAction SilentlyContinue
        Remove-Job -Job $browserJob -Force -ErrorAction SilentlyContinue
    }
}
