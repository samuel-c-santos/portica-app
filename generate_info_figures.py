"""
Gerador das figuras técnicas de `core/assets/info/`.

Todas as figuras exibidas no app (painéis de ilustração e diálogos de
tabelas) são DESENHADAS POR ESTE SCRIPT — nenhuma imagem de origem
desconhecida é distribuída com o repositório.

Uso:
    python generate_info_figures.py

As figuras são vetoriais em estilo próprio (matplotlib, sem marca de terceiro,
sem fotografia de terceiros), coerentes com o visual das demais figuras do app.
"""

import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, Polygon, Rectangle

# ── Estilo ──────────────────────────────────────────────────────────────────
FUNDO = "#eef1f5"
TRACO = "#2d4b73"
TRACO_CLARO = "#8fa3bd"
CONCRETO = "#c9d3e0"
ACO_TRACAO = "#1f5fa8"
ACO_COMPR = "#c0392b"
ACO_ESTRIBO = "#2e7d32"
TEXTO = "#1a1a1a"

RAIZ = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RAIZ, "core", "assets", "info")


def _novo_eixo(figsize=(9.0, 5.0), xlim=(-1, 10), ylim=(-1, 6)):
    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    fig.patch.set_facecolor(FUNDO)
    ax.set_facecolor(FUNDO)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def _apaga_eixo(ax):
    ax.set_xticks([])
    ax.set_yticks([])


def _texto(ax, x, y, txt, ha="center", va="center", size=11, estilo="normal",
           cor=TEXTO, rotacao=0, peso="normal"):
    ax.text(x, y, txt, ha=ha, va=va, fontsize=size, style=estilo, color=cor,
            rotation=rotacao, weight=peso)


def _seta(ax, x, y, dx, dy, cor=TEXTO, largura=1.4, ponta=9, zorder=6):
    ax.annotate(
        "",
        xy=(x + dx, y + dy),
        xytext=(x, y),
        arrowprops=dict(arrowstyle="-|>", color=cor, lw=largura,
                        mutation_scale=ponta),
        zorder=zorder,
    )


def _apoio_triangular(ax, x, y, largura=0.75):
    ax.add_patch(Polygon(
        [(x - largura / 2, y), (x + largura / 2, y), (x, y + 0.55)],
        closed=True, facecolor=CONCRETO, edgecolor=TRACO, lw=1.2, zorder=4,
    ))
    ax.plot([x - largura / 2 - 0.12, x + largura / 2 + 0.12], [y - 0.02, y - 0.02],
            color=TRACO, lw=1.8, zorder=4)


def _apoio_rolo(ax, x, y, r=0.22):
    ax.add_patch(Circle((x, y + r), r, facecolor=FUNDO, edgecolor=TRACO,
                        lw=1.4, zorder=5))
    ax.plot([x - 0.45, x + 0.45], [y - 0.02, y - 0.02], color=TRACO, lw=1.8,
            zorder=4)


