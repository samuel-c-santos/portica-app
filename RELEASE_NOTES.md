# Pórtica App: v1.0.1

Calculadora estrutural de vigas de concreto armado conforme a **ABNT NBR 6118:2023**,
com entrada manual ou importação de esforços exportados do FTOOL. Gera relatório PDF,
exportação DXF e verificações de ELS. Desenvolvido em Python + Flet, licenciado sob
**Apache-2.0**.

## Correções na v1.0.1

- Corrige o erro `Text(...) Control must be added to the page first` ao carregar
  um projeto quando o painel FTOOL estava recolhido. O fluxo de "Carregar Projeto"
  atualizava os rótulos do painel FTOOL mesmo quando ele não estava montado na
  página. Agora o painel é reconstruído conforme a fonte de entrada do projeto
  **antes** de sincronizar esses rótulos, e a sincronização só ocorre quando o
  painel está visível.

## O que é

O Pórtica App dimensiona e detalha vigas de concreto armado (seção retangular e seção
T), partindo dos esforços que o engenheiro já tem: digitados à mão ou importados dos
arquivos `.txt` exportados pelo FTOOL. É uma ferramenta de apoio ao projeto: os
resultados devem ser verificados por engenheiro civil habilitado, com ART/RRT.

## Funcionalidades principais

- **Flexão**: seção retangular e seção T (mesa colaborante), com verificação dos domínios de deformação.
- **Cisalhamento**: Modelo I da NBR 6118, com contribuição do concreto e do aço.
- **Armadura dupla**: solução com armadura de compressão quando o momento excede o limite do domínio 3.
- **Armadura de pele**: dimensionamento automático das costelas para vigas com `h ≥ 60 cm`.
- **ELS**: flecha (imediata e diferida) e fissuração (`wk1`, `wk2` e mínima), por classe de agressividade.
- **Relatório PDF**: capa, dados de entrada, tabelas, diagramas M(x)/V(x), esquema da seção e campos de ART/CREA.
- **Exportação DXF**: desenho da seção R/T com layers e grampos.
- **Projetos `.ptc`**: salvar e carregar o projeto completo (geometria, materiais, esforços, ajustes).
- **Importação FTOOL**: leitura dos `.txt` exportados (momento fletor, cortante e deformações), detecção das seções críticas, envelope de combinações e dimensionamento automático.

## Como usar

### Entrada manual

1. Na tela inicial, escolha o tipo de seção: **viga retangular** ou **viga T**.
2. Informe a geometria, os materiais (`fck`, `fyk`, classe de agressividade) e o estribo adotado.
3. Preencha as tabelas de trechos de **flexão** (momentos `M`) e de **cisalhamento** (cortantes `V`).
4. Clique em **Calcular** e confira a armadura adotada e os *checks* normativos.
5. Gere o **relatório PDF** e/ou a **exportação DXF**.
6. Use **Salvar Projeto** para gravar o `.ptc` e **Carregar Projeto** para retomá-lo.

### Importação do FTOOL

1. Na tela da viga, clique em **Importar do FTOOL**.
2. Selecione os `.txt` exportados (momento fletor, esforço cortante e deformações). O app valida o formato e mostra a curva importada.
3. A partir dos esforços, o app detecta as **seções críticas**, monta o **envelope de combinações** e executa o **dimensionamento automático** (flexão, cisalhamento, estribos por região e grampos suplementares).
4. Os **diagramas M(x) e V(x)** entram no relatório PDF, junto do detalhamento e da verificação de ELS.

> O app é apenas **compatível com os arquivos** exportados pelo FTOOL. Não há vínculo,
> endosso ou representação oficial do produto. "FTOOL" é citado somente como
> compatibilidade de formato de arquivo.

## Aviso de responsabilidade

> **Aviso.** O Pórtica App é uma ferramenta de apoio ao dimensionamento de vigas
> de concreto armado conforme a ABNT NBR 6118. Os resultados devem ser
> verificados por engenheiro civil habilitado, com ART/RRT, antes de qualquer
> uso em projeto executivo. O software é fornecido "como está", sem garantia de
> adequação a um caso concreto. Os autores não respondem por decisões de projeto
> tomadas com base nas saídas do programa.

O aviso completo está em [`DISCLAIMER.md`](DISCLAIMER.md) e também aparece na tela
**Sobre** do app e no rodapé de cada página do relatório PDF.

## Licença

**Apache-2.0**: o texto completo está em [`LICENSE`](LICENSE), com os avisos de
copyright em [`NOTICE`](NOTICE) e as licenças das bibliotecas de terceiros em
[`THIRD_PARTY.md`](THIRD_PARTY.md).

## Assets (downloads)

Há **duas** formas de baixar o app para Windows 10/11 x64. A diferença é o cliente
gráfico do Flet: na versão **leve** ele é baixado uma única vez no primeiro uso
(~30 MB, do GitHub Releases do Flet); na versão **offline** ele já vem embutido.

| Asset | Descrição | Tamanho | SHA-256 |
|---|---|---|---|
| `portica-v1.0.1-windows-x64.exe` | Executável **leve** (cliente Flet baixado no 1º uso, ~30 MB) | ≈ 58 MB | `5ee20685d26c46aebeb20b017d25f0ac7da01c179fc1d63af15311232ee4fd5c` |
| `portica-v1.0.1-windows-x64.zip` | Pacote **offline** (cliente Flet embutido, roda sem internet desde a 1ª execução) | ≈ 96 MB | `2569694bac2a7450d0848af6ab2dbbb9b49588de53f543a5e96c80705b9bfb74` |

O `.zip` contém `portica.exe` (com o cliente embutido) e um `SHA256SUMS.txt` próprio.

Recomendação: baixe o `.zip` se a máquina de destino estiver **offline** na primeira
execução; caso contrário, o `.exe` leve é menor e se torna offline automaticamente a
partir da segunda execução (o cliente fica em cache em `%USERPROFILE%\.flet\client`).

### Conferir a integridade (PowerShell)

```powershell
Get-FileHash .\portica-v1.0.1-windows-x64.exe -Algorithm SHA256
Get-FileHash .\portica-v1.0.1-windows-x64.zip -Algorithm SHA256
```

Os valores devem coincidir com os da tabela acima e com o arquivo
[`SHA256SUMS.txt`](SHA256SUMS.txt) na raiz do repositório.

## DOI

- **Concept DOI** (todas as versões; use para citar): `10.5281/zenodo.23733497`
- **DOI da versão v1.0.1**: `10.5281/zenodo.23733498`

A referência formal está em [`CITATION.cff`](CITATION.cff).

## Como citar

> Pórtica App: Calculadora estrutural de vigas de concreto armado (NBR 6118:2023).
> Versão 1.0.1. DOI (todas as versões): <https://doi.org/10.5281/zenodo.23733497>.
