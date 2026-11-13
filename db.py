"""Banco de dados local (SQLite). Cada 'ambiente' é um tipo de busca de vaga."""
import json
import sqlite3
import paths

DB_PATH = paths.data_dir() / "vagas.db"

MODALIDADES = ["Remoto", "Híbrido", "Presencial"]
ABRANGENCIAS = ["Brasil", "Internacional"]


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


# Cada item é uma migração. Para mudar o banco numa versão futura, ADICIONE um item
# no fim da lista (nunca edite os anteriores): o programa aplica só as que faltam.
MIGRACOES = [
    """
            CREATE TABLE IF NOT EXISTS ambientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                palavras_chave TEXT DEFAULT '[]',      -- JSON: termos de busca
                palavras_excluir TEXT DEFAULT '[]',    -- JSON: descarta vaga se tiver
                modalidades TEXT DEFAULT '[]',         -- JSON
                abrangencias TEXT DEFAULT '["Brasil"]',-- JSON
                cidade TEXT DEFAULT '',                -- opcional, p/ presencial/híbrido
                curriculo TEXT DEFAULT '',
                portfolio TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS vagas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ambiente_id INTEGER NOT NULL,
                uid TEXT NOT NULL,                     -- identificador único (dedupe)
                fonte TEXT, titulo TEXT, empresa TEXT, local TEXT,
                descricao TEXT, link TEXT, data TEXT,
                modalidade TEXT,                       -- detectada: Remoto/Híbrido/Presencial/?
                nota INTEGER,                          -- 1 a 10
                justificativa TEXT,
                status TEXT DEFAULT 'nova',            -- nova/interessa/candidatei/descartada
                UNIQUE(ambiente_id, uid)
            );
            """,
]


def init():
    with conn() as c:
        atual = c.execute("PRAGMA user_version").fetchone()[0]
        for n, script in enumerate(MIGRACOES[atual:], start=atual + 1):
            c.executescript(script)
            c.execute(f"PRAGMA user_version = {n}")


def _loads(v, default):
    try:
        return json.loads(v)
    except Exception:
        return default


def listar_ambientes():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM ambientes ORDER BY nome")]


def obter_ambiente(amb_id):
    with conn() as c:
        r = c.execute("SELECT * FROM ambientes WHERE id=?", (amb_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["palavras_chave"] = _loads(d["palavras_chave"], [])
    d["palavras_excluir"] = _loads(d["palavras_excluir"], [])
    d["modalidades"] = _loads(d["modalidades"], [])
    d["abrangencias"] = _loads(d["abrangencias"], [])
    return d


def criar_ambiente(nome):
    with conn() as c:
        cur = c.execute("INSERT INTO ambientes (nome) VALUES (?)", (nome.strip(),))
        return cur.lastrowid


def salvar_ambiente(amb_id, **campos):
    for k in ("palavras_chave", "palavras_excluir", "modalidades", "abrangencias"):
        if k in campos and not isinstance(campos[k], str):
            campos[k] = json.dumps(campos[k], ensure_ascii=False)
    sets = ", ".join(f"{k}=?" for k in campos)
    with conn() as c:
        c.execute(f"UPDATE ambientes SET {sets} WHERE id=?", (*campos.values(), amb_id))


def excluir_ambiente(amb_id):
    with conn() as c:
        c.execute("DELETE FROM vagas WHERE ambiente_id=?", (amb_id,))
        c.execute("DELETE FROM ambientes WHERE id=?", (amb_id,))


def uids_existentes(amb_id):
    with conn() as c:
        return {r[0] for r in c.execute("SELECT uid FROM vagas WHERE ambiente_id=?", (amb_id,))}


def inserir_vaga(amb_id, v):
    with conn() as c:
        c.execute(
            """INSERT OR IGNORE INTO vagas
               (ambiente_id, uid, fonte, titulo, empresa, local, descricao, link, data,
                modalidade, nota, justificativa)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (amb_id, v["uid"], v["fonte"], v["titulo"], v["empresa"], v["local"],
             v["descricao"], v["link"], v["data"], v["modalidade"],
             v.get("nota"), v.get("justificativa")),
        )


def listar_vagas(amb_id):
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM vagas WHERE ambiente_id=? ORDER BY COALESCE(nota,0) DESC, id DESC",
            (amb_id,))]


def atualizar_status(vaga_id, status):
    with conn() as c:
        c.execute("UPDATE vagas SET status=? WHERE id=?", (status, vaga_id))
