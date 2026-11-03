"""RREO – Relatório Resumido da Execução Orçamentária (LRF, arts. 52 e 53), bimestral."""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from ms_fiscal import graficos as G
from ms_fiscal import relatorios as REL
from ms_fiscal import ui
from paginas import rreo_anexos, rreo_resumo

ANEXOS = {
    "RREO-Anexo 01": "Balanço Orçamentário (receitas e despesas por categoria)",
    "RREO-Anexo 02": "Despesa por função e subfunção",
    "RREO-Anexo 03": "Receita Corrente Líquida (12 meses)",
    "RREO-Anexo 04": "Receitas e despesas previdenciárias (RPPS)",
    "RREO-Anexo 06": "Resultados primário e nominal",
    "RREO-Anexo 07": "Restos a pagar por Poder e órgão",
    "RREO-Anexo 08": "Manutenção e desenvolvimento do ensino (MDE)",
    "RREO-Anexo 09": "Operações de crédito e despesas de capital",
    "RREO-Anexo 10 - RPPS": "Projeção atuarial do RPPS",
    "RREO-Anexo 11": "Alienação de ativos e aplicação dos recursos",
    "RREO-Anexo 12": "Ações e serviços públicos de saúde (ASPS)",
    "RREO-Anexo 13": "Parcerias público-privadas",
    "RREO-Anexo 14": "Demonstrativo simplificado",
}


BIMESTRES = {1: "1º (jan–fev)", 2: "2º (mar–abr)", 3: "3º (mai–jun)", 4: "4º (jul–ago)", 5: "5º (set–out)",
             6: "6º (nov–dez)"}
VISOES = ["Acumulado no ano, por exercício", "Valor de cada bimestre, por exercício", "Sequência original"]

COLETA = ("**Coleta** (`python coletar.py --siconfi`): para cada bimestre que o Estado entregou ao Siconfi (lista do "
          "endpoint `/extrato_entregas`), o painel consulta a API `/rreo` em apidatalake.tesouro.gov.br (an_exercicio, "
          "nr_periodo = bimestre, co_tipo_demonstrativo=RREO, co_esfera=E, id_ente=50) e grava a resposta JSON em "
          "`dados/dashboard/rreo_AAAA_B.parquet`, um arquivo por bimestre.")


# ------------------------------------------------------------------ aba Resumo
NOTA_A14 = ("RREO, Anexo 14 (Demonstrativo Simplificado), que reúne os totais dos demais anexos; valores nominais "
            "acumulados de janeiro ao fim do bimestre")


def _cartao(col, titulo: str, valor: str, *, delta: str | None = None, cor_delta: str = "normal",
            selo: tuple[str, str] | None = None, detalhe: str | None = None, serie=None, ajuda: str | None = None,
            esticar: bool = True):
    """Cartão com borda: métrica (com minigráfico opcional), selo de situação e uma linha de contexto."""
    with col.container(border=True, height="stretch" if esticar else "content"):
        st.metric(titulo, valor, delta, delta_color=cor_delta, help=ajuda,
                  chart_data=list(serie) if serie is not None and len(serie) > 1 else None, chart_type="area")
        if selo:
            st.badge(selo[0], color=selo[1])
        if detalhe:
            st.caption(detalhe.replace("$", "\\$"))  # "R$ … R$" viraria fórmula LaTeX


def _var(v, base, vs: str) -> str | None:
    """Variação percentual contra o mesmo bimestre do ano anterior."""
    if base is None or pd.isna(base) or base == 0 or pd.isna(v):
        return None
    return f"{(v / base - 1) * 100:+.1f}%".replace(".", ",") + f" vs {vs}"


def _dif(v, base, vs: str) -> str | None:
    """Diferença em reais (para resultados, que mudam de sinal)."""
    if base is None or pd.isna(base) or pd.isna(v):
        return None
    d = v - base
    return ("+" if d >= 0 else "-") + G.brl(abs(d))  # hífen: o st.metric só pinta de vermelho com "-" + f" vs {vs}"


def _comparacao(res: pd.DataFrame, a: int, b: int, ind: str, nome: str, chave: str, onde) -> None:
    """Valor acumulado no ano, bimestre a bimestre, com uma linha por exercício (até 3 anos)."""
    t = res[(res["exercicio"] >= a - 2) & ((res["exercicio"] < a) | (res["periodo"] <= b))].assign(
        ano=lambda d: d["exercicio"].astype(int).astype(str), bimestre=lambda d: d["periodo"].astype(int).map(BIMESTRES))
    fig = G.linhas(t, "bimestre", ind, "ano", f"{nome} acumulada no ano")
    fig.update_xaxes(categoryorder="array", categoryarray=list(BIMESTRES.values()))
    fig.update_yaxes(rangemode="tozero")
    ui.grafico(fig, chave, "siconfi_rreo", onde=onde, valores=False,
               nota=f"{NOTA_A14}; cada linha é um exercício e cada ponto acumula de janeiro ao fim do bimestre")


def _nota(v: float) -> str:
    return "–" if pd.isna(v) else f"{v:.3f}".replace(".", ",")


