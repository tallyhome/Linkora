# TODO-2 — Bibliothèque média (cahier des charges)

Fonctionnalité future de Linkora : scanner disques / dossiers, inventaire intelligent,
doublons, diff PC ↔ NAS, optionnellement affiches (TMDB).

**Total : 5 phases.**  
**Versions :** phase 1 → `1.5.0` · 2 → `1.6.0` · 3 → `1.7.0` · 4 → `1.8.0` · 5 → **`2.0.0`**  
(à chaque phase : commit + push + tag + release GitHub)

| Phase | Nom | Objectif | État | Version |
|------:|-----|----------|------|---------|
| **1** | Scan & inventaire | Scanner un dossier, lister films/séries/archives avec identité intelligente | ✅ faite | **1.5.0** |
| **2** | Vue bibliothèque | Arborescence Série → Saison → Épisodes + liste Films | ✅ faite | **1.6.0** |
| **3** | Doublons | Détecter le même film / épisode malgré des noms de fichiers différents | ✅ faite | **1.7.0** |
| **4** | Diff PC ↔ NAS | Comparer deux racines : manquants des deux côtés | ⏳ | 1.8.0 |
| **5** | Affiches (option) | Enrichir avec TMDB (posters) + cache local | ⏳ | **2.0.0** |

---

## Phase 1 — Scan & inventaire

### But
Pouvoir indiquer un répertoire (disque local, dossier, éventuellement chemin UNC NAS) et obtenir une **liste plate** de tous les fichiers média reconnus, avec métadonnées issues du **nommage intelligent** déjà présent dans Linkora.

### Périmètre
- Nouvel onglet UI **Bibliothèque**
- Champ dossier + option récursif + bouton Scanner
- Tableau résultats : type, titre, saison, épisode, année, nom fichier, chemin, **clé d’identité**
- Détection des **archives** `.zip` / `.rar` / `.7z` (ex. saison complète → « pack saison »)
- API `POST /api/library/scan`
- Module dédié (réutilise `smart_naming.suggest_name`)
- Compteurs : N fichiers, N séries (épisodes), N films, N archives, N autres
- Barre de progression / état « Scan… » (UX)

### Hors périmètre (phases suivantes)
- Groupement arborescent, doublons, diff 2 dossiers, affiches

### Critères d’acceptation
- [x] Onglet visible à côté de Renommage / Aide
- [x] Scan d’un dossier existant → liste non vide si médias présents
- [x] Deux fichiers du même épisode (noms différents) partagent la **même clé d’identité**
- [x] Erreur claire si dossier introuvable
- [x] Pas de modification de fichiers (lecture seule)

---

## Phase 2 — Vue bibliothèque structurée

### But
Présenter l’inventaire de façon lisible : **Films** d’un côté, **Séries → Saisons → Épisodes** de l’autre.

### Périmètre
- Groupement par `media_identity` / titre
- Compteurs par série (épisodes trouvés)
- Filtres simples : Films / Séries / Tout + recherche texte
- Export liste (texte / CSV) optionnel

### Critères d’acceptation
- [x] Une série regroupe ses saisons/épisodes
- [x] Les films sont listés séparément
- [x] Recherche filtre la vue

---

## Phase 3 — Doublons

### But
Repérer les fichiers qui représentent le **même** film ou le **même** épisode, même si les noms diffèrent.

Exemple :
- `Defiance.S03.E01 HDTV.www.zone-telechargement.lol.MP4`
- `Defiance S03 S01E001.MP4`  
→ même identité `defiance|s03e01` (après normalisation)

### Périmètre
- Groupes de doublons (clé d’identité partagée, ≥ 2 fichiers)
- Affichage des chemins + tailles + dates si dispo
- Actions soft : copier la liste, ouvrir le dossier (pas de suppression auto en v1)
- Score / avertissement si parsing ambigu

### Critères d’acceptation
- [x] Les 2 exemples Defiance ci-dessus apparaissent dans le **même** groupe
- [x] Un film unique n’apparaît pas en doublon
- [x] Liste exportable

---

## Phase 4 — Diff PC ↔ NAS

### But
Comparer **deux racines** (ex. `D:\Media` et `\\NAS\Media` ou `Z:\`) :
- présent sur le PC, **absent** du NAS
- présent sur le NAS, **absent** du PC
- présent des deux côtés (OK)

### Périmètre
- Deux champs dossier (A = PC, B = NAS)
- Scan des deux + comparaison par **clé d’identité** (pas par nom de fichier brut)
- Trois listes : Manquants sur NAS / Manquants sur PC / Communs
- Export des listes (pour copier / sync manuel)

### Hors périmètre (plus tard éventuel)
- Copie automatique des fichiers vers le NAS
- Sync bidirectionnelle temps réel

### Critères d’acceptation
- [ ] Un épisode seulement sur le PC apparaît dans « Manquant sur NAS »
- [ ] Un épisode seulement sur le NAS apparaît dans « Manquant sur PC »
- [ ] Même épisode, noms différents → considéré comme **présent des deux côtés**

---

## Phase 5 — Affiches TMDB (optionnel)

### But
Enrichir la vue bibliothèque avec posters / infos (esprit Plex / Jellyfin léger).

### Périmètre
- Clé API TMDB dans Paramètres (locale)
- Matching titre (+ année / saison si possible)
- Cache images dans `data/posters/`
- Affichage optionnel (case à cocher) — l’app reste utilisable sans

### Critères d’acceptation
- [ ] Sans clé TMDB : bibliothèque fonctionne normalement
- [ ] Avec clé : posters affichés pour les titres matchés
- [ ] Cache évite de re-télécharger à chaque scan

---

## Principes transverses

1. **Lecture seule** jusqu’à décision explicite (pas de delete/move auto en phases 1–4).
2. **Identité média** = titre normalisé + saison/épisode ou année — base des doublons et du diff.
3. Réutiliser au maximum `smart_naming` (déjà séries, films, anime).
4. Chemins Windows locaux + UNC (`\\NAS\share`) supportés.
5. Gros volumes : feedback UI (chargement) ; cache inventaire possible plus tard.
6. Opt-in pour TMDB (phase 5) — rien d’envoyé sans clé / action user.

---

## Suivi d’implémentation

- [x] Phase 1 — Scan & inventaire
- [x] Phase 2 — Vue bibliothèque
- [x] Phase 3 — Doublons
- [ ] Phase 4 — Diff PC ↔ NAS
- [ ] Phase 5 — Affiches TMDB

### Fichiers phases 1–3
- `todo-2.md` — cahier des charges
- `library_scan.py` — inventaire, archives, arbre, `find_duplicates`
- `smart_naming.py` — `S03.E01` / `Titre S03 S01E001`
- `app.py` — `POST /api/library/scan`
- UI : onglet Bibliothèque (arbre / liste / doublons)