"""Filtros por requisito (modalidade, exclusões) e nota 1-10 via Gemini.

Se não houver chave do Gemini (ou a chamada falhar), usa uma nota por palavras-chave,
então o programa continua funcionando sem IA.
"""
import json
import os
import re
import time

import requests

MODELO = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"


def _norm(s):
    return (s or "").lower()


def detectar_modalidade(vaga):
    t = _norm(f"{vaga['titulo']} {vaga['local']} {vaga['descricao'][:1500]}")
    if re.search(r"h[ií]brid|hybrid", t):
        return "Híbrido"
    if re.search(r"remot|home ?office|anywhere|work from home|trabalho a dist", t):
        return "Remoto"
    if re.search(r"presencial|on-?site|in-?office", t):
        return "Presencial"
    return "?"


def passa_filtros(vaga, amb):
    """Aplica os requisitos do ambiente. Modalidade desconhecida passa (a IA avalia)."""
    texto = _norm(f"{vaga['titulo']} {vaga['descricao']}")
    if any(_norm(x) in texto for x in amb["palavras_excluir"] if x.strip()):
        return False
    mods = amb["modalidades"]
    if mods and vaga["modalidade"] != "?" and vaga["modalidade"] not in mods:
        return False
    # Presencial/híbrido com cidade definida: exige a cidade, exceto vaga remota
    cidade = _norm(amb.get("cidade"))
    if cidade and vaga["modalidade"] in ("Presencial", "Híbrido"):
        if cidade not in _norm(f"{vaga['local']} {vaga['descricao'][:800]}"):
            return False
    return True


def nota_por_palavras(vaga, amb):
    """Plano B sem IA: proporção de palavras-chave do ambiente presentes na vaga."""
    termos = [_norm(x) for x in amb["palavras_chave"] if x.strip()]
    if not termos:
        return 5, "Sem IA: nenhuma palavra-chave definida."
    texto = _norm(f"{vaga['titulo']} {vaga['descricao']}")
    achou = [t for t in termos if t in texto]
    na_titulo = sum(1 for t in termos if t in _norm(vaga["titulo"]))
    nota = 1 + round(7 * len(achou) / len(termos)) + min(2, na_titulo)
    return max(1, min(10, nota)), f"Sem IA: {len(achou)}/{len(termos)} palavras-chave presentes."


def _prompt(vaga, amb):
    return f"""Você avalia o quanto uma vaga combina com um candidato.

CURRÍCULO DO CANDIDATO:
{amb['curriculo'][:6000]}

PORTFÓLIO / OBSERVAÇÕES:
{amb['portfolio'][:2000]}

VAGA:
Título: {vaga['titulo']}
Empresa: {vaga['empresa']}
Local: {vaga['local']}
Descrição: {vaga['descricao'][:4000]}

Dê uma nota inteira de 1 a 10 (10 = encaixe quase perfeito com requisitos e experiência;
5 = parcial; 1 = nada a ver). Considere requisitos obrigatórios que o candidato não cumpre.
Responda SOMENTE JSON: {{"nota": <1-10>, "justificativa": "<até 25 palavras, em português>"}}"""


def nota_gemini(vaga, amb, chave):
    r = requests.post(
        GEMINI_URL.format(m=MODELO),
        params={"key": chave},
        json={
            "contents": [{"parts": [{"text": _prompt(vaga, amb)}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        },
        timeout=60,
    )
    r.raise_for_status()
    texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    d = json.loads(texto)
    return max(1, min(10, int(d["nota"]))), str(d.get("justificativa", ""))[:300]


def pontuar(vaga, amb):
    chave = os.getenv("GEMINI_API_KEY")
    if chave and amb["curriculo"].strip():
        for tentativa in range(3):
            try:
                return nota_gemini(vaga, amb, chave)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    time.sleep(8 * (tentativa + 1))  # limite por minuto: espera e tenta de novo
                    continue
                break
            except Exception:
                break
    return nota_por_palavras(vaga, amb)