def _ifgf(df: pd.DataFrame, a: int, b: int) -> None:
    """Índice Firjan de Gestão Fiscal (feito para municípios) com os dados equivalentes do Estado."""
    st.markdown("##### 🏅 Gestão fiscal pela metodologia do IFGF (Firjan), adaptada ao Estado")
    t = REL.ifgf_estado(df, ui.relatorio("rgf"))
    lin = t[(t["exercicio"] == a) & (t["periodo"] == b)]
    if lin.empty or pd.isna(lin["autonomia"].iat[0]):
        st.info("O IFGF usa 12 meses de dados: para este bimestre falta o exercício anterior nos RREOs carregados. "
                "Escolha um bimestre a partir do 6º de 2024.")
        return
    r = lin.iloc[0]
    k = st.columns(5)
    _cartao(k[0], "IFGF consolidado", _nota(r["ifgf"]), selo=REL.ifgf_conceito(r["ifgf"]),
            detalhe="Média simples dos quatro indicadores (25% cada)",
            ajuda="Escala de 0 a 1. Acima de 0,8: gestão de excelência; 0,6 a 0,8: boa gestão; 0,4 a 0,6: gestão em "
                  "dificuldade; abaixo de 0,4: gestão crítica (Firjan).")
    _cartao(k[1], "Autonomia", _nota(r["autonomia"]), selo=REL.ifgf_conceito(r["autonomia"]),
            detalhe=f"(Receita local {G.brl(r['receita_local'])} − custo administrativo {G.brl(r['custo_adm'])}) "
                    f"÷ RCL = {G.pct(100 * r['autonomia_ind'])}. Nota 1 acima de 25%",
            ajuda="Se a arrecadação ligada à economia do Estado paga a estrutura administrativa (funções Legislativa, "
                  "Judiciária, Essencial à Justiça e Administração). 12 meses até o fim do bimestre.")
    _cartao(k[2], "Gastos com pessoal", _nota(r["pessoal"]), selo=REL.ifgf_conceito(r["pessoal"]),
            detalhe=f"Despesa com pessoal de todos os Poderes = {G.pct(100 * r['pessoal_pct'])} da RCL "
                    f"(RGF, {r['pessoal_ref']}). Nota 1 abaixo de 45%; 0 acima de 60%",
            ajuda="Despesa total com pessoal (LRF, arts. 18 a 20) dos últimos 12 meses ÷ RCL ajustada. O RREO não traz "
                  "esse conceito; vem do RGF, Anexo 1, somando Executivo, Legislativo, Judiciário e Ministério Público.")
    _cartao(k[3], "Liquidez", _nota(r["liquidez"]), selo=REL.ifgf_conceito(r["liquidez"]),
            detalhe=f"(Caixa {G.brl(r['caixa'])} − restos a pagar do ano {G.brl(r['rp_inscrito_ano'])}) ÷ RCL = "
                    f"{G.pct(100 * r['liquidez_ind'])}, em {r['liquidez_ref']}",
            ajuda="Se o caixa cobre as despesas empurradas para o ano seguinte. Só existe para o fim de cada exercício: "
                  "caixa bruta do RGF, Anexo 5 (3º quadrimestre), e restos a pagar = empenhado − pago no ano (RREO, Anexo 14).")
    _cartao(k[4], "Investimentos", _nota(r["investimentos_nota"]), selo=REL.ifgf_conceito(r["investimentos_nota"]),
            detalhe=f"Investimentos + inversões {G.brl(r['investimentos'])} ÷ receita total "
                    f"{G.brl(r['receita_total'])} = {G.pct(100 * r['investimentos_ind'])}. Nota 1 acima de 12%",
            ajuda="Parcela da receita destinada a investimentos e inversões financeiras (despesa liquidada, Anexo 1, "
                  "exceto intraorçamentárias), em 12 meses.")
    h = t.dropna(subset=["ifgf"])
    h = h[h["exercicio"] * 10 + h["periodo"] <= a * 10 + b].assign(
        rotulo=lambda d: d["periodo"].astype(int).astype(str) + "º/" + d["exercicio"].astype(int).astype(str).str[2:])
    fig = G.notas_com_faixas(h, "rotulo", {"ifgf": ("IFGF consolidado", G.OUTROS), "autonomia": ("Autonomia", G.CORES[0]),
                                           "pessoal": ("Gastos com pessoal", G.CORES[1]), "liquidez": ("Liquidez", G.CORES[2]),
                                           "investimentos_nota": ("Investimentos", G.CORES[6])},
                             [(0.8, "Excelência", G.STATUS["bom"]), (0.6, "Boa gestão", G.CORES[0]),
                              (0.4, "Dificuldade", G.STATUS["alerta"]), (0.0, "Crítica", G.STATUS["critico"])],
                             "IFGF adaptado ao Estado, 12 meses até cada bimestre")
    ui.grafico(fig, "rr_r_ifgf", "siconfi_rreo", "siconfi_rgf", valores=False,
               nota="Autonomia e Investimentos: RREO, Anexos 1, 2 e 3, em 12 meses móveis; Gastos com pessoal: RGF, "
                    "Anexo 1, último quadrimestre encerrado; Liquidez: posição de 31/12 do último exercício encerrado")
    with st.expander("ℹ️ Metodologia do IFGF e adaptações para o Estado", expanded=False):
        st.markdown(
            "O **Índice Firjan de Gestão Fiscal (IFGF)** avalia prefeituras com dados do Siconfi, em quatro indicadores "
            "de 0 a 1, com peso de 25% cada ([Anexo Metodológico, edição 2025](https://www.firjan.com.br/ifgf/metodologia/)). "
            "Aqui a mesma régua é aplicada ao Estado de MS com os demonstrativos estaduais:\n\n"
            "| Indicador | Fórmula da Firjan (municípios) | Equivalente estadual usado | Nota |\n|---|---|---|---|\n"
            "| **Autonomia** | (receitas da atividade econômica local − custo da Câmara e da Administração) ÷ RCL | "
            "Receita: ICMS, IPVA, ITCD e IRRF menos transferências constitucionais a municípios e dedução para o FUNDEB, "
            "mais outras receitas patrimoniais e de serviços (RREO, Anexo 3, 12 meses). Custo: funções 01 Legislativa, "
            "02 Judiciária, 03 Essencial à Justiça e 04 Administração, liquidado (Anexo 2) | 1 se > 25%; indicador ÷ 25%; 0 se < 0 |\n"
            "| **Gastos com pessoal** | despesa líquida com pessoal (12 meses) ÷ RCL | Despesa total com pessoal de todos os "
            "Poderes e órgãos ÷ RCL ajustada (RGF, Anexo 1) | 1 se < 45%; 1 − (ind. − 45%) ÷ 15%; 0 se > 60% |\n"
            "| **Liquidez** | (caixa − restos a pagar inscritos no ano) ÷ RCL | Caixa bruta de todos os Poderes (RGF, "
            "Anexo 5, 3º quadrimestre) − (empenhado − pago no ano, RREO Anexo 14, 6º bimestre) ÷ RCL | 1 se > 25%; "
            "0,4 + 0,6 × ind. ÷ 25%; 0 se < 0 |\n"
            "| **Investimentos** | (investimentos + inversões financeiras) ÷ receita total | Despesa liquidada nos grupos "
            "4.4 e 4.5 ÷ receita realizada, exceto intraorçamentárias (RREO, Anexo 1, 12 meses) | 1 se > 12%; ind. ÷ 12% |\n\n"
            "**Conceitos**: acima de 0,8, gestão de excelência; de 0,6 a 0,8, boa gestão; de 0,4 a 0,6, gestão em "
            "dificuldade; abaixo de 0,4, gestão crítica.\n\n"
            "**Cuidados na comparação**\n"
            "- O IFGF foi calibrado para prefeituras: as notas de corte (25% de autonomia, 12% de investimento) não "
            "foram pensadas para Estados, e o resultado **não é comparável** com o ranking municipal da Firjan.\n"
            "- **Autonomia**: no Estado, a função Judiciária inclui todo o Tribunal de Justiça, e a Essencial à "
            "Justiça, o Ministério Público, a Defensoria e a PGE; nos municípios essas funções quase não existem. "
            "A cota-parte do IPI-exportação do Estado não é separável no Anexo 3 e ficou de fora.\n"
            "- **Pessoal**: o RREO não traz a despesa com pessoal da LRF (que exclui inativos pagos pelo RPPS, "
            "indenizações etc.); por isso vem do RGF. O limite de 60% da RCL vale tanto para o Estado quanto para os municípios.\n"
            "- **Liquidez**: o caixa só é publicado no RGF do 3º quadrimestre; nos bimestres do ano em curso, vale a "
            "posição de 31/12 do ano anterior.\n"
            "- **12 meses móveis**: valores \"até o bimestre\" viram 12 meses somando o total do ano anterior e "
            "subtraindo o acumulado do ano anterior até o mesmo bimestre; no 6º bimestre, é o próprio exercício.")


