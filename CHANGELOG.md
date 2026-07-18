# Changelog — Linkora

Toutes les dates en **2026**. Format inspiré de [Keep a Changelog](https://keepachangelog.com/).

---

## [2.2.3] — 2026-07-18

### Ajouté
- Historique biblio : bouton **Relancer** (rescan / re-diff, accéléré par le cache)

### Amélioré
- Formulaire **Diff PC ↔ NAS** : pleine largeur, champs de chemins plus longs
- **Reboots** : séries séparées par année (`Les 4400 (2004)` ≠ `(2021)`) dans l’arbre, les doublons et le diff

### Corrigé (inclus depuis 2.2.2 local)
- Bascules Vue arbre / Liste plate / Doublons
- Affichage clair des groupes de doublons

---

## [2.2.2] — 2026-07-18

### Corrigé — Vues bibliothèque
- **Vue arbre / liste plate / doublons** : le CSS `display:flex` masquait l’attribut `hidden` → les 3 vues se superposaient
- **Doublons** : groupes repliables avec titre + SxxExx + taille + chemin de chaque copie

---

## [2.2.1] — 2026-07-18

### Amélioré — Perf scan NAS + TMDB
- Scan : **parcours parallèle** des dossiers (masque la latence SMB, pas le débit 1 Gb/s)
- TMDB : vrai **parallélisme** (le verrou ne bloque plus le réseau), sessions HTTP réutilisées
- Affiches affichées **au fur et à mesure** pendant le chargement
- Images CDN sans throttle API

---

## [2.2.0] — 2026-07-18

### Amélioré — Affiches TMDB + arbre + perf
- **Corriger une affiche** : bouton TMDB sur chaque jaquette → recherche et choix manuel
- Arbre **fermé par défaut** + boutons Tout ouvrir / Tout fermer
- Affiches TMDB plus rapides : cache d’abord, fetch **parallèle**, images plus légères
- Scan NAS : indexation puis **analyse parallèle** des nouveaux fichiers

---

## [2.1.0] — 2026-07-18

### Amélioré — Bibliothèque plus intelligente + cache
- Parseur : `01 - Collection 1909` → **épisode** (plus un faux film 1909)
- Regroupement séries tolérant aux fautes (`L'Agence Tout Risques` / `Tous Risquess`)
- Distinction des reboot via **année** (ex. Les 4400 2004 vs 2021)
- Titre de série / saison / année lus dans les **dossiers parents**
- **Cache incrémental** des scans (rescans NAS beaucoup plus rapides)
- Parcours `scandir` (plus efficace que `rglob` sur gros volumes)
- **Historique bibliothèque** (scans + diffs) rouvrable comme l’historique Récupération

---

## [2.0.0] — 2026-07-18

### Ajouté — Bibliothèque phase 5 : affiches TMDB
- Clé API TMDB dans Paramètres (+ test de connexion)
- Matching titre / type / année, cache local `data/posters/`
- Affiches optionnelles dans la vue arbre (séries + films)
- Bouton **TMDB** + case **Affiches** — l’app fonctionne sans clé

---

## [1.10.0] — 2026-07-18

### Ajouté — Accès NAS (login / mot de passe)
- Paramètres → **Accès NAS** : hôte, partage, utilisateur, mot de passe
- Connexion Windows (UNC) automatique avant scan / diff bibliothèque
- Bouton **Tester la connexion**
- Scan bibliothèque **asynchrone** avec barre de progression (évite les faux « erreur réseau » sur scans longs)

---

## [1.9.0] — 2026-07-18

### Ajouté — Diff PC ↔ NAS multi-dossiers
- Plusieurs chemins **PC** et **NAS** (ex. 2 HDD NAS avec chacun un dossier Séries)
- Agrégation : tout ce qui est présent / manquant d’un côté ou de l’autre
- **Barre de progression** pendant le scan (plus de doute si ça tourne ou si c’est figé)
- API async : `POST /api/library/diff` + `GET /api/library/diff/progress`

---

## [1.8.1] — 2026-07-18

### Corrigé
- **UI figée** : erreur de syntaxe JS (guillemet manquant) qui empêchait le chargement
  de `app.js` — plus aucun bouton ne répondait.

---

## [1.8.0] — 2026-07-18

### Ajouté — Bibliothèque (phase 4 / 5) + Changelog in-app
- **Diff PC ↔ NAS** : compare deux dossiers par identité (manquants NAS / PC / communs)
- Copie des listes de diff
- **Changelog** dans Aide (charge `CHANGELOG.md` via `/api/changelog`)

---

## [1.7.0] — 2026-07-18

### Ajouté — Bibliothèque (phase 3 / 5)
- Vue **Doublons** : groupes par identité intelligente (≥ 2 fichiers)
- Affiche taille + chemin ; badge « À vérifier » si parsing ambigu
- Copie de la liste des doublons
- Ex. `Defiance.S03.E01…` et `Defiance S03 S01E001` → même groupe

---

## [1.6.0] — 2026-07-18

### Ajouté — Bibliothèque (phase 2 / 5)
- **Vue arbre** : Séries → Saisons → Épisodes, Films et Archives séparés
- Filtres Tout / Séries / Films / Archives + **recherche** par titre
- Bascule vue arbre / liste plate
- Onglets qui passent à la ligne (4e onglet Bibliothèque plus visible)
- Cache-bust static `?v=version` pour forcer le rechargement UI

---

## [1.5.0] — 2026-07-18

### Ajouté — Bibliothèque (phase 1 / 5)
- Nouvel onglet **Bibliothèque** : scan d’un dossier / disque (lecture seule)
- Inventaire films / séries / anime avec **clé d’identité** intelligente
  (ex. `Defiance.S03.E01…` et `Defiance S03 S01E001` → `defiance|s03e01`)
- Détection des **archives** `.zip` / `.rar` / `.7z` (packs saison signalés)
- API `POST /api/library/scan` · cahier des charges : `todo-2.md`
- Parseur : mieux gère `S03.E01` et les noms type `Titre S03 S01E001`

---

## [1.4.0] — 2026-07-18

### Sécurité
- **Updater** : protection anti « zip slip » (toute archive contenant des chemins
  sortant du dossier d'installation est rejetée).
- **Updater** : manifeste de MAJ perso en **HTTPS obligatoire** + vérification
  **SHA-256** optionnelle du zip (`"sha256"` dans `latest.json`).
- **API locale** : garde anti-CSRF / DNS-rebinding — seules les requêtes venant de
  `127.0.0.1` / `localhost` sont acceptées ; une origine web tierce est refusée (403).
- **Extraction** : seuls les liens `http(s)://` sont retenus (bloque `javascript:`, `data:`…).
- **SSL** : le contournement des erreurs SSL des pages est désormais **désactivé par
  défaut** — nouvelle option « Ignorer les erreurs SSL » dans Paramètres si besoin.
- **Debug** : le débogueur Flask n'est plus actif par défaut en mode source
  (`LINKORA_DEBUG=1` pour développer).
- **Aide / Paramètres** : avertissement — le backup contient les clés API en clair.

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
