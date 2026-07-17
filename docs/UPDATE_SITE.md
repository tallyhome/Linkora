# Site de mise à jour dédié

Linkora peut se mettre à jour **sans GitHub** via une URL de manifeste.

## Fichier `latest.json`

Exemple : [latest.example.json](latest.example.json)

```json
{
  "version": "1.3.0",
  "url": "https://votresite.com/linkora/Linkora-windows-v1.3.0.zip",
  "notes": "Correctifs et nouveautés…"
}
```

1. Hébergez le zip Windows (même contenu que la release GitHub).
2. Hébergez `latest.json` en HTTPS.
3. Dans Linkora → **Paramètres** → **URL manifeste MAJ** → collez l’URL du JSON.
4. Laissez l’auto-update activé, ou cliquez **Vérifier les mises à jour**.

Si l’URL manifeste est vide, Linkora utilise les releases GitHub par défaut.
