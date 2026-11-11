"""Automação de release do Pórtica App.

A versão vive em um único lugar, `core/version.py` (APP_VERSION), mas reaparece
em outros arquivos do repositório. Este script mantém tudo em sincronia:

    --check        valida a consistência dos 5 lugares + SHA256SUMS.txt;
                   sai com código 1 e lista as divergências. Avisos (ex.:
                   assets ausentes em dist/) não falham o comando, para
                   permitir o uso em CI e em clone fresco.
    --bump X.Y.Z   avança a versão nos 5 lugares de uma vez; exige semver
                   estritamente maior que a versão atual; atualiza também a
                   `date-released` do CITATION.cff (--date, padrão: hoje).
                   O corpo editorial do RELEASE_NOTES.md não é reescrito:
                   o --check cobra as menções que sobraram.
    --sums         regenera SHA256SUMS.txt a partir de dist/ e atualiza os
                   hashes da tabela de assets em RELEASE_NOTES.md.
    --verify-sums  confere cada linha de SHA256SUMS.txt contra dist/.

Arquivos manipulados:

    core/version.py      fonte única: APP_VERSION = "X.Y.Z"
    CITATION.cff         version: e date-released: (raiz e preferred-citation)
    RELEASE_NOTES.md     H1 "# Pórtica App: vX.Y.Z" (corpo é editorial)
    docs/CHANGELOG.md    nova seção [X.Y.Z], link-refs e [Não publicado]
    site/index.html      URLs de download e citação (versão X.Y.Z)
    SHA256SUMS.txt       hashes "<sha256>  <nome>" dos assets de dist/

Fluxo de release:

    1. python build/release.py --bump 1.0.2
    2. editar RELEASE_NOTES.md e a seção do CHANGELOG (checklist impresso)
    3. python build/build_portica.py
    4. python build/release.py --sums
    5. python build/release.py --check   # deve passar limpo
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path
from typing import NoReturn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "core" / "version.py"
CITATION_FILE = PROJECT_ROOT / "CITATION.cff"
NOTES_FILE = PROJECT_ROOT / "RELEASE_NOTES.md"
CHANGELOG_FILE = PROJECT_ROOT / "docs" / "CHANGELOG.md"
SITE_FILE = PROJECT_ROOT / "site" / "index.html"
DIST_DIR = PROJECT_ROOT / "dist"
SUMS_FILE = PROJECT_ROOT / "SHA256SUMS.txt"

REPO_URL = "https://github.com/samuel-c-santos/portica-app"
# Texto padrão da seção [Não publicado] do docs/CHANGELOG.md.
PLACEHOLDER_NAO_PUBLICADO = "Mudanças aceitas e ainda não publicadas em uma versão."
# Título provisório que o --bump grava na nova seção do CHANGELOG; o --check
# recusa qualquer seção de versão publicada que ainda o carregue.
TITULO_PENDENTE = "resumo pendente"
SEMVER = r"\d+\.\d+\.\d+"

# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------


def ler(path: Path) -> str:
    """Lê o arquivo preservando EOLs originais (repo tem LF e CRLF mistos)."""
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            return fh.read()
    except OSError as e:
        die(f"não consegui ler {path}: {e}")


def gravar(path: Path, texto: str) -> None:
    """Grava sem traduzir EOLs (newline='' escreve exatamente o que vem)."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(texto)


def sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def die(msg: str) -> NoReturn:
    print(f"[ERRO] {msg}", file=sys.stderr)
    raise SystemExit(1)


def parse_semver(texto: str) -> tuple[int, int, int]:
    partes = texto.split(".")
    return int(partes[0]), int(partes[1]), int(partes[2])


def ler_versao_app() -> str:
    texto = ler(VERSION_FILE)
    m = re.search(rf'^APP_VERSION = "({SEMVER})"\s*$', texto, re.M)
    if not m:
        die(f"{VERSION_FILE.name}: não encontrei 'APP_VERSION = \"X.Y.Z\"'")
    return m.group(1)


