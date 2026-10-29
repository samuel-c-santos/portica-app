# Changelog

Todas as mudanças relevantes do Pórtica App são registradas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

## [Não publicado]

Mudanças aceitas e ainda não publicadas em uma versão.

## [1.0.1]: correção do carregamento de projetos

### Corrigido

- Erro ao carregar projeto quando o painel FTOOL estava recolhido:
  `Text(...) Control must be added to the page first`. O fluxo de
  "Carregar Projeto" atualizava os rótulos do painel FTOOL mesmo quando ele
  não estava montado na página. Agora o painel é reconstruído conforme a
  fonte de entrada do projeto **antes** de sincronizar esses rótulos, e a
  sincronização só ocorre quando o painel está visível.
- Adicionado teste de regressão que reproduz o ciclo de vida real do Flet
  (`update()` em controle fora da página), que o mock de UI anterior escondia.

## [1.0.0]: primeira publicação open source (Apache-2.0)

### Adicionado

- **Licença Apache-2.0** como licença do código-fonte, da documentação e das
  figuras técnicas (`LICENSE`, com o apêndice de copyright preenchido).
- `NOTICE` com copyright, aviso de fornecimento "AS IS", ausência de garantia
  e responsabilização do usuário pela verificação dos resultados.
- `DISCLAIMER.md` com o aviso de responsabilidade técnica: o app é ferramenta
  de apoio e **não substitui** a verificação de engenheiro civil habilitado,
  com ART/RRT.
- `CITATION.cff` (CFF 1.2.0) com metadados de citação e bloco
  `preferred-citation` (DOI ainda é placeholder, a ser emitido na publicação
  Zenodo).
- `CONTRIBUTING.md` com como rodar a suíte, padrão de commit
  (*Conventional Commits*) e o que é bem-vindo e o que não será aceito.
- `SECURITY.md` com o procedimento de relato de falha de cálculo.
- `THIRD_PARTY.md` com as licenças de Flet, fpdf2, svglib, reportlab,
  rlPyCairo, ezdxf e das dependências transitivas, cada uma verificada no
  pacote instalado.
- Aviso de responsabilidade na tela **Sobre**, no rodapé de cada página do
  relatório PDF e no README.
- Rodapé do PDF com aviso de responsabilidade do usuário e indicação do
  README do projeto.
- `docs/CHANGELOG.md` (este arquivo).

### Alterado

- Build unificado em **um único script**, `build/build_portica.py` (PyInstaller
  `onefile`/`windowed`), que gera `dist/portica.exe` (~58 MB), o zip de
  distribuição e o `SHA256SUMS.txt` de conferência. O script resolve os
  caminhos do ambiente em tempo de execução e usa um diretório temporário
  fora do repositório.
- `build/launcher.py` passa a chamar `ft.run()` (API atual do Flet) em vez de
  `ft.app()`, depreciado desde o Flet 0.80.
- Primeira execução do executável agora é orientada: `build/flet_bootstrap.py`
  verifica o cliente desktop do Flet antes de abrir o app, mostra uma tela de
  progresso durante o download único (~30 MB) e, se o download falhar
  (sem internet, proxy, firewall), apresenta uma mensagem de erro com o que
  fazer, em vez de uma janela em branco. O download é gravado no cache do
  Flet (`%USERPROFILE%\.flet\client`), então as execuções seguintes são
  offline.
- README reescrito para open source: o que é, instalação, uso, importação
  FTOOL, limitações, aviso de responsabilidade, licença e como citar.
- Amostras reduzidas ao mínimo necessário e artefatos gerados (PDF/DXF)
  removidos do versionamento.

### Removido

- Scripts e specs obsoletos de build (`build_all.py`, `build_standard*.py`,
  `build_premium*.py`, `portica-standard.spec`, `portica-premium.spec`): havia
  duas árvores de build para as edições Standard e Premium, que não existem
  mais desde a unificação do app.
- Licença proprietária do código-fonte e seção de licença paga do README.
- Documentos de licença de uso final do produto (`docs/eula.md`) e demais
  documentos internos de planejamento, movidos para fora do repositório
  público.

[Não publicado]: https://github.com/samuel-c-santos/portica-app/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/samuel-c-santos/portica-app/releases/tag/v1.0.1
[1.0.0]: https://github.com/samuel-c-santos/portica-app/releases/tag/v1.0.0
