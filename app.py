"""Application web — Récupérateur de liens."""

from __future__ import annotations

import csv
import io
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, send_file
from fpdf import FPDF
from fpdf.enums import XPos, YPos

import debrid
import episode_gaps
import settings as app_settings
import smart_naming
import storage
import updater
from paths import DATA_DIR, resource_root
from scraper import scrape

app = Flask(
    __name__,
    template_folder=str(resource_root() / "templates"),
    static_folder=str(resource_root() / "static"),
)
storage.init_db()
app_settings.load_settings()

_BACKUP_ALLOW = frozenset({"settings.json", "history.db"})

# Hôtes locaux légitimes (le serveur n'écoute que sur 127.0.0.1)
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "[::1]"})

# Progression Diff PC/NAS (scan multi-dossiers)
_diff_lock = threading.Lock()
_diff_apply_lock = threading.Lock()
_diff_state: dict = {
    "busy": False,
    "done": False,
    "error": "",
    "percent": 0,
    "phase": "",
    "message": "",
    "result": None,
}

# Progression scan bibliothèque
_scan_lock = threading.Lock()
_scan_apply_lock = threading.Lock()
_scan_state: dict = {
    "busy": False,
    "done": False,
    "error": "",
    "percent": 0,
    "phase": "",
    "message": "",
    "result": None,
}

# Progression enrichissement TMDB
_enrich_lock = threading.Lock()
_enrich_apply_lock = threading.Lock()
_enrich_state: dict = {
    "busy": False,
    "done": False,
    "error": "",
    "percent": 0,
    "phase": "",
    "message": "",
    "result": None,
}


def _diff_get_state() -> dict:
    with _diff_lock:
        return {
            "busy": _diff_state["busy"],
            "done": _diff_state["done"],
            "error": _diff_state["error"],
            "percent": _diff_state["percent"],
            "phase": _diff_state["phase"],
            "message": _diff_state["message"],
        }


def _diff_set_state(**kwargs) -> None:
    with _diff_lock:
        _diff_state.update(kwargs)


def _scan_get_state() -> dict:
    with _scan_lock:
        return {
            "busy": _scan_state["busy"],
            "done": _scan_state["done"],
            "error": _scan_state["error"],
            "percent": _scan_state["percent"],
            "phase": _scan_state["phase"],
            "message": _scan_state["message"],
        }


def _scan_set_state(**kwargs) -> None:
    with _scan_lock:
        _scan_state.update(kwargs)


def _enrich_get_state() -> dict:
    with _enrich_lock:
        return {
            "busy": _enrich_state["busy"],
            "done": _enrich_state["done"],
            "error": _enrich_state["error"],
            "percent": _enrich_state["percent"],
            "phase": _enrich_state["phase"],
            "message": _enrich_state["message"],
        }


def _enrich_set_state(**kwargs) -> None:
    with _enrich_lock:
        _enrich_state.update(kwargs)


@app.before_request
def _local_only_guard():
    """
    Anti CSRF / DNS-rebinding : l'API n'est servie qu'en local.
    - Host doit être 127.0.0.1 / localhost (bloque le DNS rebinding).
    - Sur les requêtes qui modifient l'état, un en-tête Origin étranger
      (site web tiers ouvert dans le navigateur) est refusé.
    """
    host = (request.host or "").rsplit(":", 1)[0].lower()
    if host not in _LOCAL_HOSTS:
        return jsonify({"error": "Hôte non autorisé."}), 403
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origin = request.headers.get("Origin") or ""
        if origin:
            o_host = (urlparse(origin).hostname or "").lower()
            if o_host not in ("127.0.0.1", "localhost", "::1"):
                return jsonify({"error": "Origine non autorisée."}), 403
    return None


def _page_title(url: str) -> str:
    try:
        path = urlparse(url).query
        if "id=" in path:
            raw = path.split("id=", 1)[1].split("&", 1)[0]
            return raw.replace("-", " ").strip()
    except Exception:
        pass
    return urlparse(url).netloc or "Extraction"


def _parse_hosts(data: dict) -> list[str]:
    """Accepte hosts[] et/ou host (rétrocompat). Max 3, dédupliqués."""
    candidates: list[str] = []
    raw_hosts = data.get("hosts")
    if isinstance(raw_hosts, list):
        candidates.extend(str(h) for h in raw_hosts)
    elif isinstance(raw_hosts, str) and raw_hosts.strip():
        for part in raw_hosts.replace(";", ",").replace("|", ",").split(","):
            if part.strip():
                candidates.append(part.strip())
    single = (data.get("host") or "").strip()
    if single:
        if " + " in single and not candidates:
            candidates.extend(p.strip() for p in single.split(" + ") if p.strip())
        elif not any(c.strip().lower() == single.lower() for c in candidates):
            candidates.insert(0, single)

    out: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        value = str(item or "").strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
        if len(out) >= 6:
            break
    return out


@app.get("/api/changelog")
def api_changelog():
    """Changelog embarqué (Aide) — lecture seule."""
    from paths import ROOT, resource_root

    text = ""
    for base in (resource_root(), ROOT):
        path = base / "CHANGELOG.md"
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
                break
            except OSError:
                continue
    if not text:
        return jsonify({"error": "Changelog introuvable.", "markdown": "", "html": ""})
    return jsonify(
        {
            "version": updater.read_version(),
            "markdown": text,
            "html": _changelog_to_html(text),
        }
    )


def _format_inline_md(text: str) -> str:
    """Échappe le texte et applique **gras** / `code` simples."""
    import re

    parts: list[str] = []
    for tok in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text or ""):
        if tok.startswith("**") and tok.endswith("**") and len(tok) >= 4:
            parts.append(f"<strong>{_esc(tok[2:-2])}</strong>")
        elif tok.startswith("`") and tok.endswith("`") and len(tok) >= 2:
            parts.append(f"<code>{_esc(tok[1:-1])}</code>")
        else:
            parts.append(_esc(tok))
    return "".join(parts)


def _changelog_to_html(md: str) -> str:
    """Conversion légère Markdown → HTML (titres, listes, hr)."""
    lines = (md or "").splitlines()
    out: list[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            close_list()
            continue
        if line.strip() == "---":
            close_list()
            out.append("<hr>")
            continue
        if line.startswith("## "):
            close_list()
            out.append(f"<h3>{_esc(line[3:].strip())}</h3>")
            continue
        if line.startswith("### "):
            close_list()
            out.append(f"<h4>{_esc(line[4:].strip())}</h4>")
            continue
        if line.startswith("# "):
            close_list()
            out.append(f"<h2>{_esc(line[2:].strip())}</h2>")
            continue
        if line.lstrip().startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_format_inline_md(line.lstrip()[2:].strip())}</li>")
            continue
        close_list()
        out.append(f"<p>{_format_inline_md(line)}</p>")
    close_list()
    return "\n".join(out)