# ── 1. Momento fletor e deformação sob flexão ───────────────────────────────
def figura_momento_fletor():
    """Viga biapoiada com carregamento uniforme: deformada e diagrama de M(x)."""
    fig, ax = _novo_eixo(figsize=(9.5, 5.0), xlim=(-0.8, 9.8), ylim=(-0.8, 4.4))

    x0, x1 = 0.8, 8.8
    ybase = 1.9
    h = 0.5
    vao = x1 - x0

    # Diagrama de momento fletor (parábola preenchida abaixo da viga)
    xs = [x0 + vao * k / 200 for k in range(201)]
    ms = [ybase - 1.45 * (4 * ((x - x0) / vao) * (1 - (x - x0) / vao)) for x in xs]
    ax.fill_between(xs, ms, ybase, color="#9db4d4", alpha=0.55, zorder=1)
    ax.plot(xs, ms, color=TRACO, lw=1.8, zorder=2)

    # Linha de base do diagrama
    ax.plot([x0, x1], [ybase, ybase], color=TRACO_CLARO, lw=1.0, ls=":", zorder=2)

    # Viga
    ax.add_patch(Rectangle((x0, ybase), vao, h, facecolor=CONCRETO,
                           edgecolor=TRACO, lw=1.6, zorder=3))
    _apoio_triangular(ax, x0, ybase)
    _apoio_rolo(ax, x1, ybase)

    # Linha deformada (parábola, tracejada)
    xs2, ys2 = [], []
    for k in range(201):
        xi = x0 + vao * k / 200
        ys2.append(ybase + h / 2 - 0.55 * (4 * ((xi - x0) / vao) * (1 - (xi - x0) / vao)))
        xs2.append(xi)
    ax.plot(xs2, ys2, color=TRACO, lw=1.6, ls="--", zorder=4)

    # Carga uniforme
    for i in range(9):
        x = x0 + 0.45 + i * (vao - 0.9) / 8
        _seta(ax, x, 3.85, 0, -0.75, cor=TEXTO, largura=1.3, ponta=8)
    ax.plot([x0 + 0.25, x1 - 0.25], [3.92, 3.92], color=TEXTO, lw=1.4)
    _texto(ax, (x0 + x1) / 2, 4.2, "carregamento uniforme", size=12, estilo="italic")

    # Rótulos
    _texto(ax, (x0 + x1) / 2, 0.15, "M(x)", size=13, estilo="italic")
    _texto(ax, x1 + 0.15, ybase + 0.62, "deformada", ha="left", size=11,
           estilo="italic", cor=TRACO)
    _texto(ax, x1 + 0.15, 0.55, "diagrama de momento", ha="left", size=11,
           estilo="italic", cor=TRACO)

    # Cota do vão
    ax.annotate("", xy=(x0, -0.45), xytext=(x1, -0.45),
                arrowprops=dict(arrowstyle="<|-|>", color=TEXTO, lw=1.1))
    _texto(ax, (x0 + x1) / 2, -0.7, "L", size=12, estilo="italic")

    _apaga_eixo(ax)
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(DESTINO, "momento_fletor.jpg"),
                facecolor=fig.get_facecolor(), format="jpg", dpi=150)
    plt.close(fig)


