# Página pública do Pórtica App (site/)

Páginas estáticas construídas com o design system **Aipim**, publicadas via
**GitHub Pages**:

- `index.html` — página principal (download, funcionalidades, FAQ, doação);
- `calculo.html` — página do **modelo de cálculo** (fórmulas da NBR 6118:2023).

Não usa CDN: CSS, JS, fontes, ícones e imagens são locais — as páginas abrem
offline. Ambas têm alternância **claro/escuro** (tema do Aipim + `theme.js`).

### Estrutura

| Arquivo | Papel |
|---|---|
| `theme.css` | Sobrepõe só os tokens semânticos de cor primária (azul Pórtica). |
| `base.css` | Layout, fontes locais (`@font-face`), galeria de figuras, inversão de equações no escuro. |
| `theme.js` | Alternância claro/escuro (persiste no `localStorage`) + troca de imagens temáticas. |
| `img/equations/*.png` | Equações renderizadas — origem: `docs/equations/` (script `generate_equation_images.py`). |
| `img/viga_*_secao.png`, `img/cisalhamento.png`, `img/partes_armadura_viga.png` | Figuras técnicas do app — origem: `core/assets/info/`. |

## Como publicar no GitHub Pages

Escolha adotada: **branch `gh-pages`**, servida a partir da raiz do branch.
É a opção mais simples de manter para um site estático: o `site/` vive junto do
código e o deploy é um único comando; nada de CI obrigatório.

### Passo a passo (feito pelo autor, uma única vez)

1. **Suba o branch `gh-pages`** com o conteúdo de `site/` (`public` é o
   remote do repositório público — ajuste se o seu remote tiver outro nome):

   ```powershell
   # Envia o conteúdo de site/ para o branch gh-pages (raiz do branch).
   git push public $(git subtree split --prefix site HEAD):gh-pages --force
   ```

   Alternativa manual (se o `subtree` falhar no Windows):

   ```powershell
   git checkout --orphan gh-pages
   git rm -rf .
   # copie o conteúdo de site/ para a raiz do repositório, depois:
   git add -A; git commit -m "site: pagina publica (gh-pages)"; git push public gh-pages
   ```

2. **Habilite o Pages.** No GitHub: *Settings → Pages → Source*:
   - *Deploy from a branch*
   - Branch: `gh-pages`
   - Pasta: `/ (root)`

3. **Confirme a URL.** Ela será
   `https://samuel-c-santos.github.io/portica-app/`
   (ajuste se o nome do repositório mudar).

4. **Atualize os links de "Documentação"** no `index.html`, caso o branch
   padrão do repositório público deixe de ser `public-main` (os links usam
   `blob/public-main/...`).

### Por que `gh-pages` e não `/docs`?

O repositório já tem uma pasta `docs/` com a documentação técnica
(`calculo.md`, `CHANGELOG.md` etc.). Servir o site por `/docs` misturaria o
conteúdo da página com os documentos internos e obrigaria a renomear a pasta
`site/`. O branch `gh-pages` mantém a página isolada, com deploy de um comando.

## Como o Aipim foi integrado (sem CDN)

| Item | Local | Origem / licença |
|---|---|---|
| Tokens (`--aipim-*`, claro e escuro) | `vendor/aipim/aipim.css` | Aipim (MIT) |
| Componentes (card, alert, button, tag, accordion, link, badge…) | `vendor/aipim/aipim-components.css` | Aipim (MIT) |
| Script opcional (tabs/modal/dismiss) | `vendor/aipim/aipim.js` | Aipim (MIT) — **não carregado** atualmente (a página usa só `<details>` nativo e links) |
| Ícones (SVG sprite) | `vendor/aipim/sprite.svg` | Hugeicons Free (MIT) |
| Fonte Antonio (variável) | `vendor/fonts/antonio.ttf` | SIL OFL 1.1 |
| Fonte Karla (variável) | `vendor/fonts/karla.ttf` | SIL OFL 1.1 |

- Os cabeçalhos de copyright/licença dos arquivos vendored **foram mantidos**.
- `theme.css` sobrescreve **apenas** os tokens semânticos de ação primária
  (`--aipim-action-primary-*`) para usar o azul da marca do Pórtica
  (`#1565C0`). O CSS do Aipim **não** foi editado.
- O rodapé das páginas traz a atribuição: *"Design system: Aipim, por Talis
  Galhardi (MIT / CC BY 4.0)."* e cita fontes e ícones.
- As imagens em `img/equations/` e as figuras técnicas são **cópias** dos
  arquivos de `docs/equations/` e `core/assets/info/` (necessário porque o
  `site/` é publicado isolado no branch `gh-pages`). Ao regenerar as equações
  (`python generate_equation_images.py`), copie-as de novo para
  `img/equations/`.

## O que falta o autor preencher

- **QR Pix**: extraído do PDF do banco (chave e-mail `samuelsantosambiental@gmail.com`,
  Belém/PA). Já está em `img/qr-pix.png`.
- **Ko-fi**: configurado — `https://ko-fi.com/samuelsantosportica` (também em
  `.github/FUNDING.yml`).
- **DOI**: `10.5281/zenodo.23733498` (Zenodo) — já preenchido.
- **Screenshots**: as capturas de tela do app ainda não existem. Os marcadores
  `<!-- SCREENSHOT: ... -->` em `index.html` indicam onde inseri-las.
- **URL final**: confirmar `https://samuel-c-santos.github.io/portica-app/` e
  atualizar o README principal com o link/badge definitivo.

## Verificações feitas

- Nenhum CDN externo (CSS, JS, fontes, ícones e imagens são locais).
- Links de documentação apontam para o repositório público
  (`github.com/samuel-c-santos/portica-app`).
- Alternância claro/escuro por botão (segue o sistema na primeira visita).
- Foco visível, estado nunca por cor sozinha (ícones + texto nos alertas).
