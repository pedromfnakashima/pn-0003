"""RGF de todos os Estados e do Distrito Federal, por Poder (API de dados abertos do Siconfi).

Endpoint /rgf (https://apidatalake.tesouro.gov.br/docs/siconfi/): um ente e um Poder por chamada — id_ente e co_poder
são obrigatórios (sem co_poder a API devolve vazio). Parâmetros: an_exercicio, in_periodicidade=Q, nr_periodo
(quadrimestre), co_tipo_demonstrativo=RGF, co_esfera=E, co_poder (E, L, J, M, D).

Gravação: dados/dashboard/rgf_estados/rgf_uf_AAAA_Q.parquet (todas as UFs e Poderes de um quadrimestre, zstd).

Séries mensais (o RGF é quadrimestral):
- Anexo 1 (pessoal): colunas <MR-11> … <MR>, em que <MR> é o último mês do quadrimestre (4·q) → série mensal de fato;
- saldos (Anexos 2 e 3: 'SALDO DO EXERCÍCIO ANTERIOR', 'Até o kº Quadrimestre') → posição no fim de dez/abr/ago/dez,
  com opção de interpolação linear mensal;
- fluxos do quadrimestre ou acumulados no ano → valor do quadrimestre e média mensal (valor ÷ 4 em cada mês);
- demais colunas → um ponto por relatório, no mês de referência (abr, ago, dez).
"""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd

from . import rreo_estados as RE
from .config import caminho

log = logging.getLogger(__name__)

DIR = caminho("rgf_estados")
PODERES = {"E": "Executivo", "L": "Legislativo", "J": "Judiciário", "M": "Ministério Público", "D": "Defensoria Pública"}
COLUNAS = ["exercicio", "periodo", "cod_ibge", "uf", "co_poder", "instituicao", "anexo", "rotulo", "coluna",
           "cod_conta", "conta", "valor"]
CATEGORICAS = ["uf", "co_poder", "instituicao", "anexo", "rotulo", "coluna", "cod_conta", "conta"]
EXTRAS = ("co_poder", "instituicao")
MESES = 4  # meses por quadrimestre

MENSAL = "Mensal: colunas <MR-11> … <MR> (Anexo 1)"
SALDOS = "Saldo no fim de cada quadrimestre (série)"
MODOS_MENSAL = RE.MODOS_MENSAL
MODOS_SALDO = ["Fim de cada quadrimestre (como publicado)", "Mensal por interpolação linear"]
MODOS_ACUMULADO = ["Acumulado no ano (como publicado)", "Valor do quadrimestre (desacumulado)",
                   "Média mensal do quadrimestre (÷ 4)"]
MODOS_FLUXO = ["Valor do quadrimestre", "Média mensal do quadrimestre (÷ 4)"]
_SALDO = re.compile(r"^(SALDO DO EXERC[ÍI]CIO ANTERIOR|At[ée] o (\d)º Quadrimestre)$", re.I)


# ------------------------------------------------------------------ coleta
def _rgf(ano: int, q: int, cod: int, poder: str) -> pd.DataFrame:
    it = RE._get("rgf", {"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": q, "co_tipo_demonstrativo": "RGF",
                         "co_esfera": "E", "co_poder": poder, "id_ente": cod})
    if not it:
        return pd.DataFrame(columns=COLUNAS)
    d = pd.DataFrame(it)
    for c in COLUNAS:
        if c not in d:
            d[c] = None
    return d[COLUNAS]


def _compactar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["valor"])
    df["exercicio"] = df["exercicio"].astype("int16")
    df["periodo"] = df["periodo"].astype("int8")
    df["cod_ibge"] = df["cod_ibge"].astype("int8")
    for c in CATEGORICAS:
        df[c] = df[c].astype(str).str.strip().astype("category")
    return df.sort_values(["uf", "co_poder", "instituicao", "anexo"], kind="stable").reset_index(drop=True)


def arquivo(ano: int, q: int):
    return DIR / f"rgf_uf_{ano}_{q}.parquet"


