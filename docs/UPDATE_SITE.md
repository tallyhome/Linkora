# Site de mise à jour dédié

Linkora peut se mettre à jour **sans GitHub** via une URL de manifeste.

## Fichier `latest.json`

Exemple : [latest.example.json](latest.example.json)

```json
{
  "version": "1.3.0",
  "url": "https://votresite.com/linkora/Linkora-windows-v1.3.0.zip",
  "notes": "Correctifs et nouveautés…",
  "sha256": "empreinte-sha256-du-zip-en-hexadécimal (optionnel mais recommandé)"
}
```

1. Hébergez le zip Windows (même contenu que la release GitHub).
2. Hébergez `latest.json` en HTTPS — **obligatoire** : les URL `http://` sont refusées
   (manifeste et zip), pour empêcher une interception réseau.
3. (Recommandé) Renseignez `sha256` : Linkora vérifie l’empreinte du zip téléchargé
   et annule la MAJ si elle ne correspond pas.
   Pour calculer l’empreinte : `Get-FileHash .\Linkora-windows-vX.Y.Z.zip -Algorithm SHA256`
4. Dans Linkora → **Paramètres** → **URL manifeste MAJ** → collez l’URL du JSON.
5. Laissez l’auto-update activé, ou cliquez **Vérifier les mises à jour**.

Si l’URL manifeste est vide, Linkora utilise les releases GitHub par défaut.
