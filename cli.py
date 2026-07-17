"""CLI / mode headless Linkora.

Exemples :
  python cli.py version
  python cli.py extract --url "https://..." --host rapidgator
  python cli.py extract --url "https://..." --host rapidgator --resolve --json
  python cli.py rename --folder "D:\\Downloads\\Serie" --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys

import debrid
import settings as app_settings
import smart_naming
import storage
import updater
from scraper import scrape


def cmd_version(_: argparse.Namespace) -> int:
    print(updater.read_version())
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    storage.init_db()
    app_settings.load_settings()
    urls = [u.strip() for u in (args.url or []) if str(u).strip()]
    if args.file:
        text = open(args.file, encoding="utf-8").read()
        urls.extend(line.strip() for line in text.splitlines() if line.strip())
    urls = list(dict.fromkeys(urls))
    host = (args.host or "").strip()
    if not urls or not host:
        print("Indiquez --url et --host (ou --file).", file=sys.stderr)
        return 2

    batches = []
    for url in urls:
        try:
            links = scrape(url, host)
        except Exception as exc:
            print(f"ERREUR extract {url}: {exc}", file=sys.stderr)
            continue
        batches.append({"source_url": url, "host": host, "links": links})

    if args.resolve:
        name, keys = app_settings.get_provider_keys(args.provider)
        if not keys:
            print(f"Aucune clé API pour {name}.", file=sys.stderr)
            return 3
        for batch in batches:
            resolved = []
            for item in batch["links"]:
                resolved.append(
                    debrid.resolve_item_rotating(
                        name, keys, item, max_retries=app_settings.get_max_retries()
                    )
                )
            batch["links"] = resolved
            batch["provider"] = name

    if args.json:
        print(json.dumps({"batches": batches}, ensure_ascii=False, indent=2))
    else:
        for batch in batches:
            print(f"# {batch['source_url']} ({len(batch['links'])} liens)")
            for link in batch["links"]:
                url = link.get("real_url") or link.get("url") or ""
                label = link.get("resolve_filename") or link.get("label") or ""
                status = link.get("resolve_status") or "-"
                print(f"{status}\t{url}\t{label}")
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    folder = (args.folder or "").strip()
    if not folder:
        print("Indiquez --folder.", file=sys.stderr)
        return 2
    template = args.template or app_settings.get_rename_template()
    items = smart_naming.scan_folder(
        folder, recursive=bool(args.recursive), template_id=template
    )
    if args.json:
        print(json.dumps({"items": items}, ensure_ascii=False, indent=2))
    else:
        for item in items:
            print(f"{item.get('original')} -> {item.get('suggested')}")
    if args.apply and not args.dry_run:
        result = smart_naming.apply_renames(items, dry_run=False)
        print(json.dumps(result, ensure_ascii=False) if args.json else result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="linkora", description="Linkora CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ver = sub.add_parser("version", help="Affiche la version")
    p_ver.set_defaults(func=cmd_version)

    p_ex = sub.add_parser("extract", help="Extrait (et optionnellement résout) des liens")
    p_ex.add_argument("--url", action="append", default=[], help="URL de page (répétable)")
    p_ex.add_argument("--file", help="Fichier texte d'URLs")
    p_ex.add_argument("--host", required=True, help="Filtre hébergeur (rapidgator…)")
    p_ex.add_argument("--resolve", action="store_true", help="Résoudre via débrideur")
    p_ex.add_argument("--provider", default=None, help="alldebrid | realdebrid")
    p_ex.add_argument("--json", action="store_true", help="Sortie JSON")
    p_ex.set_defaults(func=cmd_extract)

    p_rn = sub.add_parser("rename", help="Aperçu / renommage d'un dossier")
    p_rn.add_argument("--folder", required=True)
    p_rn.add_argument("--recursive", action="store_true")
    p_rn.add_argument("--template", default=None)
    p_rn.add_argument("--dry-run", action="store_true")
    p_rn.add_argument("--apply", action="store_true")
    p_rn.add_argument("--json", action="store_true")
    p_rn.set_defaults(func=cmd_rename)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