@app.get("/api/version")
def api_version():
    return jsonify(
        {
            "version": updater.read_version(),
            "update": updater.get_state(),
        }
    )


@app.get("/api/update/status")
def api_update_status():
    return jsonify(updater.get_state())


@app.post("/api/update/check")
def api_update_check():
    data = request.get_json(silent=True) or {}
    manifest = (data.get("manifest_url") or "").strip() or app_settings.get_update_manifest_url()
    return jsonify(updater.check_for_update(manifest or None))


@app.post("/api/update/apply")
def api_update_apply():
    data = request.get_json(silent=True) or {}
    tag = (data.get("tag") or "").strip() or None
    manifest = (data.get("manifest_url") or "").strip() or app_settings.get_update_manifest_url()
    # Toujours en arrière-plan pour laisser l’UI afficher la progression
    result = updater.apply_update(tag, manifest_url=manifest or None, background=True)
    return jsonify(result)


@app.get("/api/update/progress")
def api_update_progress():
    return jsonify(updater.get_state())


@app.post("/api/episodes/missing")
def api_episodes_missing():
    data = request.get_json(silent=True) or {}
    links = data.get("links") or []
    season = data.get("season")
    expected = data.get("expected_count")
    try:
        season_i = int(season) if season is not None and str(season) != "" else None
    except (TypeError, ValueError):
        season_i = None
    try:
        expected_i = int(expected) if expected is not None and str(expected) != "" else None
    except (TypeError, ValueError):
        expected_i = None
    return jsonify(
        episode_gaps.find_missing(links, season=season_i, expected_count=expected_i)
    )


@app.get("/api/rename/templates")
def api_rename_templates():
    return jsonify({"templates": smart_naming.list_templates()})


@app.get("/")
def index():
    return render_template("index.html", app_version=updater.read_version())


@app.get("/api/settings")
def api_settings_get():
    return jsonify(app_settings.public_settings())


@app.put("/api/settings")
def api_settings_put():
    data = request.get_json(silent=True) or {}
    try:
        app_settings.update_settings(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(app_settings.public_settings())


@app.post("/api/settings/profiles/apply")
def api_settings_profile_apply():
    data = request.get_json(silent=True) or {}
    profile_id = str(data.get("id") or "").strip()
    if not profile_id:
        return jsonify({"error": "Profil manquant."}), 400
    prof = app_settings.apply_profile(profile_id)
    if not prof:
        return jsonify({"error": "Profil introuvable."}), 404
    return jsonify({"profile": prof, "settings": app_settings.public_settings()})


@app.get("/api/data/backup")
def api_data_backup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in sorted(_BACKUP_ALLOW):
            path = DATA_DIR / name
            if path.is_file():
                zf.write(path, arcname=name)
    buf.seek(0)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"linkora-data-{stamp}.zip",
        mimetype="application/zip",
    )


