"""Componentes de interface reutilizados pelas páginas do Streamlit."""
from __future__ import annotations

import html
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from . import dados_abertos, indicadores_rreo, portal, rgf_estados, rreo_estados, siconfi, transformacoes
from . import fontes_dados as FD
from . import referencias as R
from .config import DIR_DADOS, LRF_URL, MCASP_URL, caminho
from .graficos import MESES, brl

RAIZ_APP = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ carga de dados
def _assinatura(pasta: Path = DIR_DADOS) -> str:
    """Muda sempre que algum arquivo de dados muda (invalida o cache).

    Vai como argumento *sem* "_" inicial: o st.cache_data ignora na chave os parâmetros que começam com "_"."""
    return ";".join(f"{p.name}:{p.stat().st_mtime_ns}:{p.stat().st_size}" for p in sorted(pasta.glob("*")) if p.is_file())


@st.cache_data(show_spinner="Carregando a MSC (Siconfi)…")
def _msc(assin: str):
    msc = siconfi.carregar_msc()
    transformacoes.definir_rotulos_receita(portal.arvore_receita_rotulos())
    return transformacoes.receitas_msc(msc), transformacoes.despesas_msc(msc), transformacoes.restos_a_pagar_msc(msc)


@st.cache_data(show_spinner="Carregando despesas por credor…")
def _credores(assin: str):
    return dados_abertos.carregar_despesas_credor()


@st.cache_data(show_spinner=False)
def _parquet(nome: str, assin: str) -> pd.DataFrame:
    arq = caminho(nome)
    return pd.read_parquet(arq) if arq.exists() else pd.DataFrame()


@st.cache_data(show_spinner=False)
def _relatorio(tipo: str, assin: str) -> pd.DataFrame:
    return siconfi.carregar_relatorio(tipo)


@st.cache_data(show_spinner=False)
def _glob(padrao: str, assin: str) -> pd.DataFrame:
    arqs = sorted(DIR_DADOS.glob(padrao))
    return pd.concat([pd.read_parquet(a) for a in arqs], ignore_index=True) if arqs else pd.DataFrame()


def receitas_msc():
    transformacoes.definir_rotulos_receita(portal.arvore_receita_rotulos())
    return _msc(_assinatura())[0]


def despesas_msc():
    return _msc(_assinatura())[1]


def rp_msc():
    return _msc(_assinatura())[2]


def credores():
    return _credores(_assinatura())


def parquet(nome: str) -> pd.DataFrame:
    return _parquet(nome, _assinatura())


def relatorio(tipo: str) -> pd.DataFrame:
    return _relatorio(tipo, _assinatura())


def glob(padrao: str) -> pd.DataFrame:
    return _glob(padrao, _assinatura())


def ipca() -> pd.DataFrame:
    return parquet("ipca.parquet")


# ------------------------------------------------------------------ RREO de todas as UFs
@st.cache_resource(show_spinner="Carregando o RREO de todas as UFs…", max_entries=1)
def _rreo_uf(assin: str) -> dict:
    """Base preparada, catálogo de linhas e RCL. cache_resource devolve o mesmo objeto (sem cópia a cada execução):
    trate como somente leitura."""
    bruto = rreo_estados.carregar()
    base, catalogo = rreo_estados.preparar(bruto)
    rcl_mes, rcl_rel = rreo_estados.rcl(bruto)
    return {"base": base, "catalogo": catalogo, "rcl_mes": rcl_mes, "rcl_rel": rcl_rel, "assin": assin,
            "indicadores": indicadores_rreo.calcular(bruto, rcl_rel)}


def assinatura_rreo_uf() -> str:
    return _assinatura(rreo_estados.DIR) if rreo_estados.DIR.exists() else ""


def rreo_uf() -> dict:
    return _rreo_uf(assinatura_rreo_uf())


@st.cache_resource(show_spinner="Carregando o RGF de todas as UFs…", max_entries=1)
def _rgf_uf(assin: str) -> dict:
    """Base preparada e catálogo de linhas do RGF de todas as UFs (somente leitura)."""
    bruto = rgf_estados.carregar()
    base, catalogo = rgf_estados.preparar(bruto)
    return {"base": base, "catalogo": catalogo, "lrf": rgf_estados.indicadores_lrf(bruto), "assin": assin}


