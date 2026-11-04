"""RGF › aba Anexos: todos os anexos do RGF das 27 UFs, por Poder, em séries mensais, com comparações entre Estados e
dentro de um Estado, em valores brutos ou como % da Receita Corrente Líquida."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import rgf_estados as RG
from ms_fiscal import transformacoes as T
from ms_fiscal import ui
from paginas.rreo_anexos import (MAX_SERIES, REGIOES, SIGLA_REGIAO, UFS_PADRAO, UNIDADES, _cores_estaveis, _curto,
                                 _eixo, _escolher, _linhas, _rotulos)

ANEXOS = {
    "RGF-Anexo 01": "Despesa com pessoal",
    "RGF-Anexo 02": "Dívida consolidada líquida",
    "RGF-Anexo 03": "Garantias e contragarantias",
    "RGF-Anexo 04": "Operações de crédito",
    "RGF-Anexo 05": "Disponibilidade de caixa e restos a pagar",
    "RGF-Anexo 06": "Demonstrativo simplificado",
}
CONSOLIDADO = "Todos os Poderes (soma)"
OPCOES_PODER = [CONSOLIDADO] + [f"{v} ({k})" for k, v in RG.PODERES.items()]


@st.cache_data(show_spinner="Montando a série…", max_entries=64)
def _serie(assin: str, anexo: str, linhas: tuple[str, ...], coluna: str, modo: str | None,
           poderes: tuple[str, ...]) -> pd.DataFrame:
    d = ui.rgf_uf()
    return RG.serie(d["base"], ui.rreo_uf()["rcl_mes"], anexo, list(linhas), coluna, modo, list(poderes))


@st.cache_data(show_spinner=False, max_entries=256)
def _colunas(assin: str, anexo: str, linha: str, poderes: tuple[str, ...]) -> list[str]:
    b = ui.rgf_uf()["base"]
    m = (b["anexo"] == anexo) & (b["linha"] == linha) & b["co_poder"].isin(poderes)
    return RG.colunas_da_linha(T.distintos(b.loc[m, "coluna"]))


def _modos(coluna: str) -> tuple[list[str] | None, str]:
    if coluna == RG.MENSAL:
        return RG.MODOS_MENSAL, "Soma em 12 meses é o conceito da LRF (despesa com pessoal dos últimos 12 meses)."
    if coluna == RG.SALDOS:
        return RG.MODOS_SALDO, ("O saldo só é publicado no fim de cada quadrimestre (e em 31/12 do ano anterior). A "
                                "interpolação linear preenche os meses entre eles: é uma estimativa, não um dado publicado.")
    if RG.acumula(coluna):
        return RG.MODOS_ACUMULADO, ("A coluna acumula de janeiro ao fim do quadrimestre. 'Valor do quadrimestre' é a "
                                    "diferença entre relatórios; a média mensal divide esse valor por 4 em cada mês.")
    if RG.fluxo(coluna):
        return RG.MODOS_FLUXO, "A média mensal divide o valor do quadrimestre por 4 e o repete em cada um dos 4 meses."
    return None, ""


def render() -> None:
    dados = ui.rgf_uf()
    base, cat = dados["base"], dados["catalogo"]
    if base.empty:
        ui.sem_dados("RGF de todas as UFs", "python coletar.py --rgf-estados")
        return
    assin = dados["assin"] + ui.assinatura_rreo_uf()  # o % da RCL usa a RCL do RREO
    entes = ui.entes_uf()
    regiao = dict(zip(entes["uf"], entes["regiao"].map(REGIOES))) if not entes.empty else {}
    todas_ufs = sorted(T.distintos(base["uf"]))
    ex = base[["exercicio", "periodo"]].drop_duplicates().sort_values(["exercicio", "periodo"])
    a0, q0 = ex.iloc[0]
    a1, q1 = ex.iloc[-1]
    st.markdown(f"**RGF das {len(todas_ufs)} UFs, de cada Poder e órgão autônomo, do {q0}º quadrimestre de {a0} ao "
                f"{q1}º quadrimestre de {a1}.** Escolha o Poder, o anexo, a linha e a coluna; os gráficos mostram a "
                "série mensal (quando o anexo tem colunas mensais) ou quadrimestral, entre Estados e dentro de um Estado.")

    ui.explicar_filtros(
        "API de dados abertos do Siconfi (Tesouro Nacional), endpoint `/rgf`, uma consulta por UF, Poder e "
        "quadrimestre. As opções vêm dos campos do JSON (`co_poder`, `instituicao`, `anexo`, `rotulo`, `cod_conta`, "
        "`conta`, `coluna`).",
        ["**Coleta** (`python coletar.py --rgf-estados` ou o botão *RGF de todas as UFs*): para cada UF (endpoint "
         "`/entes`), cada Poder (E, L, J, M, D) e cada quadrimestre encerrado dos últimos 4 exercícios, o painel "
         "consulta `/rgf` (in_periodicidade=Q, co_esfera=E). Um arquivo por quadrimestre: "
         "`dados/dashboard/rgf_estados/rgf_uf_AAAA_Q.parquet`.",
         "**Poder**: cada Poder publica o seu RGF; no Legislativo, a Assembleia e o Tribunal de Contas publicam "
         "separadamente. A opção *Todos os Poderes* soma as instituições. Um ponto só entra na soma se todas as "
         "instituições que a UF costuma publicar naquela linha estiverem presentes.",
         "**Séries mensais**: no Anexo 1, `<MR>` é o último mês do quadrimestre (abr, ago, dez) e `<MR-k>`, k meses "
         "antes; vale o relatório mais recente de cada instituição. Nos Anexos 2 e 3, os saldos 'SALDO DO EXERCÍCIO "
         "ANTERIOR' e 'Até o kº Quadrimestre' formam a série de saldos (dez, abr, ago). As colunas do quadrimestre "
         "podem virar média mensal (÷ 4).",
         "**% da RCL**: valor ÷ RCL dos 12 meses que terminam no mês, da mesma UF, calculada com as colunas mensais do "
         "RREO, Anexo 3. Os limites da LRF usam a RCL *ajustada*, publicada no próprio RGF (colunas '% sobre a RCL "
         "Ajustada'); a diferença costuma ser pequena."],
        [("Poder", "Parâmetro `co_poder` da API; os nomes são do painel."),
         ("Anexo", "Campo `anexo`. O Anexo 5 (caixa) só existe no 3º quadrimestre; os Anexos 2 a 4, só no Executivo."),
         ("Linha", "Linhas do anexo na ordem do relatório de MS; ao lado, quantas UFs publicaram a linha."),
         ("Coluna", "Campo `coluna`; as colunas `<MR-k>` viram a opção *Mensal* e os saldos datados, *Saldo no fim de "
                    "cada quadrimestre*."),
         ("Transformação", "Lista fixa, conforme o tipo da coluna (mensal, saldo, acumulada ou do quadrimestre)."),
         ("Estados", "Siglas das UFs; regiões da API `/entes`.")],
        ["**Média mensal e interpolação** são construções do painel para pôr dados quadrimestrais em base mensal; não "
         "são valores publicados.",
         "**Leiautes diferentes**: algumas linhas só existem em parte das UFs, dos Poderes ou dos anos.",
         "**Valores reais (IPCA)** corrigem pelo mês de cada ponto; não se aplicam ao % da RCL."],
        fontes=("siconfi_rgf_uf", "siconfi_rreo_uf"), nota="campos do JSON listados acima")

    # ---------------------------------------------------------------- filtros comuns
    c = st.columns([1.3, 1.2, 2.4, 1.8])
    p_sel = c[0].selectbox("Poder", OPCOES_PODER, key="gx_poder")
    poderes = tuple(RG.PODERES) if p_sel == CONSOLIDADO else (p_sel[-2],)
    presentes = set(T.distintos(base.loc[base["co_poder"].isin(poderes), "anexo"]))
    anexos = [a for a in ANEXOS if a in presentes] + sorted(presentes - set(ANEXOS))
    anexo = _escolher(c[1], "Anexo", anexos, "gx_anexo", "RGF-Anexo 01",
                      format_func=lambda a: f"{a.replace('RGF-', '')} – {ANEXOS.get(a, '')}")
    lin_ok = set(T.distintos(base.loc[(base["anexo"] == anexo) & base["co_poder"].isin(poderes), "linha"]))
    ca = cat[(cat["anexo"] == anexo) & cat["linha"].isin(lin_ok)].reset_index(drop=True)
    rot = _rotulos(ca)
    # padrão no Anexo 1: despesa líquida com pessoal (tem as colunas mensais <MR-k>)
    padrao_linha = next((ln for cod in ("DespesaComPessoalLiquida", "DespesaComPessoalBruta", "DespesaComPessoalTotal")
                         for ln in ca["linha"] if f"| {cod} |" in ln),
                        ca.loc[ca["n_ufs"] == ca["n_ufs"].max(), "linha"].iat[0])
    linha = _escolher(c[2], "Linha do demonstrativo", list(rot), f"gx_linha_{anexo}", padrao_linha,
                      format_func=rot.get, help="Digite para buscar. Ao lado do nome, quantas UFs publicaram a linha.")
    colunas = _colunas(assin, anexo, linha, poderes)
    padrao_col = next((x for x in (RG.MENSAL, RG.SALDOS) if x in colunas), colunas[0] if colunas else None)
    coluna = _escolher(c[3], "Coluna", colunas, f"gx_col_{anexo}", padrao_col)

    c = st.columns([1.9, 1.3, 2.2])
    modos, ajuda = _modos(coluna)
    if modos:
        tipo = {id(RG.MODOS_MENSAL): "mensal", id(RG.MODOS_SALDO): "saldo", id(RG.MODOS_ACUMULADO): "acum",
                id(RG.MODOS_FLUXO): "fluxo"}[id(modos)]
        modo = c[0].radio("Transformação", modos, horizontal=True, key=f"gx_modo_{tipo}", help=ajuda)
    else:
        modo = None
        c[0].caption("Transformação: valor como publicado, um ponto por relatório (abr, ago, dez).")
    eh_pct = RG.percentual(coluna)
    if eh_pct:
        unidade = "%"
        c[1].caption("Unidade: percentual publicado no próprio demonstrativo." +
                     (" Na soma dos Poderes, os percentuais se somam (mesma RCL)." if p_sel == CONSOLIDADO else ""))
    else:
        unidade = c[1].radio("Unidade", UNIDADES, horizontal=True, key="gx_unid")
    pct_rcl = unidade == UNIDADES[1]
    y = "pct_rcl" if pct_rcl else "valor"
    em_pct = pct_rcl or eh_pct
    moeda = not em_pct

    s = _serie(assin, anexo, (linha,), coluna, modo, poderes)
    if s.empty:
        st.info("Sem valores para essa combinação de Poder, linha e coluna." + (
            " Na soma dos Poderes, um ponto só entra quando todas as instituições publicaram a mesma linha e coluna "
            "(no Anexo 6, por exemplo, cada Poder usa um nome de coluna diferente). Escolha um Poder."
            if p_sel == CONSOLIDADO else ""))
        return
    meses = pd.date_range(s["data"].min(), s["data"].max(), freq="MS")
    if len(meses) > 1:
        ini, fim = c[2].select_slider("Período", options=list(meses), value=(meses[0], meses[-1]),
                                      format_func=lambda d: d.strftime("%m/%Y"), key=f"gx_per_{coluna}_{modo}")
    else:
        ini, fim = meses[0], meses[-1]
    s = s[(s["data"] >= ini) & (s["data"] <= fim)]
    if moeda:
        s = ui.ajustar(s, ["valor"])
    nome_linha = _curto(rot[linha], 80)
    # Poder sempre explícito nos títulos (o RGF é publicado por Poder)
    poder_txt = "Todos os Poderes (soma)" if p_sel == CONSOLIDADO else f"Poder: {p_sel.rsplit(' (', 1)[0]}"
    desc = {RG.MENSAL: "mensal", RG.SALDOS: "saldo"}.get(coluna, coluna) + (f", {modo.lower()}" if modo else "")
    sufixo = " (% da RCL)" if pct_rcl else ""
    nota_base = (f"RGF {anexo.replace('RGF-', '')}, {p_sel.lower()}, linha '{nome_linha}', coluna '{coluna}'"
                 + (f", {modo.lower()}" if modo else "") + ("; % da RCL de 12 meses da própria UF (RREO, Anexo 3)"
                                                            if pct_rcl else ""))
    marcadores = coluna != RG.MENSAL and modo not in (RG.MODOS_SALDO[1], RG.MODOS_ACUMULADO[2], RG.MODOS_FLUXO[1])

    t_inter, t_intra, t_lrf = st.tabs(["🗺️ Entre Estados", "📍 Dentro de um Estado", "⚖️ Limites da LRF"])
    with t_lrf:
        _limites(dados["lrf"], todas_ufs, regiao)

    # ---------------------------------------------------------------- entre Estados
    with t_inter:
        if anexo == "RGF-Anexo 01":
            st.caption("⚖️ Os limites da despesa com pessoal variam por Poder e por UF (LRF, arts. 19 e 20): Executivo "
                       "49% (48,6% em BA, GO e PA, que têm Tribunal de Contas dos Municípios), Legislativo 3% (3,4%), "
                       "Judiciário 6%, Ministério Público 2%, total 60% (52% no DF). Por isso, valores de Poderes ou UFs "
                       "diferentes não se comparam diretamente com um único limite: a sub-aba **Limites da LRF** "
                       "compara cada UF com o seu próprio limite.")
        c = st.columns([1.3, 3])
        regs = c[0].multiselect("Região (atalho)", list(REGIOES.values()), key="gx_reg", placeholder="Todas")
        opc = [u for u in todas_ufs if not regs or regiao.get(u) in regs]
        if "gx_ufs" in st.session_state:
            st.session_state["gx_ufs"] = [u for u in st.session_state["gx_ufs"] if u in opc]
        ufs = c[1].multiselect(f"Estados (até {MAX_SERIES})", opc, default=[u for u in UFS_PADRAO if u in opc],
                               max_selections=MAX_SERIES, key="gx_ufs",
                               format_func=lambda u: f"{u} ({SIGLA_REGIAO.get(regiao.get(u), '')})")
        mostra_med = st.toggle("Mostrar a mediana das 27 UFs", value=True, key="gx_med",
                               help="Mediana entre as UFs com valor no mês (mínimo de 14).")
        cores = _cores_estaveis("gx_cores_uf", ufs)
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
            fig = _linhas(d, "uf", y, f"{poder_txt} · {nome_linha} – {desc}{sufixo}", cores, em_pct, moeda,
                          ordem=list(ufs) + (["Mediana das UFs"] if mostra_med else []), marcadores=marcadores)
            fig.for_each_trace(lambda tr: tr.update(line=dict(dash="dot", width=2)) if tr.name == "Mediana das UFs" else None)
            ui.grafico(fig, "gx_inter_linhas", "siconfi_rgf_uf", nota=nota_base, valores=moeda)

        datas = sorted(s["data"].unique(), reverse=True)
        cont = s.groupby("data")[y].count()
        padrao = next((x for x in datas if cont.get(x, 0) >= 0.8 * cont.max()), datas[0])
        c = st.columns([1, 3])
        ref = c[0].selectbox("Mês do ranking", datas, index=datas.index(padrao),
                             format_func=lambda x: pd.Timestamp(x).strftime("%m/%Y"),
                             key=f"gx_rank_{anexo}_{coluna}_{modo}_{p_sel}",
                             help="O padrão é o mês mais recente em que ao menos 80% das UFs já publicaram.")
        r = s[s["data"] == ref].dropna(subset=[y]).sort_values(y, ascending=False)
        if not r.empty:
            fig = go.Figure(go.Bar(x=r["uf"], y=r[y], marker_line_width=0,
                                   marker_color=[cores.get(u, G.SEQ[2]) if u in ufs else G.SEQ[1] for u in r["uf"]],
                                   customdata=r["uf"].map(lambda u: regiao.get(u, ""))))
            G._layout(fig, f"{poder_txt} · todas as UFs em {pd.Timestamp(ref).strftime('%m/%Y')} – {nome_linha}{sufixo}", 380,
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
            ui.grafico(fig, "gx_inter_rank", "siconfi_rgf_uf", nota=nota_base, valores=moeda)

        larga = s[s["uf"].isin(ufs or todas_ufs)].pivot_table(index="data", columns="uf", values=y, aggfunc="sum")
        larga = larga.sort_index(ascending=False)
        larga.index = larga.index.strftime("%m/%Y")
        larga = larga.reset_index().rename(columns={"data": "Mês"})
        num = [x for x in larga.columns if x != "Mês"]
        with st.expander("📋 Tabela: Estados escolhidos, mês a mês", expanded=False):
            ui.tabela(larga, "gx_inter_tab", moeda=[] if em_pct else num, pct=num if em_pct else [],
                      ordenar_padrao="(ordem original)", fontes=["siconfi_rgf_uf"], nota=nota_base)

    # ---------------------------------------------------------------- dentro de um Estado
    with t_intra:
        c = st.columns([1, 3])
        uf = _escolher(c[0], "Estado", todas_ufs, "gx_uf", "MS", format_func=lambda u: f"{u} – {regiao.get(u, '')}")
        m = (base["anexo"] == anexo) & (base["uf"] == uf) & base["co_poder"].isin(poderes)
        presentes_uf = set(T.distintos(base.loc[m, "linha"]))
        opc = [ln for ln in rot if ln in presentes_uf]
        chave = f"gx_linhas_{anexo}"
        if chave in st.session_state:
            st.session_state[chave] = [x for x in st.session_state[chave] if x in opc]
        outras = c[1].multiselect(f"Linhas para comparar (até {MAX_SERIES}, mesma coluna e unidade)", opc,
                                  default=[linha] if linha in opc else [], max_selections=MAX_SERIES, key=chave,
                                  format_func=rot.get)
        if outras:
            si = _serie(assin, anexo, tuple(outras), coluna, modo, poderes)
            si = si[(si["uf"] == uf) & (si["data"] >= ini) & (si["data"] <= fim)]
            if moeda:
                si = ui.ajustar(si, ["valor"])
            si = si.assign(serie=si["linha"].map(lambda ln: _curto(rot.get(ln, ln), 60)))
            nomes = [_curto(rot[ln], 60) for ln in outras]
            if si.empty:
                st.info(f"{uf} não publicou essas linhas nesta coluna.")
            else:
                fig = _linhas(si, "serie", y, f"{uf}, {poder_txt} · {ANEXOS.get(anexo, anexo)}, {desc}{sufixo}",
                              _cores_estaveis("gx_cores_linha", nomes), em_pct, moeda, ordem=nomes, marcadores=marcadores)
                ui.grafico(fig, "gx_intra_linhas", "siconfi_rgf_uf", valores=moeda,
                           nota=f"RGF {anexo.replace('RGF-', '')} de {uf}, {p_sel.lower()}, coluna '{coluna}'"
                                + (f", {modo.lower()}" if modo else ""))

        # comparação entre anos (Poderes separados ou o mesmo mês entre exercícios)
        sa = s[s["uf"] == uf].dropna(subset=[y]).copy()
        if not sa.empty:
            sa["Ano"] = sa["ano"].astype(str)
            sa["Mês"] = sa["mes"].map(lambda x: G.MESES[x - 1])
            anos = sorted(sa["Ano"].unique())
            fig = go.Figure()
            for i, a in enumerate(anos):
                t = sa[sa["Ano"] == a].sort_values("mes")
                fig.add_scatter(x=t["Mês"], y=t[y], name=a, mode="lines+markers",
                                line=dict(width=2, color=G.CORES[i % len(G.CORES)]), marker=dict(size=8))
            G._layout(fig, f"{uf}, {poder_txt} · {nome_linha}: cada linha é um ano{sufixo}", 400)
            fig.update_xaxes(categoryorder="array", categoryarray=G.MESES)
            _eixo(fig, em_pct, moeda)
            if not em_pct:
                fig.update_traces(hovertemplate="R$ %{y:,.2f}")
            ui.grafico(fig, "gx_intra_anos", "siconfi_rgf_uf", valores=moeda,
                       nota=nota_base + "; compara o mesmo mês entre exercícios")
            larga = sa.pivot_table(index="Ano", columns="mes", values=y, aggfunc="sum")
            larga.columns = [G.MESES[x - 1] for x in larga.columns]
            larga = larga.reset_index()
            num = [x for x in larga.columns if x != "Ano"]
            with st.expander(f"📋 Tabela: {uf}, ano × mês", expanded=False):
                ui.tabela(larga, "gx_intra_tab", moeda=[] if em_pct else num, pct=num if em_pct else [],
                          ordenar_padrao="(ordem original)", fontes=["siconfi_rgf_uf"], nota=nota_base)

        # cada Poder e o total, sempre (a escolha do Poder no topo não restringe este gráfico)
        partes = []
        for p in (*RG.PODERES, None):
            sp = _serie(assin, anexo, (linha,), coluna, modo, (p,) if p else tuple(RG.PODERES))
            sp = sp[(sp["uf"] == uf) & (sp["data"] >= ini) & (sp["data"] <= fim)]
            if not sp.empty:
                partes.append(sp.assign(poder=RG.PODERES[p] if p else CONSOLIDADO))
        if len(partes) > 1:
            sp = pd.concat(partes, ignore_index=True)
            if moeda:
                sp = ui.ajustar(sp, ["valor"])
            ordem = [v for v in [*RG.PODERES.values(), CONSOLIDADO] if v in set(sp["poder"])]
            cores_p = {v: G.CORES[i] for i, v in enumerate(RG.PODERES.values())} | {CONSOLIDADO: G.OUTROS}
            fig = _linhas(sp, "poder", y, f"{uf} · {nome_linha}: cada Poder separado e a soma de todos{sufixo}", cores_p, em_pct, moeda,
                          ordem=ordem, marcadores=marcadores)
            fig.for_each_trace(lambda tr: tr.update(line=dict(dash="dot", width=2.5)) if tr.name == CONSOLIDADO else None)
            ui.grafico(fig, "gx_intra_poderes", "siconfi_rgf_uf", valores=moeda,
                       nota=nota_base.replace(p_sel.lower(), "cada Poder e a soma de todos")
                            + "; independe do filtro de Poder no topo")


# ------------------------------------------------------------------ limites da LRF
SITUACOES = {  # situação → (cor de status, ícone)
    "dentro dos limites": (G.STATUS["bom"], "✅"),
    "acima do limite de alerta": (G.STATUS["alerta"], "⚠️"),
    "acima do limite prudencial": (G.STATUS["serio"], "🟠"),
    "acima do limite máximo": (G.STATUS["critico"], "⛔"),
    "sem limite próprio": (G.OUTROS, "➖"),
    "sem dado": (G.OUTROS, "·"),
}
GRUPOS_PESSOAL = [*RG.PODERES.values(), RG.TODOS]


def _sit(r) -> str:
    return RG.situacao(r["valor"], r["alerta"], r["prudencial"], r["maximo"])


def _fig_limite(t: pd.DataFrame, titulo: str, altura: int = 320) -> go.Figure:
    """Indicador (% da RCL ajustada) com as linhas de alerta, prudencial e máximo; marcador colorido pela situação."""
    t = t.sort_values("data")
    fig = go.Figure()
    for col, nome, cor, traco in (("maximo", "Limite máximo", G.STATUS["critico"], "solid"),
                                  ("prudencial", "Limite prudencial", G.STATUS["serio"], "dash"),
                                  ("alerta", "Limite de alerta", G.STATUS["alerta"], "dot")):
        if t[col].notna().any():
            fig.add_scatter(x=t["data"], y=t[col], name=nome, mode="lines", line=dict(color=cor, width=1.5, dash=traco),
                            line_shape="hv", hovertemplate=f"{nome}: %{{y:,.2f}}%<extra></extra>")
    if "divergencia" in t and t["divergencia"].fillna(False).any():
        fig.add_scatter(x=t["data"], y=t["maximo_publicado"], name="Máximo publicado pela UF (≠ legal)", mode="lines",
                        line=dict(color=G.OUTROS, width=1.5, dash="dashdot"), line_shape="hv",
                        hovertemplate="Máximo publicado no RGF: %{y:,.2f}%<extra></extra>")
    sit = t.apply(_sit, axis=1)
    fig.add_scatter(x=t["data"], y=t["valor"], name="Apurado", mode="lines+markers",
                    line=dict(color=G.CORES[0], width=2.5),
                    marker=dict(size=9, color=[SITUACOES[x][0] for x in sit], line=dict(width=1.5, color="white")),
                    customdata=[f"{SITUACOES[x][1]} {x}" for x in sit],
                    hovertemplate="Apurado: %{y:,.2f}%<br>%{customdata}<extra></extra>")
    G._layout(fig, titulo, altura)
    fig.update_layout(hovermode="x unified", margin=dict(l=8, r=8, t=84, b=8))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    fig.update_xaxes(tickformat="%m/%y", dtick="M8", tick0=t["data"].min(), tickangle=0, hoverformat="%m/%Y")
    return fig


def _titulo_sit(t: pd.DataFrame, nome: str) -> str:
    if t.empty:
        return nome
    u = t.sort_values("data").iloc[-1]
    s = _sit(u)
    lim = (f"limite legal {G.pct(u['maximo'], 1)} · {u['base_legal']}" if not pd.isna(u["maximo"])
           else str(u.get("base_legal", "sem limite")))
    return (f"{nome}<br><sup>{lim}</sup><br><sup>{SITUACOES[s][1]} {G.pct(u['valor'], 2)} em {u['data']:%m/%Y}: "
            f"{s}</sup>")


def _limites(lrf: pd.DataFrame, todas_ufs: list[str], regiao: dict) -> None:
    if lrf is None or lrf.empty:
        st.info("Sem dados do RGF para calcular os indicadores.")
        return
    st.markdown("Cumprimento dos limites da LRF e das resoluções do Senado, em **% da RCL ajustada**, no fim de cada "
                "quadrimestre. Marcador verde: dentro dos limites; amarelo: acima do alerta; laranja: acima do "
                "prudencial; vermelho: acima do máximo.")
    with st.expander("ℹ️ Limites e como são calculados", expanded=False):
        st.markdown(
            "**Os limites de pessoal variam por esfera, por Poder e no agregado** (LRF, arts. 19 e 20). O painel usa, "
            "para cada UF e Poder, o **limite legal** que se aplica a ela:\n\n"
            "| Despesa total com pessoal (% da RCL) | Total | Executivo | Legislativo | Judiciário | Ministério Público | Base legal |\n"
            "|---|---|---|---|---|---|---|\n"
            "| **Estados** (caso geral, inclui MS) | 60% | 49% | 3% (Assembleia + TCE) | 6% | 2% | art. 19, II; art. 20, II |\n"
            "| **Estados com Tribunal de Contas dos Municípios** (BA, GO, PA) | 60% | 48,6% | 3,4% (Assembleia + TCE + TCM) | 6% | 2% | art. 20, §4º |\n"
            "| **Distrito Federal** | 52%¹ | 49% | 3% | – (União) | – (União) | art. 20, II; CF, art. 21, XIII |\n"
            "| União (referência) | 50% | 40,9% | 2,5% (inclui TCU) | 6% | 0,6% | art. 19, I; art. 20, I |\n"
            "| Municípios (referência) | 60% | 54% | 6% (inclui TCM, se houver) | – | – | art. 19, III; art. 20, III |\n\n"
            "¹ O Judiciário e o Ministério Público do DF são organizados e mantidos pela União (CF, art. 21, XIII); "
            "não há RGF distrital desses Poderes, e o total do DF soma só os limites do Executivo e do Legislativo.\n\n"
            "- **Prudencial** = 95% do limite máximo (art. 22, parágrafo único) e **alerta** = 90% (art. 59, §1º, II), "
            "calculados sobre o limite de cada Poder ou do total. Ex.: Executivo de MS, 46,55% e 44,1%; Executivo da "
            "BA, 46,17% e 43,74%; total do Estado, 57% e 54%.\n"
            "- **Dentro de cada Poder**, a lei estadual reparte o limite entre os órgãos (art. 20, §1º; ex.: Assembleia "
            "e Tribunal de Contas dividem os 3% do Legislativo). O painel avalia o Poder inteiro, somando as instituições.\n"
            "- **Limite publicado × legal**: cada RGF também traz o limite que a própria UF calculou. Quando ele difere "
            "do legal em mais de 0,05 p.p., o gráfico mostra uma linha cinza tracejada e o quadro abaixo lista o caso "
            "(ex.: o CE ainda publica 3,4% no Legislativo, embora tenha extinto o TCM em 2017).\n"
            "- **Apurado**: DTP de cada instituição (Anexo 1, coluna 'Valor', em R$), somada por Poder e no total, ÷ RCL "
            "ajustada do RGF. Um ponto só aparece quando todas as instituições do Poder (e, no total, todos os Poderes) "
            "publicaram o RGF do quadrimestre.\n"
            "- **Defensoria Pública**: não tem limite próprio no art. 20 da LRF, e o RGF dela na API não traz DTP nem "
            "limites. O painel mostra a despesa líquida de 12 meses + restos a pagar não processados ÷ RCL ajustada, "
            "sem linhas de limite, e não a soma ao total do Estado.\n\n"
            "| Endividamento (Executivo, todas as UFs) | Limite máximo | Alerta (90%) | Base legal |\n|---|---|---|---|\n"
            "| Dívida consolidada líquida | 200% da RCL | 180% | Res. Senado 40/2001, art. 3º, I; LRF, art. 59, §1º, III |\n"
            "| Garantias concedidas | 22% | 19,8% | Res. Senado 43/2001, art. 9º |\n"
            "| Operações de crédito (no exercício) | 16% | 14,4% | Res. Senado 43/2001, art. 7º, I |\n\n"
            "Garantias só aparecem nas UFs que as concedem.")
    c = st.columns([1, 3])
    uf = _escolher(c[0], "Estado", todas_ufs, "gx_lrf_uf", "MS", format_func=lambda u: f"{u} – {regiao.get(u, '')}")
    lu = lrf[lrf["uf"] == uf]

    st.markdown(f"##### 👥 Despesa total com pessoal – {uf}, por Poder e no total")
    cols = st.columns(3)
    for i, grupo in enumerate([RG.TODOS, *RG.PODERES.values()]):
        t = lu[(lu["indicador"] == "Despesa total com pessoal") & (lu["grupo"] == grupo)]
        if t.empty:
            cols[i % 3].caption(f"{grupo}: sem dados.")
            continue
        ui.grafico(_fig_limite(t, _titulo_sit(t, grupo)), f"gx_lrf_p_{i}", "siconfi_rgf_uf", onde=cols[i % 3],
                   valores=False, nota="RGF, Anexo 1: DTP em R$ ÷ RCL ajustada; limites legais da LRF para esta UF "
                                       "e este Poder (prudencial = 95% e alerta = 90% do máximo)")

    st.markdown(f"##### 🏦 Endividamento – {uf} (Executivo)")
    cols = st.columns(3)
    for i, nome in enumerate(RG.ENDIVIDAMENTO):
        t = lu[lu["indicador"] == nome]
        if t.empty:
            cols[i].caption(f"{nome}: a UF não publicou o indicador (sem operações no período).")
            continue
        an = RG.ENDIVIDAMENTO[nome][0].replace("RGF-", "")
        ui.grafico(_fig_limite(t, _titulo_sit(t, nome)), f"gx_lrf_e_{i}", "siconfi_rgf_uf", onde=cols[i],
                   valores=False, nota=f"RGF, {an}: percentual publicado sobre a RCL ajustada")

    # ---- todas as UFs
    st.markdown("##### 🗺️ Todas as UFs")
    datas = sorted(lrf["data"].unique(), reverse=True)
    cont = lrf[lrf["grupo"] == RG.TODOS].groupby("data")["uf"].nunique()
    padrao = next((d for d in datas if cont.get(d, 0) >= 0.8 * len(todas_ufs)), datas[0])
    c = st.columns([1, 1.6, 2])
    ref = c[0].selectbox("Fim do quadrimestre", datas, index=datas.index(padrao),
                         format_func=lambda d: pd.Timestamp(d).strftime("%m/%Y"), key="gx_lrf_ref",
                         help="O padrão é o quadrimestre mais recente em que ao menos 80% das UFs publicaram o RGF "
                              "de todos os Poderes com limite.")
    opcoes = [f"Pessoal – {g}" for g in GRUPOS_PESSOAL if g != RG.PODERES["D"]] + list(RG.ENDIVIDAMENTO)
    escolha = c[1].selectbox("Indicador do ranking", opcoes, key="gx_lrf_ind")
    x = lrf[lrf["data"] == ref].copy()
    x["sit"] = x.apply(_sit, axis=1)
    if escolha.startswith("Pessoal – "):
        r = x[(x["indicador"] == "Despesa total com pessoal") & (x["grupo"] == escolha.split(" – ", 1)[1])]
    else:
        r = x[x["indicador"] == escolha]
    r = r.assign(uso=100 * r["valor"] / r["maximo"]).dropna(subset=["uso"]).sort_values("uso", ascending=False)
    vis = st.radio("Leitura do ranking", ["Uso do limite da própria UF (%)", "% da RCL, com o limite legal de cada UF"],
                   horizontal=True, key="gx_lrf_vis",
                   help="Os limites diferem entre UFs (Executivo de BA, GO e PA: 48,6%; Legislativo: 3,4%; total do DF: "
                        "52%). O uso do limite (apurado ÷ limite da UF) põe todas na mesma régua; a segunda leitura "
                        "mostra o percentual bruto e marca o limite de cada UF.")
    if not r.empty:
        cd = list(zip(r["valor"], r["maximo"], r["sit"], r["base_legal"]))
        hover = ("%{x}: apurado %{customdata[0]:,.2f}% da RCL ajustada<br>limite legal %{customdata[1]:,.2f}% "
                 "(%{customdata[3]})<br>usa " + ("%{y:,.1f}" if vis.startswith("Uso") else "%{text}") +
                 "% do limite · %{customdata[2]}<extra></extra>")
        if vis.startswith("Uso"):
            fig = go.Figure(go.Bar(x=r["uf"], y=r["uso"], marker_color=[SITUACOES[s][0] for s in r["sit"]],
                                   marker_line_width=0, customdata=cd, hovertemplate=hover))
            for nivel, nome, cor, pos in ((100, "máximo 100%", G.STATUS["critico"], "top right"),
                                          (95, "", G.STATUS["serio"], "top right"),
                                          (90, "alerta 90%", G.STATUS["alerta"], "bottom right")):
                if nivel != 95 or r["prudencial"].notna().any():
                    fig.add_hline(y=nivel, line_dash="dot", line_color=cor, line_width=1.5, annotation_text=nome,
                                  annotation_position=pos, annotation_font_size=11)
            titulo = f"{escolha}: quanto do limite legal de cada UF está sendo usado, {pd.Timestamp(ref):%m/%Y}"
        else:
            r = r.sort_values("valor", ascending=False)
            cd = list(zip(r["valor"], r["maximo"], r["sit"], r["base_legal"]))
            fig = go.Figure(go.Bar(x=r["uf"], y=r["valor"], marker_color=[SITUACOES[s][0] for s in r["sit"]],
                                   marker_line_width=0, customdata=cd, text=[f"{u:,.1f}" for u in r["uso"]],
                                   textposition="none", hovertemplate=hover, name="Apurado"))
            for col, nome, cor, simb in (("maximo", "Limite máximo da UF", G.STATUS["critico"], "line-ew-open"),
                                         ("prudencial", "Prudencial da UF", G.STATUS["serio"], "line-ew-open"),
                                         ("alerta", "Alerta da UF", G.STATUS["alerta"], "line-ew-open")):
                if r[col].notna().any():
                    fig.add_scatter(x=r["uf"], y=r[col], mode="markers", name=nome,
                                    marker=dict(symbol=simb, size=22, color=cor, line=dict(width=3, color=cor)),
                                    hovertemplate=f"{nome}: %{{y:,.2f}}%<extra></extra>")
            titulo = f"{escolha}: % da RCL ajustada e o limite legal de cada UF, {pd.Timestamp(ref):%m/%Y}"
        G._layout(fig, titulo, 420, legenda=not vis.startswith("Uso"))
        fig.update_layout(hovermode="closest")
        fig.update_yaxes(ticksuffix="%", rangemode="tozero")
        fig.update_layout(bargap=0.25)
        c[2].caption("Os limites legais diferem entre UFs: Executivo 48,6% e Legislativo 3,4% em BA, GO e PA (art. 20, "
                     "§4º); total de 52% no DF. Uso do limite = apurado ÷ limite legal da própria UF; alerta em 90% e "
                     "prudencial em 95% (só pessoal). A cor da barra é a situação.")
        ui.grafico(fig, "gx_lrf_rank", "siconfi_rgf_uf", valores=False,
                   nota="RGF de cada UF; pessoal: Anexo 1 (R$ ÷ RCL ajustada); endividamento: Anexos 2 a 4")

    # quadro de cumprimento: UF × indicador
    x["coluna"] = [f"Pessoal – {g}" if i == "Despesa total com pessoal" else i for i, g in zip(x["indicador"], x["grupo"])]
    ordem = [f"Pessoal – {g}" for g in GRUPOS_PESSOAL] + list(RG.ENDIVIDAMENTO)
    val = x.pivot_table(index="uf", columns="coluna", values="valor", aggfunc="first").reindex(columns=ordem)
    sit = x.pivot_table(index="uf", columns="coluna", values="sit", aggfunc="first").reindex(columns=ordem)
    val = val.dropna(axis=1, how="all")
    sit = sit[val.columns]
    txt = val.copy().astype(object)
    for c_ in val.columns:
        txt[c_] = [("" if pd.isna(v) else f"{SITUACOES.get(s, ('', ''))[1]} {G.pct(v, 2)}") for v, s in
                   zip(val[c_], sit[c_])]
    txt = txt.reindex(sorted(txt.index)).fillna("")
    sit = sit.reindex(txt.index)

    def _cor(col):
        return [f"background-color: {SITUACOES.get(s, (None,))[0]}33" if isinstance(s, str) and s in SITUACOES
                and s not in ("sem dado", "sem limite próprio") else "" for s in sit[col.name]]

    st.markdown(f"**Quadro de cumprimento em {pd.Timestamp(ref):%m/%Y}** (% da RCL ajustada; ícone e cor = situação "
                "em relação ao limite legal de cada UF e Poder — 49%/3% em geral, 48,6%/3,4% em BA, GO e PA; total 60%, "
                "ou 52% no DF)")
    st.dataframe(txt.rename_axis("UF").style.apply(_cor), width="stretch", height=min(990, 40 + 35 * len(txt)))
    tab = x[["uf", "coluna", "valor", "alerta", "prudencial", "maximo", "base_legal", "maximo_publicado", "sit"]].rename(
        columns={"uf": "UF", "coluna": "Indicador", "valor": "Apurado (% RCL aj.)", "alerta": "Alerta (%)",
                 "prudencial": "Prudencial (%)", "maximo": "Máximo legal (%)", "base_legal": "Base legal",
                 "maximo_publicado": "Máximo publicado pela UF (%)", "sit": "Situação"})
    div = lrf[lrf["divergencia"].fillna(False)]
    if not div.empty:
        with st.expander(f"⚠️ Limites publicados diferentes do limite legal ({div['uf'].nunique()} UFs)", expanded=False):
            st.markdown("O painel avalia sempre pelo **limite legal**; a lista mostra onde o limite que a UF publicou no "
                        "RGF difere dele em mais de 0,05 p.p.")
            dv = (div.groupby(["uf", "grupo"]).agg(quadrimestres=("data", "count"), legal=("maximo", "first"),
                                                   publicado_min=("maximo_publicado", "min"),
                                                   publicado_max=("maximo_publicado", "max"),
                                                   ultimo=("data", "max"))
                  .reset_index())
            dv["ultimo"] = dv["ultimo"].dt.strftime("%m/%Y")
            ui.tabela(dv.rename(columns={"uf": "UF", "grupo": "Poder", "quadrimestres": "Quadrimestres",
                                         "legal": "Máximo legal (%)", "publicado_min": "Publicado – mínimo (%)",
                                         "publicado_max": "Publicado – máximo (%)", "ultimo": "Último caso"}),
                      "gx_lrf_div", pct=["Máximo legal (%)", "Publicado – mínimo (%)", "Publicado – máximo (%)"],
                      ordenar_padrao="UF", fontes=["siconfi_rgf_uf"], nota="RGF, Anexo 1, linha 'LIMITE MÁXIMO'")
    with st.expander("📋 Tabela detalhada (com download)", expanded=False):
        ui.tabela(tab, "gx_lrf_tab", pct=["Apurado (% RCL aj.)", "Alerta (%)", "Prudencial (%)", "Máximo legal (%)",
                                          "Máximo publicado pela UF (%)"],
                  ordenar_padrao="UF", fontes=["siconfi_rgf_uf"], nota=f"RGF de todas as UFs, {pd.Timestamp(ref):%m/%Y}")
