"""RGF › aba Resumo: cumprimento dos limites da LRF e das resoluções do Senado por Mato Grosso do Sul."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import rgf_estados as RG
from ms_fiscal import ui
from paginas.rgf_anexos import SITUACOES, _fig_limite, _sit, _titulo_sit

UF = "MS"
ORDEM = [("Despesa total com pessoal", RG.TODOS), ("Despesa total com pessoal", "Executivo"),
         ("Despesa total com pessoal", "Legislativo"), ("Despesa total com pessoal", "Judiciário"),
         ("Despesa total com pessoal", "Ministério Público"), ("Dívida consolidada líquida", "Executivo"),
         ("Garantias concedidas", "Executivo"), ("Operações de crédito", "Executivo")]
CONSEQUENCIAS = {
    "acima do limite de alerta": "o Tribunal de Contas emite alerta ao Poder (LRF, art. 59, §1º).",
    "acima do limite prudencial": "ficam vedados, entre outros, aumentos de remuneração, criação de cargos, novas "
                                  "admissões (salvo reposições em educação, saúde e segurança) e horas extras "
                                  "(LRF, art. 22, parágrafo único).",
    "acima do limite máximo": "o excesso tem de ser eliminado nos dois quadrimestres seguintes, com ao menos um terço "
                              "no primeiro; enquanto isso, o ente não recebe transferências voluntárias nem contrata "
                              "operações de crédito (LRF, art. 23).",
}


def _nome(ind: str, grupo: str) -> str:
    if ind == "Despesa total com pessoal":
        return "Pessoal – total do Estado" if grupo == RG.TODOS else f"Pessoal – {grupo}"
    return ind


def render() -> None:
    lrf = ui.rgf_uf().get("lrf")
    if lrf is None or lrf.empty:
        ui.sem_dados("RGF de todas as UFs", "python coletar.py --rgf-estados")
        return
    ms = lrf[lrf["uf"] == UF].copy()
    if ms.empty:
        st.info(f"Sem RGF de {UF}.")
        return
    ms["sit"] = ms.apply(_sit, axis=1)
    datas = sorted(ms["data"].unique(), reverse=True)
    c = st.columns([1, 3])
    ref = c[0].selectbox("Fim do quadrimestre", datas, format_func=lambda d: pd.Timestamp(d).strftime("%m/%Y"),
                         key="rg_res_ref", help="Abril = 1º quadrimestre; agosto = 2º; dezembro = 3º.")
    q = {4: 1, 8: 2, 12: 3}[pd.Timestamp(ref).month]
    st.markdown(f"### {UF} e os limites da LRF – {q}º quadrimestre de {pd.Timestamp(ref).year}")
    c[1].caption("Despesa com pessoal: últimos 12 meses ÷ RCL ajustada, por Poder (limites publicados no RGF de cada "
                 "instituição). Endividamento: saldo no fim do quadrimestre (dívida, garantias) ou acumulado no ano "
                 "(operações de crédito) ÷ RCL ajustada. A Defensoria Pública não tem limite próprio na LRF.")

    x = ms[ms["data"] == ref]
    linhas = []
    for ind, grupo in ORDEM:
        r = x[(x["indicador"] == ind) & (x["grupo"] == grupo)]
        if r.empty:
            continue
        r = r.iloc[0]
        rcl = r["valor_rs"] / r["valor"] * 100 if ind == "Despesa total com pessoal" and r["valor"] else None
        todas = lrf[(lrf["data"] == ref) & (lrf["indicador"] == ind) & (lrf["grupo"] == grupo)]
        uso_todas = (todas["valor"] / todas["maximo"]).sort_values(ascending=False).reset_index(drop=True)
        uso = r["valor"] / r["maximo"]
        linhas.append({
            "Indicador": _nome(ind, grupo), "Apurado (% RCL aj.)": r["valor"], "Alerta (%)": r["alerta"],
            "Prudencial (%)": r["prudencial"], "Máximo (%)": r["maximo"], "Uso do limite (%)": 100 * uso,
            "Folga até o máximo (p.p.)": r["maximo"] - r["valor"],
            "Folga até o máximo (R$)": (r["maximo"] - r["valor"]) / 100 * rcl if rcl else None,
            "Situação": r["sit"],
            "Posição entre as UFs (1 = maior uso)": int((uso_todas > uso).sum() + 1) if len(uso_todas) else None,
            "UFs": len(uso_todas), "Base legal do limite": r["base_legal"],
            "Máximo publicado no RGF (%)": r["maximo_publicado"]})
    t = pd.DataFrame(linhas)
    if t.empty:
        st.info("Sem indicadores para o quadrimestre escolhido.")
        return

    # ---- síntese em texto
    fora = t[t["Situação"] != "dentro dos limites"]
    frases = []
    if fora.empty:
        frases.append(f"Em {pd.Timestamp(ref):%m/%Y}, **{UF} cumpre todos os limites**, sem nenhum indicador acima "
                      "do alerta.")
    else:
        for r in fora.itertuples():
            frases.append(f"- {SITUACOES[r.Situação][1]} **{r.Indicador}**: {G.pct(r._2, 2)} da RCL ajustada, "
                          f"**{r.Situação}** (alerta {G.pct(r._3, 2)}"
                          + (f", prudencial {G.pct(r._4, 2)}" if not pd.isna(r._4) else "")
                          + f", máximo {G.pct(r._5, 2)}). Consequência: {CONSEQUENCIAS.get(r.Situação, '')}")
    dentro = t[t["Situação"] == "dentro dos limites"]["Indicador"].tolist()
    with st.container(border=True):
        st.markdown("**🧭 Em resumo**\n\n" + "\n".join(frases).replace("$", "\\$") +
                    (f"\n\nDentro dos limites: {', '.join(dentro)}." if dentro and not fora.empty else ""))

    # ---- cartões
    cols = st.columns(4)
    for i, r in enumerate(t.itertuples()):
        cor = {"dentro dos limites": "green", "acima do limite de alerta": "orange",
               "acima do limite prudencial": "orange", "acima do limite máximo": "red"}.get(r.Situação, "gray")
        with cols[i % 4].container(border=True):
            st.metric(r.Indicador, G.pct(r._2, 2),
                      help=f"Limite máximo {G.pct(r._5, 2)} da RCL ajustada ({r._12}); prudencial = 95% e alerta = "
                           f"90% desse limite.")
            st.caption(f"Limite: {G.pct(r._5, 1)} · {r._12}")
            st.badge(f"{SITUACOES[r.Situação][1]} {r.Situação}", color=cor)
            folga = f"Folga até o máximo: {r._7:,.2f} p.p.".replace(",", "X").replace(".", ",").replace("X", ".")
            if r._8 is not None and not pd.isna(r._8):
                folga += f" ({G.brl(r._8)})"
            st.caption(folga + f" · usa {r._6:,.0f}% do limite".replace(".", ",") +
                       f" · {r._10}ª maior utilização entre {r.UFs} UFs")

    # ---- uso do limite, todos os indicadores
    fig = go.Figure(go.Bar(y=t["Indicador"], x=t["Uso do limite (%)"], orientation="h", marker_line_width=0,
                           marker_color=[SITUACOES[s][0] for s in t["Situação"]],
                           text=[f"{v:,.1f}%".replace(".", ",") for v in t["Uso do limite (%)"]], textposition="outside",
                           customdata=t[["Apurado (% RCL aj.)", "Máximo (%)", "Situação"]].to_numpy(),
                           hovertemplate="%{y}: usa %{x:,.1f}% do limite<br>apurado %{customdata[0]:,.2f}% da RCL; "
                                         "máximo %{customdata[1]:,.2f}%<br>%{customdata[2]}<extra></extra>"))
    for nivel, cor in ((100, G.STATUS["critico"]), (95, G.STATUS["serio"]), (90, G.STATUS["alerta"])):
        fig.add_vline(x=nivel, line_dash="dot", line_color=cor, line_width=1.5)
    G._layout(fig, f"{UF}: quanto de cada limite está sendo usado, {pd.Timestamp(ref):%m/%Y}", 60 + 46 * len(t),
              legenda=False)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(ticksuffix="%", range=[0, max(110, t["Uso do limite (%)"].max() * 1.12)])
    ui.grafico(fig, "rg_res_uso", "siconfi_rgf_uf", valores=False,
               nota="uso do limite = apurado ÷ limite máximo; linhas pontilhadas: alerta (90%, amarela), prudencial "
                    "(95%, laranja, só pessoal) e máximo (100%, vermelha); cor da barra = situação; RGF de cada Poder, "
                    "Anexos 1 a 4")

    ui.tabela(t.drop(columns=["UFs"]).rename(columns={"Máximo (%)": "Máximo legal (%)"}), "rg_res_tab",
              pct=["Apurado (% RCL aj.)", "Alerta (%)", "Prudencial (%)", "Máximo legal (%)", "Uso do limite (%)",
                   "Folga até o máximo (p.p.)", "Máximo publicado no RGF (%)"], moeda=["Folga até o máximo (R$)"], ordenar_padrao="(ordem original)",
              fontes=["siconfi_rgf_uf"], nota=f"RGF de {UF}, {pd.Timestamp(ref):%m/%Y}")

    # ---- histórico: situação a cada quadrimestre
    st.markdown(f"##### 📅 Histórico: situação de {UF} em cada quadrimestre")
    h = ms.assign(Indicador=[_nome(i, g) for i, g in zip(ms["indicador"], ms["grupo"])])
    h = h[h["Indicador"].isin(t["Indicador"])]
    nomes = [n for n in t["Indicador"]]
    datas_h = sorted(h["data"].unique())
    niveis = {"dentro dos limites": 0, "acima do limite de alerta": 1, "acima do limite prudencial": 2,
              "acima do limite máximo": 3}
    z = [[niveis.get(h[(h["Indicador"] == n) & (h["data"] == d)]["sit"].squeeze() if not
          h[(h["Indicador"] == n) & (h["data"] == d)].empty else "", None) for d in datas_h] for n in nomes]
    txt = [[(lambda s: f"{s['valor'].iat[0]:,.1f}".replace(".", ",") if not s.empty else "")(
        h[(h["Indicador"] == n) & (h["data"] == d)]) for d in datas_h] for n in nomes]
    escala = [[0, G.STATUS["bom"]], [0.25, G.STATUS["bom"]], [0.25, G.STATUS["alerta"]], [0.5, G.STATUS["alerta"]],
              [0.5, G.STATUS["serio"]], [0.75, G.STATUS["serio"]], [0.75, G.STATUS["critico"]], [1, G.STATUS["critico"]]]
    fig = go.Figure(go.Heatmap(z=z, x=[pd.Timestamp(d).strftime("%m/%Y") for d in datas_h], y=nomes, text=txt,
                               texttemplate="%{text}", zmin=-0.5, zmax=3.5, colorscale=escala, showscale=False,
                               xgap=2, ygap=2, hovertemplate="%{y}, %{x}: %{text}% da RCL ajustada<extra></extra>"))
    G._layout(fig, "Valor apurado (% da RCL ajustada); cor = situação: verde dentro, amarelo alerta, laranja "
                   "prudencial, vermelho máximo", 60 + 40 * len(nomes), legenda=False)
    fig.update_yaxes(autorange="reversed")
    ui.grafico(fig, "rg_res_hist", "siconfi_rgf_uf", valores=False, nota="RGF de MS, todos os quadrimestres desde 2023")

    c = st.columns(2)
    for i, (ind, grupo) in enumerate([("Despesa total com pessoal", RG.TODOS), ("Despesa total com pessoal",
                                                                                  "Executivo")]):
        s = ms[(ms["indicador"] == ind) & (ms["grupo"] == grupo)]
        if not s.empty:
            ui.grafico(_fig_limite(s, _titulo_sit(s, _nome(ind, grupo)), 360), f"rg_res_lim_{i}", "siconfi_rgf_uf",
                       onde=c[i], valores=False, nota="RGF, Anexo 1: DTP e limites em R$ ÷ RCL ajustada")
    with st.expander("ℹ️ Limites considerados e base legal", expanded=False):
        st.markdown(
            "- **Os limites de pessoal variam por esfera e por Poder** (LRF, arts. 19 e 20): União 50% (Executivo "
            "40,9%, Legislativo 2,5%, Judiciário 6%, MPU 0,6%); Estados 60% (Executivo 49%, Legislativo 3%, "
            "Judiciário 6%, Ministério Público 2%); Municípios 60% (Executivo 54%, Legislativo 6%). Nos Estados com "
            "Tribunal de Contas dos Municípios (BA, GO e PA), o Legislativo sobe para 3,4% e o Executivo cai para 48,6% "
            "(art. 20, §4º).\n"
            "- **Limites de MS**: como Estado sem TCM, total de 60% da RCL (art. 19, II); Executivo 49% (art. 20, II, "
            "c); Legislativo 3%, para a Assembleia e o Tribunal de Contas juntos (art. 20, II, a; a lei estadual reparte "
            "entre os dois, §1º); Judiciário 6% (II, b); Ministério Público 2% (II, d). A Defensoria Pública não tem "
            "limite próprio no art. 20.\n"
            "- Limite prudencial = 95% do máximo do Poder (art. 22, parágrafo único); alerta = 90% (art. 59, §1º, II). "
            "Para o total do Estado: 57% e 54%.\n"
            "- **Dívida consolidada líquida**: até 200% da RCL (Res. Senado 40/2001); alerta em 90% (180%).\n"
            "- **Garantias**: até 22% da RCL (Res. Senado 43/2001, art. 9º); alerta em 90%.\n"
            "- **Operações de crédito**: até 16% da RCL no exercício (Res. Senado 43/2001, art. 7º, I); alerta em 90%.\n"
            "- O apurado é a DTP publicada no RGF de cada instituição, somada por Poder, ÷ RCL ajustada. Os limites são "
            "os legais; o limite publicado no RGF aparece na tabela para conferência.\n"
            "- A comparação com as demais UFs está na aba **Anexos › Limites da LRF**.")
