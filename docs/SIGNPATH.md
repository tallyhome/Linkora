# SignPath Foundation — Linkora

Signature Authenticode **gratuite** pour l’open source (MIT).  
Site : [https://signpath.org/](https://signpath.org/)

## Prérequis (déjà en place côté repo)

- [x] Licence OSI : MIT (`LICENSE`)
- [x] Dépôt public : `tallyhome/Linkora`
- [x] Politique de signature : [`CODE_SIGNING_POLICY.md`](../CODE_SIGNING_POLICY.md)
- [x] Builds reproductibles documentés + workflow CI (voir ci-dessous)
- [x] Compte SignPath + candidature **acceptée** (à confirmer côté SignPath.io)
- [ ] MFA activé sur le compte GitHub du mainteneur
- [ ] Secrets GitHub `SIGNPATH_API_TOKEN` + `SIGNPATH_ORGANIZATION_ID`
- [ ] Étape CI « Sign with SignPath » **activée** (encore commentée dans le workflow)
## Étapes pour toi (une fois)

1. Active la **2FA / MFA** sur GitHub (`tallyhome`).
2. Crée un compte sur [SignPath.io](https://signpath.io) / candidature [SignPath Foundation](https://signpath.org/).
3. Dans le formulaire, indique notamment :
   - **Project** : Linkora  
   - **Repository** : `https://github.com/tallyhome/Linkora`  
   - **License** : MIT  
   - **Download / releases** : `https://github.com/tallyhome/Linkora/releases`  
   - **Code signing policy** : `https://github.com/tallyhome/Linkora/blob/main/CODE_SIGNING_POLICY.md`  
   - **Description** : outil local Windows d’extraction de liens d’hébergeurs, débridage (APIs AllDebrid/Real-Debrid), bibliothèque médias. Open source, pas de télémétrie cachée.
4. Après acceptation, SignPath te donne :
   - `organization-id`
   - `project-slug` / `signing-policy-slug`
   - un **API token**
5. Dans GitHub → Settings → Secrets and variables → Actions, ajoute :
   - `SIGNPATH_API_TOKEN`
   - `SIGNPATH_ORGANIZATION_ID`
   - (optionnel) variables pour project / policy slugs si différents des défauts du workflow
6. Décommente / active l’étape SignPath dans [`.github/workflows/windows-release.yml`](../.github/workflows/windows-release.yml) selon les instructions SignPath reçues.

## Ce que la CI fait

1. Build Windows (PyInstaller, sans UPX, avec métadonnées Tallyhome)
2. Compile l’installateur Inno Setup
3. Soumet les artefacts à SignPath pour signature
4. Publie les binaires **signés** sur la release GitHub

Tant que SignPath n’est pas branché, le workflow peut publier des builds **non signés** (comme aujourd’hui en local).

## Note éditeur

Sur le certificat SignPath Foundation, l’éditeur affiché est **SignPath Foundation** (pas Tallyhome).  
Les métadonnées PE internes restent **Tallyhome** / Linkora — c’est normal et accepté.
