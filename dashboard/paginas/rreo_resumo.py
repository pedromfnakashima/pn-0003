"""RREO › aba Resumo: MS diante das demais UFs nos indicadores do "RREO em Foco" (Tesouro Nacional), com séries
temporais, estatísticas descritivas e os pontos em que MS se destaca negativamente."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import indicadores_rreo as IR
from ms_fiscal import rreo_em_foco as RF
from ms_fiscal import ui

UF = "MS"
PUBLICACAO = "https://www.tesourotransparente.gov.br/publicacoes/rreo-em-foco-estados-e-df/2026/16"
BIM = {1: "1º bim (jan–fev)", 2: "2º bim (jan–abr)", 3: "3º bim (jan–jun)", 4: "4º bim (jan–ago)",
       5: "5º bim (jan–out)", 6: "6º bim (jan–dez)"}
PRINCIPAIS = ["poupanca_corrente", "res_orcamentario", "primario_sem_rpps", "primario_com_rpps", "dif_crescimento",
              "pessoal_rt", "despesa_rt", "rpps_capitalizacao", "var_divida", "invest_rt", "dependencia"]


def _fmt(v: float, unid: str) -> str:
    if v is None or pd.isna(v):
        return "–"
    return (f"{v:+,.1f} p.p." if unid == "p.p." else f"{v:,.1f}%").replace(",", "X").replace(".", ",").replace("X", ".")


def _rotulo(a: int, b: int) -> str:
    return f"{b}º bim/{a}"


@st.cache_data(show_spinner=False, max_entries=64)
def _estatisticas(assin: str, indicador: str, uf: str) -> pd.DataFrame:
    """IR.estatisticas em cache: percorre todos os bimestres e roda a cada interação com a página."""
    return IR.estatisticas(ui.rreo_uf()["indicadores"], indicador, uf)


def render() -> None:
    dados = ui.rreo_uf()
    ind = dados.get("indicadores")
    if ind is None or ind.empty:
        ui.sem_dados("RREO de todas as UFs", "python coletar.py --rreo-estados")
        return
    st.markdown(
        f"### {UF} diante das demais UFs: indicadores do *RREO em Foco*\n"
        "O Tesouro Nacional publica a cada bimestre o **RREO em Foco: Estados + DF**, que compara as UFs em "
        f"indicadores tirados do RREO ([página da publicação no Tesouro Transparente]({PUBLICACAO}); PDFs do "
        f"[3º bimestre]({RF.EDICOES[(2026, 3)][0]}) e do [4º bimestre de 2026]({RF.EDICOES[(2026, 4)][0]})). "
        "O painel recalcula esses "
        "indicadores para **todas as UFs e todos os bimestres desde 2023**, com o RREO do Siconfi, e mostra onde "
        f"{UF} fica entre as 27.")
    periodos = ind[["exercicio", "periodo"]].drop_duplicates().sort_values(["exercicio", "periodo"], ascending=False)
    opcoes = [tuple(map(int, x)) for x in periodos.itertuples(index=False)]
    c = st.columns([1.2, 3])
    a, b = c[0].selectbox("Bimestre de referência", opcoes, format_func=lambda x: _rotulo(*x), key="rr_res_per",
                          help="Os indicadores acumulam de janeiro ao fim do bimestre. O padrão é o último bimestre "
                               "com dados.")
    c[1].caption(f"Valores acumulados de janeiro ao fim do {b}º bimestre de {a}. Posição: 1 = pior entre as UFs "
                 "com dado no bimestre (o sentido de \"pior\" depende do indicador). Mediana e quartis: das 27 UFs.")

    # ---------------------------------------------------------------- quadro geral e destaques
    resumo = []
    for k in PRINCIPAIS:
        e = _estatisticas(dados["assin"], k, UF)
        lin = e[(e["exercicio"] == a) & (e["periodo"] == b)]
        if lin.empty or pd.isna(lin["valor_uf"].iat[0]):
            continue
        r = lin.iloc[0]
        ant = e[(e["exercicio"] == a - 1) & (e["periodo"] == b)]
        resumo.append({"chave": k, "titulo": IR.INDICADORES[k][0], "unid": IR.INDICADORES[k][1],
                       "pior": IR.INDICADORES[k][2], "valor": r["valor_uf"], "posicao": int(r["posicao"]),
                       "n": int(r["n"]), "mediana": r["mediana"], "p25": r["p25"], "p75": r["p75"],
                       "ant": ant["valor_uf"].iat[0] if not ant.empty else None})
    if not resumo:
        st.info(f"Sem indicadores de {UF} para o bimestre escolhido.")
        return
    res = pd.DataFrame(resumo)
    neg = res[res["posicao"] <= res["n"] / 4].sort_values("posicao")

    with st.container(border=True):
        if neg.empty:
            st.markdown(f"**{UF} não está no quartil pior de nenhum dos indicadores** no {b}º bimestre de {a}.")
        else:
            itens = [f"- **{r.titulo}**: {_fmt(r.valor, r.unid)} — **{r.posicao}ª pior** de {r.n} UFs "
                     f"(mediana {_fmt(r.mediana, r.unid)})" for r in neg.itertuples()]
            st.markdown(f"**⚠️ Destaques negativos de {UF} no {b}º bimestre de {a}** (quartil pior entre as UFs):\n\n"
                        + "\n".join(itens))

    cols = st.columns(4)
    for i, r in enumerate(res.sort_values("posicao").itertuples()):
        ruim = r.posicao <= r.n / 4
        with cols[i % 4].container(border=True):
            delta = None
            if r.ant is not None and not pd.isna(r.ant):
                d = r.valor - r.ant
                delta = (f"{d:+,.1f} p.p.".replace(",", "X").replace(".", ",").replace("X", ".")
                         + f" vs {b}º bim/{a - 1}")
            st.metric(r.titulo, _fmt(r.valor, r.unid), delta,
                      delta_color="inverse" if r.pior == "maior" else "normal",
                      help=f"{IR.INDICADORES[r.chave][3]}\n\n**Fórmula:** {IR.FORMULAS[r.chave][0]}\n\n"
                           f"**Período:** {RF.periodo(r.chave, a, b)}\n\n{RF.tooltip(r.chave, a, b)}")
            st.badge(f"{r.posicao}ª pior de {r.n}" if ruim else f"posição {r.posicao} de {r.n} (1 = pior)",
                     color="red" if ruim else ("orange" if r.posicao <= r.n / 2 else "green"),
                     icon=":material/warning:" if ruim else None)
            st.caption(f"Mediana das UFs: {_fmt(r.mediana, r.unid)} · 1º–3º quartil: {_fmt(r.p25, r.unid)} a "
                       f"{_fmt(r.p75, r.unid)}")

    _metodologia()

    # ---------------------------------------------------------------- um indicador em detalhe
    st.divider()
    st.markdown("#### 🔎 Um indicador em detalhe: série temporal, ranking e estatísticas descritivas")
    disp = [k for k in IR.INDICADORES if k in set(ind["indicador"])]
    padrao = neg["chave"].iat[0] if not neg.empty else disp[0]
    k = st.selectbox("Indicador", disp, index=disp.index(padrao), format_func=lambda x: IR.INDICADORES[x][0],
                     key="rr_res_ind")
    titulo, unid, pior, expl = IR.INDICADORES[k]
    st.info(f"**{titulo}.** {expl} **Pior quando {pior}.**\n\n**Fórmula:** {IR.FORMULAS[k][0]} · referência: "
            f"RREO em Foco, {IR.FORMULAS[k][2]}", icon="📐")
    comp = IR.componentes(ind, k, UF, a, b)
    vk = ind[(ind["indicador"] == k) & (ind["uf"] == UF) & (ind["exercicio"] == a) & (ind["periodo"] == b)]["valor"]
    if not comp.empty:
        with st.expander(f"🧮 Cálculo para {UF} no {b}º bimestre de {a}: termos da fórmula, em R$", expanded=True):
            ui.tabela(comp, "rr_res_comp", moeda=["Valor (R$)"], ordenar_padrao="(ordem original)",
                      fontes=["siconfi_rreo_uf"], nota=f"RREO de {UF}, {b}º bimestre de {a}")
            if not vk.empty:
                st.markdown(f"**Resultado:** {IR.FORMULAS[k][0]} = **{_fmt(vk.iat[0], unid)}**")
    e = _estatisticas(dados["assin"], k, UF).sort_values("data")
    if e.empty:
        st.info("Poucas UFs com esse indicador.")
        return
    e["rotulo"] = [_rotulo(x, y) for x, y in zip(e["exercicio"], e["periodo"])]
    suf = " p.p." if unid == "p.p." else "%"

    so_mesmo = st.toggle(f"Só o {b}º bimestre de cada ano", value=False, key="rr_res_mesmo",
                         help="Os indicadores acumulam no ano e têm sazonalidade (o IPVA entra no início do ano, o 13º "
                              "no fim). Comparar o mesmo bimestre entre anos elimina esse efeito.")
    ee = e[e["periodo"] == b] if so_mesmo else e
    fig = go.Figure()
    fig.add_scatter(x=ee["rotulo"], y=ee["p75"], mode="lines", line=dict(width=0), showlegend=False,
                    hoverinfo="skip")
    fig.add_scatter(x=ee["rotulo"], y=ee["p25"], mode="lines", line=dict(width=0), fill="tonexty",
                    fillcolor="rgba(154,152,147,0.25)", name="1º a 3º quartil das UFs",
                    hovertemplate="1º quartil: %{y:,.2f}" + suf + "<extra></extra>")
    fig.add_scatter(x=ee["rotulo"], y=ee["mediana"], mode="lines+markers", name="Mediana das UFs",
                    line=dict(color=G.OUTROS, width=2, dash="dot"), marker=dict(size=6),
                    hovertemplate="Mediana: %{y:,.2f}" + suf + "<extra></extra>")
    fig.add_scatter(x=ee["rotulo"], y=ee["valor_uf"], mode="lines+markers", name=UF,
                    line=dict(color=G.CORES[0], width=2.5), marker=dict(size=9),
                    customdata=ee[["posicao", "n"]].to_numpy(),
                    hovertemplate=UF + ": %{y:,.2f}" + suf + " · %{customdata[0]}ª pior de %{customdata[1]}<extra></extra>")
    G._layout(fig, f"{titulo}: {UF} × demais UFs<br><sup>{_subtitulo(k)}{_sufixo_rcl(k)}</sup>", 440)
    fig.update_yaxes(ticksuffix=suf)
    fig.update_xaxes(type="category")
    if (ee[["valor_uf", "p25", "p75"]] < 0).any().any():
        fig.add_hline(y=0, line_color="rgba(128,128,128,0.6)", line_width=1)
    ui.grafico(fig, "rr_res_serie", "siconfi_rreo_uf", valores=False,
               nota="RREO de todas as UFs; indicador recalculado com as definições do RREO em Foco (STN); faixa cinza: "
                    "metade central das UFs")
    st.caption("ℹ️ Paralelo no RREO em Foco (passe o mouse no ícone ao lado)", help=RF.tooltip(k, a, b))

    # ranking num bimestre à escolha (MS sempre destacado)
    pers = [tuple(map(int, x)) for x in ind.loc[ind["indicador"] == k, ["exercicio", "periodo"]]
            .drop_duplicates().sort_values(["exercicio", "periodo"], ascending=False).itertuples(index=False)]
    c = st.columns([1.2, 3])
    ra, rb = c[0].selectbox("Bimestre do ranking", pers, index=pers.index((a, b)) if (a, b) in pers else 0,
                            format_func=lambda x: _rotulo(*x), key=f"rr_res_rank_per_{k}",
                            help="Escolha o bimestre do gráfico abaixo. Os valores são acumulados de janeiro ao fim do "
                                 "bimestre escolhido. " + RF.tooltip(k, *pers[0]).split("\n\n")[0])
    c[1].markdown(f"**Período do ranking:** {RF.periodo(k, ra, rb)}. "
                  + ("Numerador acumulado no ano; denominador = RCL dos 12 meses encerrados no bimestre × "
                     f"{2 * rb}/12 (RCL proporcional). " if "RCL" in titulo else "")
                  + "Não é o valor só do bimestre nem de 12 meses.")
    d = ind[(ind["indicador"] == k) & (ind["exercicio"] == ra) & (ind["periodo"] == rb)].copy()
    d = d.sort_values("valor", ascending=(pior == "menor"))
    if not d.empty:
        pos = list(d["uf"]).index(UF) + 1 if UF in set(d["uf"]) else None
        cores = [G.CORES[0] if u == UF else G.SEQ[1] for u in d["uf"]]
        fig = go.Figure(go.Bar(x=d["uf"], y=d["valor"], marker_color=cores, marker_line_width=0,
                               text=[UF if u == UF else "" for u in d["uf"]], textposition="outside",
                               hovertemplate="%{x}: %{y:,.2f}" + suf + "<extra></extra>"))
        fig.add_hline(y=d["valor"].median(), line_dash="dot", line_color=G.OUTROS, annotation_text="mediana",
                      annotation_position="top right")
        G._layout(fig, f"{titulo} – {RF.periodo(k, ra, rb)}<br><sup>Das piores (à esquerda) para as melhores"
                       + (f"; {UF} em azul-escuro: {pos}ª pior de {len(d)}" if pos else f"; {UF} sem dado") + "</sup>",
                  420, legenda=False)
        fig.update_yaxes(ticksuffix=suf)
        fig.update_layout(bargap=0.25, margin=dict(t=72))
        ui.grafico(fig, "rr_res_rank", "siconfi_rreo_uf", valores=False,
                   nota=f"{UF} em destaque; bimestre escolhido na caixa acima")
        st.caption("ℹ️ Paralelo no RREO em Foco para este bimestre (passe o mouse no ícone ao lado)",
                   help=RF.tooltip(k, ra, rb))

    # estatísticas descritivas por bimestre
    tab = e.sort_values("data", ascending=False)[[
        "rotulo", "n", "minimo", "p25", "mediana", "media", "p75", "maximo", "desvio", "valor_uf", "posicao",
        "dif_mediana", "z", "pior_uf", "pior_valor"]].rename(columns={
            "rotulo": "Bimestre", "n": "UFs", "minimo": "Mínimo", "p25": "1º quartil", "mediana": "Mediana",
            "media": "Média", "p75": "3º quartil", "maximo": "Máximo", "desvio": "Desvio-padrão", "valor_uf": UF,
            "posicao": f"Posição de {UF} (1 = pior)", "dif_mediana": f"{UF} − mediana", "z": "Escore z",
            "pior_uf": "Pior UF", "pior_valor": "Valor da pior"})
    num = ["Mínimo", "1º quartil", "Mediana", "Média", "3º quartil", "Máximo", "Desvio-padrão", UF, f"{UF} − mediana",
           "Valor da pior"]
    st.markdown(f"**Estatísticas descritivas entre as UFs, bimestre a bimestre** ({titulo}, em {unid}; cada linha "
                "acumula de janeiro ao fim do bimestre)",
                help="As estatísticas do painel resumem as 27 UFs; o RREO em Foco mostra os valores de cada UF no "
                     "gráfico e na tabela indicados a seguir, sem quartis nem mediana.\n\n" + RF.tooltip(k, a, b))
    ui.tabela(tab, "rr_res_tab", pct=num + ["Escore z"], ordenar_padrao="(ordem original)",
              fontes=["siconfi_rreo_uf"], nota="cada linha resume as UFs com dado naquele bimestre")
    with st.expander("ℹ️ Como ler as estatísticas descritivas", expanded=True):
        st.markdown(
            "- **Mínimo e máximo**: os extremos entre as UFs no bimestre.\n"
            "- **1º quartil, mediana e 3º quartil**: dividem as UFs em quatro grupos de mesmo tamanho. A mediana é a UF "
            "do meio; metade das UFs está entre o 1º e o 3º quartil (faixa cinza do gráfico). A mediana é preferível à "
            "média porque não é puxada por valores extremos (SP, RJ e MG pesam muito nas somas, mas aqui cada UF conta "
            "uma vez).\n"
            "- **Média e desvio-padrão**: média simples das UFs e a dispersão típica em torno dela.\n"
            f"- **Posição de {UF}**: 1 = pior UF no indicador. Na 7ª posição ou antes, {UF} está no quartil pior "
            "(destaque negativo).\n"
            f"- **{UF} − mediana**: distância, em pontos percentuais, entre {UF} e a UF típica.\n"
            f"- **Escore z**: ({UF} − média) ÷ desvio-padrão. Em módulo acima de 1, {UF} está longe do padrão das UFs; "
            "acima de 2, é um caso extremo.\n"
            "**Como são calculadas** (para cada bimestre, sobre as UFs com o indicador disponível — a coluna *UFs*):\n"
            "- *Mínimo, máximo, média*: os usuais; a média é simples (cada UF pesa 1).\n"
            "- *Quartis e mediana*: método de interpolação linear entre as UFs ordenadas (o mesmo do QUARTIL.INC do "
            "Excel): com 27 UFs, a mediana é a 14ª, o 1º quartil fica entre a 7ª e a 8ª e o 3º quartil entre a 20ª e "
            "a 21ª.\n"
            "- *Desvio-padrão*: amostral, √[Σ(xᵢ − média)² ÷ (n − 1)].\n"
            "- *Posição*: as UFs são ordenadas da pior para a melhor (do maior para o menor valor quando \"pior quando "
            "maior\"; ao contrário quando \"pior quando menor\"); 1 = pior. **Destaque negativo** = posição ≤ n ÷ 4.\n"
            f"- *{UF} − mediana*: valor de {UF} menos a mediana, em pontos percentuais.\n"
            f"- *Escore z*: ({UF} − média) ÷ desvio-padrão.\n"
            "- *Variação nos cartões*: valor do bimestre menos o valor do mesmo bimestre do ano anterior, em p.p.\n\n"
            "- **Cuidados**: os indicadores acumulam de janeiro ao fim do bimestre e têm sazonalidade — compare o mesmo "
            "bimestre entre anos (opção acima do gráfico). As UFs que entregam o RREO com atraso ficam fora do "
            "bimestre até a entrega.")

    # ---------------------------------------------------------------- conferência com a publicação
    with st.expander("✅ Conferência com o RREO em Foco publicado pelo Tesouro (3º e 4º bimestres de 2026)",
                     expanded=False):
        linhas = []
        for (ea, eb), vals in sorted(RF.PUBLICADO_MS.items()):
            for kk, (pub, txt) in vals.items():
                if pub is None:
                    continue
                v = ind[(ind["indicador"] == kk) & (ind["uf"] == UF) & (ind["exercicio"] == ea) & (ind["periodo"] == eb)]
                linhas.append({"Edição": f"{eb}º bim/{ea}", "Indicador": IR.INDICADORES[kk][0],
                               "Publicado (STN)": pub, "Calculado pelo painel": v["valor"].iat[0] if not v.empty else None,
                               "Como foi publicado": txt})
        conf = pd.DataFrame(linhas)
        conf["Diferença"] = conf["Calculado pelo painel"] - conf["Publicado (STN)"]
        st.markdown(f"Valores de {UF} publicados pelo Tesouro nas edições do 3º bimestre "
                    f"({RF.EDICOES[(2026, 3)][0]}) e do 4º bimestre ({RF.EDICOES[(2026, 4)][0]}) de 2026 (arredondados, em geral, ao inteiro) e "
                    "os calculados pelo painel com os dados do Siconfi. As diferenças se devem ao arredondamento da "
                    "publicação e à data de extração (3º bim: 03/08/2026; 4º bim: 01/10/2026; o painel usa o Siconfi "
                    "mais recente, com retificações e entregas atrasadas).")
        ui.tabela(conf, "rr_res_conf", pct=["Publicado (STN)", "Calculado pelo painel", "Diferença"],
                  ordenar_padrao="(ordem original)", fontes=["siconfi_rreo_uf"],
                  nota="RREO em Foco, edições do 3º e 4º bimestres de 2026")
        st.markdown(
            "**Definições conferidas com a publicação**: receitas e despesas incluem as intraorçamentárias; as "
            "transferências a municípios registradas como despesa são deduzidas das receitas e das despesas (nota 2 da "
            "publicação); as despesas são as **liquidadas** (o texto da publicação fala em empenhadas nos Gráficos 1 e "
            "2, mas os valores publicados correspondem às liquidadas); RCL proporcional = RCL de 12 meses × meses "
            "decorridos ÷ 12.")


def _metodologia() -> None:
    with st.expander("📐 Metodologia: como cada indicador é calculado", expanded=False):
        st.markdown(
            "Todos os indicadores usam valores **acumulados de janeiro ao fim do bimestre**, tirados do RREO que cada "
            "UF entregou ao Siconfi, e seguem as convenções do *RREO em Foco* (Tesouro Nacional), conferidas com a "
            "edição do 3º bimestre de 2026:\n"
            "1. receitas e despesas **incluem as intraorçamentárias**;\n"
            "2. as **transferências a municípios** registradas como despesa (TM) são **deduzidas** das receitas e das "
            "despesas correntes e totais, para que as UFs que as contabilizam como despesa (como MS) sejam comparáveis "
            "às que as deduzem da receita;\n"
            "3. as despesas são as **liquidadas** (o texto da publicação fala em empenhadas nos Gráficos 1 e 2, mas os "
            "números publicados são os liquidados);\n"
            "4. os indicadores \"÷ RCL\" usam a **RCL proporcional** ao período, porque o numerador acumula só os meses "
            "decorridos do ano.")
        tab = pd.DataFrame([{"Indicador": IR.INDICADORES[k][0], "Fórmula": f[0], "Unidade": IR.INDICADORES[k][1],
                             "Pior quando": IR.INDICADORES[k][2], "No RREO em Foco": f[2]}
                            for k, f in IR.FORMULAS.items()])
        st.markdown("**Fórmulas**")
        st.dataframe(tab, hide_index=True, width="stretch")
        st.markdown("**Termos das fórmulas e linhas do RREO usadas**")
        st.dataframe(pd.DataFrame([{"Termo": n, "Como é obtido": d} for n, d in IR.TERMOS.values()]),
                     hide_index=True, width="stretch")
        st.caption("Para ver os valores em R$ de cada termo no cálculo de MS, escolha o indicador em \"Um indicador "
                   "em detalhe\", abaixo.")


def _sufixo_rcl(k: str) -> str:
    if "RCL" not in IR.INDICADORES[k][0]:
        return ""
    return "; denominador: RCL de 12 meses × meses decorridos ÷ 12 (RCL proporcional)"


def _subtitulo(k: str) -> str:
    if k == "var_divida":
        return "Cada ponto: variação da dívida de 31/12 do ano anterior até o fim do bimestre indicado"
    if k in ("cresc_receita", "cresc_despesa", "dif_crescimento"):
        return ("Cada ponto: janeiro até o fim do bimestre indicado, contra o mesmo período do ano anterior "
                "(não é só o bimestre nem 12 meses)")
    return "Cada ponto acumula de janeiro ao fim do bimestre indicado (não é só o bimestre nem 12 meses)"
