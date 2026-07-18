"""Persistance des réglages locaux (clés API débrideurs)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from paths import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULTS = {
    "active_provider": "alldebrid",
    "theme": "linkora",
    "max_retries": 3,
    "resolve_concurrency": 6,
    "auto_update": True,
    "update_manifest_url": "",
    "rename_template": "simple",
    "notify_on_resolve": True,
    "custom_accent": "",
    "custom_logo": False,
    "profiles": [],
    "active_profile_id": "",
    "providers": {
        "alldebrid": {"api_key": "", "api_keys": [], "enabled": True},
        "realdebrid": {"api_key": "", "api_keys": [], "enabled": True},
    },
}

RENAME_TEMPLATES = ("simple", "plex", "jellyfin", "dotted")
CUSTOM_LOGO_NAME = "custom_logo"


def _normalize_keys(raw) -> list[str]:
    keys: list[str] = []
    if isinstance(raw, str):
        parts = raw.replace(",", "\n").splitlines()
    elif isinstance(raw, list):
        parts = raw
    else:
        parts = []
    for part in parts:
        key = str(part or "").strip()
        if not key or key.startswith("••••"):
            continue
        if key not in keys:
            keys.append(key)
        if len(keys) >= 12:
            break
    return keys


def _provider_keys(conf: dict) -> list[str]:
    keys = _normalize_keys(conf.get("api_keys") or [])
    primary = str(conf.get("api_key") or "").strip()
    if primary and primary not in keys:
        keys.insert(0, primary)
    return keys


def _clamp_int(value, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _normalize_profile(raw: dict | None) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    pid = str(raw.get("id") or "").strip() or str(uuid.uuid4())
    tmpl = str(raw.get("rename_template") or "simple")
    if tmpl not in RENAME_TEMPLATES:
        tmpl = "simple"
    provider = str(raw.get("active_provider") or "alldebrid")
    if provider not in ("alldebrid", "realdebrid"):
        provider = "alldebrid"
    hosts: list[str] = []
    seen_h: set[str] = set()
    raw_hosts = raw.get("hosts")
    candidates: list[str] = []
    if isinstance(raw_hosts, list):
        candidates.extend(str(h) for h in raw_hosts)
    elif isinstance(raw_hosts, str) and raw_hosts.strip():
        candidates.append(raw_hosts)
    single = str(raw.get("host") or "").strip()
    if single:
        # Ancien format ou libellé "a + b"
        if " + " in single and not candidates:
            candidates.extend(single.split(" + "))
        else:
            candidates.insert(0, single)
    for item in candidates:
        value = str(item or "").strip()[:120]
        if not value:
            continue
        key = value.lower()
        if key in seen_h:
            continue
        seen_h.add(key)
        hosts.append(value)
        if len(hosts) >= 6:
            break
    return {
        "id": pid,
        "name": name[:80],
        "host": (hosts[0] if hosts else "")[:120],
        "hosts": hosts,
        "active_provider": provider,
        "max_retries": _clamp_int(raw.get("max_retries"), 3, 1, 8),
        "resolve_concurrency": _clamp_int(raw.get("resolve_concurrency"), 6, 1, 12),
        "rename_template": tmpl,
    }


def _normalize_profiles(raw) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        prof = _normalize_profile(item)
        if not prof or prof["id"] in seen:
            continue
        seen.add(prof["id"])
        out.append(prof)
        if len(out) >= 40:
            break
    return out


def _ensure() -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        save_settings(DEFAULTS)
        return json.loads(json.dumps(DEFAULTS))
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    merged = json.loads(json.dumps(DEFAULTS))
    merged["active_provider"] = data.get("active_provider", DEFAULTS["active_provider"])
    merged["theme"] = data.get("theme", DEFAULTS["theme"])
    merged["max_retries"] = _clamp_int(
        data.get("max_retries", DEFAULTS["max_retries"]), 3, 1, 8
    )
    merged["resolve_concurrency"] = _clamp_int(
        data.get("resolve_concurrency", DEFAULTS["resolve_concurrency"]), 6, 1, 12
    )
    if "auto_update" in data:
        merged["auto_update"] = bool(data["auto_update"])
    if "update_manifest_url" in data:
        merged["update_manifest_url"] = str(data.get("update_manifest_url") or "")
    if "rename_template" in data:
        tmpl = str(data.get("rename_template") or "simple")
        merged["rename_template"] = tmpl if tmpl in RENAME_TEMPLATES else "simple"
    if "notify_on_resolve" in data:
        merged["notify_on_resolve"] = bool(data["notify_on_resolve"])
    if "custom_accent" in data:
        accent = str(data.get("custom_accent") or "").strip()
        merged["custom_accent"] = accent if accent.startswith("#") and len(accent) in (4, 7) else ""
    if "custom_logo" in data:
        merged["custom_logo"] = bool(data["custom_logo"])
    else:
        merged["custom_logo"] = (DATA_DIR / f"{CUSTOM_LOGO_NAME}.png").is_file() or (
            DATA_DIR / f"{CUSTOM_LOGO_NAME}.jpg"
        ).is_file() or (DATA_DIR / f"{CUSTOM_LOGO_NAME}.svg").is_file() or (
            DATA_DIR / f"{CUSTOM_LOGO_NAME}.webp"
        ).is_file()
    merged["profiles"] = _normalize_profiles(data.get("profiles"))
    active_pid = str(data.get("active_profile_id") or "")
    if active_pid and any(p["id"] == active_pid for p in merged["profiles"]):
        merged["active_profile_id"] = active_pid
    else:
        merged["active_profile_id"] = ""
    for name, conf in data.get("providers", {}).items():
        if name in merged["providers"]:
            merged["providers"][name].update(conf)
        else:
            merged["providers"][name] = conf
        # Normaliser multi-clés
        keys = _provider_keys(merged["providers"][name])
        merged["providers"][name]["api_keys"] = keys
        merged["providers"][name]["api_key"] = keys[0] if keys else ""
    return merged


def load_settings() -> dict:
    return _ensure()


def save_settings(data: dict) -> dict:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def update_settings(payload: dict) -> dict:
    current = load_settings()
    if "active_provider" in payload:
        current["active_provider"] = payload["active_provider"]
    if "theme" in payload and payload["theme"] in ("linkora", "lienlab", "alldebrid", "nocturne"):
        theme = payload["theme"]
        current["theme"] = "linkora" if theme == "lienlab" else theme
    if "max_retries" in payload:
        current["max_retries"] = _clamp_int(payload["max_retries"], 3, 1, 8)
    if "resolve_concurrency" in payload:
        current["resolve_concurrency"] = _clamp_int(
            payload["resolve_concurrency"], 6, 1, 12
        )
    if "auto_update" in payload:
        current["auto_update"] = bool(payload["auto_update"])
    if "update_manifest_url" in payload:
        current["update_manifest_url"] = str(payload.get("update_manifest_url") or "").strip()
    if "rename_template" in payload:
        tmpl = str(payload.get("rename_template") or "simple")
        current["rename_template"] = tmpl if tmpl in RENAME_TEMPLATES else "simple"
    if "notify_on_resolve" in payload:
        current["notify_on_resolve"] = bool(payload["notify_on_resolve"])
    if "custom_accent" in payload:
        accent = str(payload.get("custom_accent") or "").strip()
        current["custom_accent"] = (
            accent if accent.startswith("#") and len(accent) in (4, 7) else ""
        )
    # Logo : non personnalisable (marque Linkora figée)
    if "profiles" in payload:
        current["profiles"] = _normalize_profiles(payload.get("profiles"))
    if "active_profile_id" in payload:
        pid = str(payload.get("active_profile_id") or "")
        if pid and any(p["id"] == pid for p in current["profiles"]):
            current["active_profile_id"] = pid
        else:
            current["active_profile_id"] = ""
    providers = payload.get("providers") or {}
    for name, conf in providers.items():
        if name not in current["providers"]:
            current["providers"][name] = {"api_key": "", "api_keys": [], "enabled": True}
        if "api_keys" in conf:
            keys = _normalize_keys(conf.get("api_keys"))
            current["providers"][name]["api_keys"] = keys
            current["providers"][name]["api_key"] = keys[0] if keys else ""
        elif "api_key" in conf:
            key = conf["api_key"]
            if key is None:
                continue
            if isinstance(key, str) and key.startswith("••••"):
                continue
            # Une seule clé collée → remplace / ajoute en tête
            text = key.strip()
            if "\n" in text or "," in text:
                keys = _normalize_keys(text)
            else:
                keys = _normalize_keys([text]) if text else []
            if keys:
                current["providers"][name]["api_keys"] = keys
                current["providers"][name]["api_key"] = keys[0]
        if "enabled" in conf:
            current["providers"][name]["enabled"] = bool(conf["enabled"])
    return save_settings(current)


def apply_profile(profile_id: str) -> dict | None:
    """Applique un profil aux réglages courants (hors clés API)."""
    current = load_settings()
    prof = next((p for p in current["profiles"] if p["id"] == profile_id), None)
    if not prof:
        return None
    current["active_profile_id"] = prof["id"]
    current["active_provider"] = prof["active_provider"]
    current["max_retries"] = prof["max_retries"]
    current["resolve_concurrency"] = prof["resolve_concurrency"]
    current["rename_template"] = prof["rename_template"]
    save_settings(current)
    return prof


def public_settings() -> dict:
    """Version masquée pour l'UI (ne révèle pas la clé complète)."""
    data = load_settings()
    out = {
        "active_provider": data["active_provider"],
        "theme": (
            "linkora"
            if (data.get("theme") or "linkora") in ("lienlab", "linkora")
            else data.get("theme")
        ),
        "max_retries": data.get("max_retries", 3),
        "resolve_concurrency": data.get("resolve_concurrency", 6),
        "auto_update": bool(data.get("auto_update", True)),
        "update_manifest_url": data.get("update_manifest_url") or "",
        "rename_template": data.get("rename_template") or "simple",
        "notify_on_resolve": bool(data.get("notify_on_resolve", True)),
        "custom_accent": data.get("custom_accent") or "",
        "custom_logo": bool(data.get("custom_logo")),
        "profiles": list(data.get("profiles") or []),
        "active_profile_id": data.get("active_profile_id") or "",
        "providers": {},
    }
    for name, conf in data["providers"].items():
        keys = _provider_keys(conf)
        out["providers"][name] = {
            "enabled": conf.get("enabled", True),
            "configured": bool(keys),
            "key_count": len(keys),
            "api_key_masked": _mask(keys[0]) if keys else "",
            "api_key": "",
        }
    return out


