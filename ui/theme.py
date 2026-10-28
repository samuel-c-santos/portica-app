"""
Pórtica App - Sistema de design e tema visual.
Cores, tipografia, espaçamentos e helpers de componentes para a UI Flet 0.85.
"""

import flet as ft


# ── Paleta de cores ────────────────────────────────────────────────────────
# Inspirada em Material 3. A classe Palette e preenchida dinamicamente
# por apply_light()/apply_dark(), permitindo troca de tema em runtime.
LIGHT_COLORS = {
    "PRIMARY":          "#1565C0",
    "PRIMARY_DARK":     "#0D47A1",
    "PRIMARY_LIGHT":    "#5E92F3",
    "ON_PRIMARY":       "#FFFFFF",

    "SECONDARY":        "#6A1B9A",
    "SECONDARY_DARK":   "#4A148C",
    "SECONDARY_LIGHT":  "#9F4DCA",
    "ON_SECONDARY":     "#FFFFFF",

    "SUCCESS":          "#2E7D32",
    "SUCCESS_LIGHT":    "#60AD5E",
    "SUCCESS_BG":       "#E8F5E9",
    "ON_SUCCESS":       "#FFFFFF",

    "WARNING":          "#E65100",
    "WARNING_LIGHT":    "#FF8A50",
    "WARNING_BG":       "#FFF3E0",
    "ON_WARNING":       "#FFFFFF",

    "ERROR":            "#C62828",
    "ERROR_LIGHT":      "#FF5F52",
    "ERROR_BG":         "#FFEBEE",
    "ON_ERROR":         "#FFFFFF",

    "INFO":             "#0277BD",
    "INFO_BG":          "#E1F5FE",

    "BG":              "#F5F7FA",
    "SURFACE":         "#FFFFFF",
    "SURFACE_VARIANT": "#ECEFF1",
    "SURFACE_HOVER":   "#F5F5F5",
    "OUTLINE":         "#CFD8DC",
    "OUTLINE_VARIANT": "#E0E0E0",
    "TEXT_PRIMARY":    "#212121",
    "TEXT_SECONDARY":  "#5F6368",
    "TEXT_DISABLED":   "#9E9E9E",
    "TEXT_ON_DARK":    "#FFFFFF",
    "SHADOW":          "#00000014",
}

DARK_COLORS = {
    "PRIMARY":          "#82B1FF",
    "PRIMARY_DARK":     "#448AFF",
    "PRIMARY_LIGHT":    "#1565C0",
    "ON_PRIMARY":       "#000000",

    "SECONDARY":        "#CE93D8",
    "SECONDARY_DARK":   "#9F4DCA",
    "SECONDARY_LIGHT":  "#6A1B9A",
    "ON_SECONDARY":     "#000000",

    "SUCCESS":          "#81C784",
    "SUCCESS_LIGHT":    "#2E7D32",
    "SUCCESS_BG":       "#1B3620",
    "ON_SUCCESS":       "#000000",

    "WARNING":          "#FFB74D",
    "WARNING_LIGHT":    "#E65100",
    "WARNING_BG":       "#3E2723",
    "ON_WARNING":       "#000000",

    "ERROR":            "#EF9A9A",
    "ERROR_LIGHT":      "#C62828",
    "ERROR_BG":         "#3B1212",
    "ON_ERROR":         "#000000",

    "INFO":             "#4FC3F7",
    "INFO_BG":          "#013C50",

    "BG":              "#0F1419",
    "SURFACE":         "#1A1F26",
    "SURFACE_VARIANT": "#232934",
    "SURFACE_HOVER":   "#2A3038",
    "OUTLINE":         "#3A4250",
    "OUTLINE_VARIANT": "#2C3440",
    "TEXT_PRIMARY":    "#E8EAED",
    "TEXT_SECONDARY":  "#B0B7C3",
    "TEXT_DISABLED":   "#5F6368",
    "TEXT_ON_DARK":    "#FFFFFF",
    "SHADOW":          "#00000033",
}


class Palette:
    """Paleta ativa. Atributos sao preenchidos por apply_light/apply_dark."""
    pass


