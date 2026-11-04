"""RREO de todos os Estados e do Distrito Federal (API de dados abertos do Siconfi).

Endpoints (https://apidatalake.tesouro.gov.br/docs/siconfi/):
- /entes: lista de entes (esfera E = Estado, D = Distrito Federal), com código IBGE, região e população;
- /rreo: um ente por chamada (id_ente é obrigatório), parâmetros an_exercicio, nr_periodo (bimestre),
  co_tipo_demonstrativo=RREO e co_esfera.

Gravação (compatível com Git/GitHub e com o Streamlit Community Cloud):
- dados/dashboard/rreo_estados/rreo_uf_AAAA_B.parquet: um arquivo por bimestre com todas as UFs (~1–2 MB, zstd,
  colunas de texto como dicionário). Atualizar um bimestre reescreve só o seu arquivo.
- dados/dashboard/rreo_estados/entes.parquet: código IBGE, UF, nome, região e população.

Séries mensais: <MR> é o mês de referência do relatório (último mês do bimestre, 2·b) e <MR-k> o k-ésimo mês
anterior. Só o Anexo 3 (RCL) traz essas colunas; nos demais anexos, o valor é posicionado no mês de referência.
"""
from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import requests

from .config import SICONFI_API, USER_AGENT, caminho

log = logging.getLogger(__name__)

DIR = caminho("rreo_estados")
COLUNAS = ["exercicio", "periodo", "cod_ibge", "uf", "anexo", "rotulo", "coluna", "cod_conta", "conta", "valor"]
CATEGORICAS = ["uf", "anexo", "rotulo", "coluna", "cod_conta", "conta"]
ANOS_PADRAO = 4  # últimos 4 exercícios, incluindo o corrente
UF_REFERENCIA = "MS"  # define a ordem das linhas nos filtros (a do relatório desta UF)

_local = requests.Session()
_local.headers["User-Agent"] = USER_AGENT


def _get(endpoint: str, params: dict, tentativas: int = 8) -> list[dict]:
    itens, offset = [], 0
    while True:
        for t in range(tentativas):
            try:
                r = _local.get(f"{SICONFI_API}/{endpoint}", params={**params, "offset": offset}, timeout=180)
                if r.status_code == 429:
                    raise requests.HTTPError("429 Too Many Requests")
                r.raise_for_status()
                js = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                if t == tentativas - 1:
                    raise
                espera = min(60, 10 * (t + 1))  # a API devolve 429 quando há muitas consultas seguidas
                log.warning("Siconfi %s %s falhou (%s); nova tentativa em %ss", endpoint, params, e, espera)
                time.sleep(espera)
        itens.extend(js.get("items", []))
        if not js.get("hasMore"):
            return itens
        offset += js.get("limit") or len(js.get("items", [])) or 5000


def entes() -> pd.DataFrame:
    """Estados e DF (código IBGE de 2 dígitos)."""
    df = pd.DataFrame(_get("entes", {}))
    df = df[df["esfera"].isin(["E", "D"])].copy()
    siglas = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO", 21: "MA", 22: "PI", 23: "CE",
              24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP",
              41: "PR", 42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}
    df["cod_ibge"] = df["cod_ibge"].astype(int)
    df["uf"] = df["cod_ibge"].map(siglas)
    df = df[["cod_ibge", "uf", "ente", "regiao", "populacao", "esfera"]].sort_values("uf").reset_index(drop=True)
    DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DIR / "entes.parquet", index=False)
    return df


def _rreo_ente(ano: int, bim: int, cod: int) -> pd.DataFrame:
    # o /entes classifica o DF como esfera "D", mas o /rreo o publica com co_esfera=E
    it = _get("rreo", {"an_exercicio": ano, "nr_periodo": bim, "co_tipo_demonstrativo": "RREO",
                       "co_esfera": "E", "id_ente": cod})
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
    return df.sort_values(["uf", "anexo", "exercicio", "periodo"], kind="stable").reset_index(drop=True)