def get_provider_key(provider: str | None = None) -> tuple[str, str]:
    name, keys = get_provider_keys(provider)
    return name, (keys[0] if keys else "")


def get_provider_keys(provider: str | None = None) -> tuple[str, list[str]]:
    data = load_settings()
    name = provider or data.get("active_provider") or "alldebrid"
    conf = data.get("providers", {}).get(name) or {}
    return name, _provider_keys(conf)


def custom_logo_path() -> Path | None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for ext in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        candidate = DATA_DIR / f"{CUSTOM_LOGO_NAME}{ext}"
        if candidate.is_file():
            return candidate
    return None


def clear_custom_logo() -> None:
    for ext in (".png", ".jpg", ".jpeg", ".svg", ".webp"):
        path = DATA_DIR / f"{CUSTOM_LOGO_NAME}{ext}"
        if path.is_file():
            path.unlink(missing_ok=True)
    data = load_settings()
    data["custom_logo"] = False
    save_settings(data)


def get_max_retries() -> int:
    return int(load_settings().get("max_retries") or 3)


def get_resolve_concurrency() -> int:
    return int(load_settings().get("resolve_concurrency") or 6)


def get_rename_template() -> str:
    return str(load_settings().get("rename_template") or "simple")


def get_update_manifest_url() -> str:
    return str(load_settings().get("update_manifest_url") or "").strip()


def _mask(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "••••" + key[-2:]
    return key[:4] + "••••" + key[-4:]
