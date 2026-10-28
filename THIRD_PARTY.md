# Bibliotecas de Terceiros

O Pórtica App não reempacota nem modifica as bibliotecas listadas abaixo: elas
são instaladas a partir do PyPI conforme [`requirements.txt`](requirements.txt) e
usadas como dependências externas.

Este arquivo foi preenchido **lendo os metadados e os textos de licença dos
pacotes efetivamente instalados** no ambiente de desenvolvimento
(`importlib.metadata.metadata` e os arquivos `LICENSE*` dentro de cada
`*.dist-info` no `site-packages`), e **não** por suposição. A coluna
"Origem da informação" indica exatamente de onde cada licença foi obtida.

> As versões abaixo são as que estavam instaladas e verificadas quando este
> arquivo foi escrito. Ao atualizar dependências, reexecute a verificação e
> atualize a tabela.

## Dependências diretas (`requirements.txt`)

| Dependência | Versão verificada | Licença | Origem da informação |
|---|---|---|---|
| **flet** | 0.85.3 | Apache-2.0 | `flet-0.85.3.dist-info/METADATA` → `License-Expression: Apache-2.0`. O pacote **não** distribui arquivo `LICENSE` no `dist-info`; a licença foi lida do próprio metadado do pacote. |
| **fpdf2** | 2.8.7 | LGPL-3.0-only | `fpdf2-2.8.7.dist-info/METADATA` → `License-Expression: LGPL-3.0-only`, **conferido** no texto `fpdf2-2.8.7.dist-info/licenses/LICENSE` ("GNU LESSER GENERAL PUBLIC LICENSE Version 3"). |
| **svglib** | 2.0.2 | LGPL-3.0-or-later | `svglib-2.0.2.dist-info/METADATA` → `License-Expression: LGPL-3.0-or-later` + `Classifier: GNU Lesser General Public License v3 (LGPLv3)`, **conferido** no texto `svglib-2.0.2.dist-info/licenses/LICENSE.txt` ("GNU LESSER GENERAL PUBLIC LICENSE Version 3"). |
| **reportlab** | 5.0.0 | BSD-3-Clause | `reportlab-5.0.0.dist-info/METADATA` → `License: BSD license (see license.txt for details), Copyright (c) 2000-2025, ReportLab Inc.` + `Classifier: BSD License`, **conferido** no texto `reportlab-5.0.0.dist-info/licenses/LICENSE` (redistribuição com retenção do aviso de copyright e da cláusula de não endosso). |
| **rlPyCairo** | 0.4.0 | BSD-3-Clause (BSD, ReportLab Inc.) | `rlpycairo-0.4.0.dist-info/METADATA` → `License: BSD license, Copyright (c) 2000-2022, ReportLab Inc.` + `Classifier: BSD License`. O pacote **não** distribui arquivo `LICENSE` no `dist-info`; a licença foi lida do próprio metadado. |
| **ezdxf** | 1.4.4 | MIT | `ezdxf-1.4.4.dist-info/licenses/LICENSE` (texto "MIT License", Copyright (c) 2020 Manfred Moitzi) + `METADATA` → `Classifier: MIT License`. |

## Dependências transitivas (instaladas junto com as diretas)

Todas com licença permissive ou copyleft livre, verificadas nos metadados dos
respectivos pacotes instalados:

| Dependência | Versão verificada | Licença | Origem da informação |
|---|---|---|---|
| defusedxml | 0.7.1 | PSFL | `METADATA` → `License: PSFL` + `Classifier: Python Software Foundation License` |
| Pillow | 12.2.0 | MIT-CMU | `METADATA` → `License-Expression: MIT-CMU` + `licenses\LICENSE` |
| fonttools | 4.63.0 | MIT | `METADATA` → `License: MIT` + `licenses\LICENSE` |
| cssselect2 | 0.9.0 | BSD-3-Clause | `METADATA` → `Classifier: BSD License` + `licenses\LICENSE` |
| lxml | 6.1.1 | BSD-3-Clause | `METADATA` → `License: BSD-3-Clause` + `licenses\LICENSE.txt` |
| tinycss2 | 1.5.1 | BSD-3-Clause | `METADATA` → `Classifier: BSD License` + `licenses\LICENSE` |
| charset-normalizer | 3.4.4 | MIT | `METADATA` → `License: MIT` + `licenses\LICENSE` |
| pycairo | 1.29.0 | LGPL-2.1-only OR MPL-1.1 | `METADATA` → `License: LGPL-2.1-only OR MPL-1.1` (licença dual) |
| freetype-py | 2.5.1 | BSD-3-Clause | `METADATA` → `Classifier: BSD License` |
| pyparsing | 3.3.2 | MIT | `METADATA` → `License-Expression: MIT` + `licenses\LICENSE` |
| typing_extensions | 4.15.0 | PSF-2.0 | `METADATA` → `License-Expression: PSF-2.0` + `licenses\LICENSE` |
| numpy | 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | `METADATA` → `License-Expression` (conjunto de licenças, com `licenses\LICENSE.txt` e arquivos de licença por subcomponente) |
| oauthlib | 3.3.1 | BSD-3-Clause | `METADATA` → `License: BSD-3-Clause` + `licenses\LICENSE` |
| httpx | 0.28.1 | BSD-3-Clause | `METADATA` → `License-Expression: BSD-3-Clause` + `Classifier: BSD License` + `licenses\LICENSE.md` |
| httpcore | 1.0.9 | BSD-3-Clause | `METADATA` → `License-Expression: BSD-3-Clause` + `licenses\LICENSE.md` |
| repath | 0.9.0 | MIT | `METADATA` → `License: MIT` + `Classifier: MIT License` |
| msgpack | 1.1.1 | Apache-2.0 | `METADATA` → `License: Apache 2.0` + `licenses\COPYING` |
| certifi | 2026.7.22 | MPL-2.0 | `METADATA` → `Classifier: Mozilla Public License 2.0 (MPL 2.0)` |
| idna | 3.11 | BSD-3-Clause | `METADATA` → `License-Expression: BSD-3-Clause` + `licenses\LICENSE.md` |
| anyio | 4.12.1 | MIT | `METADATA` → `License-Expression: MIT` + `licenses\LICENSE` |
| h11 | 0.16.0 | MIT | `METADATA` → `License: MIT` + `Classifier: MIT License` + `licenses\LICENSE.txt` |

