"""O CSS publicado do site deve ser a concatenacao exata das fontes (EP-06.9).

O site carrega apenas `site/bundle.css`. Se alguem editar `theme.css` ou
`base.css` e esquecer de regenerar o bundle, a pagina continua servindo o CSS
antigo sem nenhum erro visivel. Este teste transforma esse esquecimento em
falha de CI.
"""

from __future__ import annotations

from tools import build_site_css


def test_bundle_css_esta_sincronizado_com_as_fontes():
    atual = build_site_css.DESTINO.read_text(encoding="utf-8")
    esperado = build_site_css.gerar()
    assert atual == esperado, (
        "site/bundle.css esta desatualizado em relacao a "
        f"{', '.join(build_site_css.FONTES)}; "
        "rode `python tools/build_site_css.py`."
    )
