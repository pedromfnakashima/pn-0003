"""Indicadores fiscais do "RREO em Foco: Estados + DF" (Tesouro Nacional), recalculados para todas as UFs e todos os
bimestres com o RREO do Siconfi.

Publicação de referência: RREO em Foco: Estados e DF (Tesouro Nacional) —
https://www.tesourotransparente.gov.br/publicacoes/rreo-em-foco-estados-e-df/2026/16 (histórico de edições); PDFs do
3º bimestre (https://thot-arquivos.tesouro.gov.br/publicacao/55399) e do 4º bimestre de 2026
(https://thot-arquivos.tesouro.gov.br/publicacao/56111). As definições abaixo foram conferidas contra as tabelas dessas
edições para MS, SP, GO, AC e PR: os valores coincidem até o arredondamento.

Convenções do Tesouro reproduzidas aqui:
- Receitas e despesas somam as intraorçamentárias (Anexo 1, linhas "…Intra").
- As transferências a municípios registradas como despesa (Anexo 1, "Transferências a Municípios", liquidadas) são
  deduzidas das receitas e das despesas correntes e totais, para comparar com as UFs que as registram como dedução de
  receita (nota 2 da publicação). Nas UFs que já deduzem da receita, essa linha é zero.
- Despesas = liquidadas (a publicação fala em "empenhadas" nos Gráficos 1 e 2, mas os números publicados são os
  liquidados).
- RCL proporcional = RCL dos últimos 12 meses (Anexo 3) × meses decorridos ÷ 12.
"""
from __future__ import annotations

import re

import pandas as pd

CHAVE = ["uf", "exercicio", "periodo"]
R = "Até o Bimestre (c)"
L = "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)"

# indicador → (título, unidade, sentido em que é pior, explicação)
INDICADORES: dict[str, tuple[str, str, str, str]] = {
    "dif_crescimento": (
        "Crescimento da despesa corrente menos o da receita corrente", "p.p.", "maior",
        "Diferença, em pontos percentuais, entre o crescimento da despesa corrente liquidada e o da receita corrente "
        "realizada, acumuladas no ano, contra o mesmo período do ano anterior. Positivo: a despesa cresce mais "
        "rápido que a receita, o que estreita a margem fiscal."),
    "cresc_receita": (
        "Crescimento da receita corrente (acumulado no ano)", "%", "menor",
        "Receita corrente realizada de janeiro ao fim do bimestre ÷ mesmo período do ano anterior − 1, em valores "
        "nominais (Gráfico 1 da publicação)."),
    "cresc_despesa": (
        "Crescimento da despesa corrente (acumulado no ano)", "%", "maior",
        "Despesa corrente liquidada de janeiro ao fim do bimestre ÷ mesmo período do ano anterior − 1, em valores "
        "nominais (Gráfico 1)."),
    "res_orcamentario": (
        "Resultado orçamentário ÷ RCL proporcional", "%", "menor",
        "Receitas realizadas menos despesas liquidadas, acumuladas no ano, ÷ RCL proporcional ao período (Gráfico 2 e "
        "Tabela 1; a publicação fala em despesas empenhadas, mas os valores publicados são os liquidados). Negativo: o "
        "Estado liquidou mais despesas do que arrecadou."),
    "poupanca_corrente": (
        "Poupança corrente ÷ RCL proporcional", "%", "menor",
        "Receitas correntes menos despesas correntes liquidadas ÷ RCL proporcional (Gráfico 4). Mede quanto sobra das "
        "receitas do dia a dia para investir com recursos próprios; negativa, indica dependência de receitas de "
        "capital (empréstimos, alienações) para investir."),
    "dependencia": (
        "Transferências correntes ÷ receita corrente", "%", "maior",
        "Participação das transferências correntes recebidas (FPE, SUS, FUNDEB etc.) na receita corrente (Gráfico 3). "
        "Quanto maior, menor a autonomia de arrecadação própria."),
    "pessoal_rt": (
        "Despesa com pessoal ÷ receita total", "%", "maior",
        "Pessoal e encargos sociais liquidados (inclusive intraorçamentários) ÷ receita total (Gráfico 5 e Tabela 2). "
        "Não é o indicador da LRF (que usa a RCL e exclui inativos pagos com recursos vinculados), mas mostra quanto "
        "da receita a folha consome."),
    "custeio_rt": (
        "Custeio ÷ receita total", "%", "maior",
        "Outras despesas correntes liquidadas (sem transferências a municípios) ÷ receita total (Tabela 2)."),
    "divida_rt": (
        "Serviço da dívida ÷ receita total", "%", "maior",
        "Juros, encargos e amortização da dívida liquidados ÷ receita total (Tabela 2)."),
    "invest_rt": (
        "Investimentos e inversões ÷ receita total", "%", "menor",
        "Investimentos e inversões financeiras liquidados ÷ receita total (Tabela 2)."),
    "despesa_rt": (
        "Despesa liquidada total ÷ receita total", "%", "maior",
        "Soma de pessoal, custeio, serviço da dívida e investimentos ÷ receita total (Gráfico 5). Acima de 100%, o "
        "Estado liquidou mais do que arrecadou no período."),
    "rpps_capitalizacao": (
        "Resultado do RPPS – fundo em capitalização ÷ RCL", "%", "menor",
        "Receitas menos despesas liquidadas do fundo em capitalização (plano previdenciário), Anexo 4, ÷ RCL "
        "proporcional (Gráfico 6 e Tabela 3). Negativo: o fundo paga mais benefícios do que recebe no período."),
    "rpps_reparticao": (
        "Resultado do RPPS – fundo em repartição ÷ RCL", "%", "menor",
        "Igual ao anterior, para o fundo em repartição (plano financeiro), que só existe nas UFs com segregação de "
        "massas; os déficits são cobertos pelo Tesouro estadual."),
    "primario_sem_rpps": (
        "Resultado primário sem RPPS ÷ RCL", "%", "menor",
        "Resultado primário acima da linha, sem o RPPS (Anexo 6), ÷ RCL proporcional (Gráfico 7 e Tabela 4). "
        "Negativo: as despesas não financeiras superaram as receitas não financeiras, e a diferença é coberta com "
        "dívida ou caixa."),
    "primario_com_rpps": (
        "Resultado primário com RPPS ÷ RCL", "%", "menor",
        "Igual ao anterior, incluindo receitas e despesas do RPPS (Gráfico 8 e Tabela 5)."),
    "var_divida": (
        "Variação da dívida consolidada no ano", "%", "maior",
        "Dívida consolidada no fim do bimestre ÷ dívida consolidada em 31/12 do ano anterior − 1 (Anexo 6; Gráfico 9)."),
}


