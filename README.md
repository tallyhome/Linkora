# Linkora

<p align="center">
  <img src="docs/logo.png" alt="Linkora" width="128" height="128">
</p>

<p align="center">
  <strong>Récupération de liens · Débridage · Renommage intelligent</strong><br>
  Outil local pour extraire, résoudre (AllDebrid / Real-Debrid) et renommer vos fichiers pour Plex, Kodi ou Jellyfin.
</p>

<p align="center">
  <a href="https://github.com/tallyhome/Linkora/releases/latest"><img src="https://img.shields.io/github/v/release/tallyhome/Linkora?label=version&color=0f766e" alt="Release"></a>
  <a href="https://github.com/tallyhome/Linkora/releases/latest"><img src="https://img.shields.io/github/downloads/tallyhome/Linkora/total?label=téléchargements&color=3b82f6" alt="Downloads"></a>
  <a href="https://github.com/tallyhome/Linkora"><img src="https://img.shields.io/github/license/tallyhome/Linkora?label=license" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/tallyhome/Linkora/releases/latest/download/Linkora-Setup-v2.1.0.exe"><img src="https://img.shields.io/badge/⬇_Installateur_Windows-Setup.exe-0f766e?style=for-the-badge" alt="Télécharger l'installateur"></a>
  &nbsp;
  <a href="https://github.com/tallyhome/Linkora/releases/latest/download/Linkora-windows-v2.1.0.zip"><img src="https://img.shields.io/badge/⬇_Version_portable-ZIP-3b82f6?style=for-the-badge" alt="Télécharger le portable"></a>
</p>

<p align="center">
  <a href="https://github.com/tallyhome/Linkora/releases/latest">Toutes les versions →</a>
</p>

---

## Télécharger (Windows)

| | Fichier | Pour qui ? |
|---|--------|--------|
| **Installateur** (recommandé) | [**Linkora-Setup-v2.1.0.exe**](https://github.com/tallyhome/Linkora/releases/latest/download/Linkora-Setup-v2.1.0.exe) | Installation classique : menu Démarrer, raccourci Bureau, désinstallation |
| **Portable** | [**Linkora-windows-v2.1.0.zip**](https://github.com/tallyhome/Linkora/releases/latest/download/Linkora-windows-v2.1.0.zip) | Sans install : dézipper → lancer `Linkora.exe` (clé USB, etc.) |

> Les liens ci-dessus pointent vers la **dernière release**. Page complète : [Releases](https://github.com/tallyhome/Linkora/releases/latest).

### Démarrage rapide

1. Lancez **Setup** (ou `Linkora.exe` en portable)
2. **Paramètres** → collez votre clé API AllDebrid ou Real-Debrid → Tester → Enregistrer
3. Collez une ou plusieurs URLs, indiquez l’hébergeur (`rapidgator`, etc.)
4. **Récupérer** → **Résoudre** → exportez / copiez / JDownloader

Prérequis : compte **AllDebrid** ou **Real-Debrid** (clé API).  
Windows peut afficher un avertissement SmartScreen (exe non signé) — voir [docs/CODE_SIGNING.md](docs/CODE_SIGNING.md).

## Fonctionnalités

- **Extraction multi-pages** — collez plusieurs URLs, un bloc de résultats par page
- **Débridage** — AllDebrid / Real-Debrid (résolution parallèle + retries)
- **Historique** — une entrée par page, panneau repliable
- **Exports** — CSV, HTML, PDF, format JDownloader (`URL | Nom suggéré`)
- **Renommage intelligent** — séries `S03E01`, films `Titre (2024)`, anime… pour Plex / Kodi / Jellyfin
- **Multi-hébergeurs** — jusqu’à 6 hébergeurs + fallback si lien mort
- **Auto-update** — vérifie GitHub au démarrage et applique les mises à jour automatiquement

## macOS / Linux (depuis les sources)

Pas d’installateur desktop pour le moment : lancez l’interface web locale.

```bash
git clone https://github.com/tallyhome/Linkora.git
cd Linkora
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Ouvrez [http://127.0.0.1:5000](http://127.0.0.1:5000).  
Python **3.10+** requis.

### CLI (headless)

```bash
python cli.py version
python cli.py extract --url "https://..." --host rapidgator --resolve
python cli.py rename --folder "/chemin/dossier" --dry-run
```

## Documentation

- [Changelog](CHANGELOG.md)
- [TODO](TODO.md)
- [Roadmap](docs/ROADMAP.md)
- [Site de MAJ dédié](docs/UPDATE_SITE.md)
- [Signature Authenticode](docs/CODE_SIGNING.md)

## Auto-update

Au démarrage, Linkora interroge les [releases GitHub](https://github.com/tallyhome/Linkora/releases).

- Si une version plus récente existe → elle est **appliquée automatiquement** (si l’option est active)
- Les données locales (`data/`, clés API, historique) sont **conservées**
- Un bandeau indique qu’un **redémarrage** est recommandé après mise à jour

Vous pouvez aussi vérifier / forcer une MAJ depuis **Paramètres**.  
Désactiver : Paramètres → décocher « Mise à jour automatique ».

## Build Windows (développeurs)

```powershell
winget install JRSoftware.InnoSetup   # une fois, pour l’installateur
.\tools\build_windows.ps1
```

Sortie : `dist/Linkora/`, zip portable, et `Linkora-Setup-vX.Y.Z.exe`.  
Signature (optionnel) : [docs/CODE_SIGNING.md](docs/CODE_SIGNING.md).

## Structure

```
Linkora/
├── desktop.py          # Lanceur fenêtre Windows
├── app.py              # Serveur Flask
├── scraper.py          # Extraction des liens
├── debrid.py           # Clients AllDebrid / Real-Debrid
├── smart_naming.py     # Noms Plex / Kodi / Jellyfin
├── updater.py          # Vérification & MAJ GitHub
├── settings.py         # Réglages locaux
├── storage.py          # Historique SQLite
├── static/             # CSS, JS, logos
├── templates/          # Interface
└── data/               # Local (gitignored) — clés & historique
```

## Sécurité

- Les clés API restent **uniquement sur votre machine** (`data/settings.json`, non versionné)
- Linkora est un outil **local** : ne l’exposez pas sur Internet sans protection

## Licence

Usage personnel. Respectez les conditions d’utilisation d’AllDebrid, Real-Debrid et des sites sources.
