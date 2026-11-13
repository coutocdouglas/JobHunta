# JobHunta

Buscador de vagas pessoal e gratuito para Windows. Você cria **ambientes** (um por tipo de vaga),
cada um com currículo, portfólio, palavras-chave e requisitos (remoto/híbrido/presencial,
Brasil/internacional). O programa busca em fontes gratuitas e dá nota de 1 a 10 comparando cada
vaga com o currículo do ambiente.

## Instalar
Baixe `JobHunta-Setup.exe` na página de [Releases](../../releases/latest) e execute.
A instalação é por usuário (não pede administrador). Depois, dentro do programa:
**🔑 Chaves de API** para colar sua chave do Gemini (Adzuna e Jooble são opcionais).

## Atualizar
Dentro do programa aparece **🆕 Versão X disponível** na barra lateral; clique em **Atualizar agora**.
Currículos, vagas e chaves ficam em `%APPDATA%\JobHunta` e não são afetados.

## Fontes
Gupy, Remotive e Arbeitnow (sem chave); Adzuna e Jooble (chaves gratuitas, opcionais).
LinkedIn e Indeed: use alertas por e-mail dos próprios sites.

## Lançar uma versão nova (desenvolvimento)
```
git tag v0.2.0
git push origin v0.2.0
```
O GitHub Actions compila, testa o executável, gera `JobHunta-Setup.exe` e publica a Release.
Mudanças no banco: adicione um item no fim de `MIGRACOES` em `db.py`.

## Rodar sem instalar (dev)
```
pip install -r requirements.txt
streamlit run app.py
```
