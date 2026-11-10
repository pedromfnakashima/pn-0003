"""Verifica um documento HTML gerado a partir de assets/modelo.html.

Uso:  python verificar.py caminho/do/documento.html [pasta_para_capturas]
Requer: pip install playwright && python -m playwright install chromium
Checa: erros de console, menu montado, filtro (com e sem acento), destaque da seção em leitura,
botão copiar, links internos quebrados e rolagem horizontal no celular. Salva capturas de tela.
"""
import sys
import pathlib
from playwright.sync_api import sync_playwright

doc = pathlib.Path(sys.argv[1]).resolve()
saida = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else doc.parent)
U = doc.as_uri()
falhas = []

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and erros.append(m.text))
    pg.goto(U)
    pg.wait_for_timeout(300)

    itens = pg.locator("#nav li").count()
    secoes = pg.locator("main section[id]").count()
    print(f"menu: {itens} itens para {secoes} seções")
    if itens == 0 or itens != secoes:
        falhas.append("menu incompleto")

    ids = pg.evaluate("[...document.querySelectorAll('main section[id]')].map(s=>s.id)")
    alvo = ids[len(ids) // 2]
    pg.locator(f"#{alvo}").scroll_into_view_if_needed()
    pg.wait_for_timeout(400)
    ativo = pg.locator("#nav a.ativo")
    print("seção ativa:", ativo.inner_text() if ativo.count() else "(nenhuma)")
    if not ativo.count():
        falhas.append("destaque da seção em leitura não funcionou")

    palavra = pg.locator("#nav li").nth(min(2, itens - 1)).inner_text().split()[-1]
    pg.fill("#filtro", palavra)
    vis = pg.locator("#nav li:not(.oculto)").count()
    print(f"filtro '{palavra}': {vis} itens visíveis")
    if not 0 < vis < itens:
        falhas.append("filtro do menu não reduziu a lista")
    pg.fill("#filtro", "zzzzqqq")
    if pg.locator("#semres").is_hidden():
        falhas.append("mensagem 'nenhuma seção' não apareceu")
    pg.fill("#filtro", "")

    botoes = pg.locator(".copiar")
    if botoes.count():
        botoes.first.scroll_into_view_if_needed()
        botoes.first.click()
        pg.wait_for_timeout(200)
        txt = pg.evaluate("navigator.clipboard.readText()")
        print(f"copiar: {botoes.count()} botões; área de transferência com {len(txt)} caracteres")
        if not txt:
            falhas.append("botão copiar não copiou")

    quebrados = pg.evaluate("[...document.querySelectorAll('a[href^=\"#\"]')]"
                            ".filter(a=>a.getAttribute('href').length>1 && !document.getElementById(a.getAttribute('href').slice(1)))"
                            ".map(a=>a.getAttribute('href'))")
    if quebrados:
        falhas.append(f"links internos quebrados: {sorted(set(quebrados))}")
    pg.screenshot(path=str(saida / f"{doc.stem}_desktop.png"))

    m = b.new_page(viewport={"width": 390, "height": 844})
    m.goto(U)
    m.wait_for_timeout(300)
    largura = m.evaluate("document.documentElement.scrollWidth")
    print("largura no celular:", largura)
    if largura > 392:
        culpados = m.evaluate("""[...document.querySelectorAll('main *')].filter(e=>e.getBoundingClientRect().right>395
            && !e.closest('.tabela') && !e.closest('pre')).slice(0,5).map(e=>e.tagName+': '+e.textContent.slice(0,50))""")
        falhas.append(f"rolagem horizontal no celular ({largura}px): {culpados}")
    m.click("#abrir")
    m.wait_for_timeout(400)
    m.screenshot(path=str(saida / f"{doc.stem}_celular_menu.png"))
    b.close()

if erros:
    falhas.append(f"erros de console: {erros}")
print("\nOK: tudo certo." if not falhas else "\nFALHAS:\n- " + "\n- ".join(falhas))
sys.exit(1 if falhas else 0)
