# Politique de signature de code — Linkora

Free code signing provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org/).

## Rôles (équipe)

| Rôle | Qui |
|------|-----|
| **Committers / reviewers** | Mainteneurs du dépôt [tallyhome/Linkora](https://github.com/tallyhome/Linkora) |
| **Approvers (signature)** | Propriétaire(s) du dépôt GitHub (`tallyhome`) — chaque demande SignPath est approuvée manuellement |

L’accès GitHub et SignPath doit utiliser l’**authentification multifacteur (MFA)**.

## Ce qui est signé

- `Linkora.exe` (build PyInstaller Windows)
- `Linkora-Setup-vX.Y.Z.exe` (installateur Inno Setup), quand produit en CI

Les builds signés proviennent uniquement du dépôt source ci-dessus, via le workflow GitHub Actions documenté dans `.github/workflows/`.

## Confidentialité

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

Les appels réseau (extraction de pages, APIs AllDebrid / Real-Debrid / TMDB, vérification de mises à jour GitHub) sont initiés uniquement par l’utilisateur ou ses réglages explicites. Les clés API restent en local dans `data/`.

## Build local (non signé SignPath)

Voir [`docs/CODE_SIGNING.md`](docs/CODE_SIGNING.md) et `tools/build_windows.ps1`.
