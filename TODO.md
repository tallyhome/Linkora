# TODO — Linkora

Liste de travail active. Cocher au fur et à mesure.  
Roadmap complète : [docs/ROADMAP.md](docs/ROADMAP.md)

---

## Sprint actuel (ordre fixe)

- [x] **1. Packaging `.exe` + MAJ zip**
  - [x] Spec PyInstaller (one-folder)
  - [x] Scripts `build_windows.ps1`
  - [x] Updater mode zip (GitHub assets + URL `latest.json`)
  - [x] Préserver `data/` à la MAJ
  - [x] Installateur Inno Setup (raccourcis + désinstall)
  - [x] Doc install dans README

- [x] **2. Signature du `.exe`**
  - [x] Doc `docs/CODE_SIGNING.md`
  - [x] Script `tools/sign_windows.ps1`
  - [x] Hook dans le build si cert présent
  - [ ] Certificat réel (achat utilisateur)

- [x] **3. Détection d’épisodes manquants**
  - [x] API + bouton UI + copie liste

- [x] **4. Templates de renommage**
  - [x] Presets + réglage Paramètres

- [x] **5. Sélection / filtres + envoi JD**
  - [x] Filtre statut / texte
  - [x] Cases + sélection / copie / fichier JD

---

## Plus tard (Phase 4–5)

- [ ] Profils / presets
- [ ] Notifications Windows
- [ ] Backup / export `data/`
- [ ] File d’attente téléchargement
- [ ] Multi-clés débrideur
- [ ] Mode CLI / headless
- [ ] Source MAJ site dédié (prod)

---

## Fait récemment

- [x] Blocs par page + historique séparé
- [x] Historique repliable
- [x] Renommage intelligent + onglet dossier
- [x] Export JD / noms suggérés
- [x] Auto-update GitHub (source)
- [x] README + logo PNG
- [x] Release GitHub `v1.0.0`
