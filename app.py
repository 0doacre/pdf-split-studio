"""
Point d'entrée principal de PDF Split & Merge Studio.
Lance le serveur local et affiche l'application soit dans une fenêtre native (pywebview)
soit dans le navigateur web par défaut.
100% Hors-ligne, confidentiel et sécurisé.
"""

import os
import sys
import time
import socket
import threading
import webbrowser
import uvicorn

# Assurer l'encodage UTF-8 pour la console Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Ajouter le répertoire racine au PYTHONPATH
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from backend.server import app


def find_free_port(start_port: int = 48120, max_attempts: int = 100) -> int:
    """Trouve un port TCP libre sur localhost."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


def start_uvicorn(port: int):
    """Démarre le serveur Uvicorn local."""
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()


def main():
    use_browser = "--web" in sys.argv or "--browser" in sys.argv
    port = find_free_port(48120)
    url = f"http://127.0.0.1:{port}"

    # Démarrage du serveur backend en tâche de fond
    server_thread = threading.Thread(target=start_uvicorn, args=(port,), daemon=True)
    server_thread.start()

    # Attente brève que le serveur soit prêt
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.1)

    print("=" * 65)
    print("   [PDF SPLIT & MERGE STUDIO] - 100% HORS-LIGNE & SECURISE")
    print(f"   Serveur actif sur : {url}")
    print("=" * 65)

    if use_browser:
        print("Ouverture dans le navigateur par défaut...")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nArrêt de l'application.")
            sys.exit(0)

    # Essayer de lancer avec pywebview en mode fenêtre de bureau native
    try:
        import webview
        print("Lancement de la fenêtre de bureau native...")
        window = webview.create_window(
            title="PDF Split & Merge Studio",
            url=url,
            width=1280,
            height=860,
            min_size=(980, 680),
            background_color="#0b0f19"
        )
        webview.start(debug=False)
    except Exception as e:
        print(f"Mode natif non disponible ({e}), bascule sur le navigateur par défaut...")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nArrêt de l'application.")
            sys.exit(0)


if __name__ == "__main__":
    main()
