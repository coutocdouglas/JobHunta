"""Buscador de vagas pessoal - interface local (Streamlit).

Rodar:  streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st

import db
import fontes
import paths
import pontuacao
import settings
import updater
from version import __version__

settings.carregar()
db.init()
st.set_page_config(page_title="JobHunta", page_icon="🔎", layout="wide")

# ---------------- Barra lateral: escolher / criar ambiente ----------------
st.sidebar.title("🔎 Ambientes de busca")
ambientes = db.listar_ambientes()
nomes = {a["nome"]: a["id"] for a in ambientes}

with st.sidebar.expander("➕ Novo ambiente"):
    novo = st.text_input("Nome (ex.: Arquitetura, Visualização 3D)")
    if st.button("Criar") and novo.strip():
        try:
            db.criar_ambiente(novo)
            st.rerun()
        except Exception:
            st.error("Já existe um ambiente com esse nome.")

escolhido = st.sidebar.radio("Ambiente", list(nomes)) if nomes else None

st.sidebar.divider()


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _checar_atualizacao():
    return updater.verificar()


nova = _checar_atualizacao()
if nova:
    st.sidebar.success(f"🆕 Versão {nova['versao']} disponível")
    with st.sidebar.expander("O que mudou"):
        st.write(nova["notas"] or "Sem notas.")
    if st.sidebar.button("⬇️ Atualizar agora", type="primary"):
        if not paths.is_frozen():
            st.sidebar.info("Modo desenvolvimento: a atualização automática só roda no programa instalado.")
        else:
            barra = st.sidebar.progress(0.0, text="Baixando atualização...")
            try:
                arquivo = updater.baixar(nova, lambda p: barra.progress(p, text="Baixando atualização..."))
                st.sidebar.info("Instalando... o JobHunta vai fechar e reabrir sozinho.")
                updater.instalar_e_sair(arquivo)
            except Exception as e:
                st.sidebar.error(f"Falha na atualização: {e}")

with st.sidebar.expander("🔑 Chaves de API"):
    with st.form("chaves"):
        entradas = {k: st.text_input(rot, value=os.getenv(k, ""), type="password")
                    for k, rot in settings.CHAVES.items()}
        if st.form_submit_button("Salvar chaves"):
            settings.salvar(entradas)
            st.success("Chaves salvas.")
            st.rerun()

st.sidebar.caption(f"JobHunta v{__version__}")
if paths.is_frozen() and st.sidebar.button("⏻ Sair do programa"):
    st.sidebar.info("Encerrando... pode fechar esta aba.")
    os._exit(0)
st.sidebar.caption("Gemini: " + ("✅ chave encontrada" if os.getenv("GEMINI_API_KEY")
                                 else "⚠️ sem chave (nota por palavras-chave)"))
st.sidebar.caption("Adzuna: " + ("✅" if os.getenv("ADZUNA_APP_ID") else "— não configurado"))
st.sidebar.caption("Jooble: " + ("✅" if os.getenv("JOOBLE_KEY") else "— não configurado"))

if not nomes:
    st.title("Bem-vindo ao JobHunta")
    st.info("Crie seu primeiro ambiente de busca na barra lateral (➕ Novo ambiente).")
    st.stop()

amb_id = nomes[escolhido]
amb = db.obter_ambiente(amb_id)

st.title(f"Ambiente: {escolhido}")
aba_vagas, aba_config = st.tabs(["📋 Vagas", "⚙️ Configuração e currículo"])

# ---------------- Aba de configuração ----------------
with aba_config:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("O que procurar")
        pc = st.text_area("Palavras-chave de busca (uma por linha)",
                          "\n".join(amb["palavras_chave"]), height=130,
                          help="Cada linha vira uma busca nas fontes. Ex.: arquiteto, projetista Revit")
        pe = st.text_area("Palavras para excluir (uma por linha)",
                          "\n".join(amb["palavras_excluir"]), height=80,
                          help="Vagas com essas palavras são descartadas. Ex.: estágio, vendedor")
        st.subheader("Requisitos")
        mods = st.multiselect("Modalidade aceita", db.MODALIDADES, amb["modalidades"])
        abr = st.multiselect("Abrangência", db.ABRANGENCIAS, amb["abrangencias"])
        cidade = st.text_input("Cidade (para presencial/híbrido; vazio = qualquer)", amb["cidade"])
    with c2:
        st.subheader("Currículo deste ambiente")
        pdf = st.file_uploader("Subir currículo em PDF (opcional)", type="pdf")
        curr = amb["curriculo"]
        if pdf is not None:
            from pypdf import PdfReader
            curr = "\n".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
            st.success("PDF lido. Revise o texto abaixo e salve.")
        curr = st.text_area("Texto do currículo", curr, height=260)
        port = st.text_area("Portfólio / observações (projetos, softwares, diferenciais)",
                            amb["portfolio"], height=130)

    b1, b2, _ = st.columns([1, 1, 4])
    if b1.button("💾 Salvar", type="primary"):
        db.salvar_ambiente(
            amb_id,
            palavras_chave=[x.strip() for x in pc.splitlines() if x.strip()],
            palavras_excluir=[x.strip() for x in pe.splitlines() if x.strip()],
            modalidades=mods, abrangencias=abr, cidade=cidade.strip(),
            curriculo=curr, portfolio=port,
        )
        st.success("Salvo.")
        st.rerun()
    if b2.button("🗑️ Excluir ambiente"):
        st.session_state["confirmar_excluir"] = True
    if st.session_state.get("confirmar_excluir"):
        st.warning("Isso apaga o ambiente e todas as vagas dele.")
        if st.button("Confirmar exclusão"):
            db.excluir_ambiente(amb_id)
            st.session_state["confirmar_excluir"] = False
            st.rerun()

# ---------------- Aba de vagas ----------------
with aba_vagas:
    if st.button("🔄 Buscar vagas agora", type="primary"):
        if not amb["palavras_chave"]:
            st.error("Defina ao menos uma palavra-chave na aba de configuração.")
        elif not amb["abrangencias"]:
            st.error("Escolha Brasil e/ou Internacional na configuração.")
        else:
            with st.status("Buscando...", expanded=True) as status:
                achadas, avisos = fontes.coletar(amb)
                existentes = db.uids_existentes(amb_id)
                novas = [v for v in achadas if v["uid"] not in existentes]
                st.write(f"{len(achadas)} vagas encontradas, {len(novas)} novas.")
                aceitas = []
                for v in novas:
                    v["modalidade"] = pontuacao.detectar_modalidade(v)
                    if pontuacao.passa_filtros(v, amb):
                        aceitas.append(v)
                st.write(f"{len(aceitas)} passaram nos seus requisitos. Pontuando...")
                barra = st.progress(0.0)
                for i, v in enumerate(aceitas):
                    v["nota"], v["justificativa"] = pontuacao.pontuar(v, amb)
                    db.inserir_vaga(amb_id, v)
                    barra.progress((i + 1) / max(1, len(aceitas)))
                status.update(label=f"Pronto: {len(aceitas)} vagas adicionadas.", state="complete")
            for a in avisos:
                st.warning(a)

    vagas = db.listar_vagas(amb_id)
    if not vagas:
        st.info("Nenhuma vaga ainda. Configure o ambiente e clique em buscar.")
    else:
        f1, f2, f3 = st.columns(3)
        nota_min = f1.slider("Nota mínima", 1, 10, 1)
        status_f = f2.multiselect("Status", ["nova", "interessa", "candidatei", "descartada"],
                                  ["nova", "interessa", "candidatei"])
        busca = f3.text_input("Filtrar por texto")
        vis = [v for v in vagas
               if (v["nota"] or 0) >= nota_min and v["status"] in status_f
               and (not busca or busca.lower() in f"{v['titulo']} {v['empresa']}".lower())]
        st.caption(f"{len(vis)} de {len(vagas)} vagas")

        for v in vis:
            cor = "🟢" if (v["nota"] or 0) >= 8 else "🟡" if (v["nota"] or 0) >= 5 else "🔴"
            with st.expander(f"{cor} {v['nota']}/10 — {v['titulo']} · {v['empresa']} "
                             f"· {v['modalidade']} · {v['fonte']}"):
                st.write(f"**Local:** {v['local'] or '—'}   |   **Data:** {v['data'] or '—'}")
                st.write(f"**Por que essa nota:** {v['justificativa']}")
                if v["link"]:
                    st.link_button("Abrir vaga", v["link"])
                st.write(v["descricao"][:1500] + ("..." if len(v["descricao"]) > 1500 else ""))
                novo_status = st.selectbox(
                    "Status", ["nova", "interessa", "candidatei", "descartada"],
                    index=["nova", "interessa", "candidatei", "descartada"].index(v["status"]),
                    key=f"st{v['id']}")
                if novo_status != v["status"]:
                    db.atualizar_status(v["id"], novo_status)
                    st.rerun()

        df = pd.DataFrame(vis)[["nota", "titulo", "empresa", "local", "modalidade",
                                "fonte", "link", "status"]] if vis else None
        if df is not None:
            st.download_button("⬇️ Exportar lista (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"vagas_{escolhido}.csv", mime="text/csv")
