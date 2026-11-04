"""Teste ponta a ponta do painel com Playwright.

Sobe o Streamlit, visita cada página, verifica que não há exceções na tela,
que os gráficos foram desenhados e salva capturas de tela em tests/capturas/.

    pytest tests/test_dashboard_e2e.py -q          (ou)   python tests/test_dashboard_e2e.py
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
CAPTURAS = APP / "tests" / "capturas"
PAGINAS = ["visao-geral", "tempo-real", "receitas", "despesas", "fornecedores", "transferencias", "rreo", "rgf", "fontes"]


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def servidor():
    porta = _porta_livre()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true",
                             "--server.port", str(porta), "--browser.gatherUsageStats", "false"],
                            cwd=APP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{porta}"
    for _ in range(120):
        try:
            with socket.create_connection(("127.0.0.1", porta), timeout=1):
                break
        except OSError:
            time.sleep(0.5)
    yield url
    proc.terminate()
    proc.wait(timeout=20)


def _esperar(page, timeout=120_000):
    page.wait_for_selector('[data-testid="stApp"]', timeout=timeout)
    page.wait_for_timeout(2000)
    t0, ociosas = time.time(), 0
    while time.time() - t0 < timeout / 1000 and ociosas < 3:  # espera spinners e o "Running…" sumirem
        ocupado = (page.locator('[data-testid="stSpinner"]').count()
                   + page.locator('[data-testid="stStatusWidget"]').filter(has_text="Stop").count()
                   + page.locator('[data-testid="stStatusWidget"] button').filter(has_text="Stop").count())
        ociosas = ociosas + 1 if ocupado == 0 else 0
        page.wait_for_timeout(700)
    page.wait_for_timeout(1500)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina(servidor, pagina):
    from playwright.sync_api import sync_playwright

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 4200})
        caminho = "" if pagina == "visao-geral" else pagina  # a página padrão é servida na raiz
        page.goto(f"{servidor}/{caminho}", wait_until="domcontentloaded")
        _esperar(page)
        erros = page.locator('[data-testid="stException"]')
        texto_erros = [erros.nth(i).inner_text()[:800] for i in range(erros.count())]
        page.screenshot(path=str(CAPTURAS / f"{pagina}.png"), full_page=True)
        n_graficos = page.locator(".js-plotly-plot").count()
        b.close()
    assert not texto_erros, f"Exceções em {pagina}: {texto_erros}"
    if pagina not in ("fontes",):
        assert n_graficos > 0, f"Nenhum gráfico desenhado em {pagina}"


def _sem_excecao(page, contexto: str):
    erros = page.locator('[data-testid="stException"]')
    textos = [erros.nth(i).inner_text()[:600] for i in range(erros.count())]
    assert not textos, f"Exceções após {contexto}: {textos}"


def test_interacoes(servidor):
    """Liga 'valores reais', troca medidas e filtros e confirma que nenhuma combinação quebra a página."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 2400})
        page.goto(f"{servidor}/receitas", wait_until="domcontentloaded")
        _esperar(page)
        page.get_by_test_id("stSidebarUserContent").get_by_text("Valores reais (IPCA)").click()
        _esperar(page)
        _sem_excecao(page, "ativar valores reais")
        for medida in ("Bruta (exceto renúncia)", "Bruta registrada", "Deduções"):
            page.get_by_test_id("stSelectbox").filter(has_text="Medida").click()
            page.get_by_role("option", name=medida, exact=True).click()
            _esperar(page)
            _sem_excecao(page, f"medida {medida}")
        page.goto(f"{servidor}/fornecedores", wait_until="domcontentloaded")
        _esperar(page)
        page.locator(".st-key-fn_forn").get_by_text("Só fornecedores").click()
        _esperar(page)
        _sem_excecao(page, "desligar 'Só fornecedores'")
        page.get_by_role("tab", name="🔎 Ficha do credor").click()
        _esperar(page)
        _sem_excecao(page, "abrir a ficha do credor")
        page.goto(f"{servidor}/rgf", wait_until="domcontentloaded")
        _esperar(page)
        page.get_by_role("tab", name="legado_Despesa com pessoal").click()
        _esperar(page)
        for poder in ("Legislativo (ALEMS + TCE)", "Judiciário", "Ministério Público", "Defensoria Pública"):
            page.get_by_role("tabpanel").get_by_text(poder, exact=True).first.click()
            _esperar(page)
            _sem_excecao(page, f"RGF – {poder}")
        page.screenshot(path=str(CAPTURAS / "interacoes_rgf.png"))
        b.close()


def _clicar_opcao(page, chave: str, opcao: str):
    page.mouse.move(0, 0)  # fecha a tooltip do hover anterior, que no Streamlit ≥ 1.66 cobre o selectbox
    page.locator(f".st-key-{chave}").click()
    page.keyboard.type(opcao[:12])  # a lista é virtualizada: filtra digitando
    page.get_by_role("option", name=opcao).first.click()
    _esperar(page)