def nomes_assets(versao: str) -> list[str]:
    """Nomes canônicos dos assets de release, na ordem exe, zip."""
    return [f"portica-v{versao}-windows-x64.{ext}" for ext in ("exe", "zip")]


def urls_assets(versao: str) -> list[str]:
    """URLs completas de download dos assets na tag imutável vX.Y.Z."""
    return [f"{REPO_URL}/releases/download/v{versao}/{nome}" for nome in nomes_assets(versao)]


def versoes_no_texto(texto: str) -> list[tuple[int, str]]:
    """Todas as menções `v?X.Y.Z` do texto como (linha 1-based, versão)."""
    achados: list[tuple[int, str]] = []
    for m in re.finditer(rf"\bv?({SEMVER})\b", texto):
        if not m.group(0).startswith("v") and re.fullmatch(r"\d{1,3}\.\d{3}\.\d{3}", m.group(1)):
            continue
        linha = texto.count("\n", 0, m.start()) + 1
        achados.append((linha, m.group(1)))
    return achados


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------


class Relatorio:
    """Coleta divergências (falham o --check) e avisos (não falham)."""

    def __init__(self) -> None:
        self.divergencias: list[str] = []
        self.avisos: list[str] = []

    def diverge(self, msg: str) -> None:
        self.divergencias.append(msg)

    def avisa(self, msg: str) -> None:
        self.avisos.append(msg)


def check_citation(rep: Relatorio, v: str) -> None:
    texto = ler(CITATION_FILE)
    # `^\s*`: o bloco preferred-citation vem indentado no arquivo.
    vers = re.findall(rf'^\s*version: "({SEMVER})"\s*$', texto, re.M)
    if len(vers) != 2:
        rep.diverge(
            f"CITATION.cff: esperadas 2 ocorrências de `version:` "
            f"(raiz e preferred-citation), achei {len(vers)}"
        )
    for i, va in enumerate(vers, 1):
        if va != v:
            rep.diverge(f"CITATION.cff: ocorrência {i} de `version:` é {va}, esperado {v}")

    datas = re.findall(r'^\s*date-released: "(\d{4}-\d{2}-\d{2})"\s*$', texto, re.M)
    if len(datas) != 2:
        rep.diverge(
            f"CITATION.cff: esperadas 2 ocorrências de `date-released:`, achei {len(datas)}"
        )
    elif len(set(datas)) != 1:
        rep.diverge(f"CITATION.cff: `date-released` divergentes entre si: {datas}")
    else:
        try:
            date.fromisoformat(datas[0])
        except ValueError:
            rep.diverge(f"CITATION.cff: data inválida: {datas[0]}")


def check_notes(rep: Relatorio, v: str) -> None:
    texto = ler(NOTES_FILE)
    m = re.search(rf"^# Pórtica App: v({SEMVER})\s*$", texto, re.M)
    if not m:
        rep.diverge("RELEASE_NOTES.md: título H1 '# Pórtica App: vX.Y.Z' não encontrado")
        h1_linha = -1
    else:
        h1_linha = 1
        if m.group(1) != v:
            rep.diverge(f"RELEASE_NOTES.md: H1 anuncia v{m.group(1)}, version.py diz v{v}")

    outras = [(ln, frag) for ln, frag in versoes_no_texto(texto) if frag != v]
    if h1_linha == 1:
        outras = [(ln, frag) for ln, frag in outras if ln != h1_linha]
    if outras:
        detalhe = "; ".join(f"linha {ln}: {frag}" for ln, frag in outras[:8])
        sufixo = " ..." if len(outras) > 8 else ""
        rep.diverge(
            f"RELEASE_NOTES.md: {len(outras)} menção(ões) de versão diferente de "
            f"v{v} no corpo: {detalhe}{sufixo}"
        )

    check_tabela_assets(rep, v, texto)