def arquivo(ano: int, bim: int):
    return DIR / f"rreo_uf_{ano}_{bim}.parquet"


def periodos(anos: int = ANOS_PADRAO, hoje: date | None = None) -> list[tuple[int, int]]:
    """Bimestres já encerrados dos últimos `anos` exercícios (o prazo de publicação é de 30 dias)."""
    hoje = hoje or date.today()
    out = []
    for a in range(hoje.year - anos + 1, hoje.year + 1):
        for b in range(1, 7):
            if (a, 2 * b) < (hoje.year, hoje.month):  # bimestre encerrado
                out.append((a, b))
    return out


def atualizar(anos: int = ANOS_PADRAO, forcar_ultimos: int = 2, paralelo: int = 3) -> None:
    """Baixa os bimestres que faltam no disco e rebaixa os `forcar_ultimos` mais recentes (entregas atrasadas e
    retificações). Um bimestre já gravado também é refeito se faltar alguma UF."""
    tab = entes()
    alvo = periodos(anos)
    recentes = set(alvo[-forcar_ultimos:]) if forcar_ultimos else set()
    todas = set(tab["uf"])
    for ano, bim in alvo:
        arq = arquivo(ano, bim)
        if arq.exists() and (ano, bim) not in recentes:
            ufs = set(pd.read_parquet(arq, columns=["uf"])["uf"].astype(str))
            if ufs >= todas:
                continue
        log.info("RREO das UFs: %s, %sº bimestre …", ano, bim)
        partes = []
        with ThreadPoolExecutor(paralelo) as ex:
            fut = {ex.submit(_rreo_ente, ano, bim, int(r.cod_ibge)): r.uf for r in tab.itertuples()}
            for f in as_completed(fut):
                d = f.result()
                if not d.empty:
                    partes.append(d)
        if not partes:
            log.info("  nenhum Estado entregou ainda")
            continue
        df = _compactar(pd.concat(partes, ignore_index=True))
        log.info("  %d UFs, %d linhas", df["uf"].nunique(), len(df))
        df.to_parquet(arq, index=False, compression="zstd")


# ------------------------------------------------------------------ leitura e séries
def carregar() -> pd.DataFrame:
    """Lê todos os bimestres. As categorias são unificadas antes do concat (senão o pandas volta a 'object' e a
    memória passa de ~60 MB para ~500 MB)."""
    arqs = sorted(DIR.glob("rreo_uf_*.parquet"))
    if not arqs:
        return pd.DataFrame(columns=COLUNAS)
    partes = [pd.read_parquet(a) for a in arqs]
    for c in CATEGORICAS:
        cats = pd.api.types.union_categoricals([p[c].astype("category") for p in partes]).categories
        for p in partes:
            p[c] = p[c].astype(pd.CategoricalDtype(cats))
    return pd.concat(partes, ignore_index=True)


