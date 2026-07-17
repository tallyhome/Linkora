# Changelog — Linkora

Toutes les dates en **2026**. Format inspiré de [Keep a Changelog](https://keepachangelog.com/).

---

## [1.3.0] — 2026-07-17

### Ajouté
- Page **Aide & infos** (bouton `?` circulaire + onglet Aide)
- **Multi-clés API** avec rotation si auth / quota
- **Personnalisation** : couleur d’accent + logo perso
- **CLI** (`python cli.py extract|rename|version`)
- Doc **site de MAJ** dédié (`docs/UPDATE_SITE.md`)

### Corrigé
- MAJ `.exe` : plus d’erreur `Permission denied` sur les DLL — téléchargement puis remplacement **après fermeture** + relance auto

---

## [1.2.0] — 2026-07-17

### Ajouté
- **Profils / presets** (hébergeur, débrideur, parallélisme, template)
- **Notifications** système en fin de résolution / file d’attente
- **Backup** export / import du dossier `data/` (zip)
- **File d’attente** : récupérer + résoudre page par page
- Numéro de **version** dans le pied de page

### Modifié
- Roadmap : phases 0–4 marquées faites

---

## [1.1.0] — 2026-07-17

### Ajouté
- Roadmap / Changelog / TODO (`docs/ROADMAP.md`, `CHANGELOG.md`, `TODO.md`)
- Packaging Windows **one-folder** (`linkora.spec`, `tools/build_windows.ps1`)
- Mode **bureau** (`desktop.py` + pywebview) sans console DOS
- **Installateur Windows** Inno Setup (`tools/linkora.iss`) : raccourcis Bureau / menu Démarrer, désinstallation
- MAJ par **zip** (asset release GitHub ou site `latest.json`)
- Doc + script **signature Authenticode** (`docs/CODE_SIGNING.md`, `tools/sign_windows.ps1`)
- **Détection d’épisodes manquants** (SxxExx)
- **Templates de renommage** (simple / plex / jellyfin / dotted)
- **Filtres** résultats + **sélection** + copie / **envoi JD**
- Chemins compatibles **mode .exe** (`paths.py`)

### Modifié
- Updater : priorise zip Windows, conserve `data/`
- Paramètres : template renommage + URL manifeste MAJ
- README centré Windows (Setup / zip) ; sources CLI pour macOS / Linux
- Fix crash au lancement : icône fenêtre en `.ico` (plus de PNG pour WinForms)

---

## [1.0.0] — 2026-07-17

### Ajouté
- Application web locale **Linkora** (Flask)
- Extraction de liens par hébergeur (filtre libre : rapidgator, etc.)
- **Multi-URL** : une page par ligne → **un bloc de résultats par page**
- Résolution **AllDebrid** / **Real-Debrid** (API officielles)
- Résolution **parallèle** (concurrence réglable) + **retries** si dead
- Boutons globaux + **mêmes actions par bloc** (résoudre, copier, exports, JD…)
- Panneaux **Valides / Morts** par page
- Re-vérifier morts (global ou ligne)
- **Historique** SQLite : 1 entrée par page, panneau **repliable** (fermé par défaut)
- Ouverture historique **inline** sous l’entrée cliquée
- Exports **CSV / HTML / PDF** (+ Voir) et format **JDownloader** (`URL | Nom`)
- Onglet **Renommage** local (scan dossier, aperçu, apply)
- Nommage intelligent Plex / Kodi / Jellyfin (`SxxExx`, films `(année)`, anime)
- Thèmes **Linkora** / **AllDebrid**
- Paramètres : clés API masquées, retries, concurrence
- Logo SVG + PNG (README GitHub)
- Auto-update GitHub (`updater.py`, bandeau UI, option dans Paramètres)
- Repo public : [tallyhome/Linkora](https://github.com/tallyhome/Linkora)
- README, LICENSE (MIT), VERSION

### Sécurité / données
- Clés API et historique dans `data/` (**gitignoré**)

---

## [Unreleased]

### En cours / prévu
- Packaging Windows `.exe` (PyInstaller one-folder)
- MAJ par **zip** (releases + site `latest.json`)
- Signature Authenticode (doc + scripts)
- Détection épisodes manquants
- Templates de renommage configurables
- Filtres / sélection + envoi JDownloader

Voir [docs/ROADMAP.md](docs/ROADMAP.md) et [TODO.md](TODO.md).
