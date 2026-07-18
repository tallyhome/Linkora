# TODO — Linkora

Roadmap : [docs/ROADMAP.md](docs/ROADMAP.md)

**Phases 0 → 5 : terminées.**

## Suivi optionnel

- [ ] Certificat Authenticode réel (achat)
- [ ] PIN / mot de passe local au lancement (si demandé)

## Monétisation — dons ou paiement (à décider)

**Recommandation actuelle :** commencer par les **dons** (simple, pas de blocage).  
Le **paiement / licence** reste une option plus tard si la base d’utilisateurs le justifie.

### A) Système de dons (priorité)

- [ ] Bouton **« Soutenir Linkora »** (Aide / À propos / Paramètres)
- [ ] Lien(s) Ko-fi et/ou PayPal (1–2 max)
- [ ] Message court non intrusif (pas de popup bloquante)

**Contrepartie possible d’un don** (léger, sans verrouiller l’app) :

| Contrepartie | Idée |
|---|---|
| Remerciement | Message / badge « Supporter » dans l’UI |
| Cosmétique | Thème ou accent réservé aux supporters |
| Visibilité | Nom (optionnel) dans une page « Merci » / README |
| Accès early | Builds beta / notes de version en avant-première |

> Principe : **rien d’essentiel n’est bloqué**. Un don = merci + petit plus, pas un péage.

### B) Paiement (licence à vie — plus tard)

À envisager seulement si les dons ne suffisent pas / demande claire.

- [ ] Choisir modèle : **à vie** (préférable) plutôt qu’abonnement dès le départ
- [ ] Essai **7–14 jours** (pas 24 h)
- [ ] Page / panneau **admin licence** (génération, révocation)
- [ ] Activation locale (clé) + vérif serveur légère

**Contrepartie possible d’un paiement** (vraie valeur « Pro ») :

| Contrepartie | Idée |
|---|---|
| Multi-hébergeurs avancé | Limite / fallback réservé Pro (ou quota gratuit) |
| Multi-clés / rotation | Réservé Pro |
| Profils illimités | Gratuit limité, Pro illimité |
| Backup cloud / sync | Option Pro (si un jour un compte) |
| Priorité support | Réponse prioritaire (Discord / mail) |
| Builds signés / installs facilitées | Si Authenticode payant un jour |
| CLI / automatisation | Option Pro pour scripts / headless |

> À éviter : bloquer le cœur (extraire → résoudre → exporter) derrière un paywall trop tôt.

### Décision à trancher plus tard

- [ ] **Dons seuls** (recommandé pour commencer)
- [ ] **Freemium** : gratuit + Pro à vie
- [ ] **Licence payante** après essai (dernier recours)

## Stats d’usage / nombre de postes (à décider)

Objectif : savoir **sur combien de postes** Linkora est installé / utilisé — **pas** forcément pour bloquer.

### Option 1 — Licence « soft » (compte / ID, sans payer)

Idée : à la 1ʳᵉ ouverture, générer un **ID anonyme** (ou compte léger) et l’enregistrer côté serveur → panneau admin avec compteur.

- [ ] ID machine / install anonyme (UUID stocké dans `data/`)
- [ ] Ping serveur au démarrage ou à la vérif de MAJ (« install active »)
- [ ] Panneau admin : nombre d’installs, actives 7/30 j, versions
- [ ] Opt-out clair (« Ne pas envoyer de stats »)

> Avantage : tu as un vrai compteur.  
> Inconvénient : il faut un petit serveur + RGPD / transparence.

### Option 2 — Sans licence (souvent suffisant, recommandé pour commencer)

| Source | Ce que ça mesure | Limite |
|---|---|---|
| **Téléchargements GitHub Releases** | Combien ont téléchargé Setup/zip | ≠ posts réellement utilisés ; un même PC peut re-télécharger |
| **Ping de MAJ** (déjà existant) | Combien de postes vérifient une MAJ | Sous-estime si auto-update off / offline |
| **Compteur anonyme au check MAJ** | Installs uniques (UUID) + version | Léger, opt-out ; le plus rentable |
| **Site `latest.json`** (logs serveur) | Hits sur le manifeste | Seulement si MAJ via ton site |

