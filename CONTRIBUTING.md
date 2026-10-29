# Contribuindo com o Pórtica App

Obrigado pelo interesse. Este projeto é mantido por uma pessoa, no tempo
disponível. O guia abaixo existe para que sua contribuição seja-reviewed de
forma rápida e sem atrito.

## Como rodar os testes

Requisitos: Python 3.10 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Rodar a suíte completa:

```powershell
python -m pytest tests -q
```

Rodar um arquivo ou um teste específico:

```powershell
python -m pytest tests\test_relatorio.py -q
python -m pytest tests\test_relatorio.py::test_gerar_pdf -q
```

Antes de abrir um *pull request*, a suíte precisa passar inteira. Não há
serviço de CI configurado no momento; a verificação é local.

## Padrão de commit (*Conventional Commits*)

Cada commit deve ter uma linha de assunto no formato:

```
<tipo>(<escopo>): <descrição curta em imperativo>
```

Tipos aceitos:

| Tipo | Quando usar |
|---|---|
| `fix` | correção de cálculo, de bug ou de texto |
| `feat` | funcionalidade nova |
| `refactor` | reorganização de código sem mudança de comportamento |
| `docs` | documentação |
| `test` | testes |
| `chore` | manutenção, dependências, build, licença |
| `perf` | desempenho |

Exemplos:

```
fix(flexao): corrige armadura minima em secao T com h >= 60 cm
feat(ftool): importa deformacoes do arquivo .txt do FTOOL
docs(readme): atualiza secao de instalacao
```

Escopo opcional entre parênteses, sempre em minúsculas. A descrição fica no
imperativo e sem ponto final.

## O que é bem-vindo

- **Correção de cálculo**, sempre acompanhada de teste de regressão que
  falhe antes da correção e passe depois. É a contribuição mais valiosa.
- Correção de bug de interface, de relatório ou de leitura de arquivo.
- Testes: casos de carregamento, de combinação e de verificação normativa.
- Melhorias de documentação, inclusive a referência à cláusula da norma
  aplicada.
- Correções de português, de acentuação e de diagramação do relatório PDF.

Ao reportar ou corrigir um cálculo, **indique a referência normativa**
(cláusula da NBR 6118, ou item da Emenda) que fundamenta o resultado
esperado.

## O que não será aceito

- **Mudanças de licenciamento** (chave de API, ativação, HWID, backends de
  licença, telemetria de ativação). O projeto é e permanece Apache-2.0, sem
  infraestrutura de licenciamento (decisão D4 do planejamento interno).
- **Paywall, features bloqueadas, remoção de features existentes** ou
  qualquer mecanismo que condicione o uso do software a pagamento, cadastro ou
  chave.
- **Refatoração de interface sem issue prévia**. Discuta primeiro em uma
  *issue*. Mudanças grandes de UI são caras de revisar para um maintainer
  único e tends a conflitar.
- Mudanças no motor de cálculo (`core/calculos`) sem teste de regressão.
- Dependências novas sem necessidade clara e sem atualização do `THIRD_PARTY.md`.
- Commits com segredos, credenciais, dados de cliente ou arquivos gerados
  (PDF/DXF) versionados.

## Como abrir uma *issue*

Use o repositório: <https://github.com/samuel-c-santos/portica-app/issues>.

Inclua, sempre que possível:

1. versão do app (visível na tela **Sobre**);
2. dados de entrada usados;
3. saída obtida pelo programa;
4. valor esperado e a referência normativa;
5. passos para reproduzir.

Para falhas de cálculo, o procedimento está detalhado em
[`SECURITY.md`](SECURITY.md).

## Código de conduta

Não há um código de conduta formal. Treatamento basicamente decente com os
demais é o mínimo esperado: nada de assédio, Discriminação ou ataques
pessoais.

## Licença das contribuições

Ao enviar um *pull request*, você concorda em licenciá-lo sob a
**Apache-2.0**, a mesma licença do projeto.