def test_rreo_anexos(servidor):
    """Aba Anexos do RREO: todas as UFs, troca de anexo, unidade (% da RCL), transformação e aba intra-estado."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 3200})
        page.goto(f"{servidor}/rreo", wait_until="domcontentloaded")
        _esperar(page)
        page.get_by_role("tab", name="📚 Anexos").click()
        _esperar(page)
        _sem_excecao(page, "abrir a aba Anexos")
        assert page.locator(".js-plotly-plot").count() >= 2, "a aba Anexos não desenhou os gráficos"
        page.locator(".st-key-rx_modo_m").get_by_text("Soma em 12 meses").click()
        _esperar(page)
        page.locator(".st-key-rx_unid").get_by_text("% da RCL").click()
        _esperar(page)
        _sem_excecao(page, "% da RCL, soma de 12 meses")
        page.screenshot(path=str(CAPTURAS / "rreo_anexos_entre_estados.png"), full_page=True)
        for anexo in ("Anexo 01 – Balanço Orçamentário", "Anexo 02 – Despesa por função e subfunção",
                      "Anexo 06 – Resultados primário e nominal", "Anexo 14 – Demonstrativo simplificado"):
            _clicar_opcao(page, "rx_anexo", anexo)
            _sem_excecao(page, f"anexo {anexo}")
        page.locator(".st-key-rx_modo_a").get_by_text("Valor do bimestre (desacumulado)").click()
        _esperar(page)
        _sem_excecao(page, "valor do bimestre")
        page.get_by_role("tab", name="📍 Dentro de um Estado").click()
        _esperar(page)
        _sem_excecao(page, "aba Dentro de um Estado")
        page.get_by_test_id("stSidebarUserContent").get_by_text("Valores reais (IPCA)").click()
        _esperar(page)
        _sem_excecao(page, "valores reais na aba Anexos")
        page.screenshot(path=str(CAPTURAS / "rreo_anexos_intra.png"), full_page=True)
        b.close()


def test_botoes_atualizacao_e_ipca(servidor):
    """Botões da barra lateral: IPCA (IBGE) e RREO de todas as UFs; depois, legenda de valores reais."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 2000})
        page.goto(f"{servidor}/rreo", wait_until="domcontentloaded")
        _esperar(page)
        lateral = page.get_by_test_id("stSidebarUserContent")
        for botao, minutos in (("IPCA (IBGE)", 2), ("RREO de todas as UFs (Siconfi)", 15), ("RGF de todas as UFs (Siconfi)", 15)):
            if not lateral.get_by_role("button", name=botao).is_visible():  # o expansor pode já estar aberto
                lateral.get_by_text("🔄 Atualizar dados").click()
            lateral.get_by_role("button", name=botao).click()
            lateral.get_by_text(f"{botao}: concluído.").wait_for(state="attached", timeout=minutos * 60_000)
            _esperar(page)
            _sem_excecao(page, f"botão {botao}")
        lateral.get_by_text("Valores reais (IPCA)").click()
        _esperar(page)
        assert lateral.get_by_text("Valores reais, a preços de").count() > 0, "legenda de valores reais ausente"
        page.screenshot(path=str(CAPTURAS / "botoes.png"))
        b.close()


def test_rgf_anexos(servidor):
    """Aba Anexos do RGF: Poderes (cada um e a soma), anexos, transformações e a sub-aba de limites da LRF."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 3200})
        page.goto(f"{servidor}/rgf", wait_until="domcontentloaded")
        _esperar(page)
        page.get_by_role("tab", name="📚 Anexos").click()
        _esperar(page)
        _sem_excecao(page, "abrir a aba Anexos do RGF")
        assert page.locator(".js-plotly-plot").count() >= 2, "a aba Anexos do RGF não desenhou os gráficos"
        page.locator(".st-key-gx_modo_mensal").get_by_text("Soma em 12 meses").click()
        _esperar(page)
        page.locator(".st-key-gx_unid").get_by_text("% da RCL").click()
        _esperar(page)
        _sem_excecao(page, "pessoal, 12 meses, % da RCL")
        page.screenshot(path=str(CAPTURAS / "rgf_anexos_entre_estados.png"), full_page=True)
        for poder in ("Executivo (E)", "Legislativo (L)", "Defensoria Pública (D)", "Todos os Poderes (soma)"):
            _clicar_opcao(page, "gx_poder", poder)
            _sem_excecao(page, f"Poder {poder}")
        _clicar_opcao(page, "gx_anexo", "Anexo 02 – Dívida consolidada líquida")
        _sem_excecao(page, "anexo 2")
        page.get_by_role("tab", name="📍 Dentro de um Estado").click()
        _esperar(page)
        _sem_excecao(page, "Dentro de um Estado (RGF)")
        page.get_by_role("tab", name="⚖️ Limites da LRF").click()
        _esperar(page)
        _sem_excecao(page, "Limites da LRF")
        assert page.get_by_text("Quadro de cumprimento").count() > 0
        page.screenshot(path=str(CAPTURAS / "rgf_limites_lrf.png"), full_page=True)
        b.close()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
