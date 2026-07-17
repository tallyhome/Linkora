# Linkora — Roadmap

Vision produit en **phases**. Chaque phase s’appuie sur la précédente.

---

## Phase 0 — Fondations ✅ (fait)

Socle actuel stable.

- Extraction multi-pages (blocs par URL)
- Débridage AllDebrid / Real-Debrid (parallèle + retries)
- Historique repliable (1 entrée / page)
- Exports CSV / HTML / PDF / JDownloader
- Renommage intelligent (séries, films, anime)
- Thèmes Linkora / AllDebrid
- Auto-update GitHub (source)
- Repo public + README + logo

---

## Phase 1 — Distribution & mises à jour ✅ (implémenté)

Rendre Linkora utilisable en **double-clic** et maintenable sans Python.

| # | Fonctionnalité | Description |
|---|---|---|
| 1.1 | **Packaging `.exe` (one-folder)** | Build PyInstaller : dossier `Linkora/` + `Linkora.exe` |
| 1.2 | **MAJ par zip** | Téléchargement asset release / URL perso, préserve `data/` |
| 1.3 | **Source MAJ duale** | GitHub **ou** site (`latest.json` + zip) |
| 1.4 | **Signature du `.exe`** | Scripts + doc (certificat à fournir) |

---

## Phase 2 — Qualité des packs & renommage ✅ (implémenté)

| # | Fonctionnalité | Description |
|---|---|---|
| 2.1 | **Détection d’épisodes manquants** | Après résolution : “il manque S03E07, E12…” |
| 2.2 | **Templates de renommage** | simple / plex / jellyfin / dotted |
| 2.3 | **Aperçu avant/après renommage** | Onglet Renommage + noms suggérés |

---

## Phase 3 — Sélection, filtres & téléchargement ✅ (implémenté)

| # | Fonctionnalité | Description |
|---|---|---|
| 3.1 | **Filtres résultats** | Valides / morts / recherche texte |
| 3.2 | **Sélection multiple** | Cases à cocher + actions groupées |
| 3.3 | **Envoi JDownloader** | Copie JD + fichier `.txt` |

---

## Phase 4 — Productivité (priorité moyenne)

| # | Fonctionnalité | Description |
|---|---|---|
| 4.1 | **Profils / presets** | “Rapidgator + AllDebrid + 6 parallèles” |
| 4.2 | **Notifications Windows** | Fin de résolution (gros lots) |
| 4.3 | **Backup / export `data/`** | Changer de PC sans perdre clés + historique |
| 4.4 | **File d’attente téléchargement** | Enchaîner résolution → téléchargement |

---

## Phase 5 — Avancé (nice to have)

| # | Fonctionnalité | Description |
|---|---|---|
| 5.1 | Multi-clés / rotation débrideur | Limites API |
| 5.2 | Thème / logo perso | Branding |
| 5.3 | Mode headless / CLI | Automatisation |
| 5.4 | Site de MAJ dédié | `latest.json` hébergé hors GitHub |

---

## Ordre d’exécution immédiat

1. `.exe` + MAJ zip  
2. Signature du `.exe`  
3. Détection d’épisodes manquants  
4. Templates de renommage  
5. Sélection / filtres + envoi JD  

Voir aussi : [CHANGELOG.md](../CHANGELOG.md) · [TODO.md](../TODO.md)
