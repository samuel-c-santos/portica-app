"""Componentes de input reutilizaveis e abridores de dialogos da tela de viga."""

import os

import flet as ft

from core.calculos import (
    CAA_DATA,
    GAMMA_F_TABLE,
)
from ui.theme import (
    Palette,
    Radius,
    Spacing,
    br_all,
    caption,
    section_header,
    surface_card,
)

MAX_TRECHOS = 20
DEFAULT_TRECHOS = 3


# ── Componentes de input reutilizáveis ─────────────────────────────────────


class _StyledContainer(ft.Container):
    """Container que envolve um TextField/Dropdown com botao de info opcional.
    Expoe o controle via .control para acesso direto a .value."""

    def __init__(self, control, info_btn=None):
        self.control = control
        controls = []
        # O input ocupa todo o espaco disponivel
        control.expand = True
        controls.append(control)
        if info_btn is not None:
            controls.append(info_btn)
        super().__init__(
            content=ft.Row(
                controls,
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=0,
        )


def _on_change_br(original_on_change):
    """Wrapper que substitui ponto por vírgula antes de chamar o on_change original.

    Permite que o usuário digite 135.9 ou 135,9 — ambos são interpretados como 135.9.
    """

    def wrapper(e):
        # Substitui ponto por vírgula no valor digitado
        e.control.value = e.control.value.replace(".", ",")
        if original_on_change:
            original_on_change(e)

    return wrapper


def _styled_textfield(
    label_text,
    value,
    *,
    hint="",
    on_change=None,
    info_on_click=None,
    keyboard_type=ft.KeyboardType.NUMBER,
    max_length=None,
):
    """TextField com label, valor default e opcional botao de info.
    Retorna Container que expoe .control (o TextField) para acesso a .value."""
    info_btn = None
    if info_on_click is not None:
        info_btn = ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            icon_color=Palette.PRIMARY,
            icon_size=16,
            tooltip="Ver tabela",
            on_click=info_on_click,
        )

    # Campos numéricos: substitui ponto por vírgula automaticamente
    wrapped_on_change = (
        _on_change_br(on_change) if keyboard_type == ft.KeyboardType.NUMBER else on_change
    )

    tf = ft.TextField(
        label=label_text,
        value=str(value),
        border_radius=br_all(Radius.SM),
        text_size=14,
        filled=True,
        dense=True,
        bgcolor=Palette.SURFACE_VARIANT,
        border_color=Palette.OUTLINE_VARIANT,
        focused_border_color=Palette.PRIMARY,
        cursor_color=Palette.PRIMARY,
        keyboard_type=keyboard_type,
        hint_text=hint,
        on_change=wrapped_on_change,
        expand=True,
        max_length=max_length,
    )
    return _StyledContainer(tf, info_btn)


def _styled_dropdown(label_text, value, options, *, on_change=None, info_on_click=None):
    """Dropdown com label e opcional botao de info.
    Retorna Container que expoe .control (o Dropdown) para acesso a .value."""
    info_btn = None
    if info_on_click is not None:
        info_btn = ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            icon_color=Palette.PRIMARY,
            icon_size=16,
            tooltip="Ver tabela",
            on_click=info_on_click,
        )
    dd = ft.Dropdown(
        label=label_text,
        value=value,
        options=options,
        border_radius=br_all(Radius.SM),
        filled=True,
        dense=True,
        bgcolor=Palette.SURFACE_VARIANT,
        border_color=Palette.OUTLINE_VARIANT,
        focused_border_color=Palette.PRIMARY,
        text_size=14,
        on_select=on_change,
        expand=True,
    )
    return _StyledContainer(dd, info_btn)


def _make_options(values, formatter=None):
    return [ft.dropdown.Option(str(v), formatter(v) if formatter else str(v)) for v in values]


def _make_caa_options():
    return [ft.dropdown.Option(str(k), f"CAA {k} - {v['nome']}") for k, v in CAA_DATA.items()]


def _make_gamma_f_options():
    return [
        ft.dropdown.Option(k, f"{v['nome']} (gf = {v['gamma_f']})")
        for k, v in GAMMA_F_TABLE.items()
    ]


def _build_illustrations_panel(page, title, subtitle, image_specs):
    """Cria um card contendo ilustrações técnicas com legendas clicáveis para ampliar."""
    from core.utils_tempfile import resource_path
    from ui.dialogs import open_image_preview

    assets_root = resource_path("core/assets/info")

    controls = [
        section_header(
            title, icon=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=Palette.TEXT_SECONDARY)
        ),
        caption(subtitle, color=Palette.TEXT_SECONDARY),
        ft.Container(height=Spacing.SM),
    ]

    for i, spec in enumerate(image_specs):
        filename, label = spec
        img_path = os.path.join(assets_root, filename)
        if os.path.exists(img_path):
            if i > 0:
                controls.append(ft.Container(height=Spacing.SM))
                controls.append(ft.Divider(color=Palette.OUTLINE_VARIANT, height=1))
                controls.append(ft.Container(height=Spacing.SM))

            # Local click handler helper
            def make_click_handler(path, title_text):
                return lambda e: open_image_preview(page, path, title_text)

            controls.append(
                ft.Container(
                    content=ft.Image(
                        src=img_path,
                        fit=ft.BoxFit.CONTAIN,
                        border_radius=br_all(Radius.SM),
                        height=160 if len(image_specs) > 1 else 320,
                    ),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=make_click_handler(img_path, label),
                    tooltip="Clique para ampliar",
                )
            )
            controls.append(ft.Container(height=Spacing.XXS))
            controls.append(
                caption(label, color=Palette.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER)
            )

    return surface_card(
        ft.Column(
            controls=controls,
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=Spacing.LG,
    )


# ── Helpers de dialogs NBR (locais para evitar dependencia circular) ──────


def _open_caa(page):
    from ui.dialogs import open_caa_info

    open_caa_info(page)


def _open_cobrimento(page):
    from ui.dialogs import open_cobrimento_info

    open_cobrimento_info(page)


def _open_diametros(page):
    from ui.dialogs import open_diametros_info

    open_diametros_info(page)


def _open_fck(page):
    from ui.dialogs import open_fck_info

    open_fck_info(page)


def _open_aco(page):
    from ui.dialogs import open_aco_info

    open_aco_info(page)


def _open_gamma_f(page):
    from ui.dialogs import open_gamma_f_info

    open_gamma_f_info(page)


def _open_geometria(page):
    from ui.dialogs import open_geometria_info

    open_geometria_info(page)


def _open_viga_t(page):
    from ui.dialogs import open_viga_t_info

    open_viga_t_info(page)


def _open_b1(page):
    from ui.dialogs import open_b1_info

    open_b1_info(page)
