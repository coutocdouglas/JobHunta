"""Coleta de vagas em fontes gratuitas e legítimas (APIs / feeds públicos).

Cada função devolve uma lista de dicts no formato padrão:
  uid, fonte, titulo, empresa, local, descricao, link, data
Falha de uma fonte nunca derruba as outras: o erro vai para a lista de avisos.
"""
import html
import os
import re

import requests

TIMEOUT = 20
HEADERS = {"User-Agent": "buscador-vagas-pessoal/1.0"}


def _limpar(texto):
    texto = html.unescape(texto or "")
    texto = re.sub(r"<[^>]+>", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


# ---------- Gupy (portal público de vagas, Brasil) ----------
def gupy(termo, limite=50):
    url = "https://portal.api.gupy.io/api/v1/jobs"
    r = requests.get(url, params={"jobName": termo, "limit": limite, "offset": 0},
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    saida = []
    for j in r.json().get("data", []):
        local = ", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)
        wp = (j.get("workplaceType") or "").lower()   # remote / hybrid / on-site
        if wp == "remote":
            local = f"Remoto - {local}" if local else "Remoto"
        elif wp == "hybrid":
            local = f"Híbrido - {local}" if local else "Híbrido"
        saida.append({
            "uid": f"gupy-{j.get('id')}",
            "fonte": "Gupy",
            "titulo": j.get("name", ""),
            "empresa": j.get("careerPageName", ""),
            "local": local,
            "descricao": _limpar(j.get("description", "")),
            "link": j.get("jobUrl", ""),
            "data": (j.get("publishedDate") or "")[:10],
        })
    return saida


# ---------- Remotive (vagas remotas, internacional) ----------
def remotive(termo, limite=50):
    r = requests.get("https://remotive.com/api/remote-jobs",
                     params={"search": termo, "limit": limite},
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return [{
        "uid": f"remotive-{j.get('id')}",
        "fonte": "Remotive",
        "titulo": j.get("title", ""),
        "empresa": j.get("company_name", ""),
        "local": "Remoto - " + (j.get("candidate_required_location") or "Mundo"),
        "descricao": _limpar(j.get("description", "")),
        "link": j.get("url", ""),
        "data": (j.get("publication_date") or "")[:10],
    } for j in r.json().get("jobs", [])]


# ---------- Arbeitnow (vagas Europa/remoto, API aberta) ----------
def arbeitnow(termo, limite=50):
    r = requests.get("https://www.arbeitnow.com/api/job-board-api",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    t = termo.lower()
    saida = []
    for j in r.json().get("data", []):
        texto = f"{j.get('title','')} {j.get('description','')}".lower()
        if t not in texto:
            continue
        saida.append({
            "uid": f"arbeitnow-{j.get('slug')}",
            "fonte": "Arbeitnow",
            "titulo": j.get("title", ""),
            "empresa": j.get("company_name", ""),
            "local": ("Remoto - " if j.get("remote") else "") + (j.get("location") or ""),
            "descricao": _limpar(j.get("description", "")),
            "link": j.get("url", ""),
            "data": "",
        })
        if len(saida) >= limite:
            break
    return saida


# ---------- Adzuna (agregador; precisa de chave gratuita) ----------
def adzuna(termo, pais="br", limite=50):
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return []
    r = requests.get(f"https://api.adzuna.com/v1/api/jobs/{pais}/search/1",
                     params={"app_id": app_id, "app_key": app_key, "what": termo,
                             "results_per_page": limite},
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return [{
        "uid": f"adzuna-{j.get('id')}",
        "fonte": "Adzuna",
        "titulo": _limpar(j.get("title", "")),
        "empresa": (j.get("company") or {}).get("display_name", ""),
        "local": (j.get("location") or {}).get("display_name", ""),
        "descricao": _limpar(j.get("description", "")),
        "link": j.get("redirect_url", ""),
        "data": (j.get("created") or "")[:10],
    } for j in r.json().get("results", [])]


# ---------- Jooble (agregador; precisa de chave gratuita) ----------
def jooble(termo, local="", limite=50):
    chave = os.getenv("JOOBLE_KEY")
    if not chave:
        return []
    r = requests.post(f"https://jooble.org/api/{chave}",
                      json={"keywords": termo, "location": local},
                      headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return [{
        "uid": f"jooble-{j.get('id')}",
        "fonte": "Jooble",
        "titulo": _limpar(j.get("title", "")),
        "empresa": j.get("company", ""),
        "local": j.get("location", ""),
        "descricao": _limpar(j.get("snippet", "")),
        "link": j.get("link", ""),
        "data": (j.get("updated") or "")[:10],
    } for j in r.json().get("jobs", [])[:limite]]


def coletar(ambiente):
    """Roda todas as fontes aplicáveis ao ambiente. Retorna (vagas, avisos)."""
    vagas, avisos = [], []
    br = "Brasil" in ambiente["abrangencias"]
    intl = "Internacional" in ambiente["abrangencias"]
    cidade = ambiente.get("cidade", "")

    for termo in ambiente["palavras_chave"]:
        tarefas = []
        if br:
            tarefas += [("Gupy", lambda t=termo: gupy(t)),
                        ("Adzuna", lambda t=termo: adzuna(t, "br")),
                        ("Jooble", lambda t=termo: jooble(t, cidade or "Brasil"))]
        if intl:
            tarefas += [("Remotive", lambda t=termo: remotive(t)),
                        ("Arbeitnow", lambda t=termo: arbeitnow(t)),
                        ("Jooble", lambda t=termo: jooble(t, ""))]
        for nome, fn in tarefas:
            try:
                vagas += fn()
            except Exception as e:  # uma fonte fora do ar não pode travar o resto
                avisos.append(f"{nome} ('{termo}'): {type(e).__name__} - {e}")

    unicas = {v["uid"]: v for v in vagas if v.get("uid") and v.get("titulo")}
    return list(unicas.values()), avisos
