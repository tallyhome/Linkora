# Signature Authenticode (optionnel — certificat payant requis pour SmartScreen)
# Usage:
#   $env:LINKORA_CERT = "C:\certs\linkora.pfx"
#   $env:LINKORA_CERT_PASS = "motdepasse"
#   .\tools\sign_windows.ps1 -Target .\dist\Linkora\Linkora.exe
#
# Prérequis: Windows SDK (signtool.exe) dans le PATH

param(
    [Parameter(Mandatory = $true)]
    [string]$Target
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Target)) {
    throw "Fichier introuvable: $Target"
}

$Cert = $env:LINKORA_CERT
$Pass = $env:LINKORA_CERT_PASS

if (-not $Cert -or -not (Test-Path $Cert)) {
    Write-Host "Pas de certificat (LINKORA_CERT). Signature ignoree." -ForegroundColor Yellow
    Write-Host "Voir docs/CODE_SIGNING.md"
    exit 0
}

$Signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $Signtool) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe",
        "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe"
    )
    $found = Get-Item $candidates -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $found) {
        throw "signtool.exe introuvable. Installez le Windows SDK."
    }
    $SigntoolPath = $found.FullName
} else {
    $SigntoolPath = $Signtool.Source
}

Write-Host "Sign with $SigntoolPath"
& $SigntoolPath sign /f $Cert /p $Pass /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $Target
if ($LASTEXITCODE -ne 0) { throw "Signature echouee" }

& $SigntoolPath verify /pa $Target
Write-Host "Signe OK: $Target" -ForegroundColor Green
