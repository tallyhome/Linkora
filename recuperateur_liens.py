#!/usr/bin/env python3
"""
Récupérateur de liens (CLI) — même logique que l'interface web.

Usage:
    python recuperateur_liens.py <url> [--host rapidgator] [--out liens.txt]
"""

import argparse
import sys

from scraper import scrape


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL de la page à analyser")
    parser.add_argument(
        "--host",
        default="rapidgator",
        help="Nom de l'hébergeur à filtrer (défaut: rapidgator)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Fichier de sortie (optionnel).",
    )
    args = parser.parse_args()

    try:
        links = scrape(args.url, args.host)
    except Exception as exc:
        print(f"Erreur lors de la récupération de la page : {exc}", file=sys.stderr)
        sys.exit(1)

    if not links:
        print(f"Aucun lien '{args.host}' trouvé sur cette page.")
        sys.exit(0)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for link in links:
                f.write(link["url"] + "\n")
        print(f"{len(links)} lien(s) '{args.host}' enregistré(s) dans {args.out}")
    else:
        for link in links:
            label = link["label"].rstrip(" :") if link.get("label") else ""
            prefix = f"{label} : " if label else ""
            print(f"{prefix}{link['url']}")
        print(f"\nTotal : {len(links)} lien(s) '{args.host}'")


if __name__ == "__main__":
    main()
