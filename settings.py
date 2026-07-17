"""Persistance des réglages locaux (clés API débrideurs)."""

from __future__ import annotations

import json

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
    "providers": {
        "alldebrid": {"api_key": "", "enabled": True},
        "realdebrid": {"api_key": "", "enabled": True},
    },
}


def _clamp_int(value, default: int, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


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
        merged["rename_template"] = tmpl if tmpl in (
            "simple",
            "plex",
            "jellyfin",
            "dotted",
        ) else "simple"
    for name, conf in data.get("providers", {}).items():
        if name in merged["providers"]:
            merged["providers"][name].update(conf)
        else:
            merged["providers"][name] = conf
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
    if "theme" in payload and payload["theme"] in ("linkora", "lienlab", "alldebrid"):
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
        current["rename_template"] = (
            tmpl if tmpl in ("simple", "plex", "jellyfin", "dotted") else "simple"
        )
    providers = payload.get("providers") or {}
    for name, conf in providers.items():
        if name not in current["providers"]:
            current["providers"][name] = {"api_key": "", "enabled": True}
        if "api_key" in conf:
            key = conf["api_key"]
            if key is None:
                continue
            if isinstance(key, str) and key.startswith("••••"):
                continue
            current["providers"][name]["api_key"] = key.strip()
        if "enabled" in conf:
            current["providers"][name]["enabled"] = bool(conf["enabled"])
    return save_settings(current)


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
        "providers": {},
    }
    for name, conf in data["providers"].items():
        key = conf.get("api_key") or ""
        out["providers"][name] = {
            "enabled": conf.get("enabled", True),
            "configured": bool(key),
            "api_key_masked": _mask(key),
            "api_key": "",
        }
    return out


def get_provider_key(provider: str | None = None) -> tuple[str, str]:
    data = load_settings()
    name = provider or data.get("active_provider") or "alldebrid"
    conf = data.get("providers", {}).get(name) or {}
    return name, (conf.get("api_key") or "").strip()


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
