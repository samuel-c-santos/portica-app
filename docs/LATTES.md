# Lattes — Como declarar o Pórtica App

> Guia para registrar o software no **Currículo Lattes** (CNPq) e no **ORCID**.
> O DOI (concept DOI — "todas as versões") já está preenchido: `10.5281/zenodo.23733497`;
> o resto é copiar e colar.

## 1. Dados prontos para preencher

Tela do Lattes: **Produção técnica → Software** (aba "Outra produção técnica").

| Campo | Valor |
|---|---|
| Tipo | Produção técnica → Software |
| Título | Pórtica App — Calculadora estrutural de vigas de concreto armado (NBR 6118:2023) |
| Ano | 2026 |
| Finalidade | Ferramenta de cálculo e detalhamento de vigas de concreto armado, com entrada manual e importação de esforços exportados do FTOOL |
| Disponibilidade | Irrestrita (código aberto) |
| URL | https://github.com/samuel-c-santos/portica-app |
| DOI | `10.5281/zenodo.23733497` |
| Linguagem | Python |
| Licença | Apache-2.0 |

> Campos opcionais do formulário (preencher se pedir): **País** = Brasil;
> **Idioma** = Português; **Meio de divulgação** = Vários / Digital;
> **Plataforma** = Windows.

## 2. Resumo (campo "Resumo" da produção)

> O Pórtica App é uma calculadora estrutural de vigas de concreto armado
> conforme a ABNT NBR 6118:2023. A partir dos esforços digitados ou importados
> do FTOOL, dimensiona e detalha flexão, cisalhamento, armadura dupla, armadura
> de pele e ELS, com relatório PDF e exportação DXF. Software livre (Apache-2.0),
> em substituição a ferramentas comerciais pagas no uso acadêmico.

## 3. Versão curta para o currículo Lattes

> SANTOS, Samuel da Costa dos. **Pórtica App: calculadora estrutural de vigas de
> concreto armado (NBR 6118:2023)**. Versão 1.0.1 [software]. Zenodo, 2026.
> DOI: `10.5281/zenodo.23733497`.

Use esta linha na listagem resumida de produções do currículo.

## 4. Como anexar a publicação (evidência)

O Lattes não anexa arquivos no registro de software; a evidência fica nos links.
Faça assim:

1. No campo **URL/Homepage**, cole o DOI resolvível
   `https://doi.org/10.5281/zenodo.23733497` (ou o link do repositório).
2. Em **Informações adicionais**, cole a "versão curta" da seção 3.
3. Guarde para o seu arquivo (e para anexar a editais/institucional, se pedirem):
   - **print da página do DOI** no Zenodo (mostra título, autores, licença e DOI);
   - **PDF da release** no GitHub (página da release → imprimir em PDF) ou o
     relatório PDF gerado pelo próprio app (**Relatório PDF**).

## 5. Observação de impacto

O Pórtica App substitui, no uso acadêmico (disciplinas de concreto armado, TCC,
pesquisa e extensão), um **produto comercial pago** de dimensionamento e
detalhamento de vigas. Isso é relevante no Lattes porque evidencia transferência
e impacto: um software aberto, gratuito e citável no lugar de uma ferramenta paga.

## 6. Como declarar no ORCID

Se você tem ORCID, adicione o software à lista de trabalhos:

1. Em <https://orcid.org>, abra **Works → Add work → Add DOI**.
2. Cole o DOI (`10.5281/zenodo.23733497`). O ORCID puxa os metadados
   automaticamente via DataCite e cria a entrada "Software".
3. Confira autores, ano, licença e o link e salve.

Isso mantém o crédito consistente entre Lattes e ORCID.
