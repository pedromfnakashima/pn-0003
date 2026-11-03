"""Atualiza as bases do painel fiscal de MS a partir das fontes primárias.

Exemplos:
    python coletar.py --tudo                 # todas as fontes (primeira carga: ~15-25 min)
    python coletar.py --portal               # só o Portal da Transparência (Playwright, ~2-4 min)
    python coletar.py --siconfi --anos 2023 2024 2025 2026
    python coletar.py --credores --desde 2024-01
    python coletar.py --rreo-estados         # RREO das 27 UFs, últimos 4 exercícios
    python coletar.py --rgf-estados          # RGF das 27 UFs e dos 5 Poderes, últimos 4 exercícios
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from ms_fiscal import dados_abertos, portal, rgf_estados, rreo_estados, siconfi
from ms_fiscal.config import ANOS_PADRAO


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tudo", action="store_true", help="atualiza todas as fontes")
    ap.add_argument("--portal", action="store_true", help="Portal da Transparência (diário, via Playwright)")
    ap.add_argument("--siconfi", action="store_true", help="MSC (mensal), RREO (bimestral) e RGF (quadrimestral)")
    ap.add_argument("--credores", action="store_true", help="despesas por credor (mensal, dados.ms.gov.br)")
    ap.add_argument("--repasses", action="store_true", help="repasses constitucionais a municípios (mensal)")
    ap.add_argument("--ipca", action="store_true", help="IPCA (IBGE/SIDRA, tabela 1737; reserva: BCB/SGS 433)")
    ap.add_argument("--rreo-estados", action="store_true",
                    help="RREO de todas as UFs, últimos 4 exercícios (Siconfi; ~10 min na primeira carga)")
    ap.add_argument("--rgf-estados", action="store_true",
                    help="RGF de todas as UFs e Poderes, últimos 4 exercícios (Siconfi; ~20 min na primeira carga)")
    ap.add_argument("--anos", type=int, nargs="+", default=ANOS_PADRAO, help="exercícios do Siconfi")
    ap.add_argument("--desde", default=f"{ANOS_PADRAO[0] + 1}-01", help="mês inicial (AAAA-MM) para credores/repasses")
    ap.add_argument("--dias", type=int, default=45, help="dias de série diária no portal")
    ap.add_argument("--meses-credor", type=int, default=2, help="meses de credores coletados no portal")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    desde = tuple(int(x) for x in a.desde.split("-"))
    if not any([a.tudo, a.portal, a.siconfi, a.credores, a.repasses, a.ipca, a.rreo_estados, a.rgf_estados]):
        ap.print_help()
        return 1
    erros = []

    def etapa(nome, f):
        try:
            logging.info("== %s", nome)
            f()
        except Exception as e:  # uma fonte fora do ar não deve impedir as demais
            logging.exception("Falha em %s", nome)
            erros.append(f"{nome}: {e}")

    if a.tudo or a.ipca:
        etapa("IPCA", dados_abertos.atualizar_ipca)
    if a.tudo or a.portal:
        etapa("Portal da Transparência", lambda: portal.coletar(a.dias, a.meses_credor, date.today()))
    if a.tudo or a.repasses:
        etapa("Repasses a municípios", lambda: dados_abertos.atualizar_repasses(desde))
    if a.tudo or a.credores:
        etapa("Despesas por credor", lambda: dados_abertos.atualizar_despesas_credor(desde))
    if a.tudo or a.siconfi:
        def _sic():
            ex = siconfi.extrato_entregas(a.anos)
            siconfi.atualizar_relatorios(a.anos, ex)
            siconfi.atualizar_msc(a.anos, ex)
        etapa("Siconfi", _sic)
    if a.tudo or a.rreo_estados:
        etapa("RREO de todas as UFs", rreo_estados.atualizar)
    if a.tudo or a.rgf_estados:
        etapa("RGF de todas as UFs", rgf_estados.atualizar)
    if erros:
        print("Concluído com falhas:\n- " + "\n- ".join(erros))
        return 2
    print("Concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