def _soma(df: pd.DataFrame, anexo: str, cods: list[str], coluna: str | re.Pattern) -> pd.Series:
    d = df[(df["anexo"] == anexo) & df["cod_conta"].isin(cods)]
    d = d[d["coluna"].astype(str).str.fullmatch(coluna)] if isinstance(coluna, re.Pattern) else d[d["coluna"] == coluna]
    if d.empty:
        return pd.Series(dtype=float)
    s = d.groupby(CHAVE, observed=True)["valor"].sum()
    s.index = s.index.set_levels(s.index.levels[0].astype(str), level=0)
    return s


def calcular(df: pd.DataFrame, rcl_rel: pd.DataFrame) -> pd.DataFrame:
    """Indicadores por UF e bimestre (formato longo: uf, exercicio, periodo, data, indicador, valor) e, à parte, os
    valores em R$ usados (colunas *_rs no formato largo)."""
    if df.empty:
        return pd.DataFrame()
    df = df[df["anexo"].isin(["RREO-Anexo 01", "RREO-Anexo 04", "RREO-Anexo 06"])]
    a1 = "RREO-Anexo 01"
    s = lambda cods, col, anexo=a1: _soma(df, anexo, cods, col)  # noqa: E731
    tm = s(["TransferenciasAMunicipios"], L)
    w = pd.DataFrame({
        "rc": s(["ReceitasCorrentes", "ReceitasCorrentesIntra"], R),
        "rt": s(["TotalReceitas"], R),
        "transf": s(["TransferenciasCorrentes", "TransferenciasCorrentesIntra"], R),
        "dc": s(["DespesasCorrentes", "DespesasCorrentesIntra"], L),
        "dt_liq": s(["TotalDespesas"], L),
        "pessoal": s(["PessoalEEncargosSociais", "PessoalEEncargosSociaisIntra"], L),
        "custeio": s(["OutrasDespesasCorrentes", "OutrasDespesasCorrentesIntra"], L),
        "divida": s(["JurosEEncargosDaDivida", "AmortizacaoDaDivida", "JurosEEncargosDaDividaIntra",
                     "AmortizacaoDaDividaIntra"], L),
        "invest": s(["Investimentos", "InversoesFinanceiras", "InvestimentosIntra", "InversoesFinanceirasIntra"], L),
        "tm": tm,
        "rpps_cap": s(["RREO4ResultadoRPPSPrevidenciario"], "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (e)", "RREO-Anexo 04"),
        "rpps_rep": s(["RREO4ResultadoRPPSFinanceiro"], "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (e)", "RREO-Anexo 04"),
        "prim_sem": s(["ResultadoPrimarioSemRPPSAcimaDaLinha"], "VALOR", "RREO-Anexo 06"),
        "prim_com": s(["ResultadoPrimarioComRPPSAcimaDaLinha"], "VALOR", "RREO-Anexo 06"),
        "dc_ini": s(["DividaConsolidada"], re.compile(r"Em 31/12/\d{4} \(a\)"), "RREO-Anexo 06"),
        "dc_fim": s(["DividaConsolidada"], re.compile(r"Até o Bimestre \d{4} \(b\)"), "RREO-Anexo 06"),
    })
    w["tm"] = w["tm"].fillna(0)
    for c in ("rc", "rt", "dc", "custeio"):
        w[c] = w[c] - w["tm"]
    w["dt_liq"] = w["dt_liq"] - w["tm"]
    w = w.reset_index()
    rcl = rcl_rel.assign(uf=rcl_rel["uf"].astype(str))
    w = w.merge(rcl, on=CHAVE, how="left")
    w["rcl_prop"] = w["rcl12"] * 2 * w["periodo"] / 12
    ant = w[CHAVE + ["rc", "dc"]].assign(exercicio=w["exercicio"] + 1).rename(columns={"rc": "rc_ant", "dc": "dc_ant"})
    w = w.merge(ant, on=CHAVE, how="left")

    pct = lambda a, b: 100 * a / b.where(b.abs() > 0)  # noqa: E731
    out = pd.DataFrame({
        "cresc_receita": pct(w["rc"], w["rc_ant"]) - 100,
        "cresc_despesa": pct(w["dc"], w["dc_ant"]) - 100,
        "res_orcamentario": pct(w["rt"] - w["dt_liq"], w["rcl_prop"]),
        "poupanca_corrente": pct(w["rc"] - w["dc"], w["rcl_prop"]),
        "dependencia": pct(w["transf"], w["rc"]),
        "pessoal_rt": pct(w["pessoal"], w["rt"]),
        "custeio_rt": pct(w["custeio"], w["rt"]),
        "divida_rt": pct(w["divida"], w["rt"]),
        "invest_rt": pct(w["invest"], w["rt"]),
        "rpps_capitalizacao": pct(w["rpps_cap"], w["rcl_prop"]),
        "rpps_reparticao": pct(w["rpps_rep"], w["rcl_prop"]),
        "primario_sem_rpps": pct(w["prim_sem"], w["rcl_prop"]),
        "primario_com_rpps": pct(w["prim_com"], w["rcl_prop"]),
        "var_divida": pct(w["dc_fim"], w["dc_ini"]) - 100,
    })
    out["despesa_rt"] = out[["pessoal_rt", "custeio_rt", "divida_rt", "invest_rt"]].sum(axis=1, min_count=4)
    out["dif_crescimento"] = out["cresc_despesa"] - out["cresc_receita"]
    out = pd.concat([w[CHAVE], out], axis=1)
    longo = out.melt(id_vars=CHAVE, var_name="indicador", value_name="valor").dropna(subset=["valor"])
    longo["data"] = pd.to_datetime(dict(year=longo["exercicio"].astype(int), month=longo["periodo"].astype(int) * 2,
                                        day=1))
    longo.attrs["valores_rs"] = w  # valores em R$ (para a tabela de conferência)
    return longo.reset_index(drop=True)