def periodos(anos: int = RE.ANOS_PADRAO, hoje: date | None = None) -> list[tuple[int, int]]:
    """Quadrimestres encerrados dos últimos `anos` exercícios."""
    hoje = hoje or date.today()
    return [(a, q) for a in range(hoje.year - anos + 1, hoje.year + 1) for q in (1, 2, 3)
            if (a, 4 * q) < (hoje.year, hoje.month)]


def atualizar(anos: int = RE.ANOS_PADRAO, forcar_ultimos: int = 1, paralelo: int = 3) -> None:
    """Baixa os quadrimestres que faltam e rebaixa os `forcar_ultimos` mais recentes. Um quadrimestre já gravado é
    refeito se faltar alguma UF."""
    tab = RE.entes()
    alvo = periodos(anos)
    recentes = set(alvo[-forcar_ultimos:]) if forcar_ultimos else set()
    DIR.mkdir(parents=True, exist_ok=True)
    for ano, q in alvo:
        arq = arquivo(ano, q)
        if arq.exists() and (ano, q) not in recentes:
            if set(pd.read_parquet(arq, columns=["uf"])["uf"].astype(str)) >= set(tab["uf"]):
                continue
        log.info("RGF das UFs: %s, %sº quadrimestre …", ano, q)
        partes = []
        with ThreadPoolExecutor(paralelo) as ex:
            fut = [ex.submit(_rgf, ano, q, int(r.cod_ibge), p) for r in tab.itertuples() for p in PODERES]
            for f in as_completed(fut):
                d = f.result()
                if not d.empty:
                    partes.append(d)
        if not partes:
            log.info("  nenhum Estado entregou ainda")
            continue
        df = _compactar(pd.concat(partes, ignore_index=True))
        log.info("  %d UFs, %d instituições, %d linhas", df["uf"].nunique(),
                 df[["uf", "instituicao"]].drop_duplicates().shape[0], len(df))
        df.to_parquet(arq, index=False, compression="zstd")


def carregar() -> pd.DataFrame:
    arqs = sorted(DIR.glob("rgf_uf_*.parquet"))
    if not arqs:
        return pd.DataFrame(columns=COLUNAS)
    partes = [pd.read_parquet(a) for a in arqs]
    for c in CATEGORICAS:
        cats = pd.api.types.union_categoricals([p[c].astype("category") for p in partes]).categories
        for p in partes:
            p[c] = p[c].astype(pd.CategoricalDtype(cats))
    return pd.concat(partes, ignore_index=True)


