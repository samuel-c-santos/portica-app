"""Gera o cartao de compartilhamento do site (`og:image`).

O cartao e o que aparece no preview de link do LinkedIn, WhatsApp, X e
Discord. Ele precisa ser 1200x630 e ficar legivel tambem recortado, porque
cada plataforma corta uma margem diferente. A imagem versionada vai para
`site/img/og-preview.png` e e referenciada por `index.html` e `calculo.html`.

Duas variantes usam a mesma diagramacao de base, mas respondem a perguntas
diferentes:

    claro  segue a tela de carregamento do app: fundo #f5f7fa, reguas azuis,
           marca grande e o nome em Antonio. E o padrao, porque a marca fica
           legivel mesmo no tamanho de feed do celular.
    escuro painel escuro com screenshot do FTOOL, para quando o preview
           precisar mostrar a interface em vez da identidade.

Uso:

    python tools/generate_og_image.py                 # variante claro
    python tools/generate_og_image.py -v escuro       # variante escuro
    python tools/generate_og_image.py -o /tmp/x.png   # destino alternativo

O script usa as fontes variaveis e o logotipo do proprio site, entao o cartao
acompanha a identidade visual sem depender de arquivo externo.
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SITE = Path(__file__).resolve().parent.parent / "site"
IMG = SITE / "img"
FONTES = SITE / "vendor" / "fonts"
DESTINO = IMG / "og-preview.png"

LARGURA = 1200
ALTURA = 630

AZUL = "#1565c0"

# Variante escura.
FUNDO = "#0f1419"
TITULO = "#e8edf3"
TEXTO = "#b8c6d4"
APAGADO = "#7d8fa3"
LINHA = "#2a3644"
PILULA = "#141c25"
AZUL_CLARO = "#5e92f3"
ROXO = "#6a1b9a"
MARGEM = 72

# Variante clara (mesma paleta da tela de carregamento do app).
FUNDO_CLARO = "#f5f7fa"
TINTA = "#1f2933"
TEXTO_CLARO = "#48586a"
APAGADO_CLARO = "#5a6875"
LINHA_CLARA = "#d5dde5"
MARGEM_CLARA = 96


def _fonte(arquivo: str, tamanho: int, peso: int | None = None) -> ImageFont.FreeTypeFont:
    """Carrega uma fonte variavel do site no peso pedido."""
    dados = BytesIO()
    TTFont(FONTES / arquivo).save(dados)
    dados.seek(0)
    fonte = ImageFont.truetype(dados, tamanho)
    if peso is not None:
        fonte.set_variation_by_axes([peso])
    return fonte


def _brilho(base: Image.Image, centro: tuple[int, int], raio: int, cor: str, alpha: int) -> None:
    """Aplica um brilho radial suave sobre a base (in place)."""
    camada = Image.new("RGBA", base.size, (0, 0, 0, 0))
    desenho = ImageDraw.Draw(camada)
    x, y = centro
    desenho.ellipse((x - raio, y - raio, x + raio, y + raio), fill=cor + f"{alpha:02x}")
    camada = camada.filter(ImageFilter.GaussianBlur(raio // 2))
    base.alpha_composite(camada)


def _pilula(
    desenho: ImageDraw.ImageDraw,
    x: int,
    y: int,
    texto: str,
    fonte: ImageFont.FreeTypeFont,
) -> int:
    """Desenha uma pilula e devolve o x seguinte."""
    largura = int(desenho.textlength(texto, font=fonte)) + 36
    altura = 46
    desenho.rounded_rectangle(
        (x, y, x + largura, y + altura),
        radius=altura // 2,
        fill=PILULA,
        outline=LINHA,
        width=1,
    )
    desenho.text((x + largura / 2, y + altura / 2 - 1), texto, font=fonte, fill=TEXTO, anchor="mm")
    return x + largura + 12


def _screenshot(base: Image.Image, caminho: Path, caixa: tuple[int, int, int, int]) -> None:
    """Cola um screenshot com cantos arredondados, sombra e borda."""
    x, y, largura, altura = caixa
    foto = Image.open(caminho).convert("RGB")
    foto = foto.resize((largura, altura), Image.LANCZOS)

    raio = 18
    mascara = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, largura - 1, altura - 1), radius=raio, fill=255
    )

    sombra = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sombra.paste(Image.new("RGBA", (largura, altura), (0, 0, 0, 170)), (x, y + 16), mascara)
    base.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(26)))

    base.paste(foto, (x, y), mascara)
    ImageDraw.Draw(base).rounded_rectangle(
        (x, y, x + largura - 1, y + altura - 1),
        radius=raio,
        outline=LINHA,
        width=1,
    )


def _cartao_claro() -> Image.Image:
    """Cartao limpo, no espirito da tela de carregamento do app."""
    base = Image.new("RGB", (LARGURA, ALTURA), FUNDO_CLARO)
    desenho = ImageDraw.Draw(base)

    # Reguas azuis superior e inferior, como no splash do app.
    desenho.rectangle((0, 0, LARGURA, 4), fill=AZUL)
    desenho.rectangle((0, ALTURA - 4, LARGURA, ALTURA), fill=AZUL)

    # Marca grande a direita, o "p" e o elemento de reconhecimento.
    logo = Image.open(IMG / "logo.png").convert("RGBA")
    altura_logo = 340
    largura_logo = round(logo.width * altura_logo / logo.height)
    logo = logo.resize((largura_logo, altura_logo), Image.LANCZOS)
    base.paste(
        logo,
        (LARGURA - MARGEM_CLARA - largura_logo, (ALTURA - altura_logo) // 2),
        logo,
    )

    fonte_nome = _fonte("antonio.woff2", 118, 600)
    desenho.text((MARGEM_CLARA - 4, 142), "PÓRTICA APP", font=fonte_nome, fill=TINTA)

    fonte_sub = _fonte("karla.woff2", 27, 500)
    desenho.text(
        (MARGEM_CLARA, 295),
        "Calculadora estrutural de vigas de concreto armado",
        font=fonte_sub,
        fill=TEXTO_CLARO,
    )

    fonte_norma = _fonte("karla.woff2", 26, 700)
    desenho.text((MARGEM_CLARA, 346), "ABNT NBR 6118:2023", font=fonte_norma, fill=AZUL)

    desenho.line((MARGEM_CLARA, 411, MARGEM_CLARA + 420, 411), fill=LINHA_CLARA, width=1)

    fonte_rodape = _fonte("karla.woff2", 21, 500)
    desenho.text(
        (MARGEM_CLARA, 427),
        "Open source · Apache-2.0 · DOI no Zenodo",
        font=fonte_rodape,
        fill=APAGADO_CLARO,
    )
    desenho.text(
        (MARGEM_CLARA, 463),
        "samuel-c-santos.github.io/portica-app",
        font=fonte_rodape,
        fill=APAGADO_CLARO,
    )

    return base


def _cartao_escuro() -> Image.Image:
    """Cartao com screenshot do FTOOL, para preview que mostra a interface."""
    base = Image.new("RGBA", (LARGURA, ALTURA), FUNDO)
    _brilho(base, (170, 40), 520, AZUL, 70)
    _brilho(base, (1150, 640), 460, ROXO, 48)

    desenho = ImageDraw.Draw(base)
    desenho.rectangle((0, 0, LARGURA - 1, ALTURA - 1), outline=LINHA, width=1)

    # Marca no topo da coluna de texto.
    logo = Image.open(IMG / "logo_dark.png").convert("RGBA")
    altura_logo = 92
    largura_logo = round(logo.width * altura_logo / logo.height)
    logo = logo.resize((largura_logo, altura_logo), Image.LANCZOS)
    base.alpha_composite(logo, (MARGEM, 62))

    fonte_eyebrow = _fonte("karla.woff2", 22, 600)
    desenho.text(
        (MARGEM + largura_logo + 20, 62 + altura_logo / 2),
        "CALCULADORA ESTRUTURAL",
        font=fonte_eyebrow,
        fill=AZUL_CLARO,
        anchor="lm",
    )

    fonte_titulo = _fonte("antonio.woff2", 104, 600)
    desenho.text((MARGEM - 4, 170), "Pórtica App", font=fonte_titulo, fill=TITULO)

    desenho.rounded_rectangle((MARGEM, 306, MARGEM + 96, 312), radius=3, fill=AZUL_CLARO)

    fonte_sub = _fonte("karla.woff2", 34, 700)
    desenho.text((MARGEM, 342), "Vigas de concreto armado", font=fonte_sub, fill=TEXTO)

    fonte_apoio = _fonte("karla.woff2", 25, 500)
    desenho.text((MARGEM, 394), "ABNT NBR 6118:2023", font=fonte_apoio, fill=TEXTO)
    desenho.text(
        (MARGEM, 428),
        "flexão · cisalhamento · ELS · detalhamento",
        font=fonte_apoio,
        fill=APAGADO,
    )

    fonte_pilula = _fonte("karla.woff2", 21, 600)
    x = MARGEM
    x = _pilula(desenho, x, 496, "Open source · Apache-2.0", fonte_pilula)
    _pilula(desenho, x, 496, "DOI no Zenodo", fonte_pilula)

    fonte_rodape = _fonte("karla.woff2", 21, 500)
    desenho.text(
        (MARGEM, 566),
        "samuel-c-santos.github.io/portica-app",
        font=fonte_rodape,
        fill=APAGADO,
    )

    # Screenshot das secoes criticas no painel direito.
    fonte_legenda = _fonte("karla.woff2", 20, 600)
    desenho.text(
        (640, 108), "IMPORTAÇÃO DO FTOOL · SEÇÕES CRÍTICAS", font=fonte_legenda, fill=APAGADO
    )
    _screenshot(base, IMG / "04-secoes.png", (640, 146, 488, 290))

    return base.convert("RGB")


VARIANTES = {"claro": _cartao_claro, "escuro": _cartao_escuro}


def gerar(variante: str = "claro") -> Image.Image:
    """Monta o cartao 1200x630 da variante pedida."""
    try:
        montar = VARIANTES[variante]
    except KeyError as exc:
        raise ValueError(f"variante desconhecida: {variante}") from exc
    return montar()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--variante", choices=sorted(VARIANTES), default="claro")
    parser.add_argument("-o", "--saida", type=Path, default=DESTINO)
    args = parser.parse_args(argv)

    imagem = gerar(args.variante)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    imagem.save(args.saida, "PNG", optimize=True)
    try:
        destino = args.saida.relative_to(SITE.parent)
    except ValueError:
        destino = args.saida
    print(f"[OK] {destino} gerado ({imagem.width}x{imagem.height}, variante {args.variante})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
