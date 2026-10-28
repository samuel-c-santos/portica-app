"""
Pórtica App - Tela inicial (Home / Dashboard).

Layout profissional inspirado em Revit/Word:
  - Cabeçalho com título e badge NBR
  - Dois cards de seleção de modo lado a lado,
    cada um com ilustração 3D atrás e gradiente de máscara
  - Lista de Projetos Recentes clicável abaixo
"""

import os
from datetime import datetime

import flet as ft
from ui.theme import (
    Palette, Spacing, Radius, pad_sym, pad_only, br_all,
    surface_card,
    display_large, headline_small,
    title_medium, title_small,
    body_medium, body_small,
    overline, label_small, caption,
    logo_path_for, is_dark,
    border_bottom,
    SHADOW_SM, SHADOW_LG,
)
from ui.recent_projects import get_recent, remove_recent
from core.utils_tempfile import resource_path


# ── Utilitários ───────────────────────────────────────────────────────────

def _format_accessed(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        diff = (datetime.now() - dt).days
        if diff == 0:
            return "Hoje"
        if diff == 1:
            return "Ontem"
        if diff < 7:
            return f"Há {diff} dias"
        if diff < 30:
            w = diff // 7
            return f"Há {w} semana{'s' if w > 1 else ''}"
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return "—"


def _truncate_path(path: str, max_len: int = 60) -> str:
    if len(path) <= max_len:
        return path
    return f"{path[:22]}...{path[-(max_len - 25):]}"


def _asset(name: str) -> str:
    return resource_path(os.path.join("core", "assets", name))


# ── Card de modo de cálculo ───────────────────────────────────────────────

def _mode_card(page, title, description, mode_label, accent, icon_asset, illustration_asset, on_click):
    """
    Card horizontal com:
      - Ilustração 3D posicionada à direita atrás do conteúdo
      - Gradiente da esquerda cobrindo o texto
      - Ícone PNG + badge de modo + título + descrição + botão Iniciar
    """
    bg_illustration = ft.Image(
        src=illustration_asset,
        fit=ft.BoxFit.CONTAIN,
        width=220,
        opacity=0.90,
    )

    bg_layer = ft.Container(
        content=bg_illustration,
        alignment=ft.Alignment(1.0, 0.5),   # ancorada à direita
        left=0,
        top=0,
        right=0,
        bottom=0,
    )

    # Gradiente máscara da esquerda → protege legibilidade do texto
    mask = ft.Container(
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1.0, 0),
            end=ft.Alignment(0.6, 0),
            colors=[
                Palette.SURFACE,
                Palette.SURFACE,
                ft.Colors.with_opacity(0.0, Palette.SURFACE),
            ],
            stops=[0.0, 0.55, 1.0],
        ),
        left=0,
        top=0,
        right=0,
        bottom=0,
    )

    # Ícone PNG
    icon_img = ft.Image(
        src=icon_asset,
        width=52, height=52,
        fit=ft.BoxFit.CONTAIN,
    )
    icon_box = ft.Container(
        content=icon_img,
        width=64, height=64,
        border_radius=br_all(Radius.MD),
        bgcolor=accent,
        alignment=ft.Alignment.CENTER,
        shadow=SHADOW_SM,
    )

    # Badge de modo
    badge = ft.Container(
        content=overline(mode_label, color=Palette.TEXT_SECONDARY),
        padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.XXS),
        border_radius=br_all(Radius.PILL),
        bgcolor=Palette.SURFACE_VARIANT,
    )

    # Botão iniciar — cor adaptável ao tema
    dark = is_dark(page)
    btn_bg    = accent if dark else "#0F1728"
    btn_color = Palette.TEXT_ON_DARK

    btn = ft.Container(
        content=ft.Row(
            controls=[
                title_small("Iniciar", color=btn_color),
                ft.Container(width=6),
                ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, color=btn_color, size=16),
            ],
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=btn_bg,
        padding=pad_sym(horizontal=Spacing.LG, vertical=Spacing.SM),
        border_radius=br_all(Radius.MD),
        on_click=on_click,
        ink=True,
        ink_color=ft.Colors.with_opacity(0.15, btn_color),
    )

    # Conteúdo textual (camada frontal)
    foreground = ft.Container(
        content=ft.Column(
            controls=[
                # ── Topo: ícone + badge ───────────────────────────
                ft.Row(
                    controls=[icon_box, ft.Container(expand=True), badge],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                # Espaçador flexível empurra o bloco inferior para o fundo
                ft.Container(expand=True),
                # ── Base: título + descrição + botão (alinhado à direita) ──
                ft.Column(
                    controls=[
                        # Máscara adicional para o texto garantindo legibilidade 100% sobre a ilustração
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    title_medium(title, color=Palette.TEXT_PRIMARY),
                                    ft.Container(height=Spacing.XS),
                                    body_small(description, color=Palette.TEXT_SECONDARY),
                                ],
                                spacing=0,
                            ),
                            padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
                            border_radius=br_all(Radius.MD),
                            bgcolor=ft.Colors.with_opacity(0.65, Palette.SURFACE),
                        ),
                        ft.Container(height=Spacing.MD),
                        ft.Row(
                            controls=[ft.Container(expand=True), btn],
                        ),
                    ],
                    spacing=0,
                ),
            ],
            spacing=0,
            expand=True,
        ),
        padding=pad_sym(horizontal=Spacing.XXL, vertical=Spacing.LG),
        left=0,
        top=0,
        right=0,
        bottom=0,
    )

    # Stack: fundo → máscara → frente
    stack = ft.Stack(
        controls=[bg_layer, mask, foreground],
        expand=True,
    )

    card = ft.Container(
        content=stack,
        bgcolor=Palette.SURFACE,
        border_radius=br_all(Radius.LG),
        shadow=SHADOW_LG,
        height=260,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        border=ft.Border(
            top=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            bottom=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            left=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            right=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
        ),
    )

    return card