def apply_light():
    for k, v in LIGHT_COLORS.items():
        setattr(Palette, k, v)


def apply_dark():
    for k, v in DARK_COLORS.items():
        setattr(Palette, k, v)


# Inicializa com tema claro
apply_light()


def is_dark(page) -> bool:
    """Verifica se o tema atual e escuro."""
    try:
        return page.theme_mode == ft.ThemeMode.DARK
    except (AttributeError, TypeError):
        # page.theme_mode inacessivel (Flet nao inicializou)
        return False


def logo_path_for(page) -> str:
    """Caminho do logo apropriado para o tema atual."""
    import os
    from core.utils_tempfile import resource_path
    name = "logo_dark.png" if is_dark(page) else "logo.png"
    return resource_path(os.path.join("core", "assets", name))


# ── Tipografia ─────────────────────────────────────────────────────────────
class Type:
    DISPLAY_LG  = ("Roboto", 32, ft.FontWeight.W_700)
    HEADLINE_LG = ("Roboto", 28, ft.FontWeight.W_700)
    HEADLINE_MD = ("Roboto", 24, ft.FontWeight.W_600)
    HEADLINE_SM = ("Roboto", 20, ft.FontWeight.W_600)
    TITLE_LG    = ("Roboto", 18, ft.FontWeight.W_600)
    TITLE_MD    = ("Roboto", 16, ft.FontWeight.W_600)
    TITLE_SM    = ("Roboto", 14, ft.FontWeight.W_600)
    BODY_LG     = ("Roboto", 16, ft.FontWeight.W_400)
    BODY_MD     = ("Roboto", 14, ft.FontWeight.W_400)
    BODY_SM     = ("Roboto", 13, ft.FontWeight.W_400)
    LABEL_LG    = ("Roboto", 14, ft.FontWeight.W_500)
    LABEL_MD    = ("Roboto", 13, ft.FontWeight.W_500)
    LABEL_SM    = ("Roboto", 12, ft.FontWeight.W_500)
    CAPTION     = ("Roboto", 12, ft.FontWeight.W_400)
    OVERLINE    = ("Roboto", 11, ft.FontWeight.W_500)


# ── Espaçamento (8pt grid) ────────────────────────────────────────────────
class Spacing:
    XXS = 2
    XS  = 4
    SM  = 8
    MD  = 12
    LG  = 16
    XL  = 24
    XXL = 32
    XXXL = 48


# ── Raios de borda ─────────────────────────────────────────────────────────
class Radius:
    SM  = 6
    MD  = 10
    LG  = 16
    XL  = 24
    PILL = 999


# ── Sombras ────────────────────────────────────────────────────────────────
SHADOW_SM = ft.BoxShadow(
    spread_radius=0, blur_radius=4, offset=ft.Offset(0, 1),
    color=Palette.SHADOW,
)
SHADOW_MD = ft.BoxShadow(
    spread_radius=0, blur_radius=10, offset=ft.Offset(0, 4),
    color=Palette.SHADOW,
)
SHADOW_LG = ft.BoxShadow(
    spread_radius=0, blur_radius=20, offset=ft.Offset(0, 8),
    color=Palette.SHADOW,
)


# ── Helpers de padding/border (Flet 0.85 keyword-only) ────────────────────
def pad_sym(horizontal=0, vertical=0):
    return ft.Padding.symmetric(horizontal=horizontal, vertical=vertical)


def pad_only(left=0, top=0, right=0, bottom=0):
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)


def pad_all(value):
    return ft.Padding.all(value)


def br_only(top_left=0, top_right=0, bottom_left=0, bottom_right=0):
    return ft.BorderRadius.only(
        top_left=top_left, top_right=top_right,
        bottom_left=bottom_left, bottom_right=bottom_right,
    )


def br_all(value):
    return ft.BorderRadius.all(value)


def border_all(width=1, color=Palette.OUTLINE_VARIANT):
    """Helper para ft.border.all (Flet 0.85: Border(...) com N BorderSides)."""
    return ft.Border(
        top=ft.BorderSide(width, color),
        right=ft.BorderSide(width, color),
        bottom=ft.BorderSide(width, color),
        left=ft.BorderSide(width, color),
    )


