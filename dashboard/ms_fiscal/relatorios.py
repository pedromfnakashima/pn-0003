"""Extração de séries dos anexos do RREO e do RGF (Manual de Demonstrativos Fiscais)."""
from __future__ import annotations

import re

import pandas as pd


def rotulo_periodo(df: pd.DataFrame, tipo: str) -> pd.Series:
    suf = "º bim" if tipo == "rreo" else "º quad"
    return df["exercicio"].astype(int).astype(str) + " – " + df["periodo"].astype(int).astype(str) + suf


def ultimo_periodo(df: pd.DataFrame) -> tuple[int, int] | None:
    if df.empty:
        return None
    a = int(df["exercicio"].max())
    return a, int(df.loc[df["exercicio"] == a, "periodo"].max())


def mensal_mr(df: pd.DataFrame, anexo: str, cod_conta: str, meses_por_periodo: int) -> pd.DataFrame:
    """Converte as colunas <MR-11> … <MR> (12 meses móveis) em série mensal.

    <MR> é o último mês do período (bimestre: 2·b; quadrimestre: 4·q). Quando um mês
    aparece em mais de um relatório, prevalece o relatório mais recente.
    """
    d = df[(df["anexo"] == anexo) & (df["cod_conta"] == cod_conta) & df["coluna"].str.startswith("<MR")].copy()
    if d.empty:
        return pd.DataFrame(columns=["data", "valor"])
    d["defasagem"] = d["coluna"].str.extract(r"<MR-?(\d*)>")[0].replace("", "0").astype(int)
    fim = pd.to_datetime(dict(year=d["exercicio"], month=d["periodo"] * meses_por_periodo, day=1))
    d["data"] = [f - pd.DateOffset(months=k) for f, k in zip(fim, d["defasagem"])]
    d["ordem"] = d["exercicio"] * 10 + d["periodo"]
    d = d.sort_values("ordem").drop_duplicates(["data", "instituicao"], keep="last")
    return d.groupby("data", as_index=False)["valor"].sum().sort_values("data")


IMPOSTOS_ANEXO3 = {
    "ICMSLiquidoExcetoTransferenciasEFUNDEB": "ICMS",
    "IPVALiquidoExcetoTransferenciasEFUNDEB": "IPVA",
    "ITCDLiquidoExcetoTransferenciasEFUNDEB": "ITCD",
    "IRRFLiquidoExcetoTransferenciasEFUNDEB": "IRRF",
}


def impostos_no_anexo1(df: pd.DataFrame) -> pd.DataFrame:
    """Linhas de ICMS, IPVA, ITCD e IRRF do Anexo 3 nas colunas do Anexo 1 (o Anexo 1 só desce até "Impostos").

    Em cada relatório (exercício, bimestre b), <MR-k> é o mês 2·b − k: "No Bimestre (b)" soma <MR-1> e <MR>;
    "Até o Bimestre (c)" soma de <MR-(2·b−1)> a <MR>; "PREVISÃO ATUALIZADA (a)" vem de "PREVISÃO ATUALIZADA AAAA".
    Os valores do Anexo 3 são brutos: antes das transferências a municípios e da dedução para o FUNDEB.
    """
    d = df[(df["anexo"] == "RREO-Anexo 03") & df["cod_conta"].isin(IMPOSTOS_ANEXO3)]
    if d.empty:
        return d
    chave = ["exercicio", "periodo", "cod_conta"]
    mr = d[d["coluna"].str.startswith("<MR")].copy()
    mr["k"] = mr["coluna"].str.extract(r"<MR-?(\d*)>")[0].replace("", "0").astype(int)
    bim = mr[mr["k"] <= 1].groupby(chave)["valor"].sum()
    ate = mr[mr["k"] < 2 * mr["periodo"]].groupby(chave)["valor"].sum()
    prev = d[d["coluna"] == "PREVISÃO ATUALIZADA " + d["exercicio"].astype(int).astype(str)].groupby(chave)["valor"].sum()
    t = pd.DataFrame({"PREVISÃO ATUALIZADA (a)": prev, "No Bimestre (b)": bim, "Até o Bimestre (c)": ate})
    t["% (b/a)"] = 100 * t["No Bimestre (b)"] / t["PREVISÃO ATUALIZADA (a)"]
    t["% (c/a)"] = 100 * t["Até o Bimestre (c)"] / t["PREVISÃO ATUALIZADA (a)"]
    t["SALDO (a-c)"] = t["PREVISÃO ATUALIZADA (a)"] - t["Até o Bimestre (c)"]
    t = t.reset_index().melt(id_vars=chave, var_name="coluna", value_name="valor").dropna(subset=["valor"])
    t["conta"] = "↳ " + t["cod_conta"].map(IMPOSTOS_ANEXO3) + " (do Anexo 3, bruto)"
    t["anexo"] = "RREO-Anexo 01"
    return t


