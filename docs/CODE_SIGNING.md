# Signature de code Windows (Authenticode)

## Pourquoi ?

Sans signature, Windows SmartScreen affiche souvent :

> « Windows a protégé votre PC »

Un certificat **Authenticode** (OV/EV Code Signing) réduit fortement ces alertes après un peu de réputation de téléchargement.

## Ce que Linkora prévoit

- Script : [`tools/sign_windows.ps1`](../tools/sign_windows.ps1)
- Intégré au build si `LINKORA_CERT` est défini : [`tools/build_windows.ps1`](../tools/build_windows.ps1)

## Obtenir un certificat

1. Acheter un **Code Signing** chez un CA (DigiCert, Sectigo, SSL.com…)
2. Depuis ~2023 : souvent livré sur **token USB** / HSM (pas seulement un `.pfx` fichier)
3. Exporter / utiliser selon les instructions du fournisseur

Coût indicatif : **200–500 € / an** (OV) ; EV plus cher, meilleure confiance initiale.

## Utilisation

```powershell
$env:LINKORA_CERT = "C:\certs\linkora.pfx"
$env:LINKORA_CERT_PASS = "********"
.\tools\build_windows.ps1
```

Ou signature seule :

```powershell
.\tools\sign_windows.ps1 -Target .\dist\Linkora\Linkora.exe
```

Prérequis : **Windows SDK** (`signtool.exe`).

## Sans certificat

Le `.exe` fonctionne quand même. L’utilisateur clique « Informations complémentaires » → « Exécuter quand même ».

## Alternative

- Notarisation / Softener : publier longtemps les mêmes builds signés
- Distribution via Microsoft Store (autre flux, hors scope actuel)
