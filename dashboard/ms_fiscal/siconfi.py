"""Coleta na API de dados abertos do Siconfi (Tesouro Nacional).

Endpoints usados (https://apidatalake.tesouro.gov.br/docs/siconfi/):
- /extrato_entregas: quais matrizes e relatórios o ente já entregou;
- /msc_orcamentaria: Matriz de Saldos Contábeis, classe 6 (execução do orçamento) – MENSAL;
- /rreo: Relatório Resumido da Execução Orçamentária – BIMESTRAL (LRF, arts. 52-53);
- /rgf: Relatório de Gestão Fiscal – QUADRIMESTRAL (LRF, arts. 54-55).
"""
from __future__ import annotations

import logging
import time
from typing import Iterable

import pandas as pd
import requests

from .config import ID_ENTE, SICONFI_API, USER_AGENT, caminho

log = logging.getLogger(__name__)
_sessao = requests.Session()
_sessao.headers["User-Agent"] = USER_AGENT


def _get_paginado(endpoint: str, params: dict, tentativas: int = 4) -> list[dict]:
    """Percorre a paginação ORDS (offset/limit/hasMore) e devolve todos os itens."""
    itens: list[dict] = []
    offset = 0
    while True:
        for t in range(tentativas):
            try:
                r = _sessao.get(f"{SICONFI_API}/{endpoint}", params={**params, "offset": offset}, timeout=180)
                r.raise_for_status()
                js = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                if t == tentativas - 1:
                    raise
                espera = 5 * (t + 1)
                log.warning("Siconfi %s falhou (%s); nova tentativa em %ss", endpoint, e, espera)
                time.sleep(espera)
        itens.extend(js.get("items", []))
        if not js.get("hasMore"):
            return itens
        offset += js.get("limit", len(js.get("items", [])) or 5000)


# --------------------------------------------------------------------------- extrato
def extrato_entregas(anos: Iterable[int]) -> pd.DataFrame:
    frames = []
    for ano in anos:
        it = _get_paginado("extrato_entregas", {"id_ente": ID_ENTE, "an_referencia": ano})
        if it:
            frames.append(pd.DataFrame(it))
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not df.empty:
        df["data_status"] = pd.to_datetime(df["data_status"], errors="coerce")
        df.to_parquet(caminho("siconfi_extrato.parquet"), index=False)
    return df


def periodos_entregues(extrato: pd.DataFrame, entregavel: str, instituicao: str = "Governo do Estado") -> list[tuple[int, int]]:
    if extrato.empty:
        return []
    m = extrato["entregavel"].str.contains(entregavel, case=False) & extrato["instituicao"].str.contains(instituicao, case=False)
    return sorted({(int(a), int(p)) for a, p in extrato.loc[m, ["exercicio", "periodo"]].itertuples(index=False)})


# --------------------------------------------------------------------------- MSC
_COLS_MSC = ["conta_contabil", "poder_orgao", "fonte_recursos", "ano_fonte_recursos", "funcao", "subfuncao",
             "natureza_despesa", "natureza_receita", "ano_inscricao", "educacao_saude", "complemento_fonte"]


def msc_mes(ano: int, mes: int, classe: int = 6) -> pd.DataFrame:
    """MSC agregada (MSCC) do mês, valores de movimento do período (period_change).

    O sinal é normalizado para a natureza credora das contas da classe 6:
    valor positivo = crédito líquido (receita realizada, despesa empenhada/liquidada/paga).
    """
    it = _get_paginado("msc_orcamentaria", {
        "id_ente": ID_ENTE, "an_referencia": ano, "me_referencia": mes,
        "co_tipo_matriz": "MSCC", "classe_conta": classe, "id_tv": "period_change",
    })
    if not it:
        return pd.DataFrame()
    df = pd.DataFrame(it)
    df["valor"] = df["valor"].astype(float) * df["natureza_conta"].map({"C": 1.0, "D": -1.0}).fillna(0)
    for c in _COLS_MSC:
        if c not in df:
            df[c] = None
        df[c] = df[c].astype("string")
    df = df.groupby(_COLS_MSC, dropna=False, as_index=False)["valor"].sum()
    df = df[df["valor"].abs() > 0.004]
    df.insert(0, "mes", mes)
    df.insert(0, "ano", ano)
    return df