## Compatibilidade com a Apache-2.0

- O projeto é distribuído sob **Apache-2.0**; o núcleo (`core/`) não contém
  código copiado das dependências.
- As bibliotecas **LGPL** usadas aqui (fpdf2, svglib e, de forma opcional,
  pycairo) são consumidas como **bibliotecas externas importadas em tempo de
  execução** (link dinâmico / importação Python), sem modificação nem
  incorporação do código-fonte delas no repositório. Essa é a condição de uso
  da LGPL que mantém a compatibilidade com a Apache-2.0.
- As bibliotecas **MIT / BSD / Apache-2.0 / PSF / MPL-2.0** são compatíveis
  com a Apache-2.0 e exigem apenas a retenção do aviso de copyright — por
  isso o `NOTICE` e este arquivo existem.

## Correção em relação ao planejamento interno

O planejamento interno (fase F3) registrava **svglib** como BSD e **fpdf2**
como "LGPL — uso por link dinâmico". A verificação feita nos pacotes
instalados mostra que:

- **svglib 2.0.2** é **LGPL-3.0-or-later**, não BSD — o texto distribuído em
  `svglib-2.0.2.dist-info/licenses/LICENSE.txt` é a LGPL versão 3;
- **reportlab 5.0.0** e **rlPyCairo 0.4.0** são **BSD** (ReportLab Inc.);
- **fpdf2 2.8.7** é **LGPL-3.0-only**, confirmado pelo texto integral da LGPL
  v3 distribuído no pacote.

Nenhuma dessas licencias é incompatível com a Apache-2.0 no modo de uso
descrito acima.

## Como reverterificar

```powershell
python -c "import importlib.metadata as md; print(md.metadata('flet').get('License-Expression'))"
```

Ou, para ler o texto de licença distribuído no pacote:

```powershell
python -c "import importlib.metadata as md, os; p=md.distribution('fpdf2')._path; print(os.path.join(p,'licenses','LICENSE'))"
```

## Nota sobre o FTOOL

O app apenas **lê** arquivos `.txt` exportados pelo FTOOL. Não há código,
biblioteca ou recurso do FTOOL distribuído neste repositório, nem qualquer
vínculo, endosso ou representação oficial do produto. Ver a decisão D7 do
planejamento interno.

## Design (página pública, `site/`)

A página pública (`site/index.html`) é construída com o design system
**Aipim** e usa seus arquivos **vendored localmente** (sem CDN) em
`site/vendor/aipim/`. Os cabeçalhos de copyright/licença dos arquivos foram
mantidos, e a atribuição aparece no rodapé da página.

| Item | Licença | Origem / uso |
|---|---|---|
| **Aipim** (design system) | Código **MIT**; design e documentação **CC BY 4.0** | <https://github.com/talis-galhardi/aipim> — tokens, componentes e script em `site/vendor/aipim/`. Crédito: "Aipim design system by Talis Galhardi". |
| **Antonio** e **Karla** (fontes) | **SIL Open Font License 1.1** | Fontes variáveis locais em `site/vendor/fonts/` (arquivos `OFL.txt` incluídos). |
| **Hugeicons Free** (ícones) | **MIT** | `site/vendor/aipim/sprite.svg` (Hugeicons Free v4.3.5, Copyright (c) 2025 Hugeicons). |

O tema do Pórtica (`site/theme.css`) sobrescreve apenas os tokens semânticos
de cor primária (`--aipim-action-primary-*`) do Aipim; o CSS do Aipim não é
modificado.