# ── 2. Analogia de treliça (bielas e tirantes) ──────────────────────────────
def figura_bielas_tirantes():
    """Modelo de bielas e tirantes aplicado a um trecho de viga."""
    fig, ax = _novo_eixo(figsize=(9.5, 4.6), xlim=(-0.6, 9.8), ylim=(-2.6, 3.2))

    x0, x1 = 1.0, 8.0
    yb, yt = 0.0, 1.8

    ax.add_patch(Rectangle((x0, yb), x1 - x0, yt - yb, facecolor=CONCRETO,
                           alpha=0.35, edgecolor=TRACO, lw=1.8, zorder=3))

    # Bielas diagonais (compressão): zigue-zague continuous
    bielas = [(1.2, yb), (2.4, yt), (3.6, yb), (4.8, yt), (6.0, yb), (7.2, yt),
              (7.9, 0.5)]
    for (xa, ya), (xb, yb_) in zip(bielas[::2], bielas[1::2]):
        ax.plot([xa, xb], [ya, yb_], color=TRACO, lw=2.2, ls=(0, (6, 3)), zorder=2)

    # Tirantes verticais (tração)
    for x in [2.4, 3.6, 4.8, 6.0, 7.2]:
        ax.plot([x, x], [yb, yt], color=ACO_TRACAO, lw=2.0, zorder=2)

    # Banzo tracionado (armadura) e banzo comprimido
    ax.plot([x0, x1], [yb, yb], color=ACO_TRACAO, lw=3.2, zorder=4)
    ax.plot([x0, x1], [yt, yt], color=TRACO, lw=3.0, zorder=4)

    # Esforço cortante na diagonal comprimida
    _seta(ax, 8.5, 2.9, 0, -0.8, cor=TEXTO, largura=1.5)
    _texto(ax, 8.5, 3.05, "V", size=12, estilo="italic")

    # Fissura de flexão (na tração) e fissura inclinada (no cisalhamento)
    ax.plot([4.8 - 0.22, 4.8 + 0.22], [yb + 0.05, yb], color=ACO_COMPR, lw=1.3,
            zorder=5)
    ax.plot([6.0, 6.55], [yb + 0.1, yb + 1.1], color=ACO_COMPR, lw=1.4, zorder=5)

    # Legendas (rodapé)
    ax.plot([0.2, 0.95], [-1.95, -1.95], color=TRACO, lw=2.2, ls=(0, (6, 3)))
    _texto(ax, 1.05, -1.95, "biela (compressão)", ha="left", size=11)
    ax.plot([4.6, 5.35], [-1.95, -1.95], color=ACO_TRACAO, lw=2.0)
    _texto(ax, 5.45, -1.95, "tirante (tração)", ha="left", size=11)
    ax.plot([0.2, 0.95], [-2.4, -2.4], color=ACO_COMPR, lw=1.4)
    _texto(ax, 1.05, -2.4, "fissura", ha="left", size=11)

    _texto(ax, (x0 + x1) / 2, yt + 0.25, "banzo comprimido", size=11,
           estilo="italic")
    _texto(ax, (x0 + x1) / 2, yb - 0.3, "armadura tracionada", size=11,
           estilo="italic")

    _apaga_eixo(ax)
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(DESTINO, "bielas_tirantes.jpg"),
                facecolor=fig.get_facecolor(), format="jpg", dpi=150)
    plt.close(fig)


# ── 3. Fissuração inclinada por cisalhamento ────────────────────────────────
def figura_cisalhamento():
    """Padrão de fissuração inclinada (~45°) e armadura transversal."""
    fig, ax = _novo_eixo(figsize=(9.0, 3.6), xlim=(-0.6, 9.6), ylim=(-2.2, 2.6))

    x0, x1 = 0.8, 8.2
    yb, yt = -0.5, 1.5

    ax.add_patch(Rectangle((x0, yb), x1 - x0, yt - yb, facecolor="none",
                           edgecolor=TRACO, lw=1.8, zorder=3))

    # Estribos (verticais)
    for x in [1.2, 2.4, 3.6, 4.8, 6.0, 7.2]:
        ax.plot([x, x], [yb, yt], color=ACO_ESTRIBO, lw=1.8, zorder=3)

    # Armadura longitudinal tracionada
    ax.plot([x0, x1], [yb + 0.12, yb + 0.12], color=ACO_TRACAO, lw=2.6, zorder=4)
    # Armadura longitudinal comprimida
    ax.plot([x0, x1], [yt - 0.12, yt - 0.12], color=ACO_COMPR, lw=2.2, zorder=4)

    # Fissuras inclinadas a ~45°
    for x in [2.9, 4.1, 5.3, 6.5]:
        ax.plot([x, x + 0.95], [yb + 0.15, yt - 0.1], color="#7b1fa2", lw=1.8,
                zorder=5)

    # Resultante de cisalhamento
    _seta(ax, 4.5, yt + 0.85, 0, -0.7, cor=TEXTO, largura=1.5)
    _texto(ax, 4.5, yt + 1.05, "V", size=12, estilo="italic")

    # Legendas
    ax.plot([0.2, 0.9], [-1.85, -1.85], color="#7b1fa2", lw=1.8)
    _texto(ax, 1.0, -1.85, "fissura inclinada (~45°)", ha="left", size=11)
    ax.plot([5.0, 5.7], [-1.85, -1.85], color=ACO_ESTRIBO, lw=1.8)
    _texto(ax, 5.8, -1.85, "estribo", ha="left", size=11)

    _texto(ax, x1 + 0.15, yb + 0.12, "armadura tracionada", ha="left", size=10,
           estilo="italic", cor=ACO_TRACAO)
    _texto(ax, x1 + 0.15, yt - 0.12, "armadura comprimida", ha="left", size=10,
           estilo="italic", cor=ACO_COMPR)

    _apaga_eixo(ax)
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(DESTINO, "cisalhamento.png"),
                facecolor=fig.get_facecolor(), format="png", dpi=150)
    plt.close(fig)