def border_bottom(width=1, color=Palette.OUTLINE_VARIANT):
    return ft.Border(bottom=ft.BorderSide(width, color))


# ── Card estilizado com sombra suave ───────────────────────────────────────
def surface_card(
    content,
    *,
    padding=Spacing.LG,
    bgcolor=None,
    radius=Radius.MD,
    shadow=SHADOW_SM,
    on_click=None,
    ink_color=None,
):
    """Card com fundo branco, sombra sutil e cantos arredondados."""
    container = ft.Container(
        content=content,
        bgcolor=bgcolor or Palette.SURFACE,
        padding=padding,
        border_radius=br_all(radius),
        shadow=shadow,
    )
    if on_click is not None:
        container.on_click = on_click
        container.ink = True
        if ink_color is not None:
            container.ink_color = ink_color
    return container


# ── Botões estilizados ─────────────────────────────────────────────────────
def primary_button(text, on_click=None, *, icon=None, expand=False, disabled=False):
    return ft.Button(
        text,
        on_click=on_click,
        icon=icon,
        style=ft.ButtonStyle(
            bgcolor=Palette.PRIMARY,
            color=Palette.ON_PRIMARY,
            padding=pad_sym(horizontal=Spacing.XL, vertical=Spacing.MD),
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.MD)),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        expand=expand,
        disabled=disabled,
    )


def tonal_button(text, on_click=None, *, icon=None, expand=False, disabled=False):
    return ft.Button(
        text,
        on_click=on_click,
        icon=icon,
        style=ft.ButtonStyle(
            bgcolor=Palette.PRIMARY_LIGHT,
            color=Palette.ON_PRIMARY,
            padding=pad_sym(horizontal=Spacing.XL, vertical=Spacing.MD),
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.MD)),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        expand=expand,
        disabled=disabled,
    )


def outlined_button(text, on_click=None, *, icon=None, expand=False, disabled=False):
    return ft.Button(
        text,
        on_click=on_click,
        icon=icon,
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, Palette.OUTLINE),
            color=Palette.TEXT_PRIMARY,
            padding=pad_sym(horizontal=Spacing.XL, vertical=Spacing.MD),
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.MD)),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
        ),
        expand=expand,
        disabled=disabled,
    )


def success_button(text, on_click=None, *, icon=None, expand=False, disabled=False):
    return ft.Button(
        text,
        on_click=on_click,
        icon=icon,
        style=ft.ButtonStyle(
            bgcolor=Palette.SUCCESS,
            color=Palette.ON_SUCCESS,
            padding=pad_sym(horizontal=Spacing.XL, vertical=Spacing.MD),
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.MD)),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        expand=expand,
        disabled=disabled,
    )


# ── Textos estilizados ─────────────────────────────────────────────────────
def text(content, *, size=14, weight=ft.FontWeight.W_400, color=None,
         text_align=None, max_lines=None, overflow=None, **kwargs):
    style = ft.TextStyle(size=size, weight=weight)
    if color is not None:
        style.color = color
    return ft.Text(
        content, style=style, text_align=text_align,
        max_lines=max_lines, overflow=overflow, **kwargs,
    )


def display_large(s, color=None, **kwargs):
    return text(s, size=Type.DISPLAY_LG[1], weight=Type.DISPLAY_LG[2], color=color, **kwargs)


def headline_large(s, color=None, **kwargs):
    return text(s, size=Type.HEADLINE_LG[1], weight=Type.HEADLINE_LG[2], color=color, **kwargs)


def headline_medium(s, color=None, **kwargs):
    return text(s, size=Type.HEADLINE_MD[1], weight=Type.HEADLINE_MD[2], color=color, **kwargs)


def headline_small(s, color=None, **kwargs):
    return text(s, size=Type.HEADLINE_SM[1], weight=Type.HEADLINE_SM[2], color=color, **kwargs)


def title_large(s, color=None, **kwargs):
    return text(s, size=Type.TITLE_LG[1], weight=Type.TITLE_LG[2], color=color, **kwargs)


def title_medium(s, color=None, **kwargs):
    return text(s, size=Type.TITLE_MD[1], weight=Type.TITLE_MD[2], color=color, **kwargs)


