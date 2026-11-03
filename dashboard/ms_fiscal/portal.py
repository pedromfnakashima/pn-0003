"""Coleta "em tempo real" no Portal da Transparência de MS com Playwright.

O portal (www.transparencia.ms.gov.br, mantido pela CGE-MS) é uma aplicação
AngularJS: cada tela consulta APIs em https://gw.sgi.ms.gov.br com um token
emitido para o próprio navegador do visitante. Por isso a coleta abre o portal
num Chromium sem interface (Playwright), deixa a página obter o token como faria
um visitante comum e faz as mesmas consultas que os botões "Consultar" fazem,
dentro dessa sessão. Não há contorno de autenticação: são os dados públicos
exibidos nas telas, que o portal declara atualizar diariamente (LRF, arts. 48 e 48-A).

Telas e consultas usadas:
- Despesas › por órgão (despesapordataorgaos) e por credor (despesapordatacredores),
  com intervalo de datas → série diária e mensal até o dia de hoje;
- Receitas › Receita Simplificada (receitasimplificadas, por mês) e Receita
  Consolidada (receitaconsolidadas, árvore da natureza da receita no ano);
- Receitas › Pesquisa de Receita (pesquisadereceitas, por órgão e intervalo de datas).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta

import pandas as pd

from .config import PORTAL_GW, PORTAL_URL, caminho

log = logging.getLogger(__name__)

DESP = "/d0146/transpdespesas/v1"
REC = "/d0145/transpreceitas/v1"
PAUSA = 0.25  # segundos entre consultas, para não sobrecarregar o portal


class Portal:
    """Sessão Playwright no Portal da Transparência."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = self._browser = self._ctx = None
        self._auth: dict[str, str] = {}

    async def __aenter__(self) -> "Portal":
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._ctx = await self._browser.new_context(locale="pt-BR")
        page = await self._ctx.new_page()

        def _captura(req):
            if PORTAL_GW in req.url and "authorization" in req.headers:
                self._auth["authorization"] = req.headers["authorization"]

        page.on("request", _captura)
        await page.goto(PORTAL_URL + "#/Despesa", wait_until="networkidle", timeout=120_000)
        for _ in range(40):
            if self._auth:
                break
            await page.wait_for_timeout(250)
        if not self._auth:
            raise RuntimeError("O portal não emitiu o token de consulta; tente novamente mais tarde.")
        self._page = page
        return self

    async def __aexit__(self, *exc):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    async def get(self, path: str, params: dict, tentativas: int = 3) -> dict:
        for t in range(tentativas):
            r = await self._ctx.request.get(PORTAL_GW + path, params=params, headers=self._auth, timeout=180_000)
            if r.status == 401:  # token expirado: recarrega a página para renovar
                self._auth.clear()
                await self._page.reload(wait_until="networkidle")
                await self._page.wait_for_timeout(1500)
                continue
            if r.ok:
                await asyncio.sleep(PAUSA)
                return await r.json()
            log.warning("Portal %s → HTTP %s (tentativa %s)", path, r.status, t + 1)
            await asyncio.sleep(2 * (t + 1))
        raise RuntimeError(f"Falha ao consultar {path}")

    # ------------------------------------------------------------- despesas
    async def despesa_orgaos(self, ini: date, fim: date) -> pd.DataFrame:
        js = await self.get(f"{DESP}/despesapordataorgaos", {
            "anoconsulta": ini.year, "credor": "", "dataInicio": ini.isoformat(), "dataFim": fim.isoformat(),
            "exportarcsv": "false", "pageno": 1, "pagesize": 1000, "unidadeGestora": ""})
        d = (js.get("data") or [{}])[0].get("despesas") or []
        df = pd.DataFrame(d)
        if df.empty:
            return df
        df["orgao"] = df["orgao"].str.strip()
        return df[["codigo", "orgao", "empenhado", "liquidado", "pago"]]

    async def despesa_credores(self, ini: date, fim: date, pagesize: int = 500) -> pd.DataFrame:
        linhas, pag = [], 1
        while True:
            js = await self.get(f"{DESP}/despesapordatacredores", {
                "anoconsulta": ini.year, "credor": "", "dataInicio": ini.isoformat(), "dataFim": fim.isoformat(),
                "exportarcsv": "false", "pageno": pag, "pagesize": pagesize, "unidadeGestora": ""})
            d = (js.get("data") or [{}])[0].get("despesas") or []
            linhas.extend(d)
            total_pag = int((js.get("pagination") or {}).get("page_count") or 0)
            if not d or pag >= total_pag:
                break
            pag += 1
        df = pd.DataFrame(linhas)
        if df.empty:
            return df
        df["credor"] = df["credor"].str.strip()
        return df[["cpfCnpj", "credor", "empenhado", "liquidado", "pago"]].rename(columns={"cpfCnpj": "cpf_cnpj"})

    # ------------------------------------------------------------- receitas
    async def receita_simplificada(self, ano: int, mes_ini: int, mes_fim: int) -> pd.DataFrame:
        js = await self.get(f"{REC}/receitasimplificadas", {"exercicio": ano, "exportarcsv": "false",
                                                            "mesInicio": mes_ini, "mesTermino": mes_fim})
        df = pd.DataFrame(js.get("data") or [])
        if df.empty:
            return df
        return df.rename(columns={"elementId": "codigo"})[["receita", "codigo", "previsto", "arrecadado"]]

    async def receita_consolidada(self, ano: int) -> pd.DataFrame:
        js = await self.get(f"{REC}/receitaconsolidadas", {"elementId": 0, "exercicio": ano, "exportarcsv": "false",
                                                           "obterSubNiveis": "true", "descricao": ""})
        linhas: list[dict] = []

        def anda(n, pai, prof):
            linhas.append({"codigo": n["elementId"], "pai": pai, "nivel": prof, "receita": " ".join(str(n["receita"]).split()),
                           "previsto": n.get("totalAnual"), "arrecadado": n.get("totalArrecadado")})
            for c in n.get("__children__") or []:
                anda(c, n["elementId"], prof + 1)

        for n in js.get("data") or []:
            anda(n, "", 0)
        return pd.DataFrame(linhas)

    async def receita_orgaos(self, ini: date, fim: date) -> pd.DataFrame:
        js = await self.get(f"{REC}/pesquisadereceitas", {"exercicio": ini.year, "exportarcsv": "false",
                                                          "dataInicio": ini.isoformat(), "dataTermino": fim.isoformat()})
        df = pd.DataFrame(js.get("data") or [])
        if df.empty:
            return df
        df["orgao"] = df["orgao"].str.strip()
        return df.rename(columns={"unidadeGestoraCodigo": "codigo"})[["codigo", "orgao", "previsto", "arrecadado"]]


