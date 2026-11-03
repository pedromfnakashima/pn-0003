"""RREO › aba Anexos: evolução mensal de todos os anexos do RREO das 27 UFs, com comparações entre Estados e
dentro de um Estado, em valores brutos ou como % da Receita Corrente Líquida."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import rreo_estados as RE
from ms_fiscal import ui

ANEXOS = {
    "RREO-Anexo 01": "Balanço Orçamentário",
    "RREO-Anexo 02": "Despesa por função e subfunção",
    "RREO-Anexo 03": "Receita Corrente Líquida",
    "RREO-Anexo 04": "Receitas e despesas previdenciárias (RPPS)",
    "RREO-Anexo 06": "Resultados primário e nominal",
    "RREO-Anexo 07": "Restos a pagar por Poder e órgão",
    "RREO-Anexo 08": "Manutenção e desenvolvimento do ensino (MDE)",
    "RREO-Anexo 09": "Operações de crédito e despesas de capital",
    "RREO-Anexo 10 - RPPS": "Projeção atuarial do RPPS",
    "RREO-Anexo 11": "Alienação de ativos",
    "RREO-Anexo 12": "Ações e serviços públicos de saúde (ASPS)",
    "RREO-Anexo 13": "Parcerias público-privadas",
    "RREO-Anexo 14": "Demonstrativo simplificado",
}
REGIOES = {"NO": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "SU": "Sul"}
SIGLA_REGIAO = {"Norte": "N", "Nordeste": "NE", "Centro-Oeste": "CO", "Sudeste": "SE", "Sul": "S"}
UFS_PADRAO = ["MS", "MT", "GO", "DF", "PR"]
UNIDADES = ["R$ (valor bruto)", "% da RCL"]
MAX_SERIES = 8


@st.cache_data(show_spinner="Montando a série…", max_entries=64)
def _serie(assin: str, anexo: str, linhas: tuple[str, ...], coluna: str, modo: str | None) -> pd.DataFrame:
    d = ui.rreo_uf()
    return RE.serie(d["base"], d["rcl_mes"], d["rcl_rel"], anexo, list(linhas), coluna, modo)


@st.cache_data(show_spinner=False, max_entries=256)
def _colunas(assin: str, anexo: str, linha: str) -> list[str]:
    b = ui.rreo_uf()["base"]
    cols = list(dict.fromkeys(b.loc[(b["anexo"] == anexo) & (b["linha"] == linha), "coluna"].astype(str)))
    mr = [c for c in cols if c.startswith("<MR")]
    return ([RE.MENSAL] if mr else []) + [c for c in cols if not c.startswith("<MR")]


def _escolher(onde, rotulo: str, opcoes: list, key: str, padrao=None, **kw):
    """selectbox que volta ao padrão quando a opção guardada deixa de existir (ex.: troca de anexo)."""
    if key in st.session_state and st.session_state[key] not in opcoes:
        del st.session_state[key]
    idx = opcoes.index(padrao) if padrao in opcoes else 0
    return onde.selectbox(rotulo, opcoes, index=idx, key=key, **kw)


def _rotulos(cat: pd.DataFrame) -> dict[str, str]:
    """Texto de cada linha: conta (+ quadro, se não for 'Padrão'); o código entra quando o texto se repete."""
    base = cat.apply(lambda r: r["conta"].strip() + ("" if r["rotulo"] in ("Padrão", "nan") else f" — {r['rotulo']}"),
                     axis=1)
    rep = base.duplicated(keep=False)
    txt = base.where(~rep, base + " [" + cat["cod_conta"].str[:45] + "]")
    return {ln: f"{t}  ·  {n} UF{'s' if n > 1 else ''}" for ln, t, n in zip(cat["linha"], txt, cat["n_ufs"])}


def _curto(txt: str, n: int = 55) -> str:
    t = txt.split("  ·  ")[0]
    return t if len(t) <= n else t[: n - 1] + "…"


def _cores_estaveis(chave: str, itens: list[str]) -> dict[str, str]:
    """A cor acompanha a entidade: quem entra pega a primeira cor livre; quem sai libera a sua."""
    atual = {k: v for k, v in st.session_state.get(chave, {}).items() if k in itens}
    livres = [c for c in G.CORES if c not in atual.values()]
    for i in itens:
        if i not in atual and livres:
            atual[i] = livres.pop(0)
    st.session_state[chave] = atual
    return atual


def _eixo(fig: go.Figure, pct: bool, moeda: bool) -> go.Figure:
    if pct:
        fig.update_yaxes(ticksuffix="%", tickformat=",.1f")
        fig.update_traces(hovertemplate="%{y:,.2f}%")
    elif moeda:
        G.eixo_moeda(fig)
    return fig


def _linhas(df: pd.DataFrame, cor: str, y: str, titulo: str, cores: dict, pct: bool, moeda: bool,
            ordem: list[str] | None = None, marcadores: bool = True, altura: int = 440) -> go.Figure:
    fig = G.linhas(df, "data", y, cor, titulo, altura=altura, cores=cores, ordem=ordem, marcadores=marcadores,
                   moeda=moeda and not pct)
    if (df[y].dropna() >= 0).all():  # eixo a partir de zero: evita ampliar ruído (ex.: RCL ÷ RCL = 100%)
        fig.update_yaxes(rangemode="tozero")
    return _eixo(fig, pct, moeda)


def render() -> None:
    dados = ui.rreo_uf()
    base, cat = dados["base"], dados["catalogo"]
    if base.empty:
        ui.sem_dados("RREO de todas as UFs", "python coletar.py --rreo-estados")
        return
    assin = dados["assin"]
    entes = ui.entes_uf()
    regiao = dict(zip(entes["uf"], entes["regiao"].map(REGIOES))) if not entes.empty else {}
    todas_ufs = sorted(base["uf"].astype(str).unique())
    ex = base[["exercicio", "periodo"]].drop_duplicates().sort_values(["exercicio", "periodo"])
    a0, b0 = ex.iloc[0]
    a1, b1 = ex.iloc[-1]
    st.markdown(f"**RREO das {len(todas_ufs)} UFs (26 Estados e DF), do {b0}º bimestre de {a0} ao {b1}º bimestre "
                f"de {a1}.** Escolha o anexo, a linha e a coluna do demonstrativo; os gráficos mostram a série mensal, "
                "comparando Estados entre si ou linhas e anos dentro de um Estado.")

    ui.explicar_filtros(
        "API de dados abertos do Siconfi (Tesouro Nacional), endpoint `/rreo`, uma consulta por UF e bimestre. "
        "As opções vêm dos campos do JSON (`anexo`, `rotulo`, `cod_conta`, `conta`, `coluna`).",
        ["**Coleta** (`python coletar.py --rreo-estados` ou o botão *RREO de todas as UFs*): para cada UF (lista do "
         "endpoint `/entes`, esferas E e D) e cada bimestre encerrado dos últimos 4 exercícios, o painel consulta "
         "`/rreo` (an_exercicio, nr_periodo, co_tipo_demonstrativo=RREO, co_esfera=E, id_ente = código IBGE). "
         "Um arquivo por bimestre: `dados/dashboard/rreo_estados/rreo_uf_AAAA_B.parquet`.",
         "**Linha do demonstrativo** = quadro (`rotulo`) + código (`cod_conta`) + nome (`conta`). O nome é comparado "
         "sem acentos, caixa e numeração romana final, que mudam entre UFs e anos.",
         "**Série mensal**: `<MR>` é o mês de referência do relatório (último mês do bimestre) e `<MR-k>`, k meses "
         "antes. Quando o mesmo mês aparece em vários relatórios, vale o mais recente. Só o Anexo 3 (RCL) tem essas "
         "colunas; nos demais anexos cada relatório vira um ponto no seu mês de referência (fev, abr, jun, ago, out, dez).",
         "**% da RCL**: valor ÷ Receita Corrente Líquida de 12 meses da mesma UF (linha `RREO3ReceitaCorrenteLiquida` "
         "do Anexo 3): nas séries mensais, a RCL dos 12 meses que terminam no mês; nas demais, a coluna "
         "'TOTAL (ÚLTIMOS 12 MESES)' do mesmo relatório."],
        [("Anexo", "Campo `anexo` presente nos dados. Os Anexos 8 (MDE) e 12 (ASPS) não vêm na API `/rreo`."),
         ("Linha", "Linhas do anexo na ordem do relatório; ao lado, quantas UFs publicaram a linha."),
         ("Coluna", "Campo `coluna`; anos do exercício viram `<EC>` (ex.: 'PREVISÃO ATUALIZADA <EC>'). No Anexo 3, as "
                    "colunas `<MR-11>` … `<MR>` são reunidas na opção *Mensal*."),
         ("Transformação", "Lista fixa: nas séries mensais, valor do mês ou soma de 12 meses; nas colunas 'até o "
                           "bimestre', acumulado no ano ou valor do bimestre (diferença entre relatórios)."),
         ("Unidade", "R$ como publicado ou % da RCL de 12 meses."),
         ("Estados", "Siglas das UFs (código IBGE do campo `cod_ibge`); regiões da API `/entes`.")],
        ["**Acumulados**: colunas 'até o bimestre' recomeçam em janeiro; compare o mesmo mês entre anos ou use o "
         "valor do bimestre.",
         "**Leiautes diferentes**: algumas linhas (sobretudo nos Anexos 7 e 13) só existem em parte das UFs ou dos anos.",
         "**% da RCL** de valores mensais ou bimestrais é naturalmente pequeno: para comparar com a RCL anual, use a "
         "soma de 12 meses.",
         "**Valores reais (IPCA)** corrigem pelo mês de cada ponto; em colunas acumuladas no ano é uma aproximação. "
         "Não se aplicam ao % da RCL."],
        fontes=("siconfi_rreo_uf",), nota="campos do JSON listados acima")

    # ---------------------------------------------------------------- filtros comuns
    c = st.columns([1.2, 2.6, 1.8])
    anexos = [a for a in ANEXOS if a in set(cat["anexo"])] + sorted(set(cat["anexo"]) - set(ANEXOS))
    anexo = _escolher(c[0], "Anexo", anexos, "rx_anexo", "RREO-Anexo 03",
                      format_func=lambda a: f"{a.replace('RREO-', '')} – {ANEXOS.get(a, '')}")
    ca = cat[cat["anexo"] == anexo].reset_index(drop=True)
    rot = _rotulos(ca)
    # padrão: RCL no Anexo 3; nos demais, a 1ª linha (na ordem do relatório) publicada pelo maior número de UFs
    padrao_linha = next((ln for ln in ca["linha"] if f"| {RE.COD_RCL} |" in ln),
                        ca.loc[ca["n_ufs"] == ca["n_ufs"].max(), "linha"].iat[0])
    linha = _escolher(c[1], "Linha do demonstrativo", list(rot), f"rx_linha_{anexo}", padrao_linha,
                      format_func=rot.get, help="Digite para buscar. Ao lado do nome, quantas UFs publicaram a linha.")
    colunas = _colunas(assin, anexo, linha)
    padrao_col = RE.MENSAL if RE.MENSAL in colunas else next(
        (x for x in colunas if RE.acumula(x) and "LIQUIDADAS" in x.upper()),
        next((x for x in colunas if RE.acumula(x)), colunas[0]))
    coluna = _escolher(c[2], "Coluna", colunas, f"rx_col_{anexo}", padrao_col)

    c = st.columns([1.6, 1.4, 2.2])
    if coluna == RE.MENSAL:
        modo = c[0].radio("Transformação", RE.MODOS_MENSAL, horizontal=True, key="rx_modo_m",
                          help="Soma em 12 meses tira a sazonalidade e é comparável com a RCL anual.")
    elif RE.acumula(coluna):
        modo = c[0].radio("Transformação", RE.MODOS_ACUMULADO, horizontal=True, key="rx_modo_a",
                          help="A coluna acumula de janeiro ao fim do bimestre. 'Valor do bimestre' é a diferença "
                               "entre relatórios consecutivos do mesmo ano.")
    else:
        modo = None
        c[0].caption("Transformação: valor como publicado (a coluna não é mensal nem acumulada no ano).")
    eh_pct = RE.percentual(coluna)
    if eh_pct:
        unidade = "%"
        c[1].caption("Unidade: percentual publicado no próprio demonstrativo.")
    else:
        unidade = c[1].radio("Unidade", UNIDADES, horizontal=True, key="rx_unid")
    pct_rcl = unidade == UNIDADES[1]
    y = "pct_rcl" if pct_rcl else "valor"
    em_pct = pct_rcl or eh_pct
    moeda = not em_pct

    s = _serie(assin, anexo, (linha,), coluna, modo)
    if s.empty:
        st.info("Sem valores para essa combinação de linha e coluna.")
        return
    meses = pd.date_range(s["data"].min(), s["data"].max(), freq="MS")
    if len(meses) > 1:
        ini, fim = c[2].select_slider("Período", options=list(meses), value=(meses[0], meses[-1]),
                                      format_func=lambda d: d.strftime("%m/%Y"), key=f"rx_per_{coluna == RE.MENSAL}_{modo}")
    else:
        ini, fim = meses[0], meses[-1]
    s = s[(s["data"] >= ini) & (s["data"] <= fim)]
    if moeda:
        s = ui.ajustar(s, ["valor"])
    nome_linha = _curto(rot[linha], 80)
    desc = f"{coluna if coluna != RE.MENSAL else 'mensal'}" + (f", {modo.lower()}" if modo else "")
    sufixo = " (% da RCL)" if pct_rcl else ""
    nota_base = (f"RREO {anexo.replace('RREO-', '')}, linha '{nome_linha}', coluna '{coluna}'"
                 + (f", {modo.lower()}" if modo else "")
                 + ("; % da RCL de 12 meses da própria UF" if pct_rcl else ""))
    if coluna != RE.MENSAL:
        nota_base += "; um ponto por relatório, no mês de referência <MR> (fim do bimestre)"

    t_inter, t_intra = st.tabs(["🗺️ Entre Estados", "📍 Dentro de um Estado"])

    # ---------------------------------------------------------------- entre Estados
    with t_inter:
        c = st.columns([1.3, 3])
        regs = c[0].multiselect("Região (atalho)", list(REGIOES.values()), key="rx_reg", placeholder="Todas",
                                help="Limita as opções de Estados às regiões escolhidas.")
        opc = [u for u in todas_ufs if not regs or regiao.get(u) in regs]
        if "rx_ufs" in st.session_state:
            st.session_state["rx_ufs"] = [u for u in st.session_state["rx_ufs"] if u in opc]
        ufs = c[1].multiselect(f"Estados (até {MAX_SERIES})", opc, default=[u for u in UFS_PADRAO if u in opc],
                               max_selections=MAX_SERIES, key="rx_ufs",
                               format_func=lambda u: f"{u} ({SIGLA_REGIAO.get(regiao.get(u), '')})")
        mostra_med = st.toggle("Mostrar a mediana das 27 UFs", value=True, key="rx_med",
                               help="Mediana entre as UFs que publicaram o valor no mês (mínimo de 14).")
        cores = _cores_estaveis("rx_cores_uf", ufs)
        d = s[s["uf"].isin(ufs)]
        if mostra_med:
            med = s.groupby("data").agg(v=(y, "median"), n=(y, "count")).reset_index()
            med = med[med["n"] >= 14].rename(columns={"v": y}).assign(uf="Mediana das UFs")
            d = pd.concat([d, med[["uf", "data", y]]], ignore_index=True)
            cores = {**cores, "Mediana das UFs": G.OUTROS}
        if d.empty:
            st.info("Escolha ao menos um Estado." if not ufs else
                    "Os Estados escolhidos não publicaram essa linha nessa coluna; veja no ranking abaixo quem publicou.")
        else:
            ordem = [u for u in ufs] + (["Mediana das UFs"] if mostra_med else [])
            fig = _linhas(d, "uf", y, f"{nome_linha} – {desc}{sufixo}", cores, em_pct, moeda, ordem=ordem,
                          marcadores=coluna != RE.MENSAL)
            fig.for_each_trace(lambda tr: tr.update(line=dict(dash="dot", width=2)) if tr.name == "Mediana das UFs" else None)
            ui.grafico(fig, "rx_inter_linhas", "siconfi_rreo_uf", nota=nota_base, valores=moeda)

        # ranking de todas as UFs num mês
        datas = sorted(s["data"].unique(), reverse=True)
        cont = s.groupby("data")[y].count()
        padrao = next((x for x in datas if cont.get(x, 0) >= 0.8 * cont.max()), datas[0])
        c = st.columns([1, 3])
        ref = c[0].selectbox("Mês do ranking", datas, index=datas.index(padrao),
                             format_func=lambda x: pd.Timestamp(x).strftime("%m/%Y"),
                             key=f"rx_rank_{anexo}_{coluna}_{modo}",
                             help="O padrão é o mês mais recente em que ao menos 80% das UFs já publicaram.")
        r = s[s["data"] == ref].dropna(subset=[y]).sort_values(y, ascending=False)
        if not r.empty:
            cor_barras = [cores.get(u, G.SEQ[2]) if u in ufs else G.SEQ[1] for u in r["uf"]]
            fig = go.Figure(go.Bar(x=r["uf"], y=r[y], marker_color=cor_barras, marker_line_width=0,
                                   customdata=r["uf"].map(lambda u: regiao.get(u, "")),
                                   hovertemplate="%{x} (%{customdata})<br>" +
                                                 ("%{y:,.2f}%" if em_pct else "R$ %{y:,.2f}") + "<extra></extra>"))
            G._layout(fig, f"Todas as UFs em {pd.Timestamp(ref).strftime('%m/%Y')} – {nome_linha}{sufixo}", 380,
                      legenda=False)
            fig.update_layout(bargap=0.25)
            if mostra_med:
                fig.add_hline(y=r[y].median(), line_dash="dot", line_color=G.OUTROS, line_width=1.5,
                              annotation_text="mediana", annotation_position="top right")
            _eixo(fig, em_pct, moeda)
            fig.update_traces(hovertemplate="%{x} (%{customdata})<br>" + ("%{y:,.2f}%" if em_pct else "R$ %{y:,.2f}")
                              + "<extra></extra>")
            c[1].caption(f"{len(r)} UFs com valor em {pd.Timestamp(ref).strftime('%m/%Y')}. Os Estados escolhidos "
                         "acima aparecem com a sua cor; os demais, em azul-claro.")
            ui.grafico(fig, "rx_inter_rank", "siconfi_rreo_uf", nota=nota_base, valores=moeda)

        larga = s[s["uf"].isin(ufs or todas_ufs)].pivot_table(index="data", columns="uf", values=y, aggfunc="sum")
        larga = larga.sort_index(ascending=False)
        larga.index = larga.index.strftime("%m/%Y")
        larga = larga.reset_index().rename(columns={"data": "Mês"})
        num = [x for x in larga.columns if x != "Mês"]
        with st.expander("📋 Tabela: Estados escolhidos, mês a mês", expanded=False):
            ui.tabela(larga, "rx_inter_tab", moeda=[] if em_pct else num, pct=num if em_pct else [],
                      ordenar_padrao="(ordem original)", fontes=["siconfi_rreo_uf"], nota=nota_base)

    # ---------------------------------------------------------------- dentro de um Estado
    with t_intra:
        c = st.columns([1, 3])
        uf = _escolher(c[0], "Estado", todas_ufs, "rx_uf", "MS", format_func=lambda u: f"{u} – {regiao.get(u, '')}")
        presentes = set(base.loc[(base["anexo"] == anexo) & (base["uf"] == uf), "linha"].astype(str))
        opc = [ln for ln in rot if ln in presentes]
        chave = f"rx_linhas_{anexo}"
        if chave in st.session_state:
            st.session_state[chave] = [x for x in st.session_state[chave] if x in opc]
        outras = c[1].multiselect(f"Linhas para comparar (até {MAX_SERIES}, mesma coluna e unidade)", opc,
                                  default=[linha] if linha in opc else [], max_selections=MAX_SERIES, key=chave,
                                  format_func=rot.get)
        if outras:
            si = _serie(assin, anexo, tuple(outras), coluna, modo)
            si = si[(si["uf"] == uf) & (si["data"] >= ini) & (si["data"] <= fim)]
            if moeda:
                si = ui.ajustar(si, ["valor"])
            si = si.assign(serie=si["linha"].map(lambda ln: _curto(rot.get(ln, ln), 60)))
            nomes = [_curto(rot[ln], 60) for ln in outras]
            cores = _cores_estaveis("rx_cores_linha", nomes)
            if si.empty:
                st.info(f"{uf} não publicou essas linhas nesta coluna.")
            else:
                fig = _linhas(si, "serie", y, f"{uf} – {ANEXOS.get(anexo, anexo)}, {desc}{sufixo}", cores, em_pct,
                              moeda, ordem=nomes, marcadores=coluna != RE.MENSAL)
                ui.grafico(fig, "rx_intra_linhas", "siconfi_rreo_uf", valores=moeda,
                           nota=f"RREO {anexo.replace('RREO-', '')} de {uf}, coluna '{coluna}'"
                                + (f", {modo.lower()}" if modo else "") + ("; % da RCL de 12 meses" if pct_rcl else ""))

        # comparação entre anos (sazonalidade) da linha principal
        sa = s[s["uf"] == uf].dropna(subset=[y]).copy()
        if not sa.empty:
            sa["Ano"] = sa["ano"].astype(str)
            sa["Mês"] = sa["mes"].map(lambda m: G.MESES[m - 1])
            anos = sorted(sa["Ano"].unique())
            cores_ano = {a: G.CORES[i % len(G.CORES)] for i, a in enumerate(anos)}
            fig = go.Figure()
            for a in anos:
                t = sa[sa["Ano"] == a].sort_values("mes")
                fig.add_scatter(x=t["Mês"], y=t[y], name=a, mode="lines+markers", line=dict(width=2, color=cores_ano[a]),
                                marker=dict(size=8))
            G._layout(fig, f"{uf} – {nome_linha}: cada linha é um ano{sufixo}", 400)
            fig.update_xaxes(categoryorder="array", categoryarray=G.MESES)
            _eixo(fig, em_pct, moeda)
            if not em_pct:
                fig.update_traces(hovertemplate="R$ %{y:,.2f}")
            ui.grafico(fig, "rx_intra_anos", "siconfi_rreo_uf", valores=moeda,
                       nota=nota_base + "; compara o mesmo mês entre exercícios")
            larga = sa.pivot_table(index="Ano", columns="mes", values=y, aggfunc="sum")
            larga.columns = [G.MESES[m - 1] for m in larga.columns]
            larga = larga.reset_index()
            num = [x for x in larga.columns if x != "Ano"]
            with st.expander(f"📋 Tabela: {uf}, ano × mês", expanded=False):
                ui.tabela(larga, "rx_intra_tab", moeda=[] if em_pct else num, pct=num if em_pct else [],
                          ordenar_padrao="(ordem original)", fontes=["siconfi_rreo_uf"], nota=nota_base)
