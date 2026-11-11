"""Testes das URLs de release na landing page e da automação em build/release.py (EP-06.3)."""

from __future__ import annotations

from pathlib import Path

from build import release
from core.version import APP_VERSION


def test_site_nao_usa_releases_latest_com_asset_versionado():
    """Proíbe /releases/latest/download/portica-v... que quebra no próximo release."""
    html_files = list((release.PROJECT_ROOT / "site").glob("*.html"))
    assert html_files, "Nenhum HTML encontrado em site/"
    for html_path in html_files:
        conteudo = html_path.read_text(encoding="utf-8")
        assert "releases/latest/download/portica-v" not in conteudo, (
            f"{html_path.name} usa 'releases/latest/download/portica-v', "
            "que resulta em 404 assim que uma nova release é publicada."
        )


def test_site_contem_urls_de_tag_imutavel():
    """As duas URLs de download em site/index.html devem usar /releases/download/v{APP_VERSION}/."""
    conteudo = release.SITE_FILE.read_text(encoding="utf-8")
    esperadas = release.urls_assets(APP_VERSION)
    assert len(esperadas) == 2
    for url in esperadas:
        assert f"/releases/download/v{APP_VERSION}/" in url
        assert url in conteudo, f"URL imutável ausente de site/index.html: {url}"


def test_check_site_rejeita_releases_latest_e_valida_tag(monkeypatch, tmp_path: Path):
    """check_site() deve acusar divergência se /releases/latest/download/portica-v aparecer."""
    falso_html = tmp_path / "index.html"
    falso_html.write_text(
        '<a href="https://github.com/samuel-c-santos/portica-app/releases/latest/download/'
        f'portica-v{APP_VERSION}-windows-x64.exe">exe</a>\n'
        '<a href="https://github.com/samuel-c-santos/portica-app/releases/latest/download/'
        f'portica-v{APP_VERSION}-windows-x64.zip">zip</a>\n'
        f"(versão {APP_VERSION})\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "SITE_FILE", falso_html)
    rep = release.Relatorio()
    release.check_site(rep, APP_VERSION)
    assert any("releases/latest/download/portica-v" in d for d in rep.divergencias)


def test_bump_site_atualiza_tag_e_nome_do_asset(monkeypatch, tmp_path: Path):
    """bump_site() deve atualizar a tag /releases/download/vX.Y.Z/ e o nome do asset."""
    html_original = release.SITE_FILE.read_text(encoding="utf-8")
    falso_html = tmp_path / "index.html"
    falso_html.write_text(html_original, encoding="utf-8")
    monkeypatch.setattr(release, "SITE_FILE", falso_html)

    novo_html = release.bump_site(APP_VERSION, "9.9.9")
    falso_html.write_text(novo_html, encoding="utf-8")

    rep = release.Relatorio()
    release.check_site(rep, "9.9.9")
    assert rep.divergencias == []
    for url in release.urls_assets("9.9.9"):
        assert url in novo_html