def estatisticas(longo: pd.DataFrame, indicador: str, uf: str = "MS") -> pd.DataFrame:
    """Estatísticas descritivas entre as UFs, por bimestre, e a posição da UF (1 = pior).

    Colunas: data, n, minimo, p25, mediana, media, p75, maximo, desvio, valor_uf, posicao, percentil, dif_mediana."""
    pior = INDICADORES[indicador][2]
    d = longo[longo["indicador"] == indicador]
    linhas = []
    for (ano, per), g in d.groupby(["exercicio", "periodo"]):
        v = g.set_index("uf")["valor"]
        if len(v) < 10:
            continue
        ordem = v.sort_values(ascending=(pior == "menor"))  # do pior para o melhor
        x = v.get(uf)
        linhas.append({
            "exercicio": ano, "periodo": per, "data": g["data"].iat[0], "n": len(v), "minimo": v.min(),
            "p25": v.quantile(0.25), "mediana": v.median(), "media": v.mean(), "p75": v.quantile(0.75),
            "maximo": v.max(), "desvio": v.std(), "valor_uf": x,
            "posicao": (list(ordem.index).index(uf) + 1) if uf in v.index else None,
            "pior_uf": ordem.index[0], "pior_valor": ordem.iat[0],
            "dif_mediana": (x - v.median()) if x is not None else None,
            "z": ((x - v.mean()) / v.std()) if x is not None and v.std() > 0 else None,
        })
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------ metodologia (exibida no painel)
# Termos usados nas fórmulas: (nome curto, definição com as linhas do RREO). Valores acumulados de janeiro ao fim do
# bimestre; "(c)", "(h)" e "(e)" são as colunas do demonstrativo.
TERMOS: dict[str, tuple[str, str]] = {
    "rc": ("RC – receita corrente",
           "Anexo 1: 'RECEITAS CORRENTES' + 'RECEITAS CORRENTES' intraorçamentárias, coluna 'Até o Bimestre (c)', "
           "menos TM"),
    "rc_ant": ("RC do ano anterior", "RC do mesmo bimestre do exercício anterior, com a mesma definição"),
    "dc": ("DC – despesa corrente",
           "Anexo 1: 'DESPESAS CORRENTES' + 'DESPESAS CORRENTES' intraorçamentárias, coluna 'Despesas liquidadas até o "
           "bimestre (h)', menos TM"),
    "dc_ant": ("DC do ano anterior", "DC do mesmo bimestre do exercício anterior, com a mesma definição"),
    "rt": ("RT – receita total", "Anexo 1: 'TOTAL DAS RECEITAS (V)' (inclui as intraorçamentárias), coluna (c), menos TM"),
    "dt_liq": ("DT – despesa total", "Anexo 1: 'TOTAL DAS DESPESAS (XII)', liquidadas (h), menos TM"),
    "transf": ("Transferências correntes",
               "Anexo 1: 'TRANSFERÊNCIAS CORRENTES' + 'TRANSFERÊNCIAS CORRENTES' intraorçamentárias, coluna (c)"),
    "pessoal": ("Pessoal", "Anexo 1: 'PESSOAL E ENCARGOS SOCIAIS' + intraorçamentárias, liquidadas (h)"),
    "custeio": ("Custeio", "Anexo 1: 'OUTRAS DESPESAS CORRENTES' + intraorçamentárias, liquidadas (h), menos TM"),
    "divida": ("Serviço da dívida",
               "Anexo 1: 'JUROS E ENCARGOS DA DÍVIDA' + 'AMORTIZAÇÃO DA DÍVIDA' (+ intraorçamentárias), liquidadas (h)"),
    "invest": ("Investimentos",
               "Anexo 1: 'INVESTIMENTOS' + 'INVERSÕES FINANCEIRAS' (+ intraorçamentárias), liquidadas (h)"),
    "tm": ("TM – transferências a municípios",
           "Anexo 1: 'Transferências a Municípios' (dentro de Outras despesas correntes), liquidadas (h). É zero nas "
           "UFs que já registram a repartição de ICMS e IPVA como dedução da receita"),
    "rpps_cap": ("Resultado do fundo em capitalização",
                 "Anexo 4: 'RESULTADO PREVIDENCIÁRIO - FUNDO EM CAPITALIZAÇÃO (VI)', coluna 'Despesas liquidadas até o "
                 "bimestre (e)' (receitas realizadas − despesas liquidadas do plano previdenciário)"),
    "rpps_rep": ("Resultado do fundo em repartição",
                 "Anexo 4: 'RESULTADO PREVIDENCIÁRIO - FUNDO EM REPARTIÇÃO', coluna (e) (plano financeiro)"),
    "prim_sem": ("Resultado primário sem RPPS", "Anexo 6: 'RESULTADO PRIMÁRIO (SEM RPPS) - Acima da Linha', coluna 'VALOR'"),
    "prim_com": ("Resultado primário com RPPS", "Anexo 6: 'RESULTADO PRIMÁRIO (COM RPPS) - Acima da Linha', coluna 'VALOR'"),
    "dc_ini": ("Dívida consolidada em 31/12 do ano anterior", "Anexo 6: 'DÍVIDA CONSOLIDADA', coluna 'Em 31/12/<ano anterior> (a)'"),
    "dc_fim": ("Dívida consolidada no fim do bimestre", "Anexo 6: 'DÍVIDA CONSOLIDADA', coluna 'Até o Bimestre <ano> (b)'"),
    "rcl12": ("RCL de 12 meses", "Anexo 3: 'RECEITA CORRENTE LÍQUIDA (III)', coluna 'TOTAL (ÚLTIMOS 12 MESES)'"),
    "rcl_prop": ("RCL proporcional", "RCL de 12 meses × (2 × bimestre) ÷ 12 — a parte da RCL anual correspondente aos "
                                     "meses decorridos (no 3º bimestre, metade)"),
}
# indicador: (fórmula, termos usados, referência no RREO em Foco)
FORMULAS: dict[str, tuple[str, list[str], str]] = {
    "dif_crescimento": ("100 × (DC ÷ DC do ano anterior − 1) − 100 × (RC ÷ RC do ano anterior − 1)",
                        ["dc", "dc_ant", "rc", "rc_ant", "tm"], "derivado do Gráfico 1"),
    "cresc_receita": ("100 × (RC ÷ RC do ano anterior − 1)", ["rc", "rc_ant", "tm"], "Gráfico 1"),
    "cresc_despesa": ("100 × (DC ÷ DC do ano anterior − 1)", ["dc", "dc_ant", "tm"], "Gráfico 1"),
    "res_orcamentario": ("100 × (RT − DT) ÷ RCL proporcional", ["rt", "dt_liq", "tm", "rcl12", "rcl_prop"],
                         "Gráfico 2 e Tabela 1"),
    "poupanca_corrente": ("100 × (RC − DC) ÷ RCL proporcional", ["rc", "dc", "tm", "rcl12", "rcl_prop"], "Gráfico 4"),
    "dependencia": ("100 × transferências correntes ÷ RC", ["transf", "rc", "tm"], "Gráfico 3"),
    "pessoal_rt": ("100 × pessoal ÷ RT", ["pessoal", "rt", "tm"], "Gráfico 5 e Tabela 2"),
    "custeio_rt": ("100 × custeio ÷ RT", ["custeio", "rt", "tm"], "Gráfico 5 e Tabela 2"),
    "divida_rt": ("100 × serviço da dívida ÷ RT", ["divida", "rt", "tm"], "Gráfico 5 e Tabela 2"),
    "invest_rt": ("100 × investimentos ÷ RT", ["invest", "rt", "tm"], "Gráfico 5 e Tabela 2"),
    "despesa_rt": ("100 × (pessoal + custeio + serviço da dívida + investimentos) ÷ RT",
                   ["pessoal", "custeio", "divida", "invest", "rt", "tm"], "Gráfico 5"),
    "rpps_capitalizacao": ("100 × resultado do fundo em capitalização ÷ RCL proporcional",
                           ["rpps_cap", "rcl12", "rcl_prop"], "Gráfico 6 e Tabela 3"),
    "rpps_reparticao": ("100 × resultado do fundo em repartição ÷ RCL proporcional",
                        ["rpps_rep", "rcl12", "rcl_prop"], "Gráfico 6 e Tabela 3"),
    "primario_sem_rpps": ("100 × resultado primário sem RPPS ÷ RCL proporcional", ["prim_sem", "rcl12", "rcl_prop"],
                          "Gráfico 7 e Tabela 4"),
    "primario_com_rpps": ("100 × resultado primário com RPPS ÷ RCL proporcional", ["prim_com", "rcl12", "rcl_prop"],
                          "Gráfico 8 e Tabela 5"),
    "var_divida": ("100 × (dívida consolidada no fim do bimestre ÷ dívida consolidada em 31/12 do ano anterior − 1)",
                   ["dc_fim", "dc_ini"], "Gráfico 9"),
}


def componentes(longo: pd.DataFrame, indicador: str, uf: str, exercicio: int, periodo: int) -> pd.DataFrame:
    """Termos (em R$) usados no cálculo do indicador para a UF e o bimestre, com a definição de cada um."""
    w = longo.attrs.get("valores_rs")
    if w is None:
        return pd.DataFrame()
    lin = w[(w["uf"] == uf) & (w["exercicio"] == exercicio) & (w["periodo"] == periodo)]
    if lin.empty:
        return pd.DataFrame()
    lin = lin.iloc[0]
    return pd.DataFrame([{"Termo": TERMOS[t][0], "Valor (R$)": lin.get(t), "Como é obtido": TERMOS[t][1]}
                         for t in FORMULAS[indicador][1]])