# =================================================================== rotina de coleta
def _upsert(nome: str, novo: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    arq = caminho(nome)
    if arq.exists() and not novo.empty:
        antigo = pd.read_parquet(arq)
        novo = pd.concat([antigo, novo], ignore_index=True).drop_duplicates(chaves, keep="last")
    if not novo.empty:
        novo.to_parquet(arq, index=False)
    return novo


async def _coletar(dias: int, meses_credor: int, hoje: date) -> dict:
    ano = hoje.year
    inicio_ano = date(ano, 1, 1)
    agora = datetime.now().isoformat(timespec="seconds")
    resumo: dict = {"coletado_em": agora, "data_referencia": hoje.isoformat()}
    async with Portal() as p:
        # 1) despesa por órgão, por mês: exercício corrente e os 12 últimos meses (mês corrente parcial até hoje)
        frames = []
        meses = sorted({(ano, m) for m in range(1, hoje.month + 1)}
                       | {((hoje.year * 12 + hoje.month - 1 - k) // 12, (hoje.month - 1 - k) % 12 + 1) for k in range(12)})
        for a, m in meses:
            ini = date(a, m, 1)
            fim = min(hoje, (date(a + (m == 12), m % 12 + 1, 1) - timedelta(days=1)))
            df = await p.despesa_orgaos(ini, fim)
            if not df.empty:
                df.insert(0, "mes", m)
                df.insert(0, "ano", a)
                frames.append(df)
        if frames:
            _upsert("portal_despesa_mensal_orgao.parquet", pd.concat(frames), ["ano", "mes", "codigo"])
        # 2) despesa e receita por órgão, por dia (últimos `dias` dias do exercício)
        fd, fr = [], []
        d0 = max(inicio_ano, hoje - timedelta(days=dias - 1))
        for k in range((hoje - d0).days + 1):
            dia = d0 + timedelta(days=k)
            df = await p.despesa_orgaos(dia, dia)
            if not df.empty:
                df.insert(0, "dia", pd.Timestamp(dia))
                fd.append(df)
            dr = await p.receita_orgaos(dia, dia)
            if not dr.empty:
                dr.insert(0, "dia", pd.Timestamp(dia))
                fr.append(dr)
        if fd:
            _upsert("portal_despesa_diaria_orgao.parquet", pd.concat(fd), ["dia", "codigo"])
        if fr:
            _upsert("portal_receita_diaria_orgao.parquet", pd.concat(fr), ["dia", "codigo"])
        # 3) credores do mês corrente e dos anteriores (`meses_credor`)
        for k in range(meses_credor):
            m = hoje.month - k
            if m < 1:
                break
            ini = date(ano, m, 1)
            fim = min(hoje, (date(ano + (m == 12), m % 12 + 1, 1) - timedelta(days=1)))
            dc = await p.despesa_credores(ini, fim)
            if not dc.empty:
                dc.insert(0, "mes", m)
                dc.insert(0, "ano", ano)
                dc["ate"] = pd.Timestamp(fim)
                dc.to_parquet(caminho(f"portal_credores_{ano}_{m:02d}.parquet"), index=False)
        # 4) receita simplificada por mês e árvore consolidada (acumulado do ano)
        fm = []
        for m in range(1, hoje.month + 1):
            dr = await p.receita_simplificada(ano, m, m)
            if not dr.empty:
                dr.insert(0, "mes", m)
                dr.insert(0, "ano", ano)
                fm.append(dr)
        if fm:
            _upsert("portal_receita_mensal.parquet", pd.concat(fm), ["ano", "mes", "codigo", "receita"])
        arv = await p.receita_consolidada(ano)
        if not arv.empty:
            arv.insert(0, "ano", ano)
            arv["coletado_em"] = pd.Timestamp(agora)
            arv.to_parquet(caminho(f"portal_receita_arvore_{ano}.parquet"), index=False)
            # histórico de instantâneos do acumulado (permite ver a evolução dia a dia)
            snap = arv[arv["nivel"] <= 3][["ano", "codigo", "receita", "nivel", "arrecadado", "coletado_em"]]
            _upsert("portal_receita_arvore_historico.parquet", snap, ["ano", "codigo", "coletado_em"])
    caminho("portal_meta.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2))
    return resumo


def coletar(dias: int = 45, meses_credor: int = 2, hoje: date | None = None) -> dict:
    """Executa a coleta completa do portal (≈2–4 min)."""
    return asyncio.run(_coletar(dias, meses_credor, hoje or date.today()))


def arvore_receita_rotulos() -> dict[str, str]:
    """Rótulos da natureza da receita a partir da árvore do portal (código de 8 dígitos → nome)."""
    rot: dict[str, str] = {}
    for arq in sorted(caminho("").glob("portal_receita_arvore_2*.parquet")):
        df = pd.read_parquet(arq)
        for cod, nome in df[["codigo", "receita"]].itertuples(index=False):
            c8 = str(cod)[:8]
            if str(cod)[8:] == "0000" and c8 not in rot:
                rot[c8] = nome
    return rot


def meta() -> dict:
    arq = caminho("portal_meta.json")
    return json.loads(arq.read_text()) if arq.exists() else {}