def assinatura_rgf_uf() -> str:
    return _assinatura(rgf_estados.DIR) if rgf_estados.DIR.exists() else ""


def rgf_uf() -> dict:
    return _rgf_uf(assinatura_rgf_uf())


def entes_uf() -> pd.DataFrame:
    return rreo_estados.carregar_entes()


# ------------------------------------------------------------------ opções globais
def valores_reais() -> bool:
    return st.session_state.get("valores_reais", False)


def ajustar(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Aplica a opção global de valores reais (IPCA) quando marcada."""
    if valores_reais() and not df.empty and {"ano", "mes"} <= set(df.columns):
        return transformacoes.deflacionar(df, ipca(), colunas)
    return df


def legenda_valores() -> str:
    if valores_reais():
        ip = ipca()
        if ip.empty:
            return "Valores nominais (R$ correntes): o IPCA ainda não foi baixado; use Atualizar dados › IPCA."
        ref = f"{int(ip['mes'].iloc[-1]):02d}/{int(ip['ano'].iloc[-1])}"
        return f"Valores reais, a preços de {ref} (IPCA/IBGE, tabela 1737)."
    return "Valores nominais (R$ correntes)."


# ------------------------------------------------------------------ blocos de texto
def sigla(s: str, texto: str | None = None) -> str:
    """Sigla com a descrição do glossário em tooltip (HTML; use com unsafe_allow_html=True)."""
    d = R.GLOSSARIO.get(s, "")
    return f'<abbr title="{html.escape(d)}" style="cursor:help">{html.escape(texto or s)}</abbr>' if d else (texto or s)


def glossario(aberto: bool = False) -> None:
    with st.expander("🔤 Glossário de siglas", expanded=aberto):
        st.markdown("Passe o cursor sobre as siglas sublinhadas nos textos do painel para ver a descrição.")
        itens = sorted(R.GLOSSARIO.items(), key=lambda kv: kv[0].lower())
        meio = (len(itens) + 1) // 2
        cols = st.columns(2)
        for col, parte in zip(cols, (itens[:meio], itens[meio:])):
            col.markdown("\n".join(f"- **{k}** — {v}" for k, v in parte))


def base_legal(mcasp: list[str] = (), lrf: list[str] = (), extra: list[str] = (), aberto: bool = False,
               com_glossario: bool = True) -> None:
    if com_glossario:
        glossario()
    with st.expander("📘 Base normativa e conceitos", expanded=aberto):
        for k in mcasp:
            t, d = R.MCASP[k]
            st.markdown(f"- **[{t}]({MCASP_URL})** — {d}")
        for k in lrf:
            t, d = R.LRF[k]
            st.markdown(f"- **[{t}]({LRF_URL})** — {d}")
        for e in extra:
            st.markdown(f"- {e}")


def ajuda_fontes(*chaves: str) -> str:
    """Texto completo das fontes (URL, endpoint, parâmetros, arquivo) para tooltips."""
    return "\n\n---\n\n".join(FD.detalhe(c) for c in chaves)


def fonte(*chaves: str, nota: str | None = None, onde=None, valores: bool = True) -> None:
    """Legenda 'Fonte primária' sob um gráfico ou tabela; a tooltip traz URL, endpoint e arquivo."""
    partes = ["**Fonte primária:** " + "; ".join(FD.resumo(c) for c in chaves)]
    if nota:
        partes.append(nota)
    if valores:
        partes.append(legenda_valores())
    (onde or st).caption(" · ".join(partes), help=ajuda_fontes(*chaves), unsafe_allow_html=True)


def grafico(fig, chave: str, *fontes: str, onde=None, nota: str | None = None, valores: bool = True) -> None:
    """Gráfico Plotly seguido da sua fonte primária, no mesmo contêiner."""
    alvo = onde or st
    alvo.plotly_chart(fig, key=chave)
    if fontes:
        fonte(*fontes, nota=nota, onde=alvo, valores=valores)


def passos_msc(campos: str, nomes: str) -> list[str]:
    """Passos comuns às páginas que filtram a Matriz de Saldos Contábeis (MSC)."""
    n = len(list(DIR_DADOS.glob("msc6_*.parquet")))
    return [
        "**Coleta** (`python coletar.py --siconfi`): para cada mês que o Estado entregou ao Siconfi (lista do endpoint "
        "`/extrato_entregas`), o painel consulta a API `/msc_orcamentaria` em apidatalake.tesouro.gov.br "
        "(id_ente=50, matriz agregada MSCC, classe de contas 6, movimento do mês). A resposta vem em JSON.",
        f"**Campos usados**: {campos}. A MSC traz **códigos**, não nomes.",
        f"**Gravação**: um arquivo por mês em `dados/dashboard/msc6_AAAA_MM.parquet` (hoje, {n} meses).",
        f"**Nomes**: {nomes}",
        "**Montagem das opções**: cada filtro de múltipla escolha lista os valores distintos do campo em todos os meses "
        "carregados, em ordem alfabética. Como o código vem antes do nome, a ordem é a do código.",
    ]


def explicar_filtros(origem: str, passos: list[str], filtros: list[tuple[str, str]], cuidados: list[str] = (),
                     fontes: tuple[str, ...] = (), nota: str | None = None, titulo: str = "De onde vêm as opções dos filtros",
                     ipca: bool = True) -> None:
    """Acordeão padrão que explica a origem das opções de cada filtro: fonte, passos, tabela e cuidados."""
    cuidados = list(cuidados)
    if ipca:
        cuidados.append("**Valores reais (IPCA)**, na barra lateral, não muda as opções: só corrige os valores pela "
                        "inflação até o último mês divulgado.")
    md = [f"**Fonte.** {origem}", "", "**Do dado ao filtro**"]
    md += [f"{i}. {p}" for i, p in enumerate(passos, 1)]
    md += ["", "**Filtro por filtro**", "", "| Filtro | Origem das opções |", "|---|---|"]
    md += [f"| {f} | {o} |" for f, o in filtros]
    if cuidados:
        md += ["", "**Cuidados**"] + [f"- {c}" for c in cuidados]
    with st.expander(f"ℹ️ {titulo}", expanded=False):
        st.markdown("\n".join(md))
        if fontes:
            fonte(*fontes, nota=nota, valores=False)


def sem_dados(o_que: str, comando: str) -> None:
    st.info(f"Ainda não há dados de **{o_que}**. Rode `{comando}` na pasta `dashboard/` "
            "ou use **Atualizar dados** na barra lateral.", icon="ℹ️")


# ------------------------------------------------------------------ tabelas
MAX_LINHAS_TABELA = 2000
_MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'


def _numero(v, casas: int = 2) -> str:
    if v is None or pd.isna(v):
        return "–"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _html_tabela(d: pd.DataFrame, moeda: set, pct: set, altura: int) -> str:
    escuro = getattr(getattr(st.context, "theme", None), "type", "light") == "dark"
    fundo_cab = "#262730" if escuro else "#f0f2f6"
    numericas = {c for c in d.columns if c in moeda or c in pct or pd.api.types.is_float_dtype(d[c])}
    cab = "".join(f'<th class="{"n" if c in numericas else ""}">'
                  f'{html.escape(str(c) if c not in pct or "%" in str(c) else f"{c} (%)")}</th>' for c in d.columns)
    linhas = []
    for row in d.itertuples(index=False):
        cel = []
        for c, v in zip(d.columns, row):
            if c in numericas:
                cel.append(f'<td class="n">{_numero(v)}</td>')
            else:
                cel.append(f"<td>{html.escape('' if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v))}</td>")
        linhas.append("<tr>" + "".join(cel) + "</tr>")
    return f"""<div class="tab-ms" style="max-height:{altura}px">
<style>
.tab-ms {{overflow:auto; border:1px solid rgba(128,128,128,.3); border-radius:6px; margin-bottom:.5rem}}
.tab-ms table {{border-collapse:collapse; width:100%; font-size:13px}}
.tab-ms th {{position:sticky; top:0; z-index:1; background:{fundo_cab}; text-align:left; padding:6px 10px;
  font-weight:600; border-bottom:1px solid rgba(128,128,128,.4); white-space:nowrap}}
.tab-ms td {{font-family:{_MONO}; padding:4px 10px; border-bottom:1px solid rgba(128,128,128,.15); white-space:nowrap}}
.tab-ms tbody tr:nth-child(even) td {{background:rgba(128,128,128,.06)}}
.tab-ms .n {{text-align:right; font-variant-numeric:tabular-nums}}
</style>
<table><thead><tr>{cab}</tr></thead><tbody>{"".join(linhas)}</tbody></table></div>"""


def tabela(df: pd.DataFrame, chave: str, moeda: list[str] = (), pct: list[str] = (), altura: int | None = None,
           ordenar_padrao: str | None = None, fontes: tuple[str, ...] | list[str] = (), nota: str | None = None) -> None:
    """Tabela com ordenação por coluna, números com duas casas decimais, linhas em fonte monoespaçada e CSV."""
    if df.empty:
        st.caption("Sem linhas para os filtros escolhidos.")
        return
    c1, c2, c3 = st.columns([3, 1.2, 1])
    original = "(ordem original)"
    cols = [original, *df.columns]
    padrao = ordenar_padrao if ordenar_padrao in cols else (moeda[0] if moeda else original)
    por = c1.selectbox("Ordenar por coluna", cols, index=cols.index(padrao), key=f"ord_{chave}",
                       help="Escolha a coluna que define a ordem das linhas e, ao lado, o sentido. Colunas numéricas "
                            "ordenam pelo valor; colunas de texto, em ordem alfabética. '(ordem original)' mantém a "
                            "ordem em que a tabela foi montada (por exemplo, a ordem das linhas no relatório oficial). "
                            "A ordenação também vale para o CSV baixado.")
    desc = c2.radio("Sentido", ["Decrescente", "Crescente"], horizontal=True, key=f"sent_{chave}",
                    index=0 if por != original else 1) == "Decrescente"
    d = df if por == original else df.sort_values(por, ascending=not desc, kind="stable")
    if por == original and desc:
        d = d.iloc[::-1]
    c3.download_button("⬇️ CSV", d.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       file_name=f"{chave}.csv", mime="text/csv", key=f"dl_{chave}", width="stretch")
    mostra = d.head(MAX_LINHAS_TABELA)
    st.html(_html_tabela(mostra, set(moeda), set(pct), altura or min(640, 44 + 29 * len(mostra))))
    if len(d) > MAX_LINHAS_TABELA:
        st.caption(f"Exibindo as primeiras {MAX_LINHAS_TABELA:,} de {len(d):,} linhas, na ordem escolhida; "
                   "o CSV traz todas.".replace(",", "."))
    if fontes:
        fonte(*fontes, nota=nota)


def metrica(col, rotulo: str, valor: float, comparacao: float | None = None, ajuda: str | None = None, fmt=brl,
            vs: str | None = None):
    """`vs` diz com que período a variação é calculada (ex.: 'jan a ago/2025')."""
    delta = None
    if comparacao not in (None, 0) and not pd.isna(comparacao):
        delta = f"{(valor / comparacao - 1) * 100:+.1f}%".replace(".", ",") + (f" vs {vs}" if vs else "")
    col.metric(rotulo, fmt(valor), delta, help=ajuda)


def periodo(df: pd.DataFrame, somados: bool = True) -> str:
    """Meses presentes nos dados, por exercício: 'jan a ago/2026' ou 'jan a dez/2025 + jan a ago/2026'."""
    if df.empty or not {"ano", "mes"} <= set(df.columns):
        return ""
    m = df.groupby("ano")["mes"].agg(["min", "max"])
    txt = " + ".join(f"{MESES[int(a) - 1]}/{ano}" if a == b else f"{MESES[int(a) - 1]} a {MESES[int(b) - 1]}/{ano}"
                     for ano, (a, b) in m.iterrows())
    return txt + (" (exercícios somados)" if somados and len(m) > 1 else "")


def filtro_multiplo(container, rotulo: str, opcoes, chave: str, padrao=None):
    opcoes = sorted([o for o in pd.unique(pd.Series(opcoes).dropna().astype(str)) if o != ""])
    return container.multiselect(rotulo, opcoes, default=padrao or [], key=chave, placeholder="Todos")


def aplicar_filtro(df: pd.DataFrame, col: str, valores: list) -> pd.DataFrame:
    return df[df[col].astype(str).isin(valores)] if valores else df


# ------------------------------------------------------------------ status e coleta
def status_fontes() -> pd.DataFrame:
    linhas = []

    def _f(nome, padrao, periodicidade, origem):
        arqs = sorted(DIR_DADOS.glob(padrao))
        if not arqs:
            linhas.append((nome, origem, periodicidade, "—", "não coletado"))
            return
        ult = max(a.stat().st_mtime for a in arqs)
        ref = max(arqs, key=lambda a: [int(x) if x.isdigit() else 0 for x in a.stem.split("_")]).stem
        ref = "_".join(x for x in ref.split("_") if x.isdigit()) or "—"
        linhas.append((nome, origem, periodicidade, ref, datetime.fromtimestamp(ult).strftime("%d/%m/%Y %H:%M")))

    m = portal.meta()
    linhas.append(("Portal da Transparência (Playwright)", "CGE/SEFAZ-MS", "Diária",
                   m.get("data_referencia", "—"), (m.get("coletado_em", "não coletado") or "").replace("T", " ")))
    _f("MSC – Matriz de Saldos Contábeis", "msc6_*.parquet", "Mensal", "Siconfi/STN")
    _f("Despesas por credor", "credor_*.parquet", "Mensal", "dados.ms.gov.br (SEFAZ)")
    _f("Repasses a municípios", "repasses_municipios.parquet", "Mensal", "dados.ms.gov.br (SEFAZ)")
    _f("RREO", "rreo_*.parquet", "Bimestral", "Siconfi/STN")
    _f("RGF", "rgf_*.parquet", "Quadrimestral", "Siconfi/STN")
    _f("RREO de todas as UFs", "rreo_estados/rreo_uf_*.parquet", "Bimestral", "Siconfi/STN")
    _f("RGF de todas as UFs", "rgf_estados/rgf_uf_*.parquet", "Quadrimestral", "Siconfi/STN")
    ip = ipca()
    linhas.append(("IPCA", ip["fonte"].iat[0] if "fonte" in ip and not ip.empty else "IBGE", "Mensal",
                   f"{int(ip['mes'].iat[-1]):02d}/{int(ip['ano'].iat[-1])}" if not ip.empty else "—",
                   datetime.fromtimestamp(caminho("ipca.parquet").stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                   if caminho("ipca.parquet").exists() else "não coletado"))
    return pd.DataFrame(linhas, columns=["Base", "Origem", "Periodicidade", "Último período", "Atualizado em"])


def executar_coleta(args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, str(RAIZ_APP / "coletar.py"), *args]
    try:
        p = subprocess.run(cmd, cwd=RAIZ_APP, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired as e:
        return 124, f"Tempo esgotado (1 h).\n{(e.stdout or '')[-3000:]}"
    return p.returncode, (p.stdout + "\n" + p.stderr)[-4000:]


def em_nuvem() -> bool:
    """True no Streamlit Community Cloud (o repositório é montado em /mount/src)."""
    return str(RAIZ_APP).startswith("/mount/src") or os.environ.get("STREAMLIT_SHARING_MODE") is not None


def playwright_disponivel() -> bool:
    """Playwright instalado e com o Chromium baixado (python -m playwright install chromium)."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    pasta = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or Path.home() / ".cache" / "ms-playwright")
    return any(pasta.glob("chromium*"))


def extrato() -> pd.DataFrame:
    return parquet("siconfi_extrato.parquet")


def json_meta() -> str:
    return json.dumps(portal.meta(), ensure_ascii=False)