def serie_por_periodo(df: pd.DataFrame, anexo: str, cod_conta: str, coluna: str | re.Pattern,
                      tipo: str, agrega: str = "sum") -> pd.DataFrame:
    d = df[(df["anexo"] == anexo) & (df["cod_conta"] == cod_conta)]
    if isinstance(coluna, str):
        d = d[d["coluna"] == coluna]
    else:
        d = d[d["coluna"].str.contains(coluna)]
    if d.empty:
        return pd.DataFrame(columns=["exercicio", "periodo", "rotulo", "valor"])
    s = d.groupby(["exercicio", "periodo"], as_index=False)["valor"].agg(agrega)
    s["rotulo"] = rotulo_periodo(s, tipo)
    return s.sort_values(["exercicio", "periodo"])


def coluna_quadrimestre_atual(df: pd.DataFrame) -> pd.DataFrame:
    """No Anexo 2/3 do RGF, mantém a coluna 'Até o Nº Quadrimestre' que corresponde ao período do relatório."""
    alvo = "Até o " + df["periodo"].astype(int).astype(str) + "º Quadrimestre"
    return df[df["coluna"] == alvo]


def dtp_rcl(rgf: pd.DataFrame) -> pd.DataFrame:
    """% da despesa total com pessoal sobre a RCL ajustada, por poder e instituição."""
    d = rgf[(rgf["anexo"] == "RGF-Anexo 01") & (rgf["cod_conta"] == "DespesaComPessoalTotal")]
    pct = d[d["coluna"].str.contains("RCL", case=False)][["exercicio", "periodo", "co_poder", "instituicao", "valor"]]
    val = d[d["coluna"] == "Valor"][["exercicio", "periodo", "co_poder", "instituicao", "valor"]]
    out = pct.merge(val, on=["exercicio", "periodo", "co_poder", "instituicao"], suffixes=("_pct", "_valor"))
    out["rotulo"] = rotulo_periodo(out, "rgf")
    return out.sort_values(["exercicio", "periodo"])


def tabela_anexo(df: pd.DataFrame, anexo: str, ano: int, periodo: int, instituicao: str | None = None) -> pd.DataFrame:
    """Tabela larga (linhas = contas, colunas = colunas do demonstrativo), na ordem original."""
    d = df[(df["anexo"] == anexo) & (df["exercicio"] == ano) & (df["periodo"] == periodo)].copy()
    if instituicao:
        d = d[d["instituicao"] == instituicao]
    if d.empty:
        return pd.DataFrame()
    d["ordem"] = range(len(d))
    linhas = d.groupby(["rotulo", "cod_conta", "conta"], sort=False)["ordem"].min().reset_index()
    cols = list(dict.fromkeys(d["coluna"]))
    larga = d.pivot_table(index=["rotulo", "cod_conta", "conta"], columns="coluna", values="valor", aggfunc="sum", sort=False)
    larga = larga.reindex(columns=cols)
    larga = linhas.merge(larga.reset_index(), on=["rotulo", "cod_conta", "conta"]).sort_values("ordem").drop(columns="ordem")
    return larga.rename(columns={"rotulo": "Quadro", "cod_conta": "Código", "conta": "Conta"})


