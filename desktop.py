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
    """Nettoie d’anciens helpers TEMP et les staging MAJ orphelins."""
    try:
        tmp = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".")
        for pattern in (
            "linkora-apply-*.bat",
            "linkora-apply-*.ps1",
            "linkora-apply-*.vbs",
            "linkora-upd-*",
        ):
            for path in tmp.glob(pattern):
                try:
                    if path.is_dir():
                        import shutil

                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        path.unlink(missing_ok=True)
                except OSError:
                    pass
    except Exception:
        pass
    try:
        import updater

        updater.cleanup_stale_update_dirs()
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

    updater.ensure_runtime_dirs()

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

    def _open_browser_and_wait() -> None:
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{port}")
        while True:
            time.sleep(3600)

    webview.create_window(
        title="Linkora",
        url=f"http://127.0.0.1:{port}",
        width=1280,
        height=860,
        min_size=(900, 600),
        background_color="#0b1220",
        text_select=True,
    )
    # Ne PAS passer icon= à webview.start() : WinForms charge l’icône sur un
    # thread CLR — ArgumentException → popup d’erreur Windows qui disparaît.
    # L’icône de la fenêtre vient déjà de Linkora.exe (PyInstaller).
    try:
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
        install_dir = sys.argv[4] if len(sys.argv) >= 5 else None
        raise SystemExit(run_helper(sys.argv[2], pid, install_dir))

    main()
