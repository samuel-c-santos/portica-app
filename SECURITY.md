# Segurança e Relato de Problemas

Este projeto trata **correções de cálculo** como o tipo de problema mais
relevante. Erro de cálculo em ferramenta de engenharia estrutural pode
conduzir a um projeto executivo inseguro, e por isso o relato é tratado com
prioridade.

## Reportar uma falha de cálculo

Abra uma *issue* em
<https://github.com/samuel-c-santos/portica-app/issues> com o rótulo
`cálculo` (ou `bug` se não houver rótulo adequado).

Inclua **obrigatoriamente**:

| Item | O que informar |
|---|---|
| **Versão** | número exibido na tela **Sobre** (e, se disponível, a data do build) |
| **Dados de entrada** | geometria (`h`, `bw`, `bf`, `hf`), materiais (`fck`, `fyk`, classe de agressividade), estribo adotado e o tipo de seção (retangular ou T) |
| **Esforços** | tabela de trechos de flexão (`M`) e de cisalhamento (`V`) exatamente como preenchida; no caso de importação FTOOL, os arquivos `.txt` usados ou os pontos exportados |
| **Ajustes** | bitola mínima forçada, barras extras, sobrescrita de `h` ou `fck`: se algum tiver sido usado |
| **Saída obtida** | o que o programa exibiu (armadura adotada, estribos, flechas, fissuras, `checks` e o alerta exato) |
| **Valor esperado** | o resultado que você considera correto |
| **Referência normativa** | cláusula da **ABNT NBR 6118:2023** (e Emenda, se aplicável) que fundamenta o valor esperado, ou o cálculo manual de referência |
| **Arquivo `.ptc`** | opcional, mas acelera muito a reprodução (use **Salvar Projeto**) |

Exemplo de estrutura de relato:

```
Versão: 1.0.0
Seção: retangular, h = 60 cm, bw = 20 cm, fck = 30 MPa, fyk = 500 MPa
Estribo: 5 mm
M (trecho 1): 120 kN.m
V (trecho 1): 80 kN
Saída obtida: As,req = 12,3 cm² (phi 20, 4 barras)
Valor esperado: 14,8 cm²
Referência: NBR 6118:2023, item 6.3.2.2 (As,min = 0,10% Ac)
```

## O que fazer depois

1. O relato é triado e reproduzido em ambiente controlado.
2. Se confirmado, entra um *pull request* com a correção e um **teste de
   regressão** que falharia antes da correção.
3. A correção e o teste entram na mesma versão; nada é corrigido "por fora".

## O que **não** é uma falha de cálculo

- Divergência de arredondamento entre a saída do programa e o seu cálculo
  manual dentro da precisão da norma (a diferença deve ser da ordem do
  arredondamento da bitola adotada).
- Resultado que muda ao trocar a bitola adotada, sem que isso contradiga a
  norma: o programa dimensiona e depois **adota** a armadura que cabe.
- Diferença de arredondamento na flexão de seção T em que as mesas
  colaborantes dependem da largura efetiva. Nesse caso, reporte a premissa
  usada (o programa exibe `bf_efet`).

## Vulnerabilidades de segurança

Falhas de segurança (execução de código arbitrário, exposição de dados,
injeção) devem ser reportadas **privadamente**, sem abrir *issue* pública
até que exista uma correção. Use a seção **Security** do repositório no
GitHub, ou o canal privado indicado no
[perfil do autor](https://github.com/samuel-c-santos).

Este software **não** coleta dados, não usa telemetria e não faz chamadas de
rede em tempo de execução. Ainda assim, o trato é o mesmo: sem *issue*
pública antes da correção.

## Limites do que o software garante

O Pórtica App é uma ferramenta de apoio. Ver
[`DISCLAIMER.md`](DISCLAIMER.md) para o aviso completo de responsabilidade
técnica.