# ── Item de projeto recente ───────────────────────────────────────────────

def _recent_item(entry: dict, mode_icon_rec, mode_icon_t, on_open, on_remove):
    path  = entry.get("path", "")
    name  = entry.get("name", os.path.basename(path))
    adate = _format_accessed(entry.get("accessed", ""))
    spath = _truncate_path(path)

    modo = entry.get("modo")
    if modo:
        is_t_beam = (modo == "t")
    else:
        is_t_beam = "viga_t" in name.lower() or name.lower().startswith("vt")

    accent = Palette.SECONDARY if is_t_beam else Palette.PRIMARY
    icon_img = ft.Image(
        src=mode_icon_t if is_t_beam else mode_icon_rec,
        width=22, height=22,
        fit=ft.BoxFit.CONTAIN,
    )
    icon_box = ft.Container(
        content=icon_img,
        width=36, height=36,
        border_radius=br_all(Radius.SM),
        bgcolor=accent,
        shadow=SHADOW_SM,
        alignment=ft.Alignment.CENTER,
    )

    info_col = ft.Column(
        controls=[
            ft.Text(
                name,
                size=13, weight=ft.FontWeight.W_600,
                color=Palette.TEXT_PRIMARY,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1, no_wrap=True,
            ),
            ft.Text(
                spath,
                size=11,
                color=Palette.TEXT_SECONDARY,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1, no_wrap=True,
            ),
        ],
        spacing=2,
        expand=True,
    )

    remove_btn = ft.IconButton(
        icon=ft.Icons.CLOSE_ROUNDED,
        icon_size=13,
        icon_color=Palette.TEXT_DISABLED,
        tooltip="Remover da lista",
        on_click=lambda e, p=path: on_remove(p),
        width=26, height=26,
        style=ft.ButtonStyle(padding=ft.Padding.all(0)),
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                icon_box,
                ft.Container(width=Spacing.MD),
                info_col,
                ft.Container(width=Spacing.SM),
                label_small(adate, color=Palette.TEXT_DISABLED),
                ft.Container(width=Spacing.XS),
                remove_btn,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=pad_sym(horizontal=Spacing.LG, vertical=10),
        border_radius=br_all(Radius.SM),
        on_click=lambda e, p=path: on_open(p),
        ink=True,
    )


# ── Tela principal ────────────────────────────────────────────────────────

