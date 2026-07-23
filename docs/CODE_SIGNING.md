# Signature de code Windows (Authenticode)

## Pourquoi ?

Sans signature, Windows SmartScreen et certains antivirus signalent plus facilement les `.exe` peu connus (surtout PyInstaller).

Un certificat **Authenticode** de confiance (CA ou SignPath Foundation) réduit fortement ces alertes.

## Ce que Linkora fait déjà (sans certificat)

- Build **Release** (pas de console debug)
- **Pas d’UPX** / packers (`linkora.spec`)
- **Métadonnées PE** : éditeur **Tallyhome**, description, version (`tools/gen_version_info.py`)
- Installateur **Inno Setup** avec VersionInfo éditeur Tallyhome
- Staging MAJ sous `{install}/updates/` (pas `%TEMP%`)
- Distribution HTTPS via [GitHub Releases](https://github.com/tallyhome/Linkora/releases)

## Voie recommandée (gratuit) : SignPath Foundation

Voir la procédure complète : [`docs/SIGNPATH.md`](SIGNPATH.md)  
Politique publique (obligatoire SignPath) : [`CODE_SIGNING_POLICY.md`](../CODE_SIGNING_POLICY.md)

Après acceptation, la CI signe les artefacts via SignPath (pas de token USB chez toi).

## Certificat PFX local (payant / perso)

Script : [`tools/sign_windows.ps1`](../tools/sign_windows.ps1)  
Branché dans [`tools/build_windows.ps1`](../tools/build_windows.ps1) si `LINKORA_CERT` est défini.

```powershell
$env:LINKORA_CERT = "C:\certs\linkora.pfx"
$env:LINKORA_CERT_PASS = "********"
.\tools\build_windows.ps1
```

Prérequis : **Windows SDK** (`signtool.exe`).

> Un certificat **auto-signé** ne rassure ni Windows ni VirusTotal : inutile pour la confiance publique.

## Faux positifs VirusTotal

1. Rebuild **sans UPX** + métadonnées, resoumettre zip **et** `Linkora.exe`
2. Signaler les moteurs concernés (ex. Bkav, SentinelOne) avec le hash SHA-256 + lien GitHub
3. Une fois SignPath actif, republier une release signée

Liens utiles :

- [Microsoft (Defender) submission](https://www.microsoft.com/en-us/wdsi/filesubmission)
- [VirusTotal](https://www.virustotal.com/) → reanalyse après nouvelle build