def check_tabela_assets(rep: Relatorio, v: str, texto_notes: str) -> None:
    """Conferencia dos hashes da tabela de assets do RELEASE_NOTES.md."""
    for nome in nomes_assets(v):
        m = re.search(rf"^\|[^\n]*`{re.escape(nome)}`[^\n]*$", texto_notes, re.M)
        if not m:
            rep.avisa(f"RELEASE_NOTES.md: tabela de assets sem linha para '{nome}'")
            continue
        hashes_linha = re.findall(r"`([0-9a-fA-F]{64})`", m.group())
        if not hashes_linha:
            rep.avisa(f"RELEASE_NOTES.md: linha de '{nome}' sem hash SHA-256")
            continue
        f = DIST_DIR / nome
        if not f.is_file():
            rep.avisa(f"RELEASE_NOTES.md: hash de '{nome}' não conferido (asset ausente em dist/)")
            continue
        real = sha256_arquivo(f)
        if real not in hashes_linha:
            rep.diverge(f"RELEASE_NOTES.md: hash da tabela para '{nome}' diverge do asset em dist/")


def check_changelog(rep: Relatorio, v: str) -> None:
    texto = ler(CHANGELOG_FILE)
    linhas = texto.split("\n")

    heads = [m.group(1) for ln in linhas if (m := re.match(rf"^## \[({SEMVER})\]", ln))]
    if not heads:
        rep.diverge("docs/CHANGELOG.md: nenhuma seção '## [X.Y.Z]' encontrada")
    else:
        if len(set(heads)) != len(heads):
            rep.diverge(f"docs/CHANGELOG.md: seções de versão duplicadas: {heads}")
        ultimo = heads[0]
        if ultimo != v:
            rep.diverge(f"docs/CHANGELOG.md: seção mais recente é [{ultimo}], version.py diz [{v}]")
        m_tit = re.search(rf"^## \[{re.escape(ultimo)}\]:\s*([^\n]*)", texto, re.M)
        titulo = (m_tit.group(1) if m_tit else "").strip()
        if TITULO_PENDENTE in titulo.lower():
            rep.diverge(
                f"docs/CHANGELOG.md: título da seção [{ultimo}] ainda é placeholder "
                f"('{TITULO_PENDENTE}')"
            )

    refs = dict(re.findall(r"^\[([^\]\n]+)\]:\s*(\S+)", texto, re.M))
    if "Não publicado" not in refs:
        rep.diverge("docs/CHANGELOG.md: link-ref '[Não publicado]: ...' ausente")
    elif not refs["Não publicado"].endswith(f"/compare/v{v}...HEAD"):
        rep.diverge(
            f"docs/CHANGELOG.md: link-ref '[Não publicado]' deveria terminar em "
            f"/compare/v{v}...HEAD (hoje: {refs['Não publicado']})"
        )
    for h in heads:
        if h not in refs:
            rep.diverge(f"docs/CHANGELOG.md: sem link-ref para [{h}]")
    for rotulo in refs:
        if re.fullmatch(SEMVER, rotulo) and rotulo not in heads:
            rep.diverge(f"docs/CHANGELOG.md: link-ref [{rotulo}] não tem seção correspondente")

    check_nao_publicado(rep, linhas)


def check_nao_publicado(rep: Relatorio, linhas: list[str]) -> None:
    idx = next((i for i, ln in enumerate(linhas) if ln.startswith("## [Não publicado]")), None)
    if idx is None:
        rep.diverge("docs/CHANGELOG.md: seção '## [Não publicado]' não encontrada")
        return
    fim = next(
        (j for j in range(idx + 1, len(linhas)) if linhas[j].startswith("## ")),
        len(linhas),
    )
    corpo = "\n".join(linhas[idx + 1 : fim]).strip()
    if corpo != PLACEHOLDER_NAO_PUBLICADO:
        rep.diverge(
            "docs/CHANGELOG.md: há conteúdo sob '[Não publicado]' ainda não "
            "reconciliado com uma versão (rode --bump X.Y.Z)"
        )


