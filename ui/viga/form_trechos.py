"""Tabelas de trechos (momentos/cortantes) e calculo manual.

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

from functools import partial

import flet as ft

from ui.theme import (
    Palette,
    Radius,
    Spacing,
    br_all,
    caption,
    pad_all,
    primary_button,
    section_header,
    surface_card,
    tonal_button,
)
from ui.viga.widgets import (
    DEFAULT_TRECHOS,
    MAX_TRECHOS,
)


def setup_armazenamento_trechos(ctx):
    """Passo de construcao: setup_armazenamento_trechos."""
    ctx.md_rows = []  # lista de TextField para momentos

    ctx.vk_rows = []  # lista de TextField para cortantes


# ── Builder de tab de trechos (centro, dinamico) ──────────────────────


def _make_trecho_field(ctx, prefix, idx, value=""):
    """Cria um TextField de trecho (M1, M2, ...)."""
    hint = "Ex: 50,5" if prefix == "M" else "Ex: 80,0"

    def _on_change_trecho(e):
        if "." in e.control.value:
            e.control.value = e.control.value.replace(".", ",")
            e.control.update()
        ctx.validate_trecho_field(e)

    return ft.TextField(
        label=f"{prefix}{idx}",
        value=value,
        text_size=13,
        filled=True,
        dense=True,
        bgcolor=Palette.SURFACE_VARIANT,
        border_radius=br_all(Radius.SM),
        border_color=Palette.OUTLINE_VARIANT,
        focused_border_color=Palette.PRIMARY,
        cursor_color=Palette.PRIMARY,
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.CENTER,
        hint_text=hint,
        on_change=_on_change_trecho,
        expand=True,
    )


def _init_rows(ctx, target_list, prefix):
    """Inicializa a lista com DEFAULT_TRECHOS campos."""
    target_list.clear()
    for i in range(DEFAULT_TRECHOS):
        target_list.append(ctx._make_trecho_field(prefix, i + 1))


def ler_sinais(rows):
    """Le momentos com sinal: vazio = 0. Aceita vírgula ou ponto como separador decimal."""
    vals = []
    for tf in rows:
        try:
            v = float(tf.value.replace(",", ".")) if tf.value.strip() else 0.0
            vals.append(v)
        except ValueError:
            vals.append(0.0)
    return vals


def build_trechos_panel(ctx, page, target_list, prefix):
    """Painel dinamico de trechos com botao + e lixeira por linha."""
    rows_container = ft.Column(spacing=Spacing.XS)

    def _make_row(idx, tf):
        trash = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=Palette.ERROR,
            icon_size=20,
            tooltip="Remover trecho",
            on_click=lambda e: _remove(idx),
        )
        return ft.Row(
            controls=[
                ft.Container(content=tf, expand=True),
                trash,
            ],
            spacing=Spacing.XS,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _rebuild():
        rows_container.controls.clear()
        for i, tf in enumerate(target_list):
            tf.label = f"{prefix}{i + 1}"
            rows_container.controls.append(_make_row(i, tf))
        add_btn.disabled = len(target_list) >= MAX_TRECHOS
        add_btn.text = (
            f"Maximo de {MAX_TRECHOS} trechos"
            if len(target_list) >= MAX_TRECHOS
            else "Adicionar trecho"
        )
        try:
            page.update()
        except (AssertionError, RuntimeError):
            # Flet page.update() pode falhar se a pagina foi fechada
            pass

    def _add(e):
        if len(target_list) >= MAX_TRECHOS:
            return
        target_list.append(ctx._make_trecho_field(prefix, len(target_list) + 1))
        _rebuild()

    def _remove(idx):
        if len(target_list) <= 1:
            return
        target_list.pop(idx)
        _rebuild()

    add_btn = tonal_button(
        "Adicionar trecho",
        icon=ft.Icons.ADD,
        on_click=_add,
        expand=True,
    )

    ctx.panel_rebuilds[prefix] = _rebuild
    _rebuild()

    return surface_card(
        ft.Column(
            controls=[
                section_header(
                    f"Trechos de {'flexão' if prefix == 'M' else 'cisalhamento'} ({prefix}1 a {prefix}{MAX_TRECHOS})",
                    icon=ft.Icon(
                        ft.Icons.LIST_ALT if prefix == "M" else ft.Icons.SWAP_VERT,
                        size=16,
                        color=Palette.TEXT_SECONDARY,
                    ),
                ),
                caption(
                    "Use sinal negativo (-) para momentos negativos. "
                    if prefix == "M"
                    else "Forcas cortantes em kN (com sinal). ",
                    color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                rows_container,
                ft.Container(height=Spacing.MD),
                add_btn,
            ],
            spacing=Spacing.SM,
        ),
        padding=Spacing.LG,
    )


def setup_trechos(ctx):
    """Passo de construcao: setup_trechos."""
    ctx._make_trecho_field = partial(_make_trecho_field, ctx)

    ctx._init_rows = partial(_init_rows, ctx)

    ctx._init_rows(ctx.md_rows, "M")

    ctx._init_rows(ctx.vk_rows, "V")

    ctx.build_trechos_panel = partial(build_trechos_panel, ctx)


def setup_calculo_manual(ctx):
    """Passo de construcao: setup_calculo_manual."""

    # ── Centro: entrada manual (tabela de trechos) ─────────────────────────
    ctx.manual_flex_panel = ctx.build_trechos_panel(ctx.page, ctx.md_rows, "M")

    ctx.manual_cis_panel = ctx.build_trechos_panel(ctx.page, ctx.vk_rows, "V")

    ctx.btn_calcular_manual = primary_button(
        "Calcular",
        icon=ft.Icons.CALCULATE,
        on_click=ctx.on_calculate,
        expand=True,
    )

    ctx.btn_calcular_manual_cis = primary_button(
        "Calcular",
        icon=ft.Icons.CALCULATE,
        on_click=ctx.on_calculate,
        expand=True,
    )

    ctx.manual_calc_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Cálculo manual",
                    icon=ft.Icon(ft.Icons.CALCULATE, size=16, color=Palette.PRIMARY),
                ),
                ft.Text(
                    "Informe os momentos e cortantes nos trechos abaixo e clique em Calcular.",
                    size=11,
                    color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                ctx.btn_calcular_manual,
            ],
            spacing=Spacing.SM,
        ),
        padding=Spacing.LG,
    )

    ctx.manual_calc_card_cis = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Cálculo manual",
                    icon=ft.Icon(ft.Icons.CALCULATE, size=16, color=Palette.PRIMARY),
                ),
                ft.Text(
                    "Informe os momentos e cortantes nos trechos abaixo e clique em Calcular.",
                    size=11,
                    color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                ctx.btn_calcular_manual_cis,
            ],
            spacing=Spacing.SM,
        ),
        padding=Spacing.LG,
    )

    ctx.manual_tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Flexão", icon=ft.Icons.SQUARE_OUTLINED),
            ft.Tab(label="Cisalhamento", icon=ft.Icons.SWAP_VERT),
        ],
        indicator_color=Palette.PRIMARY,
        label_color=Palette.PRIMARY,
    )

    ctx.manual_flex_content = ft.Container(
        content=ft.Column(
            controls=[ctx.manual_calc_card, ctx.manual_flex_panel],
            spacing=Spacing.MD,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=pad_all(Spacing.MD),
        expand=True,
    )

    ctx.manual_cis_content = ft.Container(
        content=ft.Column(
            controls=[ctx.manual_calc_card_cis, ctx.manual_cis_panel],
            spacing=Spacing.MD,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=pad_all(Spacing.MD),
        expand=True,
    )

    ctx.manual_tab_view = ft.TabBarView(
        controls=[ctx.manual_flex_content, ctx.manual_cis_content],
        clip_behavior=ft.ClipBehavior.NONE,
        expand=True,
    )

    ctx.manual_tabs_control = ft.Tabs(
        content=ft.Column(
            controls=[ctx.manual_tab_bar, ctx.manual_tab_view], spacing=0, expand=True
        ),
        length=2,
        expand=True,
    )
