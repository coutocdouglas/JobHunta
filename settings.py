"""Chaves de API guardadas em um .env na pasta de dados do usuário."""
import os

import paths

CHAVES = {
    "GEMINI_API_KEY": "Gemini (nota 1-10 por IA)",
    "ADZUNA_APP_ID": "Adzuna - App ID (opcional)",
    "ADZUNA_APP_KEY": "Adzuna - App Key (opcional)",
    "JOOBLE_KEY": "Jooble (opcional)",
}


def _arquivo():
    return paths.data_dir() / ".env"


def carregar():
    """Lê o .env para os.environ. O arquivo vale mais que variáveis antigas do sistema."""
    p = _arquivo()
    if not p.exists():
        return
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            if v.strip():
                os.environ[k.strip()] = v.strip().strip('"')


def salvar(valores: dict):
    """Grava só os campos preenchidos; campo vazio remove a chave."""
    atuais = {}
    p = _arquivo()
    if p.exists():
        for linha in p.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                atuais[k.strip()] = v.strip()
    for k, v in valores.items():
        v = (v or "").strip()
        if v:
            atuais[k] = v
            os.environ[k] = v
        else:
            atuais.pop(k, None)
            os.environ.pop(k, None)
    p.write_text("\n".join(f"{k}={v}" for k, v in atuais.items()) + "\n", encoding="utf-8")