def preparar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mesma base enxuta do RREO, com Poder (co_poder) e instituição."""
    return RE.preparar(df, extras=EXTRAS)


# ------------------------------------------------------------------ classificação das colunas
def acumula(coluna: str) -> bool:
    """Acumuladas no ano: 'Até o Quadrimestre de Referência', 'VALOR ATÉ O QUADRIMESTRE DE REFERÊNCIA'."""
    return bool(re.search(r"at[ée] o quadrimestre de refer", coluna, re.I)) and "%" not in coluna


def fluxo(coluna: str) -> bool:
    return bool(re.search(r"^no quadrimestre", coluna, re.I))


def percentual(coluna: str) -> bool:
    return "%" in coluna


def colunas_da_linha(cols: list[str]) -> list[str]:
    """Opções de coluna: as mensais <MR-k> viram MENSAL; os saldos datados viram também SALDOS."""
    mr = [c for c in cols if c.startswith("<MR")]
    sal = [c for c in cols if _SALDO.match(c)]
    return ([MENSAL] if mr else []) + ([SALDOS] if len(sal) >= 2 else []) + [c for c in cols if not c.startswith("<MR")]


# ------------------------------------------------------------------ séries
def _saldos(d: pd.DataFrame) -> pd.DataFrame:
    """Saldos datados → posição no fim de cada quadrimestre; o relatório mais recente prevalece, por instituição."""
    m = d["coluna"].astype(str).str.extract(_SALDO)
    d = d.assign(k=pd.to_numeric(m[1], errors="coerce"), eh=m[0].notna())
    d = d[d["eh"]].copy()
    if d.empty:
        return pd.DataFrame(columns=["uf", "data", "valor"])
    ano = d["exercicio"].astype(int) - d["k"].isna().astype(int)  # saldo do exercício anterior = dezembro de ano-1
    mes = (d["k"].fillna(3) * MESES).astype(int)
    d["data"] = pd.to_datetime(dict(year=ano, month=mes, day=1))
    d["ordem"] = d["exercicio"].astype(int) * 10 + d["periodo"].astype(int)
    por = ["uf", "co_poder", "instituicao", "data"]
    d = d.groupby([*por, "ordem"], observed=True, as_index=False)["valor"].sum()
    d = d.sort_values("ordem").drop_duplicates(por, keep="last")
    return d.groupby(["uf", "data"], observed=True, as_index=False).agg(valor=("valor", "sum"),
                                                                        n_inst=("instituicao", "nunique"))


def _interpolar(s: pd.DataFrame) -> pd.DataFrame:
    out = []
    for uf, g in s.groupby("uf", observed=True):
        g = g.set_index("data")[["valor"]].asfreq("MS").interpolate("time", limit_area="inside")
        out.append(g.reset_index().assign(uf=uf))
    return pd.concat(out, ignore_index=True) if out else s


def _media_mensal(s: pd.DataFrame) -> pd.DataFrame:
    """Valor do quadrimestre → o mesmo valor ÷ 4 em cada um dos 4 meses (abr → jan…abr)."""
    if s.empty:
        return s
    linhas = []
    for k in range(MESES):
        linhas.append(s.assign(data=s["data"] - pd.DateOffset(months=k), valor=s["valor"] / MESES))
    return pd.concat(linhas, ignore_index=True)


def serie(base: pd.DataFrame, rcl_mes: pd.DataFrame, anexo: str, linhas: list[str], coluna: str,
          modo: str | None, poderes: list[str]) -> pd.DataFrame:
    """Série de uma ou mais linhas de um anexo do RGF, para todas as UFs, somando os Poderes escolhidos.

    Devolve uf, linha, data, ano, mes, valor, rcl12, pct_rcl e completo (False quando faltou alguma instituição que
    a UF costuma publicar naquela linha — o ponto é descartado na soma)."""
    d = base[(base["anexo"] == anexo) & base["linha"].isin(linhas) & base["co_poder"].isin(poderes)]
    partes = []
    for ln, g in d.groupby("linha", observed=True):
        # instituições que a UF publica nessa linha (para detectar pontos incompletos na soma)
        # (máximo de instituições num mesmo relatório: resiste a mudanças de nome entre anos)
        esperado = (g.groupby(["uf", "exercicio", "periodo"], observed=True)["instituicao"].nunique()
                    .groupby(level="uf", observed=True).max())
        if coluna == MENSAL:
            g = g[g["coluna"].astype(str).str.match(r"^<MR(?:-\d+)?>$")]
            s = []
            for inst, h in g.groupby(["uf", "co_poder", "instituicao"], observed=True):
                s.append(RE.serie_mensal(h, MESES).assign(instituicao=inst[2]))
            s = pd.concat(s, ignore_index=True) if s else pd.DataFrame(columns=["uf", "data", "valor", "instituicao"])
            s = s.groupby(["uf", "data"], observed=True, as_index=False).agg(valor=("valor", "sum"),
                                                                             n_inst=("instituicao", "nunique"))
            if modo == MODOS_MENSAL[1]:
                s = s[s["n_inst"] == s["uf"].map(esperado)]
                s = RE._soma_12m(s[["uf", "data", "valor"]]).assign(n_inst=lambda x: x["uf"].map(esperado))
        elif coluna == SALDOS:
            s = _saldos(g)
            if modo == MODOS_SALDO[1]:
                s = s[s["n_inst"] == s["uf"].map(esperado)]
                s = _interpolar(s).assign(n_inst=lambda x: x["uf"].map(esperado))
        else:
            h = g[g["coluna"] == coluna]
            s = h.groupby(["uf", "exercicio", "periodo"], observed=True, as_index=False).agg(
                valor=("valor", "sum"), n_inst=("instituicao", "nunique"))
            s["data"] = pd.to_datetime(dict(year=s["exercicio"].astype(int), month=s["periodo"].astype(int) * MESES,
                                            day=1))
            if modo in (MODOS_ACUMULADO[1], MODOS_ACUMULADO[2]):
                s = RE.desacumular(s)
            if modo in (MODOS_ACUMULADO[2], MODOS_FLUXO[1]):
                s = _media_mensal(s)
        if not s.empty:
            s["completo"] = s["n_inst"] >= s["uf"].map(esperado)
            partes.append(s.assign(linha=ln))
    cols = ["uf", "linha", "data", "ano", "mes", "valor", "rcl12", "pct_rcl", "completo"]
    if not partes:
        return pd.DataFrame(columns=cols)
    s = pd.concat(partes, ignore_index=True)
    s["uf"], s["linha"] = s["uf"].astype(str), s["linha"].astype(str)
    s["data"] = pd.to_datetime(s["data"])
    s = s[s["completo"]].merge(rcl_mes[["uf", "data", "rcl12"]], on=["uf", "data"], how="left")
    s["ano"], s["mes"] = s["data"].dt.year, s["data"].dt.month
    s["pct_rcl"] = 100 * s["valor"] / s["rcl12"].where(s["rcl12"] > 0)
    return s[cols].sort_values(["linha", "uf", "data"]).reset_index(drop=True)


# ------------------------------------------------------------------ cumprimento dos limites da LRF
TODOS = "Todos os Poderes"
# LRF (LC 101/2000), arts. 19 e 20: limites da despesa total com pessoal em % da RCL, por esfera e Poder.
LIMITES_LRF = {
    "União": {"Total": 50.0, "Legislativo (inclui o TCU)": 2.5, "Judiciário": 6.0, "Executivo": 40.9,
              "Ministério Público da União": 0.6},
    "Estados": {"Total": 60.0, "Legislativo (inclui o TCE)": 3.0, "Judiciário": 6.0, "Executivo": 49.0,
                "Ministério Público": 2.0},
    "Estados com Tribunal de Contas dos Municípios (§4º)": {"Total": 60.0, "Legislativo": 3.4, "Judiciário": 6.0,
                                                           "Executivo": 48.6, "Ministério Público": 2.0},
    "Municípios": {"Total": 60.0, "Legislativo (inclui o TCM, se houver)": 6.0, "Executivo": 54.0},
}
# UFs com Tribunal de Contas dos Municípios: Legislativo +0,4 p.p. e Executivo −0,4 p.p. (LRF, art. 20, §4º).
# O CE extinguiu o seu TCM em 2017 (EC estadual nº 92/2017) e voltou a 49% / 3%.
UFS_COM_TCM = {"BA", "GO", "PA"}


def limite_legal(uf: str, grupo: str) -> tuple[float | None, str]:
    """Limite máximo da despesa total com pessoal (% da RCL) que a LRF fixa para o Poder da UF, e a base legal.

    No DF, o Judiciário e o Ministério Público são organizados e mantidos pela União (CF, art. 21, XIII): não há RGF
    distrital desses Poderes, e o total distrital soma só Executivo (49%) e Legislativo (3%)."""
    tcm = uf in UFS_COM_TCM
    if grupo == "Executivo":
        return (48.6, "LRF, art. 20, II, c, c/c §4º (UF com TCM)") if tcm else (49.0, "LRF, art. 20, II, c")
    if grupo == "Legislativo":
        return ((3.4, "LRF, art. 20, II, a, c/c §4º (inclui TCE e TCM)") if tcm else
                (3.0, "LRF, art. 20, II, a (inclui o TCE)"))
    if grupo == "Judiciário":
        return (None, "mantido pela União (CF, art. 21, XIII)") if uf == "DF" else (6.0, "LRF, art. 20, II, b")
    if grupo == "Ministério Público":
        return (None, "mantido pela União (CF, art. 21, XIII)") if uf == "DF" else (2.0, "LRF, art. 20, II, d")
    if grupo == TODOS:
        return ((52.0, "Executivo 49% + Legislativo 3% (Judiciário e MP do DF são da União)") if uf == "DF" else
                (60.0, "LRF, art. 19, II"))
    return None, "sem limite próprio na LRF"
# indicadores de endividamento (só no Executivo): código da linha do % e limites (% da RCL ajustada)
#   DCL: Res. Senado 40/2001, art. 3º, I (2 × RCL); garantias: Res. Senado 43/2001, art. 9º (22%);
#   operações de crédito: Res. Senado 43/2001, art. 7º, I (16% no exercício); alerta: LRF, art. 59, §1º, III (90%).
ENDIVIDAMENTO = {
    "Dívida consolidada líquida": ("RGF-Anexo 02", "PercentualDaDCLSobreARCL", 200.0),
    "Garantias concedidas": ("RGF-Anexo 03", "PercentualDoTotalDasGarantiasSobreARCL", 22.0),
    "Operações de crédito": ("RGF-Anexo 04", "TotalConsideradoParaFinsDaApuracaoDoCumprimentoDoLimiteOperacoesDeCredito",
                             16.0),
}
_PESSOAL = {"DespesaComPessoalTotal": "valor", "LimiteMaximoDespesaComPessoalTotal": "maximo",
            "LimitePrudencialDespesaComPessoalTotal": "prudencial", "LimiteDeAlertaDespesaComPessoalTotal": "alerta",
            "ReceitaCorrenteLiquidaAjustada": "rcl_aj"}


def indicadores_lrf(df: pd.DataFrame) -> pd.DataFrame:
    """Indicadores da LRF em % da RCL ajustada, um ponto por UF, grupo e fim de quadrimestre.

    Limites de pessoal: os LEGAIS (arts. 19 e 20 da LRF, conforme a UF — ver `limite_legal`); o limite publicado pela
    UF no RGF fica em `maximo_publicado`, e `divergencia` marca quando difere do legal em mais de 0,05 p.p.

    Colunas: uf, indicador, grupo (Poder, 'Todos os Poderes' ou 'Executivo'), data, valor, alerta, prudencial, maximo,
    valor_rs (R$), n_inst. Pessoal: DTP e limites publicados por instituição (coluna 'Valor' do Anexo 1), somados por
    Poder e no total e divididos pela RCL ajustada da UF. Endividamento: % publicado e limites das resoluções do Senado.
    """
    if df.empty:
        return pd.DataFrame()
    saida = []
    # ---- pessoal
    a1 = df[(df["anexo"] == "RGF-Anexo 01") & df["cod_conta"].isin(_PESSOAL) & (df["coluna"] == "Valor")]
    if not a1.empty:
        w = (a1.assign(campo=a1["cod_conta"].astype(str).map(_PESSOAL))
             .pivot_table(index=["uf", "exercicio", "periodo", "co_poder", "instituicao"], columns="campo",
                          values="valor", aggfunc="sum", observed=True).reset_index())
        w = w.dropna(subset=["valor", "maximo"])
        w["uf"], w["co_poder"] = w["uf"].astype(str), w["co_poder"].astype(str)
        rcl = w.groupby(["uf", "exercicio", "periodo"])["rcl_aj"].max().rename("rcl")
        for grupo, sub in [(PODERES[p], w[w["co_poder"] == p]) for p in PODERES] + [(TODOS, w)]:
            g = sub.groupby(["uf", "exercicio", "periodo"]).agg(
                valor_rs=("valor", "sum"), maximo=("maximo", "sum"), prudencial=("prudencial", "sum"),
                alerta=("alerta", "sum"), n_inst=("instituicao", "nunique"), poderes=("co_poder", "nunique"))
            g = g.join(rcl)
            # só soma quando todas as instituições (e, no total, todos os Poderes) que a UF costuma publicar estão lá
            g = g[(g["n_inst"] == g.groupby("uf")["n_inst"].transform("max"))
                  & (g["poderes"] == g.groupby("uf")["poderes"].transform("max"))]
            g["maximo_publicado"] = 100 * g["maximo"] / g["rcl"]
            g["valor"] = 100 * g["valor_rs"] / g["rcl"]
            g = g.reset_index()
            leg = g["uf"].map(lambda u: limite_legal(u, grupo))
            g["maximo"] = leg.map(lambda t: t[0]).astype(float)
            g["base_legal"] = leg.map(lambda t: t[1])
            g["prudencial"], g["alerta"] = 0.95 * g["maximo"], 0.90 * g["maximo"]
            saida.append(g.assign(indicador="Despesa total com pessoal", grupo=grupo))
        # Defensoria: sem limite próprio no art. 20 da LRF; o RGF na API traz só a despesa bruta e a líquida.
        # DTP = despesa líquida dos 12 meses (a) + restos a pagar não processados (b), ÷ RCL ajustada da UF.
        dp = df[(df["anexo"] == "RGF-Anexo 01") & (df["co_poder"] == "D") & (df["cod_conta"] == "DespesaComPessoalLiquida")]
        dp = dp[dp["coluna"].astype(str).str.match(r"^(TOTAL \(ÚLTIMOS 12 MESES\) \(a\)|INSCRITAS EM RESTOS A PAGAR)")]
        if not dp.empty:
            g = dp.groupby(["uf", "exercicio", "periodo"], observed=True).agg(
                valor_rs=("valor", "sum"), n_inst=("instituicao", "nunique"))
            g.index = g.index.set_levels(g.index.levels[0].astype(str), level=0)
            g = g.join(rcl, how="inner")
            g["valor"] = 100 * g["valor_rs"] / g["rcl"]
            for c in ("maximo", "prudencial", "alerta", "maximo_publicado"):
                g[c] = float("nan")
            saida.append(g.reset_index().assign(indicador="Despesa total com pessoal", grupo=PODERES["D"],
                                                base_legal="sem limite próprio na LRF (art. 20 não a inclui)"))
    # ---- endividamento (Executivo)
    for nome, (anexo, cod, lim) in ENDIVIDAMENTO.items():
        e = df[(df["anexo"] == anexo) & (df["cod_conta"] == cod) & (df["co_poder"] == "E")]
        if e.empty:
            continue
        if anexo == "RGF-Anexo 04":
            e = e[e["coluna"].astype(str).str.contains("%")]
            g = e.groupby(["uf", "exercicio", "periodo"], observed=True, as_index=False)["valor"].sum()
        else:  # saldos no fim de cada quadrimestre, o relatório mais recente prevalece
            g = _saldos(e).rename(columns={"data": "data_saldo"})
            g["exercicio"], g["periodo"] = g["data_saldo"].dt.year, g["data_saldo"].dt.month // MESES
        g["uf"] = g["uf"].astype(str)
        base = {"Dívida consolidada líquida": "Res. Senado 40/2001, art. 3º, I (2 × RCL)",
                "Garantias concedidas": "Res. Senado 43/2001, art. 9º",
                "Operações de crédito": "Res. Senado 43/2001, art. 7º, I"}[nome]
        saida.append(g.assign(indicador=nome, grupo="Executivo", maximo=lim, alerta=0.9 * lim, prudencial=float("nan"),
                              n_inst=1, maximo_publicado=float("nan"), base_legal=base))
    t = pd.concat(saida, ignore_index=True)
    t["data"] = pd.to_datetime(dict(year=t["exercicio"].astype(int), month=t["periodo"].astype(int) * MESES, day=1))
    t = t[t["periodo"].between(1, 3)]
    t["divergencia"] = (t["maximo_publicado"] - t["maximo"]).abs() > 0.05  # limite publicado ≠ limite legal
    return t[["uf", "indicador", "grupo", "data", "valor", "alerta", "prudencial", "maximo", "maximo_publicado",
              "base_legal", "divergencia", "valor_rs", "n_inst"]]


def situacao(valor: float, alerta: float, prudencial: float, maximo: float) -> str:
    if pd.isna(valor):
        return "sem dado"
    if pd.isna(maximo):
        return "sem limite próprio"
    if valor > maximo:
        return "acima do limite máximo"
    if not pd.isna(prudencial) and valor > prudencial:
        return "acima do limite prudencial"
    if valor > alerta:
        return "acima do limite de alerta"
    return "dentro dos limites"