# ── 4. Partes da armadura de uma viga ──────────────────────────────────────
def figura_partes_armadura():
    """Esquema das partes que compõem a armadura de uma viga."""
    fig, ax = _novo_eixo(figsize=(9.5, 5.0), xlim=(-0.6, 9.8), ylim=(-2.2, 4.4))

    x0, x1 = 1.0, 8.0
    yb, yt = 0.0, 1.8

    # Contorno do concreto
    ax.add_patch(Rectangle((x0, yb), x1 - x0, yt - yb, facecolor=CONCRETO,
                           alpha=0.45, edgecolor=TRACO, lw=1.8, zorder=2))

    # Armadura longitudinal inferior (tracionada)
    for y in [yb + 0.18, yb + 0.36]:
        ax.plot([x0 + 0.15, x1 - 0.15], [y, y], color=ACO_TRACAO, lw=2.8, zorder=4)
    # Armadura longitudinal superior (comprimida)
    for y in [yt - 0.18, yt - 0.36]:
        ax.plot([x0 + 0.15, x1 - 0.15], [y, y], color=ACO_COMPR, lw=2.4, zorder=4)
    # Armadura de pele (costelas)
    for y in [yb + 0.75, yt - 0.75]:
        ax.plot([x0 + 0.15, x1 - 0.15], [y, y], color="#c9a227", lw=2.2, zorder=4)
    # Estribos (transversais)
    for x in [1.5, 3.2, 4.9, 6.6]:
        ax.plot([x, x], [yb + 0.12, yt - 0.12], color=ACO_ESTRIBO, lw=2.0, zorder=4)

    # Legendas (acima da viga)
    ax.plot([0.2, 0.95], [4.0, 4.0], color=ACO_TRACAO, lw=2.8)
    _texto(ax, 1.05, 4.0, "armadura longitudinal tracionada", ha="left", size=11)
    ax.plot([0.2, 0.95], [3.5, 3.5], color=ACO_COMPR, lw=2.4)
    _texto(ax, 1.05, 3.5, "armadura longitudinal comprimida", ha="left", size=11)
    ax.plot([0.2, 0.95], [3.0, 3.0], color=ACO_ESTRIBO, lw=2.0)
    _texto(ax, 1.05, 3.0, "estribo (armadura transversal)", ha="left", size=11)
    ax.plot([0.2, 0.95], [2.5, 2.5], color="#c9a227", lw=2.2)
    _texto(ax, 1.05, 2.5, "armadura de pele (costela)", ha="left", size=11)

    _texto(ax, (x0 + x1) / 2, yb - 0.5, "gaiola de armadura", size=11,
           estilo="italic", cor=TRACO)

    _apaga_eixo(ax)
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(DESTINO, "partes_armadura_viga.png"),
                facecolor=fig.get_facecolor(), format="png", dpi=150)
    plt.close(fig)


# ── Execução ────────────────────────────────────────────────────────────────
def main():
    os.makedirs(DESTINO, exist_ok=True)
    figura_momento_fletor()
    figura_bielas_tirantes()
    figura_cisalhamento()
    figura_partes_armadura()
    print("Figuras geradas em:", DESTINO)
    for nome in ("momento_fletor.jpg", "bielas_tirantes.jpg", "cisalhamento.png",
                 "partes_armadura_viga.png"):
        caminho = os.path.join(DESTINO, nome)
        print(f"  {nome}: {os.path.getsize(caminho)} bytes")


if __name__ == "__main__":
    main()
