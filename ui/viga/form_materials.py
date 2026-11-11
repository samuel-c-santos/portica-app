"""Formulario de materiais e armaduras (CAA, fck, fyk, bitolas).

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

from functools import partial

import flet as ft

from core.calculos import (
    DIAM_BARRAS,
    DIAM_BARRAS_LONG,
)
from ui.viga.widgets import (
    _make_caa_options,
    _make_gamma_f_options,
    _make_options,
    _open_aco,
    _open_caa,
    _open_diametros,
    _open_fck,
    _open_gamma_f,
    _styled_dropdown,
)


# ── Sidebar de armaduras ─────────────────────────────────────────────
def _diam_options(ctx):
    return [ft.dropdown.Option(str(d)) for d in DIAM_BARRAS]


def _diam_options_long(ctx):
    return [ft.dropdown.Option(str(d)) for d in DIAM_BARRAS_LONG]


def _diam_options_placeholder_long(ctx):
    return [ft.dropdown.Option("", "-- Selecione --")] + [
        ft.dropdown.Option(str(d)) for d in DIAM_BARRAS_LONG
    ]


def setup_materiais(ctx):
    """Passo de construcao: setup_materiais."""

    # ── Sidebar de materiais ─────────────────────────────────────────────
    ctx.caa_dd = _styled_dropdown(
        "Classe CAA",
        "2",
        _make_caa_options(),
        info_on_click=lambda e: _open_caa(ctx.page),
        info_tooltip="Tabela 6.1 e 7.2 — Classe de Agressividade Ambiental e cobrimento (NBR 6118:2023)",
    )

    ctx.fck_dd = _styled_dropdown(
        "fck (MPa)",
        "30",
        _make_options([20, 25, 30, 35, 40, 45, 50, 55, 60]),
        info_on_click=lambda e: _open_fck(ctx.page),
        info_tooltip="Classes de resistência do concreto C20 a C60 (NBR 6118:2023 — Seção 8.2.1)",
    )

    ctx.fyk_dd = _styled_dropdown(
        "fyk aço (kN/cm²)",
        "50",
        _make_options([25, 50, 60]),
        info_on_click=lambda e: _open_aco(ctx.page),
        info_tooltip="Aços para armadura passiva CA-25, CA-50 e CA-60 (NBR 7480 / NBR 6118:2023)",
    )

    ctx.fyke_dd = _styled_dropdown(
        "fyk estribo (kN/cm²)",
        "60",
        _make_options([25, 50, 60]),
        info_on_click=lambda e: _open_aco(ctx.page),
        info_tooltip="Aço dos estribos transversais (NBR 6118:2023 — Seção 17.4)",
    )

    ctx.gamma_f_dd = _styled_dropdown(
        "Combinacao (gf)",
        "normais",
        _make_gamma_f_options(),
        info_on_click=lambda e: _open_gamma_f(ctx.page),
        info_tooltip="Tabela 11.1 — Coeficiente de ponderação das ações γf (NBR 6118:2023)",
    )

    ctx._diam_options = partial(_diam_options, ctx)

    ctx._diam_options_long = partial(_diam_options_long, ctx)

    ctx._diam_options_placeholder_long = partial(_diam_options_placeholder_long, ctx)

    ctx.phi_est_dd = _styled_dropdown(
        "Estribo phi_t (mm)",
        "5",
        ctx._diam_options(),
        info_on_click=lambda e: _open_diametros(ctx.page),
        info_tooltip="Bitolas comerciais para estribos φt (NBR 7480 / NBR 6118:2023)",
    )

    def _on_phi_bar_change(e):
        if (ctx.phi_bar_dd.control.value or "").strip():
            ctx.phi_bar_dd.control.error_text = None
        ctx._check_ftool_pronto()

    ctx.phi_bar_dd = _styled_dropdown(
        "Barra phi_l (mm)",
        "",
        ctx._diam_options_placeholder_long(),
        on_change=_on_phi_bar_change,
        info_on_click=lambda e: _open_diametros(ctx.page),
        info_tooltip="Bitolas comerciais para armadura longitudinal φl (NBR 7480 / NBR 6118:2023)",
    )
