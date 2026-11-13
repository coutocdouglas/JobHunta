"""Atualização dentro do programa, via GitHub Releases.

Fluxo: consulta a última Release -> se a versão for maior, baixa JobHunta-Setup.exe,
confere o SHA-256 publicado junto, e executa o instalador em modo silencioso
(instalação por usuário, sem pedir administrador). Os dados do usuário ficam em
paths.data_dir() e não são tocados.
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests

import paths
from version import REPO, __version__

HOSTS_OK = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
HEADERS = {"User-Agent": f"JobHunta/{__version__}", "Accept": "application/vnd.github+json"}


def _tup(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def _host_confiavel(url):
    h = urlparse(url).hostname or ""
    return urlparse(url).scheme == "https" and (h in HOSTS_OK or h.endswith(".githubusercontent.com"))


def verificar():
    """Retorna dict com a versão nova (versao, notas, url, sha_url) ou None se está em dia.
    Qualquer falha de rede devolve None: atualização nunca pode impedir o uso do programa."""
    try:
        r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest",
                         headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        rel = r.json()
        if _tup(rel["tag_name"]) <= _tup(__version__):
            return None
        ativos = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
        setup = next((u for n, u in ativos.items() if n.lower().endswith("setup.exe")), None)
        if not setup or not _host_confiavel(setup):
            return None
        sha = next((u for n, u in ativos.items() if n.lower().endswith(".sha256")), None)
        return {"versao": rel["tag_name"].lstrip("v"), "notas": rel.get("body") or "",
                "url": setup, "sha_url": sha}
    except Exception:
        return None


def baixar(info, progresso=None) -> Path:
    """Baixa o instalador e confere o SHA-256. Levanta exceção se algo não bater."""
    destino = Path(tempfile.mkdtemp(prefix="jobhunta-up-")) / "JobHunta-Setup.exe"
    h = hashlib.sha256()
    with requests.get(info["url"], headers=HEADERS, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        feito = 0
        with open(destino, "wb") as f:
            for bloco in r.iter_content(1024 * 256):
                f.write(bloco)
                h.update(bloco)
                feito += len(bloco)
                if progresso and total:
                    progresso(feito / total)
    if info.get("sha_url") and _host_confiavel(info["sha_url"]):
        esperado = requests.get(info["sha_url"], headers=HEADERS, timeout=15).text.split()[0].lower()
        if esperado != h.hexdigest():
            destino.unlink(missing_ok=True)
            raise RuntimeError("Arquivo baixado não confere com o SHA-256 publicado.")
    return destino


def instalar_e_sair(instalador: Path):
    """Roda o instalador silencioso e encerra o programa para liberar os arquivos.
    O instalador reabre o JobHunta ao terminar."""
    if os.name != "nt" or not paths.is_frozen():
        raise RuntimeError("A atualização automática só funciona no programa instalado (Windows).")
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([str(instalador), "/SILENT", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     creationflags=flags, close_fds=True)
    os._exit(0)