def check_site(rep: Relatorio, v: str) -> None:
    texto = ler(SITE_FILE)
    if "releases/latest/download/portica-v" in texto:
        rep.diverge(
            "site/index.html: proibido usar 'releases/latest/download/portica-v' "
            "(quebra no próximo release; use '/releases/download/vX.Y.Z/...')"
        )
    for url in urls_assets(v):
        if url not in texto:
            rep.diverge(f"site/index.html: URL do asset '{url}' não encontrada")
    citacao = f"(versão {v})"
    if citacao not in texto:
        rep.diverge(f"site/index.html: citação '{citacao}' não encontrada")
    outras = sorted({frag for _, frag in versoes_no_texto(texto) if frag != v})
    if outras:
        rep.diverge(f"site/index.html: menções de versão diferente de v{v}: {', '.join(outras)}")


def check_sums(rep: Relatorio, v: str) -> None:
    texto = ler(SUMS_FILE)
    entradas: list[tuple[str, str]] = []
    for ln in texto.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.fullmatch(r"([0-9a-f]{64})\s{2}(.+)", ln)
        if not m:
            rep.diverge(f"SHA256SUMS.txt: linha fora do formato '<sha256>  <nome>': {ln!r}")
            continue
        entradas.append((m.group(2).strip(), m.group(1)))

    esperados = set(nomes_assets(v))
    nomes = {nome for nome, _ in entradas}
    if nomes != esperados:
        faltando = sorted(esperados - nomes)
        sobrando = sorted(nomes - esperados)
        rep.diverge(
            f"SHA256SUMS.txt: nomes divergem da versão v{v} "
            f"(faltando: {faltando}; sobrando: {sobrando}) — gere com --sums"
        )

    for nome, hash_declarado in entradas:
        if nome not in esperados:
            continue
        f = DIST_DIR / nome
        if not f.is_file():
            rep.avisa(f"SHA256SUMS.txt: '{nome}' não está em dist/ (hash não conferido)")
            continue
        real = sha256_arquivo(f)
        if real != hash_declarado:
            rep.diverge(f"SHA256SUMS.txt: hash de '{nome}' diverge do arquivo em dist/")


def cmd_check(args: argparse.Namespace) -> int:
    v = ler_versao_app()
    rep = Relatorio()
    check_citation(rep, v)
    check_notes(rep, v)
    check_changelog(rep, v)
    check_site(rep, v)
    check_sums(rep, v)

    print(f"version.py: v{v}")
    if rep.divergencias:
        print(f"[ERRO] {len(rep.divergencias)} divergência(s) contra a versão v{v}:")
        for d in rep.divergencias:
            print(f"  - {d}")
        if rep.avisos:
            print(f"[AVISO] {len(rep.avisos)} aviso(s):")
            for a in rep.avisos:
                print(f"  - {a}")
        return 1
    for a in rep.avisos:
        print(f"[AVISO] {a}")
    print(f"[OK] release consistente na versão v{v}.")
    return 0


# ---------------------------------------------------------------------------
# --bump
# ---------------------------------------------------------------------------


def bump_version_file(velho: str, novo: str) -> str:
    texto = ler(VERSION_FILE)
    alvo = f'APP_VERSION = "{velho}"'
    if texto.count(alvo) != 1:
        die(f"core/version.py: esperava 1 ocorrência de {alvo!r}, achei {texto.count(alvo)}")
    return texto.replace(alvo, f'APP_VERSION = "{novo}"')


