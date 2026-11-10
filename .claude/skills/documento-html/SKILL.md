---
name: documento-html
description: Cria documentos HTML auto-contidos (pesquisas, relatórios, tutoriais, documentação, guias, comparativos) no padrão visual e funcional do usuário — menu lateral com filtro, títulos numerados, destaque da seção em leitura, botões de copiar código, responsivo, tema claro/escuro e favicon temático. Use sempre que o usuário pedir para salvar uma pesquisa, tutorial ou documentação "em html", ou um relatório/comparativo para abrir no navegador.
---

# Documento HTML auto-contido

Um único arquivo `.html`, sem CSS, JS, fontes ou imagens externas (só links externos para fontes). Texto em
português (pt-BR), salvo pedido em contrário.

## Como fazer

1. **Parta do modelo** `assets/modelo.html` (nesta pasta da skill). Copie-o para o destino e troque só o conteúdo.
   Não reescreva o `<style>` nem o `<script>`: eles implementam todos os recursos obrigatórios.
2. **Destino e nome.** Use a pasta que o usuário indicar; se ele não indicar, pergunte. Dê ao arquivo um nome
   descritivo em kebab-case (ex.: `modelos-opensource-clonagem-voz.html`).
3. **Estrutura das seções** (o script do modelo numera e monta o menu sozinho):
   - Cada seção é `<section id="id-unico" class="s1">` com `<h2>`, ou `class="s2"` com `<h3>` para subseções.
   - Coloque as subseções logo depois da seção-mãe, como irmãs (não aninhadas).
   - Não escreva números nos títulos. A numeração (1, 1.1, …) e o menu `#nav` são gerados.
   - Os `id` devem ser únicos e estáveis, porque os links internos (`href="#id"`) dependem deles.
4. **Cabeçalho.** Preencha `{{TITULO}}`, `{{TITULO_CURTO}}` (no topo do menu), `{{FONTES}}`, `{{DATA}}` e `{{ESCOPO}}`.
   Não deixe nenhum `{{…}}` no arquivo final.
5. **Favicon temático.** Desenhe um SVG simples e legível em 16 px, ligado ao assunto (claquete para vídeo,
   microfone para voz etc.), e troque o `href` do `<link rel="icon">` por `data:image/svg+xml;base64,<SVG em base64>`.
   Mantenha o azul `#0969da` do tema como cor principal.
6. **Conteúdo típico de pesquisa ou comparativo.** Adapte ao pedido:
   - resumo executivo, com conclusões e recomendação por caso de uso;
   - conceitos fundamentais (quando o tema é técnico e o usuário pede didatismo);
   - metodologia: fontes, critérios com pesos e limitações (diga o que não foi testado);
   - ranking em `table.ordenavel` e matriz comparativa;
   - um cartão por item (`.meta`, `.links`, `h4`s, `.pn` com vantagens e desvantagens, comunidade);
   - exemplos de código, cada um em `figure.codigo` com botão `.copiar`, completos, com `pip install` e versões;
   - sugestões e próximos passos;
   - referências com URLs.
7. **Componentes disponíveis** (estilos já no modelo):
   - Tabelas largas vão dentro de `<div class="tabela">`. Use `td.c` para centralizar, `td.n` para números
     alinhados à direita e `td.nw` para não quebrar linha.
   - Barra de nota: `<span class="barra"><span style="width:85%"></span></span> <b>85</b>`.
   - Chips: `<div class="meta"><span>…</span><span class="nota">#1 · 85/100</span></div>`.
   - Prós e contras: `<div class="pn"><div class="p">…</div><div class="n">…</div></div>`.
   - Notas pequenas: `<p class="dica">…</p>`.
   - Escape o código dentro de `<pre><code>` (`&lt;`, `&gt;`, `&amp;`).
8. **Conteúdo grande.** Prefira gerar o HTML com um script Python na pasta temporária da sessão, com os dados em
   listas e dicionários e funções auxiliares para tabela, cartão e bloco de código, em vez de escrever centenas de
   linhas à mão. Use `html.escape` no código e nos textos vindos de fontes externas.
9. **Diagramas e fluxogramas** pedidos junto do documento: use a skill `archify`, salve o HTML do diagrama ao lado
   do documento e coloque um link para ele.

## Verificação obrigatória antes de entregar

```bash
python .claude/skills/documento-html/scripts/verificar.py caminho/do/documento.html <pasta-temporária-da-sessão>   # a partir da raiz do projeto pn-0003
```

O script, com Playwright e Chromium, confere:
- menu completo;
- destaque da seção em leitura;
- filtro do menu;
- botão copiar;
- links internos quebrados;
- erros de console;
- **ausência de rolagem horizontal no celular (390 px)**.

Ele também salva capturas de tela em desktop e no celular com o menu aberto: olhe as capturas. Corrija qualquer
falha e rode de novo. Ao relatar ao usuário, diga o que foi verificado e o que não foi testado.

## Recursos obrigatórios (já implementados no modelo; não remova)

- Responsividade: em ≤ 900 px o menu vira gaveta (botão `#abrir` + véu `#veu`).
- Títulos numerados hierarquicamente.
- Menu lateral esquerdo com os títulos das seções.
- Filtro do menu (`#filtro`), que ignora acentos e mantém a seção-mãe visível quando uma subseção combina.
- Destaque, no menu, da seção que está sendo lida (`a.ativo`, atualizado na rolagem).
- Botão "Copiar" em todo bloco de código.
- Tema claro e escuro (`prefers-color-scheme`), tabelas ordenáveis, botão voltar ao topo e estilos de impressão.
