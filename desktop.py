"""Lanceur bureau Linkora — fenêtre native (sans console DOS)."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from contextlib import closing
from pathlib import Path


def _cleanup_old_update_scripts() -> None:
    """Supprime d’anciens helpers .bat/.ps1/.vbs qui ouvraient des fenêtres DOS."""
    try:
        tmp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".")
        for pattern in ("linkora-apply-*.bat", "linkora-apply-*.ps1", "linkora-apply-*.vbs"):
            for path in tmp.glob(pattern):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
    except Exception:
        pass


def _port_free(port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _pick_port(preferred: int = 5000) -> int:
    for port in range(preferred, preferred + 20):
        if _port_free(port):
            return port
    return preferred


def _wait_ready(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(0.4)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.15)
    return False


def main() -> None:
    # Mode production (pas de reloader / debug)
    os.environ.setdefault("LINKORA_DESKTOP", "1")
    _cleanup_old_update_scripts()

    import app as linkora_app
    import settings as app_settings
    import updater

    port = _pick_port(5000)
    conf = app_settings.load_settings()
    updater.startup_autoupdate(
        enabled=bool(conf.get("auto_update", True)),
        manifest_url=(conf.get("update_manifest_url") or "").strip() or None,
    )

    def run_server() -> None:
        # threaded=True pour webview + API en parallèle
        linkora_app.app.run(
            host="127.0.0.1",
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    threading.Thread(target=run_server, daemon=True, name="linkora-flask").start()
    if not _wait_ready(port):
        # Fallback navigateur si le serveur ne répond pas
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{port}")
        # Garde le process vivant un peu
        while True:
            time.sleep(3600)

    try:
        import webview
    except ImportError:
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{port}")
        while True:
            time.sleep(3600)
        return

    def _window_icon() -> str | None:
        """WinForms exige un vrai .ico — un PNG fait planter System.Drawing.Icon."""
        try:
            from paths import resource_root

            for name in ("logo.ico", "icon.ico"):
                candidate = resource_root() / "static" / "img" / name
                if candidate.is_file():
                    return str(candidate)
        except Exception:
            pass
        return None

    def _open_browser_and_wait() -> None:
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{port}")
        while True:
            time.sleep(3600)

    window = webview.create_window(
        title="Linkora",
        url=f"http://127.0.0.1:{port}",
        width=1280,
        height=860,
        min_size=(900, 600),
        background_color="#0b1220",
        text_select=True,
    )
    icon = _window_icon()
    try:
        if icon:
            try:
                webview.start(icon=icon)
            except TypeError:
                webview.start()
        else:
            webview.start()
    except Exception:
        # Crash CLR / WebView → fallback navigateur plutôt que silence total
        _open_browser_and_wait()
        return

    # Fermeture de la fenêtre → fin du process
    sys.exit(0)


if __name__ == "__main__":
    # Mode helper MAJ : aucune UI, aucune console (exe windowed)
    if len(sys.argv) >= 4 and sys.argv[1] == "--linkora-updater":
        from update_helper import run_helper

        try:
            pid = int(sys.argv[3])
        except ValueError:
            raise SystemExit(1)
        raise SystemExit(run_helper(sys.argv[2], pid))

    main()
