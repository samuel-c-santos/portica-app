# DOI (Zenodo) — Passo a passo do arquivamento

> Objetivo: gerar o DOI do Pórtica App no Zenodo e devolvê-lo para o repositório.
> O DOI é **versionado**: cada release gera um DOI novo; o **concept DOI**
> permanece estável e é o que se cita no Lattes e no `CITATION.cff`.

## Pré-requisitos

- Conta no GitHub (autor do repositório).
- Release `v1.0.0` publicada no GitHub (já feita).

## 1. Criar a conta no Zenodo

1. Acesse <https://zenodo.org>.
2. Clique em **Sign up** e escolha **Sign up with GitHub** (OAuth). Autorize o app.
   Isso cria a conta e já vincula o GitHub.

## 2. Conectar o repositório

1. No Zenodo, abra **Settings → GitHub** (<https://zenodo.org/account/settings/github/>).
2. Clique em **Connect** se ainda não estiver conectado (autoriza o app "Zenodo" no GitHub).
3. Na lista de repositórios, encontre `samuel-c-santos/portica-app` e ligue o
   toggle para **On**. O Zenodo instala um webhook no repositório.

## 3. Disparar o arquivamento (release)

- Com o repositório ligado, o Zenodo arquiva automaticamente cada release criada
  no GitHub.
- A release `v1.0.0` já existe: ao ligar o toggle, o Zenodo faz o *sync*; se não
  arquivar, crie uma nova release (ou edite e republique a existente) para
  disparar o webhook.
  - Alternativa manual: em **Uploads → New upload**, carregue o tarball
    `Source code (zip)` da release e preencha os metadados à mão.

## 4. Conferir e copiar o DOI

1. Em **My uploads**, abra o registro do Pórtica App.
2. Confira os metadados: título, autores, licença (**Apache-2.0**), data (**2026**)
   e a referência ao repositório GitHub.
3. Copie o **DOI** (formato `10.5281/zenodo.1234567`).
4. Copie também o **concept DOI** (o DOI "geral", que não muda entre versões) —
   é ele que vai no Lattes e no `CITATION.cff`.
5. Copie o **badge** (Markdown/HTML) para o README e a página.

## 5. Devolver o DOI para o repositório

Substitua o placeholder `10.5281/zenodo.XXXXXXX` pelo DOI real em:

- `CITATION.cff` (campo `doi`, no topo e em `preferred-citation`)
- `README.md` (badge e seção "Como citar")
- `site/index.html` (seção "Como citar")
- `site/divulgacao.md` (link do DOI)
- `docs/LATTES.md` (campo DOI)

## Nova versão (reaproveitar)

- Crie uma nova release no GitHub. O Zenodo arquiva automaticamente e gera um
  **novo DOI** para a versão, mantendo o **concept DOI** intacto.
- Atualize `CITATION.cff` (versão e `date-released`). O **concept DOI** não muda.