def bump_citation(velho: str, novo: str, data_release: str) -> str:
    texto = ler(CITATION_FILE)
    alvo_vers = f'version: "{velho}"'
    n_vers = texto.count(alvo_vers)
    if n_vers != 2:
        die(f"CITATION.cff: esperava 2 ocorrências de {alvo_vers!r}, achei {n_vers}")
    datas = re.findall(r'^\s*date-released: "(\d{4}-\d{2}-\d{2})"', texto, re.M)
    if len(set(datas)) != 1:
        die(f"CITATION.cff: date-released divergentes entre si ({datas}); corrija à mão")
    alvo_data = f'date-released: "{datas[0]}"'
    n_data = texto.count(alvo_data)
    if n_data != 2:
        die(f"CITATION.cff: esperava 2 ocorrências de {alvo_data!r}, achei {n_data}")
    return texto.replace(alvo_vers, f'version: "{novo}"').replace(
        alvo_data, f'date-released: "{data_release}"'
    )


def bump_notes_h1(velho: str, novo: str) -> str:
    texto = ler(NOTES_FILE)
    alvo = f"# Pórtica App: v{velho}"
    if texto.count(alvo) != 1:
        die(f"RELEASE_NOTES.md: esperava 1 ocorrência de {alvo!r}, achei {texto.count(alvo)}")
    return texto.replace(alvo, f"# Pórtica App: v{novo}")


def bump_changelog(velho: str, novo: str) -> str:
    texto = ler(CHANGELOG_FILE)
    linhas = texto.split("\n")

    heads = [m.group(1) for ln in linhas if (m := re.match(rf"^## \[({SEMVER})\]", ln))]
    if not heads:
        die("docs/CHANGELOG.md: nenhuma seção '## [X.Y.Z]' encontrada; corrija à mão")
    if heads[0] != velho:
        die(
            f"docs/CHANGELOG.md: seção mais recente é [{heads[0]}], mas version.py "
            f"diz {velho}; reconcilie à mão antes do bump"
        )

    idx_np = next((i for i, ln in enumerate(linhas) if ln.startswith("## [Não publicado]")), None)
    if idx_np is None:
        die("docs/CHANGELOG.md: seção '## [Não publicado]' não encontrada")
    fim_np = next(
        (j for j in range(idx_np + 1, len(linhas)) if re.match(rf"^## \[({SEMVER})\]", linhas[j])),
        None,
    )
    if fim_np is None:
        die("docs/CHANGELOG.md: nenhuma seção de versão após '[Não publicado]'")

    # Reconciliação: o que estava sob [Não publicado] vira corpo da nova seção.
    corpo_np = "\n".join(linhas[idx_np + 1 : fim_np]).strip()
    entradas = corpo_np if corpo_np != PLACEHOLDER_NAO_PUBLICADO else ""
    nova_secao = [f"## [{novo}]: {TITULO_PENDENTE}", ""]
    if entradas:
        nova_secao.extend(entradas.split("\n"))
        nova_secao.append("")
    else:
        nova_secao.append(
            "(Preencha antes de publicar: subseções Adicionado/Alterado/Corrigido/"
            "Removido/Security e o título da seção.)"
        )
        nova_secao.append("")

    # Reseta [Não publicado] para o placeholder padrão.
    linhas[idx_np + 1 : fim_np] = ["", PLACEHOLDER_NAO_PUBLICADO, ""]

    # Insere a nova seção imediatamente antes da seção de versão mais recente.
    linhas[fim_np:fim_np] = nova_secao

    # Link-refs: atualiza [Não publicado] e acrescenta [novo] acima de [velho].
    idx_ref_np = next((i for i, ln in enumerate(linhas) if ln.startswith("[Não publicado]:")), None)
    if idx_ref_np is None:
        die("docs/CHANGELOG.md: link-ref '[Não publicado]: ...' ausente")
    linhas[idx_ref_np] = f"[Não publicado]: {REPO_URL}/compare/v{novo}...HEAD"
    linhas.insert(idx_ref_np + 1, f"[{novo}]: {REPO_URL}/releases/tag/v{novo}")

    return "\n".join(linhas)


