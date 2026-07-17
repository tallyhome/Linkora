# Build Windows one-folder + zip de release
# Usage: .\tools\build_windows.ps1
# Optionnel: $env:LINKORA_CERT = "chemin\cert.pfx" ; $env:LINKORA_CERT_PASS = "..."

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Version = (Get-Content "$Root\VERSION" -Raw).Trim()
Write-Host "=== Linkora build v$Version ===" -ForegroundColor Cyan

python -m pip install -q -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

if (Test-Path "$Root\dist\Linkora") {
    Remove-Item -Recurse -Force "$Root\dist\Linkora"
}

python -m PyInstaller --noconfirm linkora.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# Copier VERSION à la racine du dossier dist (au cas où)
Copy-Item "$Root\VERSION" "$Root\dist\Linkora\VERSION" -Force

# Signature optionnelle
$SignScript = Join-Path $PSScriptRoot "sign_windows.ps1"
if ($env:LINKORA_CERT -and (Test-Path $SignScript)) {
    Write-Host "Signature Authenticode..." -ForegroundColor Yellow
    & $SignScript -Target "$Root\dist\Linkora\Linkora.exe"
}

$ZipName = "Linkora-windows-v$Version.zip"
$ZipPath = Join-Path $Root "dist\$ZipName"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Compress-Archive -Path "$Root\dist\Linkora\*" -DestinationPath $ZipPath -Force
Write-Host "OK -> $ZipPath" -ForegroundColor Green
Write-Host "Publiez ce zip comme asset de la release GitHub v$Version"
