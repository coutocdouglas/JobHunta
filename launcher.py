"""Ponto de entrada do executável: sobe o servidor local e abre o navegador.

Variável JOBHUNTA_SMOKE=1: modo de teste (usado no CI) - sobe, confere a saúde do servidor e sai.
"""
import os
import socket
import sys
import threading
import time
import webbrowser

import paths

PORTA = int(os.getenv("JOBHUNTA_PORT", "8765"))
URL = f"http://127.0.0.1:{PORTA}"


def _redirecionar_saida():
    """Sem console (janela oculta) stdout/stderr são None e o Streamlit quebraria ao logar."""
    log = open(paths.data_dir() / "jobhunta.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = log
    if sys.stderr is None:
        sys.stderr = log


def _porta_em_uso():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORTA)) == 0


def _smoke():
    import urllib.request
    limite = time.time() + 90
    while time.time() < limite:
        try:
            with urllib.request.urlopen(URL + "/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    print("SMOKE OK", flush=True)
                    os._exit(0)
        except Exception:
            time.sleep(1)
    print("SMOKE FALHOU", flush=True)
    os._exit(1)


def main():
    _redirecionar_saida()

    # Os módulos são importados aqui para o PyInstaller incluí-los no pacote
    # (app.py é lido como arquivo de dados e não é analisado).
    import db, fontes, pontuacao, settings, updater, version  # noqa: F401

    smoke = os.getenv("JOBHUNTA_SMOKE") == "1"
    if _porta_em_uso():          # já está aberto: só traz a janela do navegador
        if not smoke:
            webbrowser.open(URL)
        return

    from streamlit.web import bootstrap

    flags = {
        "server.headless": True,
        "server.address": "127.0.0.1",
        "server.port": PORTA,
        "server.fileWatcherType": "none",
        "browser.gatherUsageStats": False,
        "global.developmentMode": False,
    }
    bootstrap.load_config_options(flag_options=flags)
    if smoke:
        threading.Thread(target=_smoke, daemon=True).start()
    else:
        threading.Timer(2.0, webbrowser.open, args=[URL]).start()
    bootstrap.run(str(paths.resource_dir() / "app.py"), False, [], flags)


if __name__ == "__main__":
    main()
