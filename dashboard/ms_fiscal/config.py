"""Configuração central do painel fiscal de Mato Grosso do Sul."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
DIR_DADOS = Path(os.environ.get("MS_FISCAL_DADOS", RAIZ_PROJETO / "dados" / "dashboard"))
DIR_DADOS.mkdir(parents=True, exist_ok=True)

# Ente: Estado de Mato Grosso do Sul (código IBGE da UF)
ID_ENTE = 50
UF = "MS"

ANO_ATUAL = date.today().year
# Exercícios cobertos por padrão (podem ser ampliados com --anos na coleta)
ANOS_PADRAO = list(range(ANO_ATUAL - 2, ANO_ATUAL + 1))

# ---------------------------------------------------------------- fontes
SICONFI_API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
SICONFI_DOCS = "https://apidatalake.tesouro.gov.br/docs/siconfi/"
CKAN_API = "https://www.dados.ms.gov.br/api/3/action"
PORTAL_URL = "https://www.transparencia.ms.gov.br/"
PORTAL_GW = "https://gw.sgi.ms.gov.br"
IBGE_AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados"
IBGE_SIDRA = "https://apisidra.ibge.gov.br/values"
BCB_IPCA = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"

MCASP_URL = "https://thot-arquivos.tesouro.gov.br/publicacao/51045"
LRF_URL = "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp101.htm"

USER_AGENT = "pn-0003-painel-fiscal-ms/1.0 (pesquisa; dados publicos)"  # só ASCII: o IBGE recusa (400) cabeçalhos com acento


def caminho(nome: str) -> Path:
    """Caminho de um arquivo Parquet/JSON na pasta de dados do painel."""
    return DIR_DADOS / nome