def anexo2_funcoes(df: pd.DataFrame, ano: int, bim: int, coluna: str) -> pd.DataFrame:
    """Anexo 2 do RREO em formato função × subfunção (as linhas vêm em sequência: função, depois subfunções)."""
    from .referencias import FUNCOES

    nomes = {v.lower(): k for k, v in FUNCOES.items()}
    nomes.update({"encargos especiais": "28", "reserva de contingência": "99", "direitos da cidadania": "14"})
    d = df[(df["anexo"] == "RREO-Anexo 02") & (df["exercicio"] == ano) & (df["periodo"] == bim) & (df["coluna"] == coluna)]
    d = d[d["rotulo"].str.contains("Exceto Intra", case=False)]
    linhas, atual = [], None
    for r in d.itertuples():
        nome = r.conta.strip()
        if nome.lower() in nomes:
            atual = f"{nomes[nome.lower()]} – {nome}"
            continue
        if nome.upper().startswith(("DESPESAS", "TOTAL")):
            atual = None
            continue
        if atual:
            sub = re.sub(r"^FU\d{2} - ", "", nome)
            linhas.append({"funcao": atual, "subfuncao": sub, "valor": r.valor})
    return pd.DataFrame(linhas)


# Anexo 14 (Demonstrativo Simplificado): (cod_conta, coluna) de cada indicador do resumo do RREO
_A14 = "DemonstrativoSimplificado"
RESUMO_A14 = {
    "receita_inicial": (f"PrevisaoInicial{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "receita_prevista": (f"PrevisaoAtualizada{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "receita_realizada": (f"ReceitasRealizadas{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "saldos_anteriores": (f"SaldoDeExerciciosAnterioresUtilizadosParaCreditosAdicionais{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "dotacao_inicial": (f"DotacaoInicial{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "dotacao": (f"DotacaoAtualizada{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "empenhada": (f"DespesasEmpenhadas{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "liquidada": (f"DespesasLiquidadas{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "paga": (f"DespesasPagas{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "superavit": (f"SuperavitOrcamentario{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "deficit": (f"DeficitOrcamentario{_A14}BalancoOrcamentario", "Até o Bimestre"),
    "rcl": (f"ReceitaCorrenteLiquida{_A14}", "Até o Bimestre"),
    "rpps_receita": (f"ReceitasPrevidenciariasRealizadasRPPSPrevidenciario{_A14}", "Até o Bimestre"),
    "rpps_despesa": (f"DespesasPrevidenciariasLiquidadasRPPSPrevidenciario{_A14}", "Até o Bimestre"),
    "rpps_resultado": (f"ResultadoPrevidenciarioRPPSPrevidenciario{_A14}", "Até o Bimestre"),
    "primario_meta": (f"ResultadoPrimarioAcimaDaLinhaSemRPPS{_A14}", "Meta Fixada no Anexo de Metas Fiscais da LDO (a)"),
    "primario": (f"ResultadoPrimarioAcimaDaLinhaSemRPPS{_A14}", "Resultado Apurado até o Bimestre (b)"),
    "nominal_meta": (f"ResultadoNominalAbaixoDaLinhaSemRPPS{_A14}", "Meta Fixada no Anexo de Metas Fiscais da LDO (a)"),
    "nominal": (f"ResultadoNominalAbaixoDaLinhaSemRPPS{_A14}", "Resultado Apurado até o Bimestre (b)"),
    "rp_inscrito": (f"TotalRestosAPagar{_A14}", "Inscrição"),
    "rp_cancelado": (f"TotalRestosAPagar{_A14}", "Cancelamento Até o Bimestre"),
    "rp_pago": (f"TotalRestosAPagar{_A14}", "Pagamento Até o Bimestre"),
    "rp_saldo": (f"TotalRestosAPagar{_A14}", "Saldo a Pagar"),
    "mde_pct": (f"MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsino{_A14}", "% Aplicado Até o Bimestre"),
    "mde_min": (f"MinimoAnualDasReceitasDeImpostosNaManutencaoEDesenvolvimentoDoEnsino{_A14}", "% Mínimo a Aplicar no Exercício"),
    "fundeb_pct": (f"MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedio{_A14}",
                   "% Aplicado Até o Bimestre"),
    "fundeb_min": (f"MinimoAnualDoFUNDEBNaRemuneracaoDoMagisterioComEducacaoInfantilEnsinoFundamentalEMedio{_A14}",
                   "% Mínimo a Aplicar no Exercício"),
    "asps_pct": ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "% Aplicado Até o Bimestre"),
    "asps_min": ("AplicacaoTotalDasDespesasComAcoesEServicosPublicosDeSaude", "% Mínimo a Aplicar no Exercício"),
    "ppp_pct": (f"TotalDasDespesasDeCaraterContinuadoEmRelacaoAReceitaCorrenteLiquida{_A14}", "Valor Apurado no Exercício Corrente"),
}

# Anexo 1: grupos de natureza da despesa (exceto intraorçamentárias)
GRUPOS_DESPESA = {
    "PessoalEEncargosSociais": "Pessoal e encargos sociais",
    "JurosEEncargosDaDivida": "Juros e encargos da dívida",
    "OutrasDespesasCorrentes": "Outras despesas correntes",
    "Investimentos": "Investimentos",
    "InversoesFinanceiras": "Inversões financeiras",
    "AmortizacaoDaDivida": "Amortização da dívida",
}


def resumo_rreo(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por relatório (exercicio, periodo) com os indicadores do Anexo 14 (ver RESUMO_A14).

    A API omite as linhas com valor zero; por isso superávit e déficit ausentes valem 0.
    `resultado` = superávit − déficit (nos bimestres intermediários, receita realizada − despesa liquidada).
    """
    d = df[df["anexo"] == "RREO-Anexo 14"]
    if d.empty:
        return pd.DataFrame()
    nomes = {v: k for k, v in RESUMO_A14.items()}
    d = d.assign(ind=[nomes.get((c, col)) for c, col in zip(d["cod_conta"], d["coluna"])]).dropna(subset=["ind"])
    t = d.pivot_table(index=["exercicio", "periodo"], columns="ind", values="valor", aggfunc="first")
    t = t.reindex(columns=list(RESUMO_A14))
    t[["superavit", "deficit", "rp_cancelado"]] = t[["superavit", "deficit", "rp_cancelado"]].fillna(0)
    t["resultado"] = t["superavit"] - t["deficit"]
    return t.reset_index().sort_values(["exercicio", "periodo"])


def despesa_por_grupo(df: pd.DataFrame, ano: int, bim: int, coluna: str = "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)") -> pd.DataFrame:
    d = df[(df["anexo"] == "RREO-Anexo 01") & (df["exercicio"] == ano) & (df["periodo"] == bim) &
           df["cod_conta"].isin(GRUPOS_DESPESA) & (df["coluna"] == coluna)]
    out = d.groupby("cod_conta", as_index=False)["valor"].sum()
    out["grupo"] = out["cod_conta"].map(GRUPOS_DESPESA)
    return out[out["valor"] > 0].sort_values("valor", ascending=False)


def acumulado_12m(mensal: pd.DataFrame) -> pd.DataFrame:
    """Soma móvel de 12 meses de uma série mensal (data, valor); só onde há 12 meses seguidos."""
    if mensal.empty:
        return mensal
    s = mensal.set_index("data")["valor"].asfreq("MS")
    return s.rolling(12, min_periods=12).sum().dropna().rename("valor").reset_index()


# ------------------------------------------------------------------ IFGF (Firjan) adaptado ao Estado
# Metodologia: Índice Firjan de Gestão Fiscal, Anexo Metodológico, edição 2025 (www.firjan.com.br/ifgf/metodologia/).
# Cada indicador vai de 0 a 1; o índice geral é a média simples dos quatro (25% cada).
IFGF_CONCEITOS = [(0.8, "Gestão de excelência", "green"), (0.6, "Boa gestão", "blue"),
                  (0.4, "Gestão em dificuldade", "orange"), (0.0, "Gestão crítica", "red")]
IFGF_RECEITA_LOCAL = ["ICMSLiquidoExcetoTransferenciasEFUNDEB", "IPVALiquidoExcetoTransferenciasEFUNDEB",
                      "ITCDLiquidoExcetoTransferenciasEFUNDEB", "IRRFLiquidoExcetoTransferenciasEFUNDEB",
                      "OutrasReceitasPatrimoniais", "RREO3ReceitaDeServicos"]
IFGF_DEDUCOES = ["ReceitaDeTransferenciasConstitucionaisELegais", "DeducaoDeReceitaParaFormacaoDoFUNDEB"]
IFGF_FUNCOES_ADM = ["Legislativa", "Judiciária", "Essencial à Justiça", "Administração"]


def ifgf_conceito(nota: float) -> tuple[str, str]:
    if pd.isna(nota):
        return "sem dado", "gray"
    return next((nome, cor) for lim, nome, cor in IFGF_CONCEITOS if nota > lim or lim == 0)


def ifgf_autonomia(ind: float) -> float:
    return float("nan") if pd.isna(ind) else 1.0 if ind > 0.25 else max(ind, 0) / 0.25


def ifgf_pessoal(ind: float) -> float:
    return float("nan") if pd.isna(ind) else 1.0 if ind < 0.45 else 0.0 if ind > 0.60 else 1 - (ind - 0.45) / 0.15


def ifgf_liquidez(ind: float) -> float:
    return float("nan") if pd.isna(ind) else 1.0 if ind > 0.25 else 0.0 if ind < 0 else 0.4 + 0.6 * ind / 0.25


def ifgf_investimentos(ind: float) -> float:
    return float("nan") if pd.isna(ind) else 1.0 if ind > 0.12 else max(ind, 0) / 0.12


def _doze_meses(s: pd.Series) -> pd.Series:
    """Converte um acumulado no ano, indexado por (exercicio, periodo), em soma dos últimos 12 meses:
    acumulado do bimestre + total do ano anterior − acumulado do ano anterior até o mesmo bimestre."""
    out = {}
    for (a, b), v in s.items():
        if b == 6:
            out[(a, b)] = v
        else:
            out[(a, b)] = v + s.get((a - 1, 6), float("nan")) - s.get((a - 1, b), float("nan"))
    return pd.Series(out, dtype=float)


def ifgf_estado(rreo: pd.DataFrame, rgf: pd.DataFrame) -> pd.DataFrame:
    """Os quatro indicadores do IFGF para o Estado, por relatório do RREO (exercicio, periodo), em 12 meses.

    - Autonomia: (receitas da economia local − custo das funções 01 a 04) ÷ RCL. Receitas = ICMS, IPVA, ITCD e
      IRRF líquidos das transferências a municípios e da dedução para o FUNDEB, mais outras receitas patrimoniais
      (exclui rendimentos de aplicação) e receita de serviços (RREO, Anexo 3, 12 meses). Custo = despesa liquidada
      nas funções Legislativa, Judiciária, Essencial à Justiça e Administração (Anexo 2, exceto intra).
    - Gastos com pessoal: despesa total com pessoal de todos os Poderes e órgãos ÷ RCL ajustada (RGF, Anexo 1,
      último quadrimestre encerrado até o fim do bimestre). O RREO não traz a despesa com pessoal da LRF.
    - Liquidez: (disponibilidade de caixa bruta − restos a pagar inscritos no ano) ÷ RCL, em 31/12 do último
      exercício encerrado (caixa: RGF, Anexo 5; restos a pagar = empenhado − pago: RREO, Anexo 14, 6º bimestre).
    - Investimentos: (investimentos + inversões financeiras liquidados) ÷ receita total (Anexo 1, exceto intra).
    """
    a3 = rreo[(rreo["anexo"] == "RREO-Anexo 03") & (rreo["coluna"] == "TOTAL (ÚLTIMOS 12 MESES)")]
    a3 = a3.pivot_table(index=["exercicio", "periodo"], columns="cod_conta", values="valor", aggfunc="sum")
    if a3.empty:
        return pd.DataFrame()
    t = pd.DataFrame(index=a3.index)
    t["receita_local"] = a3.reindex(columns=IFGF_RECEITA_LOCAL).fillna(0).sum(axis=1) - \
        a3.reindex(columns=IFGF_DEDUCOES).fillna(0).sum(axis=1)
    t["rcl"] = a3["RREO3ReceitaCorrenteLiquida"]

    a2 = rreo[(rreo["anexo"] == "RREO-Anexo 02") & (rreo["cod_conta"] == "RREO2TotalDespesas") &
              rreo["coluna"].str.startswith("DESPESAS LIQUIDADAS ATÉ") & rreo["conta"].str.strip().isin(IFGF_FUNCOES_ADM)]
    t["custo_adm"] = _doze_meses(a2.groupby(["exercicio", "periodo"])["valor"].sum())

    a1 = rreo[rreo["anexo"] == "RREO-Anexo 01"]
    inv = a1[a1["cod_conta"].isin(["Investimentos", "InversoesFinanceiras"]) &
             (a1["coluna"] == "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (h)")].groupby(["exercicio", "periodo"])["valor"].sum()
    rec = a1[(a1["cod_conta"] == "ReceitasExcetoIntraOrcamentarias") &
             (a1["coluna"] == "Até o Bimestre (c)")].groupby(["exercicio", "periodo"])["valor"].sum()
    t["investimentos"], t["receita_total"] = _doze_meses(inv), _doze_meses(rec)

    # pessoal: RGF do último quadrimestre cujo fim (mês 4q) não passa do fim do bimestre (mês 2b)
    dtp = dtp_rcl(rgf).groupby(["exercicio", "periodo"])["valor_pct"].sum() if not rgf.empty else pd.Series(dtype=float)
    # liquidez: caixa bruta de todos os Poderes no 3º quadrimestre (linhas de total de cada instituição)
    a5 = rgf[(rgf["anexo"] == "RGF-Anexo 05") & (rgf["cod_conta"] == "DisponibilidadeDeCaixaBruta") &
             rgf["conta"].str.startswith("TOTAL (")] if not rgf.empty else pd.DataFrame(columns=["exercicio", "valor"])
    caixa = a5.groupby("exercicio")["valor"].sum()
    res = resumo_rreo(rreo).set_index(["exercicio", "periodo"])
    for (a, b) in t.index:
        q = [(ea, ep) for ea, ep in dtp.index if (ea, 4 * ep) <= (a, 2 * b)]
        if q:
            ea, ep = max(q)
            t.loc[(a, b), ["pessoal_pct", "pessoal_ref"]] = dtp[(ea, ep)] / 100, f"{ep}º quad/{ea}"
        anos = [y for y in caixa.index if (y < a or (y == a and b == 6)) and (y, 6) in res.index]
        if anos:
            y = max(anos)
            r6 = res.loc[(y, 6)]
            t.loc[(a, b), ["caixa", "rp_inscrito_ano", "rcl_liquidez", "liquidez_ref"]] = (
                caixa[y], r6["empenhada"] - r6["paga"], r6["rcl"], f"31/12/{y}")
    t["autonomia_ind"] = (t["receita_local"] - t["custo_adm"]) / t["rcl"]
    t["liquidez_ind"] = (t["caixa"] - t["rp_inscrito_ano"]) / t["rcl_liquidez"]
    t["investimentos_ind"] = t["investimentos"] / t["receita_total"]
    t["autonomia"] = t["autonomia_ind"].map(ifgf_autonomia)
    t["pessoal"] = t["pessoal_pct"].astype(float).map(ifgf_pessoal)
    t["liquidez"] = t["liquidez_ind"].map(ifgf_liquidez)
    t["investimentos_nota"] = t["investimentos_ind"].map(ifgf_investimentos)
    t["ifgf"] = t[["autonomia", "pessoal", "liquidez", "investimentos_nota"]].mean(axis=1, skipna=False)
    return t.reset_index().sort_values(["exercicio", "periodo"])