def _norm(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().upper()
    t = re.sub(r"\(\s*-\s*\)", "(-)", t)                     # "( - )" = "(-)"
    t = re.sub(r"\s*=\s*\(.*$", "", t)                          # fórmula "= (I - II)"
    t = re.sub(r"\s*\((?:[IVXL]+(?:\.\d+)?)\)\s*$", "", t)        # numeração romana final, que muda entre anos
    return re.sub(r"\s+", " ", t).strip()


def _codigos(df: pd.DataFrame, cols: list[str]):
    """Combinações distintas de colunas (códigos das categóricas ou inteiros) e o índice de cada linha nelas,
    sem groupby: (únicas [n × len(cols)], inverso [len(df)])."""
    import numpy as np

    partes, bases = [], []
    for c in cols:
        v = df[c].cat.codes.to_numpy(np.int64) if isinstance(df[c].dtype, pd.CategoricalDtype) else df[c].to_numpy(np.int64)
        lo = int(v.min())
        partes.append(v - lo)
        bases.append((lo, int(v.max()) - lo + 1))
    chave = np.zeros(len(df), dtype=np.int64)
    for v, (_, n) in zip(partes, bases):  # chave mista: cabe em int64 (no máximo ~10^12 combinações aqui)
        chave = chave * n + v
    del partes
    inverso, unicas = pd.factorize(chave)  # por hash: menos memória que np.unique (que ordena e copia)
    del chave
    cols_u = []
    for lo, n in reversed(bases):
        unicas, r = np.divmod(unicas, n)
        cols_u.append(r + lo)
    return np.column_stack(cols_u[::-1]), inverso


def preparar(df: pd.DataFrame, extras: tuple[str, ...] = ()) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Base enxuta para os gráficos e catálogo de linhas.

    - `linha`: chave da linha do demonstrativo = rotulo | cod_conta | conta normalizada (caixa, acentos, espaços e
      numeração romana final). É única em cada relatório (no Anexo 2 o cod_conta é o mesmo para todas as funções; no
      Anexo 7, cada cod_conta é um grupo de colunas e a conta, o Poder/órgão).
    - `coluna`: anos do exercício trocados por <EC>, <EC-1>… ('PREVISÃO ATUALIZADA 2025' → 'PREVISÃO ATUALIZADA
      <EC>'), para a mesma coluna ter um só nome em todos os anos.

    Trabalha com códigos de grupo (sem merge sobre 2 milhões de linhas), para caber na memória do Streamlit Cloud.
    """
    import numpy as np

    if df.empty:
        return df, pd.DataFrame(columns=["anexo", "linha", "rotulo", "cod_conta", "conta", "ordem", "n_ufs"])
    # linha: um rótulo por combinação distinta de (rotulo, cod_conta, conta)
    uniq, gid = _codigos(df, ["rotulo", "cod_conta", "conta"])
    trio = {c: df[c].cat.categories[uniq[:, i]] for i, c in enumerate(["rotulo", "cod_conta", "conta"])}
    rot_trio = np.array([f"{r} | {c} | {_norm(t)}" for r, c, t in zip(trio["rotulo"], trio["cod_conta"],
                                                                       trio["conta"])], dtype=object)
    cats_linha = pd.Index(pd.unique(rot_trio))
    linha = pd.Categorical.from_codes(cats_linha.get_indexer(rot_trio)[gid], categories=cats_linha)

    # coluna sem o ano do exercício
    def _sem_ano(c: str, a: int) -> str:
        for k in range(0, 4):
            c = re.sub(rf"(?<!\d){a - k}(?!\d)", "<EC>" if k == 0 else f"<EC-{k}>", c)
        return c
    uniq, gid = _codigos(df, ["coluna", "exercicio"])
    rot_par = np.array([_sem_ano(str(df["coluna"].cat.categories[c]), int(a)) for c, a in uniq], dtype=object)
    cats_col = pd.Index(pd.unique(rot_par))
    coluna = pd.Categorical.from_codes(cats_col.get_indexer(rot_par)[gid], categories=cats_col)

    base = pd.DataFrame({"exercicio": df["exercicio"].to_numpy(), "periodo": df["periodo"].to_numpy(),
                         "uf": df["uf"], "anexo": df["anexo"], "linha": linha, "coluna": coluna,
                         "valor": df["valor"].to_numpy(), **{c: df[c] for c in extras}})
    base["uf"] = base["uf"].cat.remove_unused_categories()
    base["anexo"] = base["anexo"].cat.remove_unused_categories()

    # catálogo, a partir de uma linha por (relatório, linha): posição no relatório, rótulo mais frequente, nº de UFs
    # 1ª ocorrência de cada (relatório, linha), na ordem original, via chaves inteiras (drop_duplicates sobre
    # categóricas de 2 milhões de linhas custaria ~250 MB de pico)
    _, rep = _codigos(df, ["uf", "exercicio", "periodo", "anexo", *extras])
    chave = rep * (len(cats_linha) + 1) + linha.codes.astype(np.int64)
    _, primeiro = np.unique(chave, return_index=True)
    primeiro.sort()
    sub = df.iloc[primeiro]
    rel = pd.DataFrame({"uf": sub["uf"].to_numpy(), "exercicio": sub["exercicio"].to_numpy(),
                        "periodo": sub["periodo"].to_numpy(), "anexo": sub["anexo"].to_numpy(),
                        "linha": linha[primeiro], "rotulo": sub["rotulo"].to_numpy(),
                        "cod_conta": sub["cod_conta"].to_numpy(), "conta": sub["conta"].to_numpy()})
    rel["pos"] = pd.Series(rep[primeiro]).groupby(rep[primeiro]).cumcount().to_numpy()  # posição da linha
    conta = (rel.groupby(["anexo", "linha", "conta"], observed=True).size().reset_index(name="n")
             .sort_values("n", ascending=False).drop_duplicates(["anexo", "linha"])[["anexo", "linha", "conta"]])
    cat = (rel.groupby(["anexo", "linha"], observed=True, sort=False)
           .agg(rotulo=("rotulo", "first"), cod_conta=("cod_conta", "first"), ordem=("pos", "median"),
                n_ufs=("uf", "nunique"))
           .reset_index().merge(conta, on=["anexo", "linha"], how="left"))
    for c in ["anexo", "linha", "rotulo", "cod_conta", "conta"]:
        cat[c] = cat[c].astype(str)
    cat["conta"] = cat["conta"].str.strip()
    # ordem do relatório: a do último RREO da UF de referência (MS); as linhas que ela não publica vêm depois,
    # pela posição mediana nas demais UFs (a mediana sozinha embaralha anexos de leiaute variável, como o 2)
    ref = rel[rel["uf"].astype(str) == UF_REFERENCIA]
    cat["ordem_ref"] = float("nan")
    if not ref.empty:
        chave = ref["exercicio"].astype(int) * 10 + ref["periodo"].astype(int)
        ref = ref[chave == chave.groupby(ref["anexo"], observed=True).transform("max")]
        pos_ref = {(str(a), str(ln)): v for a, ln, v in zip(ref["anexo"], ref["linha"], ref["pos"])}
        cat["ordem_ref"] = [pos_ref.get((a, ln), float("nan")) for a, ln in zip(cat["anexo"], cat["linha"])]
    cat["sem_ref"] = cat["ordem_ref"].isna()
    cat["ordem"] = cat["ordem_ref"].fillna(cat["ordem"])
    cat = cat.sort_values(["anexo", "sem_ref", "ordem"]).drop(columns=["ordem_ref", "sem_ref"])
    return base, cat.reset_index(drop=True)


def carregar_entes() -> pd.DataFrame:
    arq = DIR / "entes.parquet"
    return pd.read_parquet(arq) if arq.exists() else pd.DataFrame(columns=["cod_ibge", "uf", "ente", "regiao", "populacao"])


_MR = re.compile(r"^<MR(?:-(\d+))?>$")


def defasagem(coluna: pd.Series) -> pd.Series:
    """<MR> → 0, <MR-1> → 1 … ; outras colunas → NaN.

    A expressão regular roda uma vez por nome de coluna distinto (são poucos), não linha a linha."""
    u = coluna.unique()
    k = pd.Series(pd.Series(u).astype(str).str.extract(r"^<MR(?:-(\d+))?>$")[0].to_numpy(), index=u)
    eh = pd.Series(pd.Series(u).astype(str).str.match(r"^<MR(?:-\d+)?>$").to_numpy(), index=u)
    k = k.fillna("0").astype(float).where(eh)
    return pd.Series(k.reindex(coluna.to_numpy()).to_numpy(), index=coluna.index, name=coluna.name)


def serie_mensal(d: pd.DataFrame, meses: int = 2, por: tuple[str, ...] = (),
                 manter: tuple[str, ...] = ()) -> pd.DataFrame:
    """Série mensal a partir das colunas <MR-k> de um recorte (uma linha do anexo, várias UFs).

    Mês = mês de referência do relatório (meses × período: 2·b no RREO, 4·q no RGF) − k. Quando o mesmo mês aparece
    em vários relatórios, prevalece o mais recente (que incorpora retificações). `por` (ex.: Poder e instituição no
    RGF) escolhe o relatório mais recente em cada grupo antes de somar os grupos. `manter` faz o mesmo, mas não soma
    os grupos: eles vão para a saída como colunas (equivale a rodar a função uma vez por grupo, em uma só passada)."""
    manter = list(manter)
    d = d.assign(k=defasagem(d["coluna"])).dropna(subset=["k"])
    if d.empty:
        return pd.DataFrame(columns=["uf", *manter, "data", "valor"])
    ex, per = d["exercicio"].astype(int), d["periodo"].astype(int)
    # meses contados desde o ano 0: mês de referência menos a defasagem k (vetorizado, sem DateOffset linha a linha)
    n = ex * 12 + per * meses - 1 - d["k"].astype(int)
    d = d.assign(data=pd.to_datetime(dict(year=n // 12, month=n % 12 + 1, day=1)), ordem=ex * 10 + per)
    chaves = ["uf", *manter, *por]
    d = d.groupby([*chaves, "data", "ordem"], observed=True, as_index=False)["valor"].sum()
    d = d.sort_values("ordem").drop_duplicates([*chaves, "data"], keep="last")
    d = d.groupby(["uf", *manter, "data"], observed=True, as_index=False)["valor"].sum()
    return d.sort_values(["uf", *manter, "data"]).reset_index(drop=True)


def serie_referencia(d: pd.DataFrame, meses: int = 2) -> pd.DataFrame:
    """Série de uma coluna não mensal: um ponto por relatório, no mês de referência (MR = 2·b no RREO, 4·q no RGF)."""
    if d.empty:
        return pd.DataFrame(columns=["uf", "data", "valor", "exercicio", "periodo"])
    d = d.groupby(["uf", "exercicio", "periodo"], observed=True, as_index=False)["valor"].sum()
    d["data"] = pd.to_datetime(dict(year=d["exercicio"].astype(int), month=d["periodo"].astype(int) * meses, day=1))
    return d.sort_values(["uf", "data"]).reset_index(drop=True)


def desacumular(s: pd.DataFrame) -> pd.DataFrame:
    """Coluna acumulada no exercício ('Até o Bimestre') → valor de cada bimestre (diferença entre relatórios
    consecutivos do mesmo ano; no 1º bimestre, o próprio acumulado; vazio se faltar o bimestre anterior)."""
    s = s.sort_values(["uf", "exercicio", "periodo"]).copy()
    g = s.groupby(["uf", "exercicio"], observed=True)
    ant, contiguo = g["valor"].shift(), g["periodo"].shift() == s["periodo"] - 1
    s["valor"] = s["valor"].where(s["periodo"] == 1, (s["valor"] - ant).where(contiguo))
    return s.dropna(subset=["valor"])


COD_RCL = "RREO3ReceitaCorrenteLiquida"
COL_RCL_12M = re.compile(r"TOTAL\s*\(\s*[ÚU]LTIMOS\s*12\s*MESES\s*\)", re.I)


def rcl(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """RCL do Anexo 3: (mensal, 12 meses por relatório).

    mensal: uf, data, valor (colunas <MR-k>) e rcl12 = soma móvel de 12 meses;
    por relatório: uf, exercicio, periodo, rcl12 (coluna 'TOTAL (ÚLTIMOS 12 MESES)')."""
    a3 = df[(df["anexo"] == "RREO-Anexo 03") & (df["cod_conta"] == COD_RCL)]
    m = serie_mensal(a3)
    if not m.empty:
        m = m.sort_values(["uf", "data"])
        m["rcl12"] = m.groupby("uf", observed=True)["valor"].transform(lambda v: v.rolling(12, min_periods=12).sum())
    tot = a3[a3["coluna"].astype(str).str.contains(COL_RCL_12M)]
    tot = tot.groupby(["uf", "exercicio", "periodo"], observed=True, as_index=False)["valor"].sum()
    return m, tot.rename(columns={"valor": "rcl12"})


# ------------------------------------------------------------------ séries para os gráficos
MENSAL = "Mensal: colunas <MR-11> … <MR> (Anexo 3)"
MODOS_MENSAL = ["Valor do mês", "Soma em 12 meses"]
MODOS_ACUMULADO = ["Acumulado no ano (como publicado)", "Valor do bimestre (desacumulado)"]


def acumula(coluna: str) -> bool:
    """Colunas que acumulam de janeiro ao fim do bimestre ('Até o Bimestre'), exceto percentuais e saldos datados."""
    return (bool(re.search(r"at[ée] o bimestre(?!\s*(<EC|\d))", coluna, re.I)) and "%" not in coluna
            and not re.search(r"saldo", coluna, re.I))  # saldos ('SALDO FINAL ATÉ O BIMESTRE') são estoques


def percentual(coluna: str) -> bool:
    return "%" in coluna


def _soma_12m(m: pd.DataFrame) -> pd.DataFrame:
    """Soma móvel de 12 meses por UF, só com 12 meses consecutivos."""
    out = []
    for uf, g in m.groupby("uf", observed=True):
        g = g.set_index("data").asfreq("MS")
        g["valor"] = g["valor"].rolling(12, min_periods=12).sum()
        g["uf"] = uf
        out.append(g.reset_index())
    return pd.concat(out, ignore_index=True).dropna(subset=["valor"]) if out else m


def serie(base: pd.DataFrame, rcl_mes: pd.DataFrame, rcl_rel: pd.DataFrame, anexo: str, linhas: list[str],
          coluna: str, modo: str | None = None) -> pd.DataFrame:
    """Série de uma ou mais linhas de um anexo, para todas as UFs.

    Devolve uf, linha, data (mês), ano, mes, valor, rcl12 e pct_rcl (= 100 × valor ÷ RCL de 12 meses).
    - coluna MENSAL: meses das colunas <MR-k>; o denominador é a RCL dos 12 meses que terminam no mês.
    - demais colunas: um ponto por relatório, no mês de referência <MR> (2·b); o denominador é a coluna
      'TOTAL (ÚLTIMOS 12 MESES)' da RCL do mesmo relatório.
    """
    d = base[(base["anexo"] == anexo) & base["linha"].isin(linhas)]
    partes = []
    if coluna == MENSAL:
        d = d[d["coluna"].astype(str).str.match(r"^<MR(?:-\d+)?>$")]
        for ln, g in d.groupby("linha", observed=True):
            m = serie_mensal(g)
            if modo == MODOS_MENSAL[1]:
                m = _soma_12m(m)
            partes.append(m.assign(linha=ln))
        s = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=["uf", "data", "valor", "linha"])
        s = s.merge(rcl_mes[["uf", "data", "rcl12"]], on=["uf", "data"], how="left") if not s.empty else s.assign(rcl12=None)
    else:
        d = d[d["coluna"] == coluna]
        for ln, g in d.groupby("linha", observed=True):
            r = serie_referencia(g)
            if modo == MODOS_ACUMULADO[1]:
                r = desacumular(r)
            partes.append(r.assign(linha=ln))
        s = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(
            columns=["uf", "exercicio", "periodo", "data", "valor", "linha"])
        s = s.merge(rcl_rel, on=["uf", "exercicio", "periodo"], how="left") if not s.empty else s.assign(rcl12=None)
    if s.empty:
        return pd.DataFrame(columns=["uf", "linha", "data", "ano", "mes", "valor", "rcl12", "pct_rcl"])
    s["uf"] = s["uf"].astype(str)
    s["linha"] = s["linha"].astype(str)
    s["data"] = pd.to_datetime(s["data"])
    s["ano"], s["mes"] = s["data"].dt.year, s["data"].dt.month
    s["rcl12"] = pd.to_numeric(s["rcl12"], errors="coerce")
    s["pct_rcl"] = 100 * s["valor"] / s["rcl12"].where(s["rcl12"] > 0)
    return s[["uf", "linha", "data", "ano", "mes", "valor", "rcl12", "pct_rcl"]].sort_values(["linha", "uf", "data"])