def bump_site(velho: str, novo: str) -> str:
    texto = ler(SITE_FILE)
    for url_velha in urls_assets(velho):
        n_url = texto.count(url_velha)
        if n_url < 1:
            die(
                f"site/index.html: esperava pelo menos 1 ocorrência de {url_velha!r}, achei {n_url}"
            )
    alvo_cit = f"(versão {velho})"
    n_cit = texto.count(alvo_cit)
    if n_cit < 1:
        die(f"site/index.html: esperava pelo menos 1 ocorrência de {alvo_cit!r}, achei {n_cit}")
    texto = re.sub(rf"\bv{re.escape(velho)}\b", f"v{novo}", texto)
    texto = re.sub(rf"\b{re.escape(velho)}\b", novo, texto)
    return texto


def cmd_bump(args: argparse.Namespace) -> int:
    velho = ler_versao_app()
    novo = args.bump.lstrip("v")
    if not re.fullmatch(SEMVER, novo):
        die(f"--bump exige X.Y.Z (semver), recebi {args.bump!r}")
    if parse_semver(novo) <= parse_semver(velho):
        die(f"a versão nova ({novo}) precisa ser estritamente maior que a atual ({velho})")
    data_release = args.date or date.today().isoformat()
    try:
        date.fromisoformat(data_release)
    except ValueError:
        die(f"--date inválida: {data_release!r} (use AAAA-MM-DD)")

    # Todas as edições são calculadas ANTES de gravar: se qualquer padrão
    # divergir do esperado, nada é escrito (o estado continua consistente).
    edicoes: list[tuple[Path, str]] = [
        (VERSION_FILE, bump_version_file(velho, novo)),
        (CITATION_FILE, bump_citation(velho, novo, data_release)),
        (NOTES_FILE, bump_notes_h1(velho, novo)),
        (CHANGELOG_FILE, bump_changelog(velho, novo)),
        (SITE_FILE, bump_site(velho, novo)),
    ]
    for path, texto in edicoes:
        gravar(path, texto)

    print(f"[OK] bump v{velho} -> v{novo} aplicado em 5 arquivos:")
    for path, _ in edicoes:
        print(f"   - {path.relative_to(PROJECT_ROOT)}")
    print()
    print("Checklist até o próximo --check passar limpo:")
    print(
        f"  1. docs/CHANGELOG.md: renomeie a seção '## [{novo}]: {TITULO_PENDENTE}'"
        " e preencha as subseções."
    )
    print(
        "  2. RELEASE_NOTES.md: o H1 já foi atualizado; reescreva o corpo que ainda"
        f" menciona v{velho} (título de seção, tabela de assets, Get-FileHash,"
        " DOI da versão, citação)."
    )
    print(
        f"  3. Build dos assets: python build/build_portica.py"
        f"  (gera dist/portica-v{novo}-windows-x64.exe/.zip)"
    )
    print(
        "  4. python build/release.py --sums"
        "  (regenera SHA256SUMS.txt e os hashes da tabela de assets)"
    )
    print(f"  5. CITATION.cff: date-released definida como {data_release}.")
    print("  6. Zenodo: nova versão publicada -> atualize o 'DOI da versão' nas notas.")
    print("  7. python build/release.py --check  # deve passar limpo")
    print("  8. Revise com git diff e commite.")
    return 0


# ---------------------------------------------------------------------------
# --sums e --verify-sums
# ---------------------------------------------------------------------------


