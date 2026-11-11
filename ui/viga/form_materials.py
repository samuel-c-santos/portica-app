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
    )

    ctx.fck_dd = _styled_dropdown(
        "fck (MPa)",
        "30",
        _make_options([20, 25, 30, 35, 40, 45, 50, 55, 60]),
        info_on_click=lambda e: _open_fck(ctx.page),
    )

    ctx.fyk_dd = _styled_dropdown(
        "fyk aço (kN/cm²)",
        "50",
        _make_options([25, 50, 60]),
        info_on_click=lambda e: _open_aco(ctx.page),
    )

    ctx.fyke_dd = _styled_dropdown(
        "fyk estribo (kN/cm²)",
        "60",
        _make_options([25, 50, 60]),
        info_on_click=lambda e: _open_aco(ctx.page),
    )

    ctx.gamma_f_dd = _styled_dropdown(
        "Combinacao (gf)",
        "normais",
        _make_gamma_f_options(),
        info_on_click=lambda e: _open_gamma_f(ctx.page),
    )

    ctx._diam_options = partial(_diam_options, ctx)

    ctx._diam_options_long = partial(_diam_options_long, ctx)

    ctx._diam_options_placeholder_long = partial(_diam_options_placeholder_long, ctx)

    ctx.phi_est_dd = _styled_dropdown(
        "Estribo phi_t (mm)",
        "5",
        ctx._diam_options(),
        info_on_click=lambda e: _open_diametros(ctx.page),
    )

    ctx.phi_bar_dd = _styled_dropdown(
        "Barra phi_l (mm)",
        "",
        ctx._diam_options_placeholder_long(),
        on_change=lambda e: ctx._check_ftool_pronto(),
        info_on_click=lambda e: _open_diametros(ctx.page),
    )