def build_home(page, on_select_mode, on_open_recent=None, on_open_file=None):
    """
    Constrói a tela inicial profissional.

    Args:
        page: ft.Page
        on_select_mode: callable("comum" | "t") -> None
        on_open_recent: callable(path: str) -> None  [opcional]
        on_open_file: callable() -> None  [opcional]  abre file picker para .ptc
    """
    dark = is_dark(page)

    # Ícones brancos (claro) ficam sobre o fundo colorido do icon_box (tema claro)
    # Ícones escuros ficam sobre fundo claro/variante (tema escuro)
    icon_rec  = _asset("icon-rec-claro.png"  if not dark else "icon-rec-escuro.png")
    icon_t    = _asset("icon-t-claro.png"    if not dark else "icon-t-escuro.png")
    illus_rec = _asset("ilustracao-viga-rec.png" if not dark else "ilustracao-viga-rec-escura.png")
    illus_t   = _asset("ilustracao-viga-t.png" if not dark else "ilustracao-viga-t-escura.png")

    # ── Cabeçalho ────────────────────────────────────────────────────────

    hero_badge = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(width=7, height=7, border_radius=br_all(4), bgcolor=Palette.SUCCESS),
                ft.Container(width=6),
                overline("ABNT NBR 6118:2023", color=Palette.SUCCESS),
            ],
            tight=True,
        ),
        padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.XS),
        border_radius=br_all(Radius.PILL),
        bgcolor=Palette.SUCCESS_BG,
    )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        display_large("Pórtica", color=Palette.TEXT_PRIMARY),
                        ft.Container(height=Spacing.XS),
                        body_medium(
                            "Calculadora estrutural de vigas de concreto armado. "
                            "Dimensione flexão e cisalhamento com praticidade e rigor normativo.",
                            color=Palette.TEXT_SECONDARY,
                        ),
                    ],
                    spacing=0,
                    expand=True,
                ),
                ft.Container(width=Spacing.XL),
                hero_badge,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=pad_only(
            left=Spacing.XXXL, right=Spacing.XXXL,
            top=Spacing.XXXL, bottom=Spacing.XL,
        ),
    )

    # ── Cards de modo ─────────────────────────────────────────────────────

    card_rec = _mode_card(
        page,
        title="Seção retangular",
        description=(
            "Flexão simples e cisalhamento de vigas com seção retangular. "
            "Resultado de armaduras longitudinal e transversal."
        ),
        mode_label="VIGA COMUM",
        accent=Palette.PRIMARY,
        icon_asset=icon_rec,
        illustration_asset=illus_rec,
        on_click=lambda e: on_select_mode("comum"),
    )

    card_t = _mode_card(
        page,
        title="Seção com mesa colaborante",
        description=(
            "Largura efetiva conforme NBR 6118:15.5.2, com abas laterais b1 "
            "e verificação automática da linha neutra na mesa. "
            "Cisalhamento pela largura da alma bw."
        ),
        mode_label="VIGA T",
        accent=Palette.SECONDARY,
        icon_asset=icon_t,
        illustration_asset=illus_t,
        on_click=lambda e: on_select_mode("t"),
    )

    cards_row = ft.Container(
        content=ft.ResponsiveRow(
            controls=[
                ft.Container(card_rec, col={"xs": 12, "lg": 6}, padding=pad_only(right=Spacing.SM)),
                ft.Container(card_t,   col={"xs": 12, "lg": 6}, padding=pad_only(left=Spacing.SM)),
            ],
        ),
        padding=pad_sym(horizontal=Spacing.XXXL, vertical=0),
    )

    # ── Seção de Projetos Recentes ────────────────────────────────────────

    recent_list_col = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO)

    async def _handle_open_file(e):
        if on_open_file:
            await on_open_file()

    def refresh_recent_list():
        recent_list_col.controls.clear()
        entries = get_recent()

        if not entries:
            recent_list_col.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED, color=Palette.TEXT_DISABLED, size=36),
                            ft.Container(height=Spacing.SM),
                            body_medium("Nenhum projeto recente", color=Palette.TEXT_DISABLED),
                            ft.Container(height=Spacing.XS),
                            caption(
                                "Projetos salvos (.ptc) aparecerão aqui para acesso rápido.",
                                color=Palette.TEXT_DISABLED,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=pad_sym(vertical=Spacing.XXXL),
                )
            )
        else:
            for i, entry in enumerate(entries):
                item = _recent_item(
                    entry,
                    mode_icon_rec=icon_rec,
                    mode_icon_t=icon_t,
                    on_open=_on_open,
                    on_remove=_on_remove,
                )
                recent_list_col.controls.append(item)
                if i < len(entries) - 1:
                    recent_list_col.controls.append(
                        ft.Container(
                            height=1,
                            bgcolor=Palette.OUTLINE_VARIANT,
                            margin=pad_only(left=Spacing.LG + 36 + Spacing.MD),
                        )
                    )

    def _on_open(path: str):
        if on_open_recent:
            on_open_recent(path)

    def _on_remove(path: str):
        remove_recent(path)
        refresh_recent_list()
        try:
            page.update()
        except Exception:
            pass

    refresh_recent_list()

    recent_section = ft.Container(
        content=ft.Column(
            controls=[
                # Header da seção
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.HISTORY_ROUNDED, color=Palette.TEXT_SECONDARY, size=16),
                            ft.Container(width=Spacing.SM),
                            title_small("Projetos recentes", color=Palette.TEXT_PRIMARY),
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, color=Palette.PRIMARY, size=15),
                                        ft.Container(width=Spacing.XXS),
                                        label_small("Abrir arquivo", color=Palette.PRIMARY),
                                    ],
                                    tight=True,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.XXS),
                                border_radius=br_all(Radius.SM),
                                border=ft.BorderSide(1, Palette.PRIMARY),
                                on_click=_handle_open_file,
                                ink=True,
                                visible=on_open_file is not None,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=pad_only(bottom=Spacing.SM),
                    border=border_bottom(color=Palette.OUTLINE_VARIANT),
                    margin=pad_only(bottom=Spacing.XS),
                ),
                # Lista com scroll interno
                ft.Container(
                    content=recent_list_col,
                    height=180,
                ),
            ],
            spacing=0,
        ),
        bgcolor=Palette.SURFACE,
        border_radius=br_all(Radius.LG),
        shadow=SHADOW_SM,
        border=ft.Border(
            top=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            bottom=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            left=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            right=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
        ),
        padding=pad_sym(horizontal=Spacing.LG, vertical=Spacing.LG),
        margin=pad_sym(horizontal=Spacing.XXXL, vertical=0),
    )

    # ── Layout final ──────────────────────────────────────────────────────

    page_col = ft.Column(
        controls=[
            header,
            cards_row,
            ft.Container(height=Spacing.XL),
            recent_section,
            ft.Container(height=Spacing.XL),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.Container(
        content=page_col,
        bgcolor=Palette.BG,
        expand=True,
    )
