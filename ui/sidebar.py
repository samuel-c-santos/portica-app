"""
Pórtica App - Sidebar de navegação persistente.
"""

import flet as ft
from core.version import APP_VERSION

from ui.theme import (
    Palette, Spacing, Radius, pad_sym, pad_only, br_all, SHADOW_SM,
    icon_pill, icon, logo_path_for, is_dark,
)


# IDs das rotas de navegação
ROUTE_HOME     = "home"
ROUTE_VIGA     = "viga"
ROUTE_SOBRE    = "sobre"


def build_sidebar(page, current_route, on_navigate, on_toggle_theme=None):
    """
    Constroi a sidebar vertical fixa à esquerda.
    current_route: string (ROUTE_*)
    on_navigate: callable(str) -> None
    on_toggle_theme: callable() -> None  (opcional, botao de tema)
    """

    def nav_item(route, label, icon_name, accent=Palette.PRIMARY):
        is_active = current_route == route
        bg = Palette.PRIMARY if is_active else Palette.SURFACE
        fg = Palette.ON_PRIMARY if is_active else Palette.TEXT_SECONDARY
        icon_color = Palette.ON_PRIMARY if is_active else Palette.TEXT_SECONDARY
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(icon_name, color=icon_color, size=22),
                    ft.Container(
                        content=ft.Text(
                            label,
                            size=10, weight=ft.FontWeight.W_600,
                            color=fg, text_align=ft.TextAlign.CENTER,
                        ),
                        margin=ft.Margin.only(top=2),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            width=76, height=68, border_radius=br_all(Radius.MD),
            bgcolor=bg, alignment=ft.Alignment.CENTER,
            ink=True, on_click=lambda e, r=route: on_navigate(r),
        )

    # Logo (topo) - usa logo claro ou escuro conforme tema
    logo = ft.Image(
        src=logo_path_for(page),
        width=44, height=44,
        fit=ft.BoxFit.CONTAIN,
    )
    header = ft.Container(
        content=logo,
        padding=pad_only(top=Spacing.LG, bottom=Spacing.LG),
        alignment=ft.Alignment.CENTER,
    )

    # Itens de navegação
    items = ft.Column(
        controls=[
            nav_item(ROUTE_HOME, "Inicio", ft.Icons.HOME_OUTLINED),
            ft.Container(height=Spacing.SM),
            nav_item(ROUTE_VIGA, "Viga", ft.Icons.CALCULATE_OUTLINED),
            ft.Container(height=Spacing.SM),
            nav_item(ROUTE_SOBRE, "Sobre", ft.Icons.INFO_OUTLINE),
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # Spacer
    spacer = ft.Container(expand=True)

    # Botao de toggle de tema
    theme_btn = None
    if on_toggle_theme is not None:
        dark = is_dark(page)
        theme_btn = ft.Container(
            content=ft.IconButton(
                icon=ft.Icons.DARK_MODE if not dark else ft.Icons.LIGHT_MODE,
                icon_color=Palette.TEXT_SECONDARY,
                tooltip="Mudar para tema escuro" if not dark else "Mudar para tema claro",
                on_click=lambda e: on_toggle_theme(),
                icon_size=20,
            ),
            width=44, height=44, border_radius=br_all(22),
            bgcolor=Palette.SURFACE_VARIANT,
            alignment=ft.Alignment.CENTER,
        )

    # Versão (rodapé)
    footer = ft.Container(
        content=ft.Text(
            f"v{APP_VERSION}",

            size=10, weight=ft.FontWeight.W_500,
            color=Palette.TEXT_DISABLED, text_align=ft.TextAlign.CENTER,
        ),
        padding=pad_only(bottom=Spacing.LG),
    )

    bottom_controls = []
    if theme_btn is not None:
        bottom_controls.append(theme_btn)
        bottom_controls.append(ft.Container(height=Spacing.SM))
    bottom_controls.append(footer)

    return ft.Container(
        content=ft.Column(
            controls=[header, items, spacer, *bottom_controls],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        width=88,
        bgcolor=Palette.SURFACE,
        shadow=ft.BoxShadow(
            spread_radius=0, blur_radius=8, offset=ft.Offset(2, 0),
            color=Palette.SHADOW,
        ),
    )
