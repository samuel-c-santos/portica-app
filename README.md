# Pórtica App

Calculadora estrutural de vigas de concreto armado conforme a **ABNT NBR 6118:2023** — flexão, cisalhamento, armadura dupla, armadura de pele, ELS e detalhamento, com entrada manual ou importação de esforços exportados do FTOOL.

[![Licença](https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Testes](https://img.shields.io/badge/testes-pytest-green.svg)](tests/)
[![Site](https://img.shields.io/badge/site-P%C3%B3rtica_App-1565C0.svg)](https://samuel-c-santos.github.io/portica-app/)
[![Doar](https://img.shields.io/badge/doar-Ko--fi-FF5E5B.svg)](https://ko-fi.com/samuelsantosportica)
<!-- Badge do DOI (Zenodo) — habilitar na fase F6, quando o DOI existir:
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.-XXXXXXX-blue.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
-->

## Screenshots

<!-- SCREENSHOT: 01-tela-inicial.png — tela inicial com os dois tipos de seção (retangular e T) -->
<!-- SCREENSHOT: 02-entrada-manual.png — tela da viga com a entrada manual (trechos de flexão e cisalhamento) -->
<!-- SCREENSHOT: 03-importacao-ftool.png — painel "Importar do FTOOL" com os arquivos de esforços carregados -->
<!-- SCREENSHOT: 04-resultados-flexao.png — modal de resultados da flexão (armadura adotada, bitolas, Checks) -->
<!-- SCREENSHOT: 05-relatorio-pdf.png — relatório PDF gerado (capa, tabelas, esquema da seção) -->

## Funcionalidades

| Área | O que o app entrega |
|---|---|
| Flexão | Seção retangular e seção T (mesa colaborante), com verificação dos domínios de deformação |
| Cisalhamento | Modelo I da NBR 6118, com contribuição do concreto e do aço |
| Armadura dupla | Solução com armadura de compressão quando o momento excede o limite do domínio 3 |
| Armadura de pele | Dimensionamento automático das costelas para vigas com `h ≥ 60 cm` |
| Coeficientes γf | Tabela de ponderação das ações da NBR 6118 (seleção por caso de combinação) |
| Relatório PDF | Capa, dados de entrada, tabelas de flexão e cisalhamento, esquema da seção e campos de ART/CREA |
| Exportação DXF | Desenho da seção R/T com layers e grampos |
| Projetos `.ptc` | Salvar e carregar o projeto completo (geometria, materiais, esforços, ajustes) |
| Parser FTOOL | Leitura dos `.txt` exportados do FTOOL: momento fletor, esforço cortante e deformações |
| Seções críticas | Detecção automática das seções governantes a partir das curvas importadas |
| Dimensionamento automático | Armadura, estribos e bitolas dimensionados a partir dos esforços importados |
| Envelope de combinações | Envelope das combinações de ação e verificação no pior caso |
| Diagramas M(x) e V(x) | Desenho dos diagramas de momento fletor e esforço cortante no relatório |
| ELS — flecha | Flecha imediata e diferida por integração numérica da curvatura |
| ELS — fissuração | Abertura de fissuras `wk1`, `wk2` e mínima, com limite por classe de agressividade |
| Estribos por região | Detalhamento dos estribos trecho a trecho, a partir do diagrama de cortantes |
| Grampos suplementares | Grampos de 2ª e 3ª camadas quando a armadura não cabe em uma camada |

## Instalação

Requisitos: Python 3.10 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python edicoes\main.py
```

Em Linux/macOS, substitua `.\.venv\Scripts\Activate.ps1` por `source .venv/bin/activate` e use `python edicoes/main.py`.

## Executável pronto

Quem não quiser instalar Python poderá baixar o executável já compilado (Windows) na aba **Releases** do repositório:

<https://github.com/samuel-c-santos/portica-app/releases>

São publicados **dois** assets para Windows 10/11 x64. A diferença entre eles é o
cliente gráfico do Flet: na versão **leve** ele é baixado uma única vez no primeiro
uso; na versão **offline** ele já vem embutido.

| Asset | Cliente Flet | Tamanho |
|---|---|---|
| `portica-v1.0.0-windows-x64.exe` | **Leve** — baixado no 1º uso (~30 MB) | ≈ 58 MB |
| `portica-v1.0.0-windows-x64.zip` | **Embutido** — roda offline desde a 1ª execução | ≈ 96 MB |

| Item | Valor |
|---|---|
| Versão | 1.0.0 |
| Plataforma | Windows 10/11 x64 |
| Checksum | [`SHA256SUMS.txt`](SHA256SUMS.txt) (raiz do repositório, e dentro do zip) |

Para conferir a integridade do download (PowerShell):

```powershell
Get-FileHash .\portica-v1.0.0-windows-x64.exe -Algorithm SHA256
Get-FileHash .\portica-v1.0.0-windows-x64.zip -Algorithm SHA256
```

O binário traz as mesmas funcionalidades do código-fonte.

**Versão leve (`.exe`):** o app é um app Flet *desktop*, então o cliente gráfico
(o binário que desenha a janela, ~30 MB) é baixado **uma única vez** do GitHub
Releases do Flet. A primeira execução mostra uma tela de progresso explicando o
que está acontecendo. Depois do download, o cliente fica em cache
(`%USERPROFILE%\.flet\client`) e o app abre **offline** a partir da segunda vez.

**Versão offline (`.zip`):** o cliente Flet já vem embutido no executável, então o
app abre **offline desde a primeira execução** — ideal para máquinas sem internet.
Basta descompactar o `.zip` e executar o `portica.exe`.

Se o download falhar (por exemplo, máquina sem internet, proxy ou firewall),
o app mostra uma mensagem explicando o que fazer em vez de abrir uma janela em
branco — basta conectar à internet e executar o Portica App novamente.

### Gerar o executável a partir do código

```powershell
pip install -r requirements.txt
pip install pyinstaller
python build/build_portica.py
```

O script usa PyInstaller (`--onefile --windowed`), resolve sozinho os caminhos do
ambiente, trabalha em um diretório temporário fora do repositório e deixa o
resultado em `dist/portica.exe`, junto com `SHA256SUMS.txt` e o zip de
distribuição. Opções: `--bundle-client` (embute o cliente Flet no executável,
+30 MB, para rodar offline já na primeira execução) e `--keep-work` (preserva o
diretório temporário do build).

## Como usar

O app tem **uma única tela de viga** com dois tipos de seção (retangular e T) e **duas formas de entrada** de esforços. A entrada manual é o estado inicial; a importação do FTOOL é um painel opcional.

### Entrada manual

1. Na tela inicial, escolha o tipo de seção: **viga retangular** ou **viga T**.
2. Na tela da viga, informe a geometria (altura `h`, largura `bw`, e para a seção T a mesa `bf`/`hf`), os materiais (`fck`, `fyk`, classe de agressividade ambiental) e o estribo adotado.
3. Preencha as tabelas de trechos de **flexão** (momentos `M`) e de **cisalhamento** (cortantes `V`) com os valores característicos. Além dos trechos, é possível informar o trecho com maior momento e o maior cortante, que são usados no dimensionamento.
4. Clique em **Calcular**. O modal de resultados mostra a armadura de flexão adotada (bitola, número de barras, camadas e espaçamento), a armadura de cisalhamento e os *checks* normativos.
5. Ajuste fino (opcional): no painel de ajustes de ELS é possível forçar bitola mínima, adicionar barras extras, sobrescrever `h` ou `fck` e recalcular.
6. Gere o **relatório PDF** e/ou a **exportação DXF**.
7. Use **Salvar Projeto** para gravar o arquivo `.ptc` e **Carregar Projeto** para retomá-lo.

### Importação de arquivos do FTOOL

O app é compatível com os arquivos `.txt` exportados pelo FTOOL (apenas leitura de dados — não há vínculo, endosso ou representação oficial do produto).

1. Na tela da viga, clique em **Importar do FTOOL**.
2. Selecione os arquivos `.txt` exportados: momento fletor, esforço cortante e deformações. O app valida o formato de cada arquivo (a primeira linha deve ser o número de pontos) e mostra a curva importada.
3. A partir dos esforços importados, o app detecta as **seções críticas**, monta o **envelope de combinações** e executa o **dimensionamento automático** (armadura de flexão e de cisalhamento, estribos por região e grampos suplementares).
4. Os **diagramas M(x) e V(x)** são incluídos no relatório PDF, junto do detalhamento e da verificação de ELS (flecha e fissuração).
5. O botão **Voltar para entrada manual** retorna à digitação direta, sem perder a geometria e os materiais já informados.

A pasta [`samples/`](samples) traz arquivos de exemplo: seis `.txt` do FTOOL (momentos, cortantes e deformações, para as seções retangular e T) e um projeto `.ptc` de exemplo (`samples/exemplo_projeto.ptc`).

## Arquitetura

```
portica_app/
├── core/calculos/       # Motor de cálculo (NBR 6118)
├── core/detailing/      # Detalhamento geométrico de seção e desenho
├── core/relatorio_base.py   # Relatório PDF compartilhado
├── ui/                  # Interface (Flet)
│   └── ftool/           # Parser FTOOL, dimensionamento, ELS, diagramas
├── edicoes/main.py      # Entry point único
├── tests/               # Suíte de testes (pytest)
├── samples/             # Arquivos de exemplo (FTOOL e projeto .ptc)
└── docs/                # Documentação técnica
```

A separação em camadas permite que o núcleo de cálculo (`core/`) seja reutilizado sem dependência de interface. O modelo de cálculo está descrito em [`docs/calculo.md`](docs/calculo.md) e o mapa do código em [`docs/mapa_codigo.md`](docs/mapa_codigo.md).

As figuras técnicas exibidas no app (`core/assets/info/`) são desenhos próprios, gerados pelo script [`generate_info_figures.py`](generate_info_figures.py) — nenhuma imagem de origem desconhecida é distribuída com o repositório.

## Testes

```powershell
python -m pytest tests -q
```

## Referências normativas

- **ABNT NBR 6118:2023** — Projeto de estruturas de concreto armado — partes 1 a 5 (referência da implementação; os valores e tabelas normativos não são reproduzidos neste repositório).
- **ABNT NBR 6118:2023, Emenda 1:2026**.
- **ABNT NBR 7480** — Aço destinado a armaduras de concreto armado.

O app implementa as fórmulas e os critérios de dimensionamento; os valores de tabelas e o texto normativo permanecem sob a titularidade da ABNT e devem ser consultados na norma vigente.

## Aviso de responsabilidade

> **Aviso.** O Pórtica App é uma ferramenta de apoio ao dimensionamento de vigas
> de concreto armado conforme a ABNT NBR 6118. Os resultados devem ser
> verificados por engenheiro civil habilitado, com ART/RRT, antes de qualquer
> uso em projeto executivo. O software é fornecido "como está", sem garantia de
> adequação a um caso concreto. Os autores não respondem por decisões de projeto
> tomadas com base nas saídas do programa.

O aviso completo, com o escopo do que o software garante e o que cabe ao
usuário, está em [`DISCLAIMER.md`](DISCLAIMER.md). O mesmo aviso aparece na
tela **Sobre** do app e no rodapé de cada página do relatório PDF.

## Como citar

O software é citável por DOI. O DOI definitivo e o arquivo `CITATION.cff` entram
na fase de publicação (F6); até lá, use a referência do repositório:

> Pórtica App — Calculadora estrutural de vigas de concreto armado (NBR 6118:2023).
> Versão 1.0.0. Disponível em: <https://github.com/samuel-c-santos/portica-app>.

Depois de publicado no Zenodo, a citação passa a ser:

> Autor (ano). *Pórtica App: calculadora estrutural de vigas de concreto armado (NBR 6118:2023)* (versão 1.0.0) [software]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX

O arquivo [`CITATION.cff`](CITATION.cff) do repositório é a referência
máquina-legível para ferramentas de citação (GitHub, Zotero, Overleaf).

## Documentação / Site

- **Página pública**: <https://samuel-c-santos.github.io/portica-app/> — download, funcionalidades, FAQ, como citar e doação (o código-fonte da página está em [`site/`](site/)).
- **Modelo de cálculo**: [`docs/calculo.md`](docs/calculo.md)
- **Mapa do código**: [`docs/mapa_codigo.md`](docs/mapa_codigo.md)
- **Histórico de versões**: [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

## Licença

**Apache-2.0**. O texto completo da licença é distribuído no arquivo [`LICENSE`](LICENSE) e vale para o código-fonte, a documentação e as figuras técnicas deste repositório.

Os avisos de copyright e de ausência de garantia estão em [`NOTICE`](NOTICE), e
as licenças das bibliotecas de terceiros em [`THIRD_PARTY.md`](THIRD_PARTY.md).

## Contribuição

Contribuições são bem-vindas — correções de cálculo sobretudo. O guia completo (como rodar a suíte, padrão de commits e o que não é aceito) está em [`CONTRIBUTING.md`](CONTRIBUTING.md).

Antes de abrir um *pull request*, rode a suíte de testes e descreva a correção com a referência normativa correspondente.

Falhas de cálculo têm um procedimento específico de relato, descrito em
[`SECURITY.md`](SECURITY.md).

O histórico de versões está em [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

## Contato e suporte

- Dúvidas, correções e Issues: <https://github.com/samuel-c-santos/portica-app/issues>
- Perfil do autor e contato: <https://github.com/samuel-c-santos>
- Doação (opcional, sem paywall e sem feature bloqueada): veja a seção **Doar** da [página pública](https://samuel-c-santos.github.io/portica-app/) — Pix ou Ko-fi.

<!-- Aviso: o badge do DOI acima entra na fase F6, quando o DOI existir. A página pública (F5) e os links de doação já estão ativos. -->
