# Changelog — Linkora

Toutes les dates en **2026**. Format inspiré de [Keep a Changelog](https://keepachangelog.com/).

---

## [1.3.9] — 2026-07-18

### Modifié
- Thème **Pro** repensé : nuit indigo lumineuse (fini le noir plat) — fond **aurora animé**,
  cartes en **verre** avec liseré dégradé et survol flottant, onglets pastilles à halo,
  bouton principal dégradé avec reflet, titres en dégradé. Respecte `prefers-reduced-motion`.

---

## [1.3.8] — 2026-07-18

### Ajouté
- Nouveau **3e thème « Pro »** (sombre graphite, dense et intuitif) : palette indigo/vert,
  en-tête compact fixe, onglets segmentés, panneaux à liseré d’accent, tableaux serrés (URL en mono),
  vert = valide / rouge = mort. Thèmes Linkora (défaut) et Ambre conservés.

---

## [1.3.7] — 2026-07-18

### Ajouté
- Multi-hébergeurs : jusqu’à **6** hébergeurs
- Après résolution : **fallback** si le 1er hébergeur est mort → miroir valide
- Bloc principal = **1 lien / épisode** ; miroirs/doublons dans un bloc séparé
- Copies / JD utilisent les liens principaux uniquement

---

## [1.3.6] — 2026-07-18

### Ajouté
- Récupération : option **multi-hébergeurs** (jusqu’à 3) via « + Ajouter un hébergeur »
- Badge hébergeur détecté sur chaque lien ; profils & file d’attente compatibles

---

## [1.3.5] — 2026-07-17

### Corrigé
- MAJ Windows : la mise à jour s’installe vraiment et **relance** Linkora
  (le helper tournait depuis l’exe installé → fichiers verrouillés → copie ratée en silence)

---

## [1.3.4] — 2026-07-17

### Corrigé
- Lancement après install : plus de popup d’erreur Windows (crash `System.Drawing.Icon` via pywebview)
- Renommage : cases à cocher déplacées à droite, juste après **Statut**

---

## [1.3.3] — 2026-07-17

### Corrigé
- MAJ : **plus aucune fenêtre DOS** — helper intégré à `Linkora.exe` (pas de .bat / PowerShell / VBS)
- Nettoyage des anciens scripts `linkora-apply-*` au démarrage

---

## [1.3.2] — 2026-07-17

### Corrigé
- MAJ `.exe` : plus de fenêtre DOS bloquée — helper silencieux (VBS/PowerShell caché)
- Popup de **progression** (téléchargement / extraction / redémarrage) puis relance auto

---

## [1.3.1] — 2026-07-17

### Ajouté
- Renommage : **cases à cocher** + case « tout » en en-tête (défaut : tout coché)

### Modifié
- Thème « AllDebrid » renommé **Ambre** (évite la confusion avec le débrideur)
- Logo Linkora **non personnalisable** (option retirée des paramètres)

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
- Installateur : si Linkora est déjà installé → choix **Mettre à jour** / **Réparer** / **Désinstaller**

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
