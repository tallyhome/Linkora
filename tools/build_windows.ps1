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

# Préserver data/ (historique + réglages) entre deux builds
$DataBackup = Join-Path $env:TEMP "linkora-data-backup-$(Get-Random)"
$DistData = "$Root\dist\Linkora\data"
if (Test-Path $DistData) {
    Write-Host "Sauvegarde data/ avant rebuild..." -ForegroundColor Yellow
    Copy-Item -Recurse -Force $DistData $DataBackup
}

if (Test-Path "$Root\dist\Linkora") {
    Remove-Item -Recurse -Force "$Root\dist\Linkora"
}

python -m PyInstaller --noconfirm linkora.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# Copier VERSION à la racine du dossier dist (au cas où)
Copy-Item "$Root\VERSION" "$Root\dist\Linkora\VERSION" -Force

if (Test-Path $DataBackup) {
    New-Item -ItemType Directory -Force -Path $DistData | Out-Null
    Copy-Item -Recurse -Force "$DataBackup\*" $DistData
    Remove-Item -Recurse -Force $DataBackup
    Write-Host "data/ restaure apres build." -ForegroundColor Green
}

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

# Installateur Inno Setup (raccourcis Bureau / menu Démarrer / désinstall)
$IsccCandidates = @(
    "${env:LocalAppData}\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:LocalAppData}\Programs\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$SetupPath = Join-Path $Root "dist\Linkora-Setup-v$Version.exe"

if ($Iscc) {
    Write-Host "Compilation installateur Inno Setup..." -ForegroundColor Cyan
    & $Iscc "/DMyAppVersion=$Version" "$Root\tools\linkora.iss"
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup (ISCC) failed" }
    Write-Host "OK -> $SetupPath" -ForegroundColor Green
} else {
    Write-Host "Inno Setup non trouve : zip portable uniquement." -ForegroundColor Yellow
    Write-Host "Installez via : winget install JRSoftware.InnoSetup" -ForegroundColor Yellow
}

Write-Host "Publiez zip (+ Setup.exe) comme assets de la release GitHub v$Version"