def title_small(s, color=None, **kwargs):
    return text(s, size=Type.TITLE_SM[1], weight=Type.TITLE_SM[2], color=color, **kwargs)


def body_large(s, color=None, **kwargs):
    return text(s, size=Type.BODY_LG[1], weight=Type.BODY_LG[2], color=color, **kwargs)


def body_medium(s, color=None, **kwargs):
    return text(s, size=Type.BODY_MD[1], weight=Type.BODY_MD[2], color=color, **kwargs)


def body_small(s, color=None, **kwargs):
    return text(s, size=Type.BODY_SM[1], weight=Type.BODY_SM[2], color=color, **kwargs)


def label_large(s, color=None, **kwargs):
    return text(s, size=Type.LABEL_LG[1], weight=Type.LABEL_LG[2], color=color, **kwargs)


def label_medium(s, color=None, **kwargs):
    return text(s, size=Type.LABEL_MD[1], weight=Type.LABEL_MD[2], color=color, **kwargs)


def label_small(s, color=None, **kwargs):
    return text(s, size=Type.LABEL_SM[1], weight=Type.LABEL_SM[2], color=color, **kwargs)


def caption(s, color=None, **kwargs):
    return text(s, size=Type.CAPTION[1], weight=Type.CAPTION[2], color=color, **kwargs)


def overline(s, color=None, **kwargs):
    return text(s, size=Type.OVERLINE[1], weight=Type.OVERLINE[2], color=color, **kwargs)


# ── Icon helpers ───────────────────────────────────────────────────────────
def icon(name, *, color=None, size=20):
    return ft.Icon(name, color=color, size=size)


# ── Status badge (chip) ────────────────────────────────────────────────────
def status_chip(label, status):
    """status: 'ok' | 'warn' | 'error' | 'info'"""
    colors = {
        "ok":   (Palette.SUCCESS_BG, Palette.SUCCESS),
        "warn": (Palette.WARNING_BG, Palette.WARNING),
        "error":(Palette.ERROR_BG,   Palette.ERROR),
        "info": (Palette.INFO_BG,    Palette.INFO),
    }
    bg, fg = colors.get(status, colors["info"])
    return ft.Container(
        content=label_small(label, color=fg),
        bgcolor=bg,
        padding=pad_sym(horizontal=Spacing.SM, vertical=Spacing.XS),
        border_radius=br_all(Radius.PILL),
    )


# ── Divisor com label (section header) ───────────────────────────────────
def section_header(title, *, icon=None, action=None):
    items = []
    if icon is not None:
        items.append(icon)
    items.append(title_small(title, color=Palette.TEXT_SECONDARY))
    spacer = ft.Container(expand=True) if action is not None else None
    if spacer is not None:
        items.append(spacer)
    if action is not None:
        items.append(action)
    return ft.Container(
        content=ft.Row(items, spacing=Spacing.SM, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=pad_only(left=4, bottom=Spacing.SM),
    )


# ── Campo de input estilizado (label acima do input) ─────────────────────
def field(label_text, control, *, hint=None):
    children = [label_medium(label_text, color=Palette.TEXT_SECONDARY)]
    children.append(control)
    if hint:
        children.append(caption(hint, color=Palette.TEXT_DISABLED))
    return ft.Column(children, spacing=Spacing.XS)


# ── Botao de info (abre dialog com tabela) ─────────────────────────────────
def info_button(on_click, *, tooltip="Ver tabela"):
    return ft.IconButton(
        icon=ft.Icons.INFO_OUTLINE,
        icon_color=Palette.PRIMARY,
        tooltip=tooltip,
        on_click=on_click,
        icon_size=18,
    )


# ── Icone em pílula colorida (para cards de modo) ─────────────────────────
def icon_pill(icon_name, *, bg=Palette.PRIMARY, fg=Palette.ON_PRIMARY, size=28):
    return ft.Container(
        content=ft.Icon(icon_name, color=fg, size=size),
        width=56, height=56, border_radius=br_all(28),
        bgcolor=bg, alignment=ft.Alignment.CENTER,
    )