def _resumo(df: pd.DataFrame) -> None:
    res = REL.resumo_rreo(df)
    if res.empty:
        st.info("O Anexo 14 (Demonstrativo Simplificado) não foi encontrado nos RREOs carregados.")
        return
    c = st.columns([1, 1, 4], vertical_alignment="bottom")
    anos = sorted(res["exercicio"].unique(), reverse=True)
    a = c[0].selectbox("Exercício", anos, key="rr_r_ano")
    b = c[1].selectbox("Bimestre", sorted(res.loc[res["exercicio"] == a, "periodo"].unique(), reverse=True),
                       format_func=BIMESTRES.get, key="rr_r_bim")
    a, b = int(a), int(b)
    r = res[(res["exercicio"] == a) & (res["periodo"] == b)].iloc[0]
    ant = res[(res["exercicio"] == a - 1) & (res["periodo"] == b)]
    p = ant.iloc[0] if not ant.empty else pd.Series(dtype=float)
    ate, vs = f"jan a {G.MESES[2 * b - 1]}/{a}", f"{b}º bim/{a - 1}"
    ritmo = 100 * b / 6
    hist = res[res["exercicio"] * 10 + res["periodo"] <= a * 10 + b].assign(
        rotulo=lambda t: t["periodo"].astype(int).astype(str) + "º/" + t["exercicio"].astype(int).astype(str).str[2:])
    pr, pe, pd_, pp = (100 * r["receita_realizada"] / r["receita_prevista"], 100 * r["empenhada"] / r["dotacao"],
                       100 * r["liquidada"] / r["dotacao"], 100 * r["paga"] / r["dotacao"])
    c[2].markdown(f"#### {b}º bimestre de {a} · valores acumulados de {ate}")

    # ---- síntese em texto
    prim_ok = r["primario"] >= r["primario_meta"]
    frases = [
        f"Até {G.MESES[2 * b - 1]}/{a}, o Estado **arrecadou {G.brl(r['receita_realizada'])}** "
        f"({G.pct(pr)} da previsão atualizada para o ano) e **liquidou {G.brl(r['liquidada'])}** em despesas "
        f"({G.pct(pd_)} da dotação atualizada).",
        f"O resultado primário apurado (**{G.brl(r['primario'])}**) está **{'acima' if prim_ok else 'abaixo'}** da "
        f"meta anual da LDO ({G.brl(r['primario_meta'])}).",
    ]
    with st.container(border=True):
        st.markdown(("**🧭 Em resumo** — " + " ".join(frases)).replace("$", "\\$"))
    fig = G.progresso([("Receita realizada ÷ previsão", pr, G.CORES[6]),
                       ("Despesa empenhada ÷ dotação", pe, G.ESTAGIOS["empenhado"]),
                       ("Despesa liquidada ÷ dotação", pd_, G.ESTAGIOS["liquidado"]),
                       ("Despesa paga ÷ dotação", pp, G.ESTAGIOS["pago"])],
                      esperado=ritmo, titulo=f"Quanto do orçamento de {a} já foi executado", altura=290)
    ui.grafico(fig, "rr_r_prog", "siconfi_rreo", valores=False,
               nota=f"{NOTA_A14}. Previsão e dotação atualizadas valem para o ano inteiro; a linha pontilhada é o "
                    f"ritmo linear ({b} de 6 bimestres)")

    # ---- receitas
    st.markdown("##### 💰 Receitas")
    rcl12 = REL.acumulado_12m(REL.mensal_mr(df, "RREO-Anexo 03", "RREO3ReceitaCorrenteLiquida", 2))
    rcl12 = rcl12[rcl12["data"] <= pd.Timestamp(a, 2 * b, 1)]
    k = st.columns(3)
    _cartao(k[0], "Receita realizada", G.brl(r["receita_realizada"]), delta=_var(r["receita_realizada"], p.get("receita_realizada"), vs),
            selo=("No ritmo do ano", "green") if pr >= ritmo - 3 else ("Abaixo do ritmo linear", "orange"),
            detalhe=f"{G.pct(pr)} da previsão atualizada",
            ajuda="Receitas realizadas de janeiro ao fim do bimestre. O ritmo linear supõe arrecadação igual em todos "
                  "os bimestres.")
    _cartao(k[1], "Previsão atualizada para o ano", G.brl(r["receita_prevista"]),
            delta=_var(r["receita_prevista"], p.get("receita_prevista"), vs), cor_delta="off",
            selo=(f"Falta arrecadar {G.brl(r['receita_prevista'] - r['receita_realizada'])}", "blue"),
            detalhe=f"Previsão inicial da LOA: {G.brl(r['receita_inicial'])}",
            ajuda="Estimativa de receita do exercício inteiro, revista ao longo do ano (Anexo 1, coluna a).")
    _cartao(k[2], "Receita Corrente Líquida (12 meses)", G.brl(r["rcl"]), delta=_var(r["rcl"], p.get("rcl"), vs),
            selo=("Base dos limites da LRF", "gray"), serie=rcl12["valor"].tail(24),
            detalhe=f"Soma de {G.MESES[2 * b % 12]}/{a - 1 if b < 6 else a} a {G.MESES[2 * b - 1]}/{a}; "
                    "minigráfico: últimos 24 meses",
            ajuda="RCL dos últimos 12 meses (Anexo 3), denominador dos limites de pessoal e dívida (LRF, art. 2º, IV).")
    g1, g2 = st.columns(2)
    _comparacao(res, a, b, "receita_realizada", "Receita realizada", "rr_r_rec", g1)
    icms = REL.acumulado_12m(REL.mensal_mr(df, "RREO-Anexo 03", "ICMSLiquidoExcetoTransferenciasEFUNDEB", 2))
    icms = icms[icms["data"] <= pd.Timestamp(a, 2 * b, 1)]
    serie = pd.concat([rcl12.assign(serie="Receita Corrente Líquida"), icms.assign(serie="ICMS (bruto)")])
    if not serie.empty:
        fig = G.linhas(serie, "data", "valor", "serie", "RCL e ICMS, acumulados em 12 meses", marcadores=False,
                       ordem=["Receita Corrente Líquida", "ICMS (bruto)"])
        fig.update_yaxes(rangemode="tozero")
        ui.grafico(fig, "rr_r_rcl", "siconfi_rreo", onde=g2, valores=False,
                   nota="RREO, Anexo 3, colunas mensais <MR-11> … <MR> de cada bimestre (prevalece o relatório mais "
                        "recente), somadas em janelas de 12 meses. ICMS antes das transferências a municípios e da "
                        "dedução para o FUNDEB; valores nominais")

    # ---- despesas
    st.markdown("##### 🧾 Despesas")
    k = st.columns(3)
    _cartao(k[0], "Despesa empenhada", G.brl(r["empenhada"]), delta=_var(r["empenhada"], p.get("empenhada"), vs),
            cor_delta="off", selo=(f"{G.pct(pe)} da dotação", "blue"),
            detalhe=f"Dotação atualizada: {G.brl(r['dotacao'])} (inicial {G.brl(r['dotacao_inicial'])})",
            ajuda="Empenho: reserva do valor no orçamento para uma despesa contratada (Lei 4.320/1964, art. 58).")
    _cartao(k[1], "Despesa liquidada", G.brl(r["liquidada"]), delta=_var(r["liquidada"], p.get("liquidada"), vs),
            cor_delta="off", selo=(f"{G.pct(pd_)} da dotação", "blue"),
            detalhe=f"{G.pct(100 * r['liquidada'] / r['empenhada'])} do empenhado",
            ajuda="Liquidação: verificação de que o bem ou serviço foi entregue (Lei 4.320/1964, art. 63).")
    _cartao(k[2], "Despesa paga", G.brl(r["paga"]), delta=_var(r["paga"], p.get("paga"), vs),
            cor_delta="off", selo=(f"{G.pct(pp)} da dotação", "blue"),
            detalhe=f"Liquidado e ainda não pago: {G.brl(r['liquidada'] - r['paga'])}",
            ajuda="Pagamento: saída de caixa da despesa liquidada (Lei 4.320/1964, art. 64).")
    g1, g2 = st.columns(2)
    _comparacao(res, a, b, "liquidada", "Despesa liquidada", "rr_r_desp", g1)
    grp = REL.despesa_por_grupo(df, a, b)
    if not grp.empty:
        grp["texto"] = (100 * grp["valor"] / grp["valor"].sum()).map(lambda v: G.pct(v))
        fig = G.barras(grp, "grupo", "valor", titulo=f"Despesa liquidada por grupo, {ate}", horizontal=True,
                       texto="texto", altura=420)
        fig.update_xaxes(range=[0, grp["valor"].max() * 1.15])  # espaço para o rótulo da maior barra
        ui.grafico(fig, "rr_r_grupo", "siconfi_rreo", onde=g2, valores=False,
                   nota="RREO, Anexo 1, coluna 'Despesas liquidadas até o bimestre (h)', exceto intraorçamentárias; "
                        "o rótulo é a participação no total dos grupos; valores nominais")

    # ---- resultado primário
    st.markdown("##### 🎯 Resultado primário")
    k = st.columns([1, 2])
    _cartao(k[0], "Resultado primário (sem RPPS)", G.brl(r["primario"]), delta=_dif(r["primario"], p.get("primario"), vs),
            selo=("Acima da meta anual", "green") if prim_ok else ("Abaixo da meta anual", "red"),
            serie=res[(res["exercicio"] == a) & (res["periodo"] <= b)]["primario"], esticar=False,
            detalhe=f"Meta da LDO para {a}: {G.brl(r['primario_meta'])}. Diferença: "
                    f"{G.brl(r['primario'] - r['primario_meta'])}",
            ajuda="Receitas menos despesas não financeiras (acima da linha). Mostra se o Estado gera recursos para "
                  "pagar a dívida. A meta é anual (LRF, art. 4º, §1º): a comparação só é definitiva no 6º bimestre.")
    ui.grafico(G.resultado_vs_meta(hist, "rotulo", "primario", "primario_meta", "Resultado primário apurado × meta anual"),
               "rr_r_prim", "siconfi_rreo", onde=k[1], valores=False,
               nota=f"{NOTA_A14}. Barra verde: apurado acima da meta da LDO; vermelha: abaixo. O apurado acumula no "
                    "ano e a meta é anual")

    st.divider()
    _ifgf(df, a, b)

    with st.expander("ℹ️ Como ler este resumo", expanded=False):
        st.markdown(
            "- **Fonte**: os cartões vêm do **Anexo 14 (Demonstrativo Simplificado)**, o resumo oficial do RREO. "
            "Os gráficos detalham com os Anexos 1 e 3.\n"
            "- **Acumulados**: tudo acumula de 1º de janeiro ao fim do bimestre e recomeça no ano seguinte. Por isso "
            "a comparação é sempre com o **mesmo bimestre** do ano anterior.\n"
            "- **A meta de resultado primário é anual** (LDO): só é cumprida ou descumprida no 6º bimestre. Antes "
            "disso, o selo indica a tendência.\n"
            "- **Ritmo linear**: referência simples (bimestre ÷ 6). A arrecadação tem sazonalidade (IPVA concentra-se "
            "no início do ano), então pequenas diferenças são normais.\n"
            "- **Valores nominais**: a opção de valores reais (IPCA) da barra lateral não se aplica a esta aba.")


