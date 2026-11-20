"""O cartao de compartilhamento (og:image) precisa existir e bater com o HTML.

Um `og:image` quebrado nao gera erro visivel: a pagina abre normalmente e o
link aparece sem imagem no LinkedIn, no WhatsApp e no X. Este teste cobre o
contrato minimo do card grande: arquivo versionado em 1200x630 e metatags
declarando as mesmas dimensoes e o mesmo arquivo.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
IMAGEM = SITE / "img" / "og-preview.png"
PAGINAS = ("index.html", "calculo.html")
URL = "https://samuel-c-santos.github.io/portica-app/img/og-preview.png"


def _dimensoes_png(caminho: Path) -> tuple[int, int]:
    """Le largura e altura direto do cabecalho IHDR, sem dependencia de imagem."""
    dados = caminho.read_bytes()[:33]
    assert dados[:8] == b"\x89PNG\r\n\x1a\n", f"{caminho.name} nao e um PNG"
    largura, altura = struct.unpack(">II", dados[16:24])
    return largura, altura


def _meta(html: str, chave: str) -> str | None:
    """Le uma metatag por `property=` (Open Graph) ou `name=` (Twitter)."""
    achado = re.search(
        rf'<meta (?:property|name)="{re.escape(chave)}" content="([^"]*)"',
        html,
    )
    return achado.group(1) if achado else None


def test_cartao_existe_no_tamanho_do_card_grande():
    assert IMAGEM.exists(), (
        "site/img/og-preview.png nao existe; rode `python tools/generate_og_image.py`."
    )
    assert _dimensoes_png(IMAGEM) == (1200, 630)


def test_paginas_declaram_o_cartao_com_as_dimensoes_corretas():
    for pagina in PAGINAS:
        html = (SITE / pagina).read_text(encoding="utf-8")
        assert _meta(html, "og:image") == URL, pagina
        assert _meta(html, "og:image:width") == "1200", pagina
        assert _meta(html, "og:image:height") == "630", pagina
        assert _meta(html, "og:image:alt"), pagina
        assert _meta(html, "twitter:image") == URL, pagina