@app.post("/api/data/restore")
def api_data_restore():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Fichier zip manquant."}), 400
    try:
        raw = uploaded.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            restored = []
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            for name in names:
                base = Path(name).name
                if base not in _BACKUP_ALLOW:
                    continue
                target = DATA_DIR / base
                with zf.open(name) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                restored.append(base)
            if not restored:
                return jsonify({"error": "Aucune donnée Linkora dans ce zip."}), 400
        # Recharger réglages / DB après restauration
        app_settings.load_settings()
        storage.init_db()
        return jsonify(
            {
                "ok": True,
                "restored": restored,
                "message": f"Restauré : {', '.join(restored)}",
                "settings": app_settings.public_settings(),
            }
        )
    except zipfile.BadZipFile:
        return jsonify({"error": "Fichier zip invalide."}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/settings/test")
def api_settings_test():
    data = request.get_json(silent=True) or {}
    provider = (data.get("provider") or "").strip()
    api_key = (data.get("api_key") or "").strip()

    if not provider:
        provider, stored = app_settings.get_provider_key()
        api_key = api_key or stored
    elif not api_key:
        _, api_key = app_settings.get_provider_key(provider)

    if not api_key:
        return jsonify({"error": "Aucune clé API configurée pour ce fournisseur."}), 400

    try:
        result = debrid.test_provider(provider, api_key)
        return jsonify(result)
    except debrid.DebridError as exc:
        return jsonify({"ok": False, "error": str(exc), "code": exc.code}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.post("/api/extract")
def api_extract():
    data = request.get_json(silent=True) or {}
    hosts = _parse_hosts(data)
    host_label = " + ".join(hosts)

    # Une URL ou une liste / texte multi-lignes
    urls_raw = data.get("urls")
    if isinstance(urls_raw, list):
        urls = [str(u).strip() for u in urls_raw if str(u).strip()]
    elif isinstance(urls_raw, str) and urls_raw.strip():
        urls = [
            u.strip()
            for u in urls_raw.replace(",", "\n").splitlines()
            if u.strip()
        ]
    else:
        single = (data.get("url") or "").strip()
        urls = [single] if single else []

    # Déduplique en gardant l'ordre
    seen = set()
    urls = [u for u in urls if not (u in seen or seen.add(u))]

    if not urls:
        return jsonify({"error": "Veuillez indiquer au moins une URL de page."}), 400
    if not hosts:
        return jsonify({"error": "Veuillez indiquer au moins un hébergeur."}), 400
    for u in urls:
        if not u.startswith(("http://", "https://")):
            return jsonify(
                {"error": f"URL invalide (http/https requis) : {u[:80]}"}
            ), 400

    batches: list[dict] = []
    errors: list[str] = []

    for u in urls:
        title = _page_title(u)
        try:
            links = scrape(u, hosts)
            enriched = [
                smart_naming.enrich_link(
                    {**link, "page_url": u, "page_title": title}
                )
                for link in links
            ]
            batches.append(
                {
                    "source_url": u,
                    "title": title,
                    "host": host_label,
                    "hosts": hosts,
                    "count": len(enriched),
                    "links": enriched,
                }
            )
        except Exception as exc:
            errors.append(f"{u} → {exc}")
            batches.append(
                {
                    "source_url": u,
                    "title": title,
                    "host": host_label,
                    "hosts": hosts,
                    "count": 0,
                    "links": [],
                    "error": str(exc),
                }
            )

    all_links = [link for batch in batches for link in batch["links"]]
    if not all_links and errors:
        return jsonify({"error": "Aucune page récupérée : " + " | ".join(errors)}), 502

    return jsonify(
        {
            "host": host_label,
            "hosts": hosts,
            "batches": batches,
            "source_url": batches[0]["source_url"] if batches else "",
            "source_urls": [b["source_url"] for b in batches],
            "title": batches[0]["title"]
            if len(batches) == 1
            else f"{len(batches)} pages",
            "count": len(all_links),
            "links": all_links,
            "errors": errors,
        }
    )


@app.post("/api/resolve")
def api_resolve():
    data = request.get_json(silent=True) or {}
    links = data.get("links") or []
    provider = (data.get("provider") or "").strip() or None

    if not isinstance(links, list) or not links:
        return jsonify({"error": "Aucun lien à résoudre."}), 400

    name, keys = app_settings.get_provider_keys(provider)
    if not keys:
        return jsonify(
            {
                "error": (
                    f"Aucune clé API pour « {name} ». "
                    "Configurez-la dans Paramètres."
                )
            }
        ), 400

    try:
        resolved = [
            debrid.resolve_item_rotating(name, keys, item, max_retries=5)
            for item in links
        ]
    except debrid.DebridError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Résolution impossible : {exc}"}), 502

    ok = sum(1 for l in resolved if l.get("resolve_status") == "ok")
    return jsonify(
        {
            "provider": name,
            "count": len(resolved),
            "ok": ok,
            "failed": len(resolved) - ok,
            "links": resolved,
        }
    )


@app.post("/api/resolve/one")
def api_resolve_one():
    """Résout un seul lien — retries inclus pour les faux dead AllDebrid."""
    data = request.get_json(silent=True) or {}
    link = data.get("link") or {}
    provider = (data.get("provider") or "").strip() or None
    try:
        max_retries = int(data.get("max_retries") or app_settings.get_max_retries())
    except (TypeError, ValueError):
        max_retries = app_settings.get_max_retries()
    max_retries = max(1, min(max_retries, 8))

    if not isinstance(link, dict) or not (link.get("url") or "").strip():
        return jsonify({"error": "Lien invalide."}), 400

    name, keys = app_settings.get_provider_keys(provider)
    if not keys:
        return jsonify(
            {
                "error": (
                    f"Aucune clé API pour « {name} ». "
                    "Configurez-la dans Paramètres."
                ),
                "provider": name,
            }
        ), 400

    try:
        resolved = debrid.resolve_item_rotating(
            name, keys, link, max_retries=max_retries
        )
    except debrid.DebridError as exc:
        return jsonify({"error": str(exc), "provider": name}), 400
    except Exception as exc:
        return jsonify({"error": f"Résolution impossible : {exc}", "provider": name}), 502

    return jsonify({"provider": name, "link": resolved})


@app.get("/api/history")
def api_history():
    return jsonify(storage.list_extractions())


@app.get("/api/history/<int:extraction_id>")
def api_history_item(extraction_id: int):
    item = storage.get_extraction(extraction_id)
    if not item:
        return jsonify({"error": "Extraction introuvable."}), 404
    item["links"] = [smart_naming.enrich_link(l) for l in item.get("links") or []]
    return jsonify(item)


@app.post("/api/history")
def api_history_save():
    data = request.get_json(silent=True) or {}
    url = (data.get("source_url") or data.get("url") or "").strip()
    host = (data.get("host") or "").strip()
    links = data.get("links") or []
    title = (data.get("title") or "").strip() or _page_title(url)
    upsert = bool(data.get("upsert", True))

    if not url or not host:
        return jsonify({"error": "Données incomplètes."}), 400
    if not isinstance(links, list) or not links:
        return jsonify({"error": "Aucun lien à sauvegarder."}), 400

    if upsert:
        saved = storage.upsert_extraction(url, host, links, title)
    else:
        saved = storage.save_extraction(url, host, links, title)
    return jsonify(saved), 201


@app.put("/api/history/<int:extraction_id>")
def api_history_update(extraction_id: int):
    data = request.get_json(silent=True) or {}
    links = data.get("links") or []
    title = data.get("title")
    if not isinstance(links, list) or not links:
        return jsonify({"error": "Aucun lien à mettre à jour."}), 400
    updated = storage.update_extraction(extraction_id, links, title=title)
    if not updated:
        return jsonify({"error": "Extraction introuvable."}), 404
    return jsonify(updated)


@app.delete("/api/history/<int:extraction_id>")
def api_history_delete(extraction_id: int):
    if not storage.delete_extraction(extraction_id):
        return jsonify({"error": "Extraction introuvable."}), 404
    return jsonify({"ok": True})


@app.get("/api/library/history")
def api_library_history():
    return jsonify(storage.list_library_history())


@app.get("/api/library/history/<int:item_id>")
def api_library_history_item(item_id: int):
    light = str(request.args.get("light") or "").lower() in ("1", "true", "yes")
    item = storage.get_library_history_item(item_id, include_result=not light)
    if not item:
        return jsonify({"error": "Entrée introuvable."}), 404
    return jsonify(item)


@app.delete("/api/library/history/<int:item_id>")
def api_library_history_delete(item_id: int):
    if not storage.delete_library_history(item_id):
        return jsonify({"error": "Entrée introuvable."}), 404
    return jsonify({"ok": True})


def _payload_from_request() -> dict:
    data = request.get_json(silent=True) or {}
    theme = (data.get("theme") or "").strip()
    if theme not in ("linkora", "lienlab", "alldebrid"):
        theme = app_settings.load_settings().get("theme") or "linkora"
    if theme == "lienlab":
        theme = "linkora"
    return {
        "source_url": (data.get("source_url") or data.get("url") or "").strip(),
        "host": (data.get("host") or "").strip(),
        "title": (data.get("title") or "Extraction").strip(),
        "links": data.get("links") or [],
        "view": bool(data.get("view")),
        "theme": theme,
    }


def _export_url(link: dict) -> str:
    return link.get("real_url") or link.get("url_display") or link.get("url") or ""


def _send_export(mem: io.BytesIO, mimetype: str, filename: str, view: bool):
    mem.seek(0)
    return send_file(
        mem,
        mimetype=mimetype,
        as_attachment=not view,
        download_name=filename,
    )


def _display_name(link: dict) -> str:
    return link.get("clean_name") or link.get("resolve_filename") or link.get("label") or ""


def _build_csv(payload: dict) -> bytes:
    links = payload["links"]
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(
        [
            "Label",
            "Nom suggéré",
            "Type média",
            "Taille",
            "URL source",
            "URL réelle / débrid",
            "Hébergeur",
            "Statut",
            "Source page",
        ]
    )
    for link in links:
        writer.writerow(
            [
                link.get("resolve_filename") or link.get("label", ""),
                _display_name(link),
                link.get("media_type") or "",
                link.get("resolve_size") or link.get("size", ""),
                link.get("url", ""),
                _export_url(link),
                link.get("resolve_host") or payload["host"],
                link.get("resolve_status") or "",
                payload["source_url"],
            ]
        )
    return buf.getvalue().encode("utf-8-sig")


def _build_jdownloader(payload: dict) -> bytes:
    """Format URL + nom suggéré (import manuel / scripts)."""
    lines: list[str] = []
    for link in payload["links"]:
        url = _export_url(link)
        if not url:
            continue
        name = _display_name(link)
        if name:
            lines.append(f"{url} | {name}")
        else:
            lines.append(url)
    header = "# Linkora — JDownloader / import\n# Format : URL | Nom suggéré\n\n"
    return (header + "\n".join(lines)).encode("utf-8")


def _build_html(payload: dict) -> bytes:
    links = payload["links"]
    theme = payload.get("theme") or "linkora"
    if theme == "lienlab":
        theme = "linkora"

    def link_class(status: str) -> str:
        if status == "ok":
            return "ok"
        if status in ("dead", "error"):
            return "dead"
        return "pending"

    detail_rows = "\n".join(
        f"<tr class=\"{link_class(l.get('resolve_status') or '')}\">"
        f"<td>{i}</td>"
        f"<td>{_esc(l.get('resolve_filename') or l.get('label') or '')}</td>"
        f"<td>{_esc(_display_name(l))}</td>"
        f"<td>{_esc(l.get('media_type') or '')}</td>"
        f"<td>{_esc(l.get('resolve_size') or l.get('size') or '')}</td>"
        f"<td class=\"col-source\"><a class=\"{link_class(l.get('resolve_status') or '')}\" "
        f"href=\"{_esc(l.get('url') or '')}\">{_esc(l.get('url') or '')}</a></td>"
        f"<td class=\"col-resolved\"><a class=\"{link_class(l.get('resolve_status') or '')}\" "
        f"href=\"{_esc(_export_url(l))}\">{_esc(_export_url(l))}</a></td>"
        f"<td>{_esc(l.get('resolve_status') or 'pending')}</td></tr>"
        for i, l in enumerate(links, 1)
    )

    source_block = "\n".join(_esc(l.get("url") or "") for l in links)
    resolved_block = "\n".join(_esc(_export_url(l)) for l in links)
    resolved_ok_block = "\n".join(
        _esc(_export_url(l)) for l in links if l.get("resolve_status") == "ok"
    )

    if theme == "alldebrid":
        css = """
  :root { --bg:#0b1220; --panel:#121a2b; --text:#e8eef7; --muted:#9aa8bc;
          --ok:#f5c518; --dead:#ff4d4f; --line:#243049; --accent:#3b82f6; }
  body { font-family: Segoe UI, Arial, sans-serif; background:var(--bg); color:var(--text);
         max-width: 1200px; margin: 0 auto; padding: 1.5rem; }
  h1,h2 { margin: 0 0 .6rem; }
  .meta { color: var(--muted); margin-bottom: 1.25rem; }
  .cols { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin:1.25rem 0 2rem; }
  .col { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:1rem; }
  .col h2 { font-size:1rem; display:flex; justify-content:space-between; align-items:center; }
  .col pre { margin:0; white-space:pre-wrap; word-break:break-all; font-size:.9rem;
             user-select:text; line-height:1.55; min-height:8rem; }
  .col-resolved pre, a.ok { color: var(--ok); }
  a.dead, .col pre.dead-list { color: var(--dead); }
  a.pending { color: var(--muted); }
  table { width:100%; border-collapse:collapse; background:var(--panel); }
  th,td { border-bottom:1px solid var(--line); padding:.55rem .4rem; text-align:left; vertical-align:top; font-size:.9rem; }
  th { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; }
  a { word-break:break-all; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .hint { color:var(--muted); font-size:.85rem; margin-top:.35rem; }
  button.copy { background:#1e293b; color:var(--text); border:1px solid var(--line);
                border-radius:6px; padding:.25rem .55rem; cursor:pointer; font-size:.8rem; }
  @media (max-width:800px){ .cols{grid-template-columns:1fr;} }
"""
    else:
        css = """
  :root { --bg:#f4f7fb; --panel:#fff; --text:#142033; --muted:#6b7a8d;
          --ok:#ca8a04; --dead:#b42318; --line:#d7dee8; --accent:#0f766e; }
  body { font-family: Georgia, serif; background:var(--bg); color:var(--text);
         max-width: 1200px; margin: 0 auto; padding: 1.5rem; }
  h1,h2 { margin: 0 0 .6rem; }
  .meta { color: var(--muted); margin-bottom: 1.25rem; }
  .cols { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin:1.25rem 0 2rem; }
  .col { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:1rem;
         box-shadow:0 8px 24px rgba(20,32,51,.06); }
  .col h2 { font-size:1rem; display:flex; justify-content:space-between; align-items:center; }
  .col pre { margin:0; white-space:pre-wrap; word-break:break-all; font-size:.9rem;
             user-select:text; line-height:1.55; min-height:8rem; font-family:Consolas,monospace; }
  .col-resolved pre, a.ok { color: var(--ok); }
  a.dead { color: var(--dead); }
  a.pending { color: var(--muted); }
  table { width:100%; border-collapse:collapse; background:var(--panel); border-radius:12px; overflow:hidden; }
  th,td { border-bottom:1px solid var(--line); padding:.6rem .45rem; text-align:left; vertical-align:top; }
  th { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; background:#f7fafc; }
  a { word-break:break-all; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .hint { color:var(--muted); font-size:.85rem; margin-top:.35rem; }
  button.copy { background:#eef6f5; color:var(--accent); border:1px solid var(--line);
                border-radius:6px; padding:.25rem .55rem; cursor:pointer; font-size:.8rem; }
  @media (max-width:800px){ .cols{grid-template-columns:1fr;} }
"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{_esc(payload['title'])} — {_esc(payload['host'])}</title>
<style>{css}</style>
</head>
<body>
  <h1>{_esc(payload['title'])}</h1>
  <p class="meta">Hébergeur : <strong>{_esc(payload['host'])}</strong>
  · {len(links)} lien(s)
  · Source : <a href="{_esc(payload['source_url'])}">{_esc(payload['source_url'])}</a></p>

  <div class="cols">
    <section class="col col-source">
      <h2>Liens source <button class="copy" type="button" onclick="copyCol('src')">Copier</button></h2>
      <pre id="src" tabindex="0">{source_block}</pre>
      <p class="hint">Cliquez dans la colonne puis Ctrl+A / Ctrl+C pour tout sélectionner.</p>
    </section>
    <section class="col col-resolved">
      <h2>Liens résolus <button class="copy" type="button" onclick="copyCol('res')">Copier</button></h2>
      <pre id="res" tabindex="0">{resolved_block}</pre>
      <p class="hint">Jaune = valide · Rouge = mort/erreur. Copie uniquement cette colonne.</p>
    </section>
  </div>

  <section class="col" style="margin-bottom:1.5rem">
    <h2>Résolus valides seulement <button class="copy" type="button" onclick="copyCol('ok')">Copier</button></h2>
    <pre id="ok" class="ok" tabindex="0">{resolved_ok_block or "(aucun)"}</pre>
  </section>

  <h2>Détail</h2>
  <table>
    <thead><tr><th>#</th><th>Label</th><th>Nom suggéré</th><th>Type</th><th>Taille</th><th>Source</th><th>Résolu</th><th>Statut</th></tr></thead>
    <tbody>
      {detail_rows}
    </tbody>
  </table>
  <script>
    function copyCol(id) {{
      const el = document.getElementById(id);
      const text = el.innerText;
      navigator.clipboard.writeText(text).then(() => {{
        const btn = el.parentElement.querySelector('button');
        if (!btn) return;
        const old = btn.textContent;
        btn.textContent = 'Copié !';
        setTimeout(() => btn.textContent = old, 1200);
      }});
    }}
  </script>
</body>
</html>
"""
    return html.encode("utf-8")


def _build_pdf_bytes(payload: dict) -> bytes:
    links = payload["links"]
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _pdf_safe(payload["title"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(
        0,
        6,
        _pdf_safe(
            f"Hebergeur : {payload['host']}  |  {len(links)} lien(s)\n"
            f"Source : {payload['source_url']}\n"
            f"Exporte le {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ),
    )
    pdf.ln(4)
    usable_width = pdf.epw

    # Colonne résolus
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(usable_width, 7, "Liens resolus (un par ligne)")
    pdf.set_font("Helvetica", "", 8)
    for link in links:
        url = _export_url(link)
        status = link.get("resolve_status") or ""
        if status == "ok":
            pdf.set_text_color(180, 140, 0)
        elif status in ("dead", "error"):
            pdf.set_text_color(180, 35, 24)
        else:
            pdf.set_text_color(80, 80, 80)
        pdf.set_x(pdf.l_margin)
        for chunk in _chunk_text(_pdf_safe(url), 95):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(usable_width, 4.2, chunk)

    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(usable_width, 7, "Liens source (un par ligne)")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(60, 60, 60)
    for link in links:
        url = link.get("url") or ""
        pdf.set_x(pdf.l_margin)
        for chunk in _chunk_text(_pdf_safe(url), 95):
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(usable_width, 4.2, chunk)

    out = pdf.output()
    return out if isinstance(out, (bytes, bytearray)) else bytes(out)


@app.post("/api/export/jdownloader")
def export_jdownloader():
    payload = _payload_from_request()
    if not payload["links"]:
        return jsonify({"error": "Aucun lien à exporter."}), 400
    return _send_export(
        io.BytesIO(_build_jdownloader(payload)),
        "text/plain",
        f"liens_{payload['host'] or 'export'}_jdownloader.txt",
        payload["view"],
    )


@app.post("/api/network/test")
def api_network_test():
    """Teste une connexion à un partage NAS (Windows)."""
    import network_shares

    data = request.get_json(silent=True) or {}
    host = (data.get("host") or "").strip()
    share = (data.get("share") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password")
    if password is None or (isinstance(password, str) and password.startswith("••••")):
        # Réutilise le mot de passe enregistré si masqué / vide
        for entry in app_settings.get_network_shares():
            if (
                entry.get("username", "").lower() == username.lower()
                and (not host or entry.get("host", "").lower() == host.lower())
                and (not share or entry.get("share", "").lower() == share.lower())
            ):
                password = entry.get("password") or ""
                break
        else:
            password = ""
    try:
        result = network_shares.test_credentials(
            host=host,
            share=share,
            username=username,
            password=str(password or ""),
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(result)


@app.post("/api/library/scan")
def api_library_scan():
    """Phase 1 — inventaire lecture seule d’un dossier média (async + progression)."""
    import library_scan

    data = request.get_json(silent=True) or {}
    folder = (data.get("folder") or "").strip()
    recursive = bool(data.get("recursive", True))
    template_id = (data.get("template") or "").strip() or app_settings.get_rename_template()
    background = bool(data.get("background", True))
    if not folder:
        return jsonify({"error": "Indiquez un dossier à scanner."}), 400

    if not _scan_apply_lock.acquire(blocking=False):
        return jsonify({**_scan_get_state(), "error": "Un scan est déjà en cours."}), 409

    def on_progress(info: dict) -> None:
        _scan_set_state(
            busy=True,
            done=False,
            error="",
            percent=int(info.get("percent") or 0),
            phase=str(info.get("phase") or ""),
            message=str(info.get("message") or ""),
        )

    def worker() -> None:
        try:
            _scan_set_state(
                busy=True,
                done=False,
                error="",
                percent=1,
                phase="prepare",
                message="Démarrage du scan…",
                result=None,
            )
            result = library_scan.scan_library(
                folder,
                recursive=recursive,
                template_id=template_id,
                on_progress=on_progress,
            )
            try:
                cache_info = result.get("cache") or {}
                storage.save_library_history(
                    kind="scan",
                    title=folder,
                    folders={"path": folder, "recursive": recursive},
                    summary=(
                        f"{result.get('count') or 0} média(s) · "
                        f"{cache_info.get('reused', 0)} cache · "
                        f"{cache_info.get('parsed', 0)} nouveaux · "
                        f"{cache_info.get('elapsed_s', '?')}s"
                    ),
                    result=result,
                    count=int(result.get("count") or 0),
                )
            except Exception:
                pass
            _scan_set_state(
                busy=False,
                done=True,
                percent=100,
                phase="done",
                message="Scan terminé.",
                error="",
                result=result,
            )
        except Exception as exc:
            _scan_set_state(
                busy=False,
                done=True,
                percent=100,
                phase="error",
                message="",
                error=str(exc),
                result=None,
            )
        finally:
            _scan_apply_lock.release()

    if background:
        threading.Thread(target=worker, daemon=True, name="linkora-library-scan").start()
        return jsonify(_scan_get_state())

    try:
        worker()
        with _scan_lock:
            err = _scan_state.get("error") or ""
            result = _scan_state.get("result")
        if err:
            return jsonify({"error": err}), 400
        return jsonify(result or {"error": "Résultat vide."})
    except Exception:
        if _scan_apply_lock.locked():
            try:
                _scan_apply_lock.release()
            except RuntimeError:
                pass
        raise


@app.get("/api/library/scan/progress")
def api_library_scan_progress():
    with _scan_lock:
        payload = {
            "busy": _scan_state["busy"],
            "done": _scan_state["done"],
            "error": _scan_state["error"],
            "percent": _scan_state["percent"],
            "phase": _scan_state["phase"],
            "message": _scan_state["message"],
        }
        if _scan_state.get("done") and _scan_state.get("result") is not None:
            payload["result"] = _scan_state["result"]
    return jsonify(payload)


@app.post("/api/tmdb/test")
def api_tmdb_test():
    import tmdb as tmdb_mod

    data = request.get_json(silent=True) or {}
    key = (data.get("api_key") or "").strip()
    if not key or key.startswith("••••"):
        key = app_settings.get_tmdb_api_key()
    try:
        result = tmdb_mod.test_api_key(key)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(result)


@app.post("/api/library/gaps")
def api_library_gaps():
    """Compare une série locale au catalogue TMDB (saisons / épisodes manquants)."""
    import tmdb as tmdb_mod

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Titre requis."}), 400
    language = (data.get("language") or "fr-FR").strip() or "fr-FR"
    year = data.get("year")
    try:
        year_i = int(year) if year is not None and str(year).strip() != "" else None
    except (TypeError, ValueError):
        year_i = None
    tmdb_id = data.get("tmdb_id")
    try:
        tmdb_id_i = int(tmdb_id) if tmdb_id is not None and str(tmdb_id).strip() != "" else None
    except (TypeError, ValueError):
        tmdb_id_i = None
    local_seasons = data.get("seasons") if isinstance(data.get("seasons"), list) else []
    api_key = app_settings.get_tmdb_api_key()
    if not api_key:
        return jsonify({"error": "Ajoutez une clé API TMDB dans Paramètres."}), 400
    try:
        result = tmdb_mod.find_series_gaps(
            api_key,
            title=title,
            year=year_i,
            tmdb_id=tmdb_id_i,
            local_seasons=local_seasons,
            language=language,
            force=bool(data.get("force")),
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    if result.get("error") == "no_key":
        return jsonify({"error": "Clé TMDB manquante."}), 400
    if not result.get("found"):
        return jsonify(result), 404
    return jsonify(result)


@app.post("/api/library/gaps/batch")
def api_library_gaps_batch():
    """Vérifie plusieurs séries (synchrone, limité)."""
    import tmdb as tmdb_mod

    data = request.get_json(silent=True) or {}
    entries = data.get("entries") or []
    if not isinstance(entries, list) or not entries:
        return jsonify({"error": "Liste de séries requise."}), 400
    language = (data.get("language") or "fr-FR").strip() or "fr-FR"
    api_key = app_settings.get_tmdb_api_key()
    if not api_key:
        return jsonify({"error": "Ajoutez une clé API TMDB dans Paramètres."}), 400

    results = []
    incomplete = 0
    for raw in entries[:80]:
        if not isinstance(raw, dict):
            continue
        title = (raw.get("title") or "").strip()
        if not title:
            continue
        year = raw.get("year")
        try:
            year_i = int(year) if year is not None and str(year).strip() != "" else None
        except (TypeError, ValueError):
            year_i = None
        tmdb_id = raw.get("tmdb_id")
        try:
            tmdb_id_i = (
                int(tmdb_id) if tmdb_id is not None and str(tmdb_id).strip() != "" else None
            )
        except (TypeError, ValueError):
            tmdb_id_i = None
        try:
            one = tmdb_mod.find_series_gaps(
                api_key,
                title=title,
                year=year_i,
                tmdb_id=tmdb_id_i,
                local_seasons=raw.get("seasons") if isinstance(raw.get("seasons"), list) else [],
                language=language,
            )
        except Exception as exc:
            one = {"found": False, "title": title, "error": str(exc)}
        if one.get("found") and (one.get("gaps") or {}).get("missing_count"):
            incomplete += 1
        results.append(one)

    return jsonify(
        {
            "count": len(results),
            "incomplete": incomplete,
            "results": results,
        }
    )


@app.get("/api/library/poster/<key>")
def api_library_poster(key: str):
    import tmdb as tmdb_mod

    safe = (key or "").strip()
    if not safe or "/" in safe or "\\" in safe or ".." in safe:
        return jsonify({"error": "Clé invalide."}), 400
    entry_id = (request.args.get("entry") or "").strip() or None
    path = tmdb_mod.poster_file_for_key(safe, entry_id=entry_id)
    if not path:
        return jsonify({"error": "Affiche introuvable."}), 404
    return send_file(path, mimetype="image/jpeg", max_age=86400 * 30)


@app.post("/api/tmdb/search")
def api_tmdb_search():
    """Recherche TMDB pour corriger une affiche (liste de candidats)."""
    import tmdb as tmdb_mod

    data = request.get_json(silent=True) or {}
    query = (data.get("query") or data.get("title") or "").strip()
    media = (data.get("media") or data.get("type") or "tv").strip() or "tv"
    language = (data.get("language") or "fr-FR").strip() or "fr-FR"
    year = data.get("year")
    try:
        year_i = int(year) if year is not None and str(year).strip() != "" else None
    except (TypeError, ValueError):
        year_i = None
    api_key = app_settings.get_tmdb_api_key()
    if not api_key:
        return jsonify({"error": "Ajoutez une clé API TMDB dans Paramètres."}), 400
    if not query:
        return jsonify({"error": "Indiquez un titre à rechercher."}), 400
    try:
        results = tmdb_mod.search_tmdb_list(
            api_key,
            query=query,
            media=media,
            year=year_i,
            language=language,
            limit=int(data.get("limit") or 8),
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"results": results, "query": query, "media": media})


@app.post("/api/library/poster/assign")
def api_library_poster_assign():
    """Associe manuellement une série/film à un résultat TMDB."""
    import tmdb as tmdb_mod

    data = request.get_json(silent=True) or {}
    entry_id = (data.get("entry_id") or data.get("id") or "").strip()
    title = (data.get("title") or "").strip()
    media = (data.get("media") or data.get("type") or "tv").strip() or "tv"
    tmdb_media = (data.get("tmdb_media") or media).strip()
    language = (data.get("language") or "fr-FR").strip() or "fr-FR"
    year = data.get("year")
    try:
        year_i = int(year) if year is not None and str(year).strip() != "" else None
    except (TypeError, ValueError):
        year_i = None
    try:
        tmdb_id = int(data.get("tmdb_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "tmdb_id invalide."}), 400
    api_key = app_settings.get_tmdb_api_key()
    if not api_key:
        return jsonify({"error": "Ajoutez une clé API TMDB dans Paramètres."}), 400
    if not entry_id or not title:
        return jsonify({"error": "entry_id et title requis."}), 400
    try:
        result = tmdb_mod.assign_poster(
            api_key,
            entry_id=entry_id,
            title=title,
            media=media,
            tmdb_id=tmdb_id,
            tmdb_media=tmdb_media,
            language=language,
            year=year_i,
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.post("/api/library/enrich")
def api_library_enrich():
    """Charge les affiches TMDB pour une liste de titres (async)."""
    import tmdb as tmdb_mod

    data = request.get_json(silent=True) or {}
    entries = data.get("entries") or []
    if not isinstance(entries, list):
        return jsonify({"error": "Liste d’entrées invalide."}), 400
    language = (data.get("language") or "fr-FR").strip() or "fr-FR"
    background = bool(data.get("background", True))
    api_key = app_settings.get_tmdb_api_key()
    if not api_key:
        return jsonify({"error": "Ajoutez une clé API TMDB dans Paramètres."}), 400

    if not _enrich_apply_lock.acquire(blocking=False):
        return jsonify({**_enrich_get_state(), "error": "Enrichissement déjà en cours."}), 409

    def on_progress(info: dict) -> None:
        posters = info.get("posters")
        stats = info.get("stats")
        kwargs = {
            "busy": True,
            "done": False,
            "error": "",
            "percent": int(info.get("percent") or 0),
            "phase": str(info.get("phase") or ""),
            "message": str(info.get("message") or ""),
        }
        if isinstance(posters, dict):
            kwargs["result"] = {
                "posters": posters,
                "stats": stats if isinstance(stats, dict) else {},
            }
        _enrich_set_state(**kwargs)

    def worker() -> None:
        try:
            _enrich_set_state(
                busy=True,
                done=False,
                error="",
                percent=1,
                phase="prepare",
                message="Préparation des affiches…",
                result=None,
            )
            result = tmdb_mod.enrich_entries(
                api_key,
                entries,
                language=language,
                on_progress=on_progress,
            )
            _enrich_set_state(
                busy=False,
                done=True,
                percent=100,
                phase="done",
                message="Affiches prêtes.",
                error="",
                result=result,
            )
        except Exception as exc:
            _enrich_set_state(
                busy=False,
                done=True,
                percent=100,
                phase="error",
                message="",
                error=str(exc),
                result=None,
            )
        finally:
            _enrich_apply_lock.release()

    if background:
        threading.Thread(target=worker, daemon=True, name="linkora-tmdb-enrich").start()
        return jsonify(_enrich_get_state())

    try:
        worker()
        with _enrich_lock:
            err = _enrich_state.get("error") or ""
            result = _enrich_state.get("result")
        if err:
            return jsonify({"error": err}), 400
        return jsonify(result or {"error": "Résultat vide."})
    except Exception:
        if _enrich_apply_lock.locked():
            try:
                _enrich_apply_lock.release()
            except RuntimeError:
                pass
        raise


@app.get("/api/library/enrich/progress")
def api_library_enrich_progress():
    with _enrich_lock:
        payload = {
            "busy": _enrich_state["busy"],
            "done": _enrich_state["done"],
            "error": _enrich_state["error"],
            "percent": _enrich_state["percent"],
            "phase": _enrich_state["phase"],
            "message": _enrich_state["message"],
        }
        # Résultat partiel pendant le fetch (affiches au fur et à mesure)
        if _enrich_state.get("result") is not None:
            payload["result"] = _enrich_state["result"]
    return jsonify(payload)


@app.post("/api/library/diff")
def api_library_diff():
    """Phase 4 — compare un ou plusieurs dossiers PC ↔ NAS (async + progression)."""
    import library_scan

    data = request.get_json(silent=True) or {}
    folders_a = data.get("folders_a") or data.get("folders_pc")
    folders_b = data.get("folders_b") or data.get("folders_nas")
    if not folders_a:
        single = (data.get("folder_a") or data.get("folder_pc") or "").strip()
        folders_a = [single] if single else []
    if not folders_b:
        single = (data.get("folder_b") or data.get("folder_nas") or "").strip()
        folders_b = [single] if single else []
    if isinstance(folders_a, str):
        folders_a = [folders_a]
    if isinstance(folders_b, str):
        folders_b = [folders_b]
    folders_a = [str(x).strip() for x in folders_a if str(x).strip()]
    folders_b = [str(x).strip() for x in folders_b if str(x).strip()]

    recursive = bool(data.get("recursive", True))
    label_a = (data.get("label_a") or "PC").strip() or "PC"
    label_b = (data.get("label_b") or "NAS").strip() or "NAS"
    template_id = (data.get("template") or "").strip() or app_settings.get_rename_template()
    background = bool(data.get("background", True))

    if not folders_a or not folders_b:
        return jsonify({"error": "Indiquez au moins un dossier PC et un dossier NAS."}), 400

    if not _diff_apply_lock.acquire(blocking=False):
        return jsonify({**_diff_get_state(), "error": "Une comparaison est déjà en cours."}), 409

    def on_progress(info: dict) -> None:
        _diff_set_state(
            busy=True,
            done=False,
            error="",
            percent=int(info.get("percent") or 0),
            phase=str(info.get("phase") or ""),
            message=str(info.get("message") or ""),
        )

    def worker() -> None:
        try:
            _diff_set_state(
                busy=True,
                done=False,
                error="",
                percent=1,
                phase="prepare",
                message="Démarrage de la comparaison…",
                result=None,
            )
            result = library_scan.diff_libraries(
                folders_a=folders_a,
                folders_b=folders_b,
                recursive=recursive,
                template_id=template_id,
                label_a=label_a,
                label_b=label_b,
                on_progress=on_progress,
            )
            try:
                storage.save_library_history(
                    kind="diff",
                    title=f"{label_a} ↔ {label_b}",
                    folders={
                        "a": list(folders_a),
                        "b": list(folders_b),
                        "recursive": recursive,
                    },
                    summary=(
                        f"{result.get('missing_on_b_count') or 0} manquants NAS · "
                        f"{result.get('missing_on_a_count') or 0} manquants PC · "
                        f"{result.get('common_count') or 0} communs"
                    ),
                    result=result,
                    count=int(result.get("common_count") or 0)
                    + int(result.get("missing_on_a_count") or 0)
                    + int(result.get("missing_on_b_count") or 0),
                )
            except Exception:
                pass
            _diff_set_state(
                busy=False,
                done=True,
                percent=100,
                phase="done",
                message="Comparaison terminée.",
                error="",
                result=result,
            )
        except Exception as exc:
            _diff_set_state(
                busy=False,
                done=True,
                percent=100,
                phase="error",
                message="",
                error=str(exc),
                result=None,
            )
        finally:
            _diff_apply_lock.release()

    if background:
        threading.Thread(target=worker, daemon=True, name="linkora-library-diff").start()
        return jsonify(_diff_get_state())

    try:
        worker()
        with _diff_lock:
            err = _diff_state.get("error") or ""
            result = _diff_state.get("result")
        if err:
            return jsonify({"error": err}), 400
        return jsonify(result or {"error": "Résultat vide."})
    except Exception:
        if _diff_apply_lock.locked():
            try:
                _diff_apply_lock.release()
            except RuntimeError:
                pass
        raise


@app.get("/api/library/diff/progress")
def api_library_diff_progress():
    with _diff_lock:
        payload = {
            "busy": _diff_state["busy"],
            "done": _diff_state["done"],
            "error": _diff_state["error"],
            "percent": _diff_state["percent"],
            "phase": _diff_state["phase"],
            "message": _diff_state["message"],
        }
        if _diff_state.get("done") and _diff_state.get("result") is not None:
            payload["result"] = _diff_state["result"]
    return jsonify(payload)


@app.post("/api/rename/preview")
def rename_preview():
    data = request.get_json(silent=True) or {}
    filename = (data.get("filename") or "").strip()
    template_id = (data.get("template") or "").strip() or app_settings.get_rename_template()
    if not filename:
        return jsonify({"error": "Nom de fichier requis."}), 400
    return jsonify(smart_naming.suggest_name(filename, template_id=template_id))


@app.post("/api/rename/scan")
def rename_scan():
    data = request.get_json(silent=True) or {}
    folder = (data.get("folder") or "").strip()
    recursive = bool(data.get("recursive", False))
    template_id = (data.get("template") or "").strip() or app_settings.get_rename_template()
    if not folder:
        return jsonify({"error": "Indiquez un dossier."}), 400
    try:
        items = smart_naming.scan_folder(
            folder, recursive=recursive, template_id=template_id
        )
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Scan impossible : {exc}"}), 400
    return jsonify(
        {
            "folder": folder,
            "count": len(items),
            "to_rename": sum(1 for i in items if not i["unchanged"]),
            "items": items,
            "template": template_id,
        }
    )


@app.post("/api/rename/apply")
def rename_apply():
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    dry_run = bool(data.get("dry_run", False))
    if not isinstance(items, list) or not items:
        return jsonify({"error": "Aucun fichier à renommer."}), 400
    result = smart_naming.apply_renames(items, dry_run=dry_run)
    return jsonify(result)


@app.post("/api/export/csv")
def export_csv():
    payload = _payload_from_request()
    if not payload["links"]:
        return jsonify({"error": "Aucun lien à exporter."}), 400
    raw = _build_csv(payload)
    if payload["view"]:
        text = raw.decode("utf-8-sig")
        preview = (
            '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
            f"<title>CSV — {_esc(payload['title'])}</title>"
            "<style>body{font-family:Consolas,monospace;margin:2rem;"
            "white-space:pre-wrap;line-height:1.5}</style>"
            f"</head><body>{_esc(text)}</body></html>"
        )
        return _send_export(
            io.BytesIO(preview.encode("utf-8")),
            "text/html",
            f"liens_{payload['host'] or 'export'}.html",
            True,
        )
    return _send_export(
        io.BytesIO(raw),
        "text/csv",
        f"liens_{payload['host'] or 'export'}.csv",
        False,
    )


@app.post("/api/export/html")
def export_html():
    payload = _payload_from_request()
    if not payload["links"]:
        return jsonify({"error": "Aucun lien à exporter."}), 400
    return _send_export(
        io.BytesIO(_build_html(payload)),
        "text/html",
        f"liens_{payload['host'] or 'export'}.html",
        payload["view"],
    )


@app.post("/api/export/pdf")
def export_pdf():
    payload = _payload_from_request()
    if not payload["links"]:
        return jsonify({"error": "Aucun lien à exporter."}), 400
    return _send_export(
        io.BytesIO(_build_pdf_bytes(payload)),
        "application/pdf",
        f"liens_{payload['host'] or 'export'}.pdf",
        payload["view"],
    )


def _chunk_text(text: str, size: int) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)]


def _esc(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pdf_safe(text: str) -> str:
    """FPDF core fonts : latin-1 approximé."""
    return (
        str(text)
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ù", "u")
        .replace("û", "u")
        .replace("ô", "o")
        .replace("î", "i")
        .replace("ï", "i")
        .replace("ç", "c")
        .replace("É", "E")
        .replace("È", "E")
        .replace("À", "A")
        .replace("œ", "oe")
        .replace("Œ", "OE")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


if __name__ == "__main__":
    import os
    import sys

    # python app.py --desktop  → fenêtre native
    if "--desktop" in sys.argv or os.environ.get("LINKORA_DESKTOP") == "1":
        from desktop import main as desktop_main

        desktop_main()
    else:
        use_reloader = True
        # Débogueur Werkzeug (exécution de code) désactivé par défaut :
        # activer explicitement avec LINKORA_DEBUG=1 pour développer.
        debug_mode = os.environ.get("LINKORA_DEBUG") == "1"
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not use_reloader:
            conf = app_settings.load_settings()
            updater.startup_autoupdate(
                enabled=bool(conf.get("auto_update", True)),
                manifest_url=(conf.get("update_manifest_url") or "").strip() or None,
            )
        app.run(debug=debug_mode, port=5000, use_reloader=use_reloader)