**Recommandation :** ne **pas** mettre une licence juste pour compter.  
Préférer un **compteur anonyme optionnel** branché sur la vérif de MAJ (UUID + version + OS), avec case à cocher et rien de personnel (pas d’IP stockée longtemps, pas de clé API, pas de fichiers).

### Option 3 — Licence + stats (si monétisation Pro un jour)

- [ ] Même panneau admin que la licence : clés actives, postes liés, dernière connexion
- [ ] Utile pour support / anti-abus, **pas** obligatoire pour un simple compteur

### Décision stats

- [ ] **Compteur anonyme via MAJ** (recommandé) — minimal, opt-out
- [ ] Licence soft + admin (si tu veux un vrai dashboard utilisateurs)
- [ ] Se fier aux stats GitHub Downloads seulement (0 code, approximatif)

## Site catalogue multi-apps (gratuit + vente) + stats installs

Idée : un **site central** pour publier toutes tes apps (gratuites ou payantes), avec un système pour savoir **combien de postes** les ont installées / les utilisent encore.

### Comment ça marche concrètement (pas besoin de “qui” nominal)

```
1. L’utilisateur télécharge (GitHub ou ton site)
        ↓
2. Il installe / lance Linkora
        ↓
3. Linkora crée un ID anonyme (UUID) dans data/   ← “cette install”
        ↓
4. Au démarrage ou à la vérif de MAJ, l’app envoie un petit ping HTTPS :
   { app: "linkora", install_id: "uuid…", version: "1.4.0", os: "windows" }
        ↓
5. Ton serveur enregistre / met à jour la ligne
        ↓
6. Ton panneau admin affiche : X installs, Y actives cette semaine, versions…
```

**Tu ne récupères pas le nom de la personne** (GitHub ne le donne pas non plus).  
Tu récupères : *« un poste anonyme tourne avec telle version »*.

| Question | Réponse |
|---|---|
| Faut-il un site ? | **Oui** pour stocker les pings (petit serveur + base). GitHub seul = seulement le nb de downloads d’assets. |
| Où envoyer le ping ? | Une URL HTTPS du type `https://ton-site.com/api/stats/ping` |
| Et les MAJ ? | Déjà : l’app contacte GitHub (ou ton `latest.json`). On peut **ajouter** le ping stats sur le même moment. |
| Opt-out | Case Paramètres « Envoyer des stats anonymes » (cochée ou non selon choix) |

Sans site : tu vois seulement les **compteurs de téléchargement** sur chaque release GitHub (anonymes, pas d’install réelle).

### Site

- [ ] Catalogue apps (fiche : gratuit / payant, téléchargement, changelog)
- [ ] Téléchargements trackés (Setup / zip) → stats “intérêt”
- [ ] Paiement (Stripe etc.) pour les apps payantes
- [ ] (Optionnel) Comptes utilisateurs

### Compteur d’installs (toutes apps)

Chaque app envoie un ping anonyme vers **la même API** du site :

- [ ] `app_id` (ex. `linkora`) + `install_id` (UUID local) + `version` + `os`
- [ ] Ping au 1er lancement et/ou à chaque vérif de MAJ
- [ ] Rien de personnel (pas de clés API, pas de fichiers) + **opt-out** dans chaque app
- [ ] Panneau admin global : installs totales, actives 7/30 j, versions, par app

| Signal | Mesure |
|---|---|
| Downloads site / GitHub | Curiosité / téléchargements |
| Pings installs | Usage réel (postes actifs) |
| Achats | Clients payants |

**Recommandation :** site catalogue + **registre d’installs anonymes** (pas besoin de licence juste pour compter). Licence = plus tard, si une app devient Pro / payante.

### Lien avec Linkora

- [ ] Brancher Linkora sur l’API stats du site (quand le site existe)
- [ ] MAJ via `latest.json` hébergé sur le même site (déjà prévu dans la doc)

## Fait récemment

- [x] Page Aide (`?`) + explications profils / options
- [x] Phase 5 : multi-clés, branding, CLI, doc site MAJ
- [x] Phase 4 : profils, notifs, backup, file d’attente
- [x] Installateur + mode bureau + releases GitHub
- [x] v1.4.0 — durcissement sécurité (CSRF, zip-slip, HTTPS/SHA-256 MAJ, etc.)