def render():
    st.title("RREO – Relatório Resumido da Execução Orçamentária")
    st.caption("Publicado a cada bimestre (até 30 dias após o fim do período) e homologado no Siconfi. Abrange todos os Poderes.")
    ui.base_legal(lrf=["art52", "art2iv", "art9", "art51"],
                  extra=["Estrutura e conceitos: Manual de Demonstrativos Fiscais (MDF) da STN, Parte II – RREO.",
                         "Mínimos constitucionais: CF, art. 212 (25% em MDE) e LC nº 141/2012, art. 6º (12% em ASPS pelos Estados)."])
    df = ui.relatorio("rreo")
    if df.empty:
        ui.sem_dados("RREO", "python coletar.py --siconfi")
        return

    abas = st.tabs(["🧭 Resumo", "🎯 Previsões", "📚 Anexos",
                    "legado_Destaques", "legado_Séries entre bimestres", "legado_Anexo completo"])
    ultimo = REL.ultimo_periodo(df)

    with abas[0]:
        rreo_resumo.render()

    with abas[1]:
        st.info("Em construção.")

    with abas[2]:
        rreo_anexos.render()

    with abas[3]:
        a, b = ultimo
        ate = f"jan a {G.MESES[2 * b - 1]}/{a}"  # "até o bimestre" = de 1º de janeiro ao fim do bimestre
        st.markdown(f"**Último RREO disponível: {b}º bimestre de {a}** · valores \"até o bimestre\" acumulam {ate}")
        x = df[(df["exercicio"] == a) & (df["periodo"] == b)]
        # Anexo 1 – receitas e despesas
        r = x[(x["anexo"] == "RREO-Anexo 01")]
        rec = r[r["cod_conta"].isin(["ReceitasCorrentes", "ReceitasDeCapital", "ReceitasIntraOrcamentarias"]) &
                r["coluna"].isin(["PREVISÃO ATUALIZADA (a)", "Até o Bimestre (c)"])]
        dsp = r[r["coluna"].isin(["DOTAÇÃO ATUALIZADA (e)", "DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)",
                                  "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)", "DESPESAS PAGAS ATÉ O BIMESTRE (j)"]) &
                r["conta"].str.match(r"^(DESPESAS CORRENTES|DESPESAS DE CAPITAL|RESERVA DE CONTING)", case=False)]
        c1, c2 = st.columns(2)
        if not rec.empty:
            ui.grafico(G.barras(rec.drop_duplicates(["conta", "coluna"]), "conta", "valor", "coluna",
                                     f"Receitas: previsão atualizada do ano × realizado de {ate}", empilhar=False, horizontal=True),
                                                "rr_a1r", "siconfi_rreo", onde=c1,
                   nota="RREO, Anexo 1 (Balanço Orçamentário), último bimestre: colunas 'Previsão atualizada (a)' "
                        f"(para o exercício inteiro) e 'Até o bimestre (c)' ({ate})")
        if not dsp.empty:
            ui.grafico(G.barras(dsp.drop_duplicates(["conta", "coluna"]), "conta", "valor", "coluna",
                                     f"Despesas: dotação atualizada do ano × execução de {ate}", empilhar=False, horizontal=True),
                                                "rr_a1d", "siconfi_rreo", onde=c2,
                   nota="RREO, Anexo 1 (Balanço Orçamentário), último bimestre: coluna (e) = dotação para o exercício "
                        f"inteiro; (f), (h) e (j) = empenhado, liquidado e pago de {ate}")
        # Anexo 2 – funções e subfunções
        a2 = REL.anexo2_funcoes(df, a, b, "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (d)")
        if not a2.empty:
            c1, c2 = st.columns([2, 3])
            ff = a2.groupby("funcao", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
            ui.grafico(G.barras(ff.head(15), "funcao", "valor", horizontal=True, altura=520,
                                     titulo=f"Anexo 2 – despesa liquidada por função, {ate}"),
                                                "rr_a2", "siconfi_rreo", onde=c1,
                   nota=f"RREO, Anexo 2 (despesa por função e subfunção), coluna 'Despesas liquidadas até o bimestre (d)' ({ate})")
            ui.grafico(G.treemap(a2, ["funcao", "subfuncao"], "valor", "Funções › subfunções (Anexo 2)", altura=520,
                                 raiz="Despesa liquidada total (exceto intra)",
                                 pct_de=f"da despesa liquidada total de {ate} (exceto intra)"),
                       "rr_a2t", "siconfi_rreo", onde=c2,
                   nota=f"RREO, Anexo 2 (despesa por função e subfunção), coluna 'Despesas liquidadas até o bimestre (d)', "
                        f"exceto intraorçamentárias; o % de cada área é sobre a despesa liquidada total do Estado de {ate} "
                        "(soma de todas as funções; acumulado só neste exercício, não na série histórica), não sobre a "
                        "RCL nem sobre a receita")
        # Anexo 14 – mínimos de educação e saúde, resultados
        s = x[x["anexo"] == "RREO-Anexo 14"]
        mde = s[s["cod_conta"].str.startswith("MinimoAnualDasReceitasDeImpostosNaManutencao")]
        asps = s[s["cod_conta"].str.startswith("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSau")]
        cc = st.columns(4)
        for col, sub, nome in ((cc[0], mde, "MDE (educação)"), (cc[1], asps, "ASPS (saúde)")):
            ap = sub[sub["coluna"].str.contains("Aplicado")]["valor"]
            mi = sub[sub["coluna"].str.contains("Mínimo")]["valor"]
            if not ap.empty:
                col.metric(f"% aplicado em {nome}, {ate}", G.pct(ap.iat[0], 2),
                           f"mínimo anual {G.pct(mi.iat[0], 0)}" if not mi.empty else None, delta_color="off")
        rp = s[s["cod_conta"].str.startswith("ResultadoPrimarioAcimaDaLinha")]
        rn = s[s["cod_conta"].str.startswith("ResultadoNominalAbaixoDaLinha")]
        for col, sub, nome in ((cc[2], rp, "Resultado primário (sem RPPS)"), (cc[3], rn, "Resultado nominal (sem RPPS)")):
            v = sub[sub["coluna"].str.contains("Apurado")]["valor"]
            meta = sub[sub["coluna"].str.contains("Meta")]["valor"]
            if not v.empty:
                col.metric(f"{nome}, {ate}", G.brl(v.iat[0]), f"meta anual LDO: {G.brl(meta.iat[0])}" if not meta.empty else None,
                           delta_color="off")
        st.caption(f"Os percentuais e resultados apurados acumulam {ate}; o mínimo constitucional e a meta da LDO valem "
                   "para o exercício inteiro, por isso a comparação só é definitiva no 6º bimestre. Resultado primário: receitas menos despesas não financeiras (indica a capacidade de pagar a dívida); "
                   "resultado nominal: variação da dívida consolidada líquida. Metas fixadas no Anexo de Metas Fiscais da LDO (LRF, art. 4º, §1º).")
        # Anexo 3 – RCL mensal
        rcl = REL.mensal_mr(df, "RREO-Anexo 03", "RREO3ReceitaCorrenteLiquida", 2)
        if not rcl.empty:
            ui.grafico(G.barras(ui.ajustar(rcl.assign(ano=rcl["data"].dt.year, mes=rcl["data"].dt.month), ["valor"]),
                                     "data", "valor", titulo="Receita Corrente Líquida mensal (Anexo 3)"),
                                                "rr_rcl", "siconfi_rreo",
                   nota="RREO, Anexo 3 (Receita Corrente Líquida), colunas mensais MR-11 a MR de cada bimestre; prevalece o relatório mais recente")

    with abas[4]:
        ui.explicar_filtros(
            "As opções vêm de campos do JSON devolvido pela API do Siconfi (endpoint `/rreo`). Não vêm de planilha nem "
            "de arquivo CSV.",
            [COLETA,
             "**Campos usados**: `anexo`, `cod_conta` (código da linha), `conta` (nome da linha), `coluna`, `exercicio`, "
             "`periodo` e `valor`.",
             "**Montagem das opções**: as linhas e as colunas são as do anexo escolhido, em todos os bimestres "
             "carregados, na ordem em que aparecem no relatório."],
            [("Anexo", "Valores distintos do campo `anexo` nos dados carregados. O nome ao lado do código é do painel."),
             ("Linhas do demonstrativo", "Campo `conta` + `cod_conta` entre colchetes, de todas as linhas do anexo. "
                                         "Até 8 linhas por vez. No Anexo 1, logo após 'Impostos', o painel acrescenta "
                                         "ICMS, IPVA, ITCD e IRRF, tirados do Anexo 3 (o Anexo 1 não detalha os "
                                         "impostos). A lista completa de códigos fica no quadro '🔢 Códigos' abaixo "
                                         "do filtro."),
             ("Coluna", "Campo `coluna` do anexo, exceto as colunas mensais (<MR-11> … <MR>). Começa na coluna \"até o "
                        "bimestre\", quando existe."),
             ("Visualização", "Só aparece nas colunas \"até o bimestre\". Lista fixa do painel: acumulado com uma "
                              "linha por exercício, valor de cada bimestre (diferença entre acumulados) ou a sequência "
                              "original dos relatórios.")],
            ["**Acumulados**: as colunas \"até o bimestre\" acumulam o exercício; compare o mesmo bimestre entre anos.",
             "**Anexos 8 e 12**: os demonstrativos de educação (MDE) e saúde (ASPS) não vêm na resposta da API "
             "`/rreo` para MS, por isso não aparecem como opção.",
             "**Mudanças de leiaute**: a STN muda nomes e códigos de linhas entre exercícios. Uma linha pode existir só "
             "em alguns anos."],
            fontes=("siconfi_rreo",), nota="campos do JSON listados acima, em todos os bimestres carregados")
        anexo = st.selectbox("Anexo", [a for a in ANEXOS if a in set(df["anexo"])], format_func=lambda a: f"{a} – {ANEXOS[a]}", key="rr_s_anexo")
        x = df[df["anexo"] == anexo]
        contas = x.drop_duplicates("cod_conta")[["cod_conta", "conta"]].assign(origem=anexo).reset_index(drop=True)
        base = df
        if anexo == "RREO-Anexo 01":  # o Anexo 1 para em "Impostos"; ICMS, IPVA, ITCD e IRRF vêm do Anexo 3
            imp = REL.impostos_no_anexo1(df)
            if not imp.empty:
                base, x = pd.concat([df, imp], ignore_index=True), pd.concat([x, imp], ignore_index=True)
                extra = imp.drop_duplicates("cod_conta").set_index("cod_conta").reindex(
                    [c for c in REL.IMPOSTOS_ANEXO3 if c in set(imp["cod_conta"])]).reset_index()[["cod_conta", "conta"]].assign(
                    origem="RREO-Anexo 03 (colunas mensais <MR-11> … <MR>)")
                pos = next((i + 1 for i, c in enumerate(contas["cod_conta"]) if c == "Impostos"), len(contas))
                contas = pd.concat([contas.iloc[:pos], extra, contas.iloc[pos:]], ignore_index=True)
        rot = {r.cod_conta: f"{r.conta.strip()[:90]}  [{r.cod_conta[:40]}]" for r in contas.itertuples()}
        sel_c = st.multiselect("Linhas do demonstrativo", list(rot), format_func=rot.get, default=list(rot)[:1], key="rr_s_conta",
                               max_selections=8)
        with st.expander(f"🔢 Códigos das {len(contas)} opções de 'Linhas do demonstrativo' ({anexo})", expanded=False):
            anos = x.groupby("cod_conta")["exercicio"].agg(lambda e: ", ".join(map(str, sorted(e.unique()))))
            ui.tabela(contas.assign(exercicios=contas["cod_conta"].map(anos))
                      .rename(columns={"cod_conta": "Código (cod_conta)", "conta": "Linha (conta)", "origem": "Origem",
                                       "exercicios": "Exercícios"}),
                      "rr_s_codigos", ordenar_padrao="(ordem original)", fontes=["siconfi_rreo"],
                      nota="campos `cod_conta` e `conta` do anexo escolhido, em todos os bimestres carregados, na ordem do relatório")
            if anexo == "RREO-Anexo 01":
                st.caption("As linhas '↳ … (do Anexo 3, bruto)' não existem no Anexo 1: o leiaute da STN para no total "
                           "de Impostos. Elas usam as colunas mensais do Anexo 3 (Receita Corrente Líquida) do mesmo "
                           "relatório: 'No Bimestre (b)' = <MR-1> + <MR>; 'Até o Bimestre (c)' = meses de janeiro ao fim "
                           "do bimestre; 'Previsão atualizada (a)' = 'PREVISÃO ATUALIZADA AAAA'. São valores brutos, "
                           "antes das transferências constitucionais a municípios (25% do ICMS, 50% do IPVA) e da "
                           "dedução para o FUNDEB; por isso a soma deles supera a linha 'Impostos' do Anexo 1, que é "
                           "líquida dessas deduções. Não há 'Previsão inicial' para elas.")
        colunas = [c for c in dict.fromkeys(x["coluna"]) if not c.startswith("<MR")]
        col = st.selectbox("Coluna", colunas, key="rr_s_col",
                           index=next((i for i, c in enumerate(colunas) if re.search(r"Até o Bimestre|ATÉ O BIMESTRE|LIQUIDADAS ATÉ", c)), 0))
        # colunas que acumulam de janeiro ao fim do bimestre (exclui saldos "Até o Bimestre 2025" e percentuais)
        acumula = bool(re.search(r"at[ée] o bimestre(?!\s*\d)", col, re.I)) and not col.startswith("%")
        modo = st.radio("Visualização", VISOES, horizontal=True, key="rr_s_modo",
                        help="A coluna acumula o exercício e recomeça em janeiro; na sequência original isso vira um "
                             "serrote. As duas primeiras opções põem os exercícios lado a lado, bimestre a bimestre."
                        ) if acumula else VISOES[2]
        partes = []
        for c in sel_c:
            s = REL.serie_por_periodo(base, anexo, c, col, "rreo")
            s["linha"] = rot[c][:60]
            partes.append(s)
        if partes and not pd.concat(partes).empty:
            s = pd.concat(partes, ignore_index=True)
            if modo == VISOES[2]:
                ui.grafico(G.linhas(s, "rotulo", "valor", "linha", f"{anexo} – {col}"), "rr_s_fig", "siconfi_rreo",
                           nota="RREO, todos os bimestres entregues; anexo, linha e coluna escolhidos nos filtros")
                ui.tabela(s[["rotulo", "linha", "valor"]], "rr_s_tab", moeda=["valor"], ordenar_padrao="rotulo",
                          fontes=["siconfi_rreo"], nota="RREO, todos os bimestres entregues; anexo, linha e coluna escolhidos nos filtros")
                if acumula:
                    st.caption("Valores 'até o bimestre' são acumulados no exercício e recomeçam em janeiro: as quedas "
                               "entre o 6º bimestre e o 1º do ano seguinte não são queda de valor.")
            else:
                s = s.sort_values(["linha", "exercicio", "periodo"]).assign(
                    ano=s["exercicio"].astype(int).astype(str), bimestre=s["periodo"].astype(int).map(BIMESTRES))
                if modo == VISOES[1]:  # valor do bimestre = acumulado − acumulado do bimestre anterior do mesmo ano
                    grp = s.groupby(["linha", "exercicio"])
                    anterior, contiguo = grp["valor"].shift(), grp["periodo"].shift() == s["periodo"] - 1
                    s["valor"] = s["valor"].where(s["periodo"] == 1, (s["valor"] - anterior).where(contiguo))
                    nota = (f"coluna '{col}': valor só do bimestre = acumulado do bimestre − acumulado do bimestre "
                            "anterior do mesmo exercício (no 1º bimestre, o próprio acumulado); fica vazio se faltar o "
                            "bimestre anterior")
                    eixo = "Valor no bimestre"
                else:
                    nota = (f"coluna '{col}': cada linha é um exercício e cada ponto soma de 1º de janeiro até o fim do "
                            "bimestre; no 6º bimestre, é o total do ano")
                    eixo = "Acumulado desde janeiro"
                linhas = list(dict.fromkeys(s["linha"]))
                cols = st.columns(2) if len(linhas) > 1 else [st]
                for i, ln in enumerate(linhas):
                    nome = ln.split("  [")[0]  # sem o código da linha
                    fig = G.linhas(s[s["linha"] == ln], "bimestre", "valor", "ano",
                                   nome if len(linhas) > 1 else f"{nome} – {modo.lower()}")
                    fig.update_xaxes(categoryorder="array", categoryarray=list(BIMESTRES.values()))
                    fig.update_yaxes(title=eixo, rangemode="tozero")
                    ui.grafico(fig, f"rr_s_fig_{i}", "siconfi_rreo", onde=cols[i % len(cols)], nota=nota)
                larga = s.pivot_table(index=["linha", "ano"], columns="bimestre", values="valor", aggfunc="sum")
                larga = larga.reindex(columns=[b for b in BIMESTRES.values() if b in larga.columns]).reset_index()
                ui.tabela(larga, "rr_s_tab", moeda=[c for c in larga.columns if c not in ("linha", "ano")],
                          ordenar_padrao="(ordem original)", fontes=["siconfi_rreo"], nota=nota)

    with abas[5]:
        ui.explicar_filtros(
            "As opções vêm de campos do JSON devolvido pela API do Siconfi (endpoint `/rreo`). Não vêm de planilha nem "
            "de arquivo CSV.",
            [COLETA,
             "**Campos usados**: `exercicio`, `periodo`, `anexo`, `cod_conta`, `conta`, `coluna` e `valor`.",
             "**Montagem das opções**: os filtros são encadeados: o exercício define os bimestres disponíveis, e o "
             "bimestre define os anexos entregues."],
            [("Exercício", "Campo `exercicio`: anos com algum RREO carregado, do mais recente ao mais antigo."),
             ("Bimestre", "Campo `periodo` do exercício escolhido, do mais recente ao mais antigo."),
             ("Anexo", "Anexos entregues no exercício e no bimestre escolhidos (campo `anexo`)."),
             ("Filtrar contas", "Texto livre, procurado no nome da linha (campo `conta`).")],
            ["**Ordem original**: a tabela começa na ordem do demonstrativo; linhas recuadas são subitens da anterior.",
             "**Anexos por bimestre**: alguns anexos só são publicados em certos bimestres (Anexos 9, 10 e 11 só no 6º). Os Anexos 8 e 12 não vêm na API."],
            fontes=("siconfi_rreo",), nota="campos do JSON listados acima")
        c = st.columns([1, 1, 3])
        anos = sorted(df["exercicio"].unique(), reverse=True)
        ano = c[0].selectbox("Exercício", anos, key="rr_t_ano")
        bims = sorted(df.loc[df["exercicio"] == ano, "periodo"].unique(), reverse=True)
        bim = c[1].selectbox("Bimestre", bims, key="rr_t_bim")
        disp = [a for a in ANEXOS if a in set(df.loc[(df["exercicio"] == ano) & (df["periodo"] == bim), "anexo"])]
        anexo = c[2].selectbox("Anexo", disp, format_func=lambda a: f"{a} – {ANEXOS[a]}", key="rr_t_anexo")
        t = REL.tabela_anexo(df, anexo, ano, bim)
        busca = st.text_input("Filtrar contas", key="rr_t_busca", placeholder="ex.: ICMS, Saúde, Pessoal")
        if busca:
            t = t[t["Conta"].str.contains(busca, case=False, na=False)]
        num = [c for c in t.columns if c not in ("Quadro", "Código", "Conta")]
        ui.tabela(t, "rr_t_tab", 
                  fontes=["siconfi_rreo"], nota="RREO do exercício, bimestre e anexo escolhidos, na ordem das linhas do relatório",
                  moeda=num, ordenar_padrao="(ordem original)")
        st.caption("Ordenação inicial = ordem do demonstrativo. Linhas recuadas são subitens da linha anterior.")
