# Linkora

<p align="center">
  <img src="static/img/logo.svg" alt="Linkora" width="96" height="96">
</p>

<p align="center">
  <strong>Récupération de liens · Débridage · Renommage intelligent</strong><br>
  Outil local pour extraire, résoudre (AllDebrid / Real-Debrid) et renommer vos fichiers pour Plex, Kodi ou Jellyfin.
</p>

<p align="center">
  <a href="https://github.com/tallyhome/Linkora/releases"><img src="https://img.shields.io/github/v/release/tallyhome/Linkora?label=version" alt="Release"></a>
  <a href="https://github.com/tallyhome/Linkora"><img src="https://img.shields.io/github/license/tallyhome/Linkora?label=license" alt="License"></a>
</p>

---

## Fonctionnalités

- **Extraction multi-pages** — collez plusieurs URLs, un bloc de résultats par page
- **Débridage** — AllDebrid / Real-Debrid (résolution parallèle + retries)
- **Historique** — une entrée par page, panneau repliable
- **Exports** — CSV, HTML, PDF, format JDownloader (`URL | Nom suggéré`)
- **Renommage intelligent** — séries `S03E01`, films `Titre (2024)`, anime… pour Plex / Kodi / Jellyfin
- **Auto-update** — vérifie GitHub au démarrage et applique les mises à jour automatiquement

## Prérequis

- Python **3.10+**
- Compte **AllDebrid** ou **Real-Debrid** (clé API)

## Installation

```bash
git clone https://github.com/tallyhome/Linkora.git
cd Linkora
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Ouvrez [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Premiers pas

1. **Paramètres** → collez votre clé API AllDebrid ou Real-Debrid → Tester → Enregistrer  
2. Collez une (ou plusieurs) URL(s) de page, indiquez l’hébergeur (`rapidgator`, etc.)  
3. **Récupérer** → **Résoudre** (globalement ou par bloc de page)  
4. Exportez / copiez les liens, ou utilisez l’onglet **Renommage** sur un dossier local  

## Auto-update

Au démarrage, Linkora interroge les [releases / tags GitHub](https://github.com/tallyhome/Linkora/releases).

- Si une version plus récente existe → elle est **appliquée automatiquement** (si l’option est active)
- Les données locales (`data/`, clés API, historique) sont **conservées**
- Un bandeau indique qu’un **redémarrage** est recommandé après mise à jour

Vous pouvez aussi vérifier / forcer une MAJ depuis **Paramètres**.

Désactiver l’auto-update : Paramètres → décocher « Mise à jour automatique ».

## Structure

```
Linkora/
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