def atualizar_msc(anos: Iterable[int], extrato: pd.DataFrame | None = None, forcar_ultimos: int = 2) -> pd.DataFrame:
    """Baixa os meses entregues que ainda não estão no disco.

    Os `forcar_ultimos` meses mais recentes são sempre rebaixados, porque o ente
    pode reenviar a matriz (retificação).
    """
    extrato = extrato if extrato is not None else extrato_entregas(anos)
    entregues = [p for p in periodos_entregues(extrato, "MSC") if p[0] in set(anos)]
    recentes = set(entregues[-forcar_ultimos:]) if forcar_ultimos else set()
    for ano, mes in entregues:
        arq = caminho(f"msc6_{ano}_{mes:02d}.parquet")
        if arq.exists() and (ano, mes) not in recentes:
            continue
        log.info("MSC %s/%02d …", ano, mes)
        df = msc_mes(ano, mes)
        if not df.empty:
            df.to_parquet(arq, index=False)
    return carregar_msc()


def carregar_msc() -> pd.DataFrame:
    arqs = sorted(caminho("").glob("msc6_*.parquet"))
    if not arqs:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(a) for a in arqs], ignore_index=True)


# --------------------------------------------------------------------------- RREO / RGF
def rreo(ano: int, bimestre: int) -> pd.DataFrame:
    it = _get_paginado("rreo", {"an_exercicio": ano, "nr_periodo": bimestre, "co_tipo_demonstrativo": "RREO",
                                "co_esfera": "E", "id_ente": ID_ENTE})
    return pd.DataFrame(it)


def rgf(ano: int, quadrimestre: int, poder: str) -> pd.DataFrame:
    it = _get_paginado("rgf", {"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": quadrimestre,
                               "co_tipo_demonstrativo": "RGF", "co_esfera": "E", "co_poder": poder, "id_ente": ID_ENTE})
    return pd.DataFrame(it)


_PODERES_RGF = {"E": "Governo do Estado", "L": "Assembleia|Tribunal de Contas", "J": "Tribunal de Justiça",
                "M": "Ministério Público", "D": "Defensoria"}


def atualizar_relatorios(anos: Iterable[int], extrato: pd.DataFrame | None = None, forcar_ultimo: bool = True) -> None:
    anos = list(anos)
    extrato = extrato if extrato is not None else extrato_entregas(anos)
    bims = [p for p in periodos_entregues(extrato, "Resumido") if p[0] in anos]
    for i, (ano, b) in enumerate(bims):
        arq = caminho(f"rreo_{ano}_{b}.parquet")
        if arq.exists() and not (forcar_ultimo and i == len(bims) - 1):
            continue
        log.info("RREO %s – %sº bimestre", ano, b)
        df = rreo(ano, b)
        if not df.empty:
            df.to_parquet(arq, index=False)
    for poder, inst in _PODERES_RGF.items():
        quads = [p for p in periodos_entregues(extrato, "Gestão Fiscal", inst) if p[0] in anos]
        for i, (ano, q) in enumerate(quads):
            arq = caminho(f"rgf_{ano}_{q}_{poder}.parquet")
            if arq.exists() and not (forcar_ultimo and i == len(quads) - 1):
                continue
            log.info("RGF %s – %sº quadrimestre – poder %s", ano, q, poder)
            df = rgf(ano, q, poder)
            if not df.empty:
                df.to_parquet(arq, index=False)


def carregar_relatorio(tipo: str) -> pd.DataFrame:
    arqs = sorted(caminho("").glob(f"{tipo}_*.parquet"))
    if not arqs:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(a) for a in arqs], ignore_index=True)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    return df