def cmd_sums(args: argparse.Namespace) -> int:
    v = ler_versao_app()
    caminhos = [(nome, DIST_DIR / nome) for nome in nomes_assets(v)]
    faltando = [nome for nome, p in caminhos if not p.is_file()]
    if faltando:
        die(f"assets ausentes em dist/: {faltando}; rode python build/build_portica.py antes")

    digests = {nome: sha256_arquivo(p) for nome, p in caminhos}
    gravar(SUMS_FILE, "".join(f"{digests[nome]}  {nome}\n" for nome, _ in caminhos))
    print(f"[OK] {SUMS_FILE.name} regenerado (versão v{v}):")
    for nome, _ in caminhos:
        print(f"   {digests[nome]}  {nome}")

    # Atualiza a tabela de assets do RELEASE_NOTES.md (linhas já renomeadas
    # para a versão nova; se ainda citarem a versão velha, o --check cobra).
    texto = ler(NOTES_FILE)
    mudados: list[str] = []
    for nome, dig in digests.items():
        m = re.search(rf"^\|[^\n]*`{re.escape(nome)}`[^\n]*$", texto, re.M)
        if not m:
            print(f"[AVISO] RELEASE_NOTES.md: tabela sem linha para '{nome}' (hash não atualizado)")
            continue
        linha_nova, n = re.subn(r"`[0-9a-fA-F]{64}`", f"`{dig}`", m.group(), count=1)
        if n != 1:
            print(f"[AVISO] RELEASE_NOTES.md: linha de '{nome}' sem hash (não atualizado)")
            continue
        if linha_nova != m.group():
            texto = texto[: m.start()] + linha_nova + texto[m.end() :]
            mudados.append(nome)
    if mudados:
        gravar(NOTES_FILE, texto)
        print(f"[OK] RELEASE_NOTES.md: hashes atualizados para: {', '.join(mudados)}")
    print("Conferência: python build/release.py --verify-sums")
    return 0


def cmd_verify_sums(args: argparse.Namespace) -> int:
    del args  # consistência de assinatura com os outros comandos
    texto = ler(SUMS_FILE)
    entradas: list[tuple[str, str]] = []
    for ln in texto.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = re.fullmatch(r"([0-9a-f]{64})\s{2}(.+)", ln)
        if not m:
            die(f"SHA256SUMS.txt: linha fora do formato '<sha256>  <nome>': {ln!r}")
        entradas.append((m.group(2).strip(), m.group(1)))
    if not entradas:
        die(f"{SUMS_FILE.name} está vazio; gere com --sums")

    falha = False
    for nome, hash_declarado in entradas:
        f = DIST_DIR / nome
        if not f.is_file():
            print(f"[ERRO] {nome}: não existe em dist/")
            falha = True
            continue
        real = sha256_arquivo(f)
        if real == hash_declarado:
            print(f"[OK]   {nome}")
        else:
            print(f"[ERRO] {nome}: hash diverge (SUMS: {hash_declarado}; dist: {real})")
            falha = True
    return 1 if falha else 0


# ---------------------------------------------------------------------------


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:  # pragma: no cover - stderr/out sem reconfigure
            pass

    parser = argparse.ArgumentParser(
        description="Valida, avança e publica a versão do Pórtica App (ver docstring).",
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--check",
        action="store_true",
        help="valida a consistência da versão nos 5 lugares + SHA256SUMS.txt",
    )
    grupo.add_argument(
        "--bump",
        metavar="X.Y.Z",
        help="avança a versão nos 5 lugares de uma vez (semver maior que o atual)",
    )
    grupo.add_argument(
        "--sums",
        action="store_true",
        help="regenera SHA256SUMS.txt a partir de dist/ e atualiza RELEASE_NOTES.md",
    )
    grupo.add_argument(
        "--verify-sums",
        action="store_true",
        help="confere cada linha de SHA256SUMS.txt contra os arquivos em dist/",
    )
    parser.add_argument(
        "--date",
        metavar="AAAA-MM-DD",
        default=None,
        help="data p/ date-released no --bump (padrão: hoje)",
    )
    args = parser.parse_args()

    if args.check:
        raise SystemExit(cmd_check(args))
    if args.bump:
        raise SystemExit(cmd_bump(args))
    if args.sums:
        raise SystemExit(cmd_sums(args))
    if args.verify_sums:
        raise SystemExit(cmd_verify_sums(args))


if __name__ == "__main__":
    main()
