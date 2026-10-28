"""
Pórtica App - Dialogs de informacao com tabelas NBR.
"""

import flet as ft
from ui.theme import (
    Palette, Spacing, Radius, pad_sym, pad_only, pad_all, br_all,
    title_medium, title_small, body_medium, body_small, caption,
)
from ui.tables import (
    TABELA_CAA, TABELA_COBRIMENTO, TABELA_RHO_MIN, TABELA_DIAMETROS,
    TABELA_FCK, TABELA_ACO, TABELA_GAMMA_F,
    INFO_GEOMETRIA, INFO_VIGA_T, INFO_B1,
)


def _build_table(data):
    """Renderiza uma tabela NBR como ListView formatada."""
    header_row = ft.Row(
        controls=[
            ft.Container(
                content=title_small(c, color=Palette.ON_PRIMARY),
                bgcolor=Palette.PRIMARY,
                padding=pad_sym(horizontal=Spacing.SM, vertical=Spacing.SM),
                border_radius=br_all(Radius.SM),
                expand=True,
                alignment=ft.Alignment.CENTER,
            ) for c in data["cabecalho"]
        ],
        spacing=Spacing.XS,
    )

    body_rows = []
    for i, linha in enumerate(data["linhas"]):
        bg = Palette.SURFACE_VARIANT if i % 2 == 0 else Palette.SURFACE
        row = ft.Row(
            controls=[
                ft.Container(
                    content=body_small(c, color=Palette.TEXT_PRIMARY, text_align=ft.TextAlign.CENTER),
                    bgcolor=bg,
                    padding=pad_sym(horizontal=Spacing.SM, vertical=Spacing.SM),
                    border_radius=br_all(Radius.SM),
                    expand=True,
                ) for c in linha
            ],
            spacing=Spacing.XS,
        )
        body_rows.append(row)

    notas = []
    if "notas" in data:
        for n in data["notas"]:
            notas.append(
                ft.Container(
                    content=caption(n, color=Palette.TEXT_SECONDARY),
                    padding=pad_only(top=Spacing.XS),
                )
            )

    return ft.Column(
        controls=[
            title_medium(data["titulo"], color=Palette.TEXT_PRIMARY),
            ft.Container(height=Spacing.SM),
            header_row,
            ft.Container(height=Spacing.XS),
            *body_rows,
            ft.Container(height=Spacing.SM),
            caption(data["fonte"], color=Palette.TEXT_DISABLED),
            *notas,
        ],
        spacing=0,
    )


def open_image_preview(page, img_path, title="Visualizacao da imagem"):
    """Exibe um dialogo modal com a imagem em tamanho expandido."""
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.ZOOM_IN, color=Palette.PRIMARY),
                ft.Container(width=Spacing.SM),
                title_medium(title),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            content=ft.Image(
                src=img_path,
                fit=ft.BoxFit.CONTAIN,
            ),
            width=720,
            height=540,
            padding=pad_all(Spacing.SM),
        ),
        actions=[
            ft.TextButton(
                "Fechar",
                on_click=lambda e: page.pop_dialog(),
                style=ft.ButtonStyle(color=Palette.PRIMARY),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=Palette.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
    )
    page.show_dialog(dialog)


def build_info_dialog(page, data):
    """Constroi e exibe um dialog com a tabela NBR."""
    content = _build_table(data)

    if "imagem" in data:
        import os
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(here, "assets", "info", data["imagem"])
        if os.path.exists(img_path):
            content.controls.append(ft.Container(height=Spacing.MD))
            content.controls.append(
                ft.Container(
                    content=ft.Image(
                        src=img_path,
                        fit=ft.BoxFit.CONTAIN,
                        height=200,
                    ),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda e, path=img_path, t=data["titulo"]: open_image_preview(page, path, t),
                    tooltip="Clique para ampliar",
                )
            )

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.MENU_BOOK, color=Palette.PRIMARY),
                ft.Container(width=Spacing.SM),
                title_medium("Informacao tecnica"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[content],
                scroll=ft.ScrollMode.AUTO,
            ),
            width=520, padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
        ),
        actions=[
            ft.TextButton(
                "Fechar",
                on_click=lambda e: page.pop_dialog(),
                style=ft.ButtonStyle(color=Palette.PRIMARY),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=Palette.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
    )
    page.show_dialog(dialog)


def open_caa_info(page):
    build_info_dialog(page, TABELA_CAA)


def open_cobrimento_info(page):
    build_info_dialog(page, TABELA_COBRIMENTO)


def open_rho_min_info(page):
    build_info_dialog(page, TABELA_RHO_MIN)


def open_diametros_info(page):
    build_info_dialog(page, TABELA_DIAMETROS)


def open_fck_info(page):
    build_info_dialog(page, TABELA_FCK)


def open_aco_info(page):
    build_info_dialog(page, TABELA_ACO)


def open_gamma_f_info(page):
    build_info_dialog(page, TABELA_GAMMA_F)


# ── Dialogs textuais (conteudo explicativo, nao-tabular) ────────────────────

def _build_text_content(data):
    """Renderiza conteudo textual com secoes (titulo + paragrafo)."""
    items = [title_medium(data["titulo"], color=Palette.TEXT_PRIMARY)]
    items.append(ft.Container(height=Spacing.SM))
    for sec in data["secoes"]:
        items.append(title_small(sec["titulo"], color=Palette.PRIMARY))
        items.append(ft.Container(height=Spacing.XXS))
        items.append(
            body_medium(sec["texto"], color=Palette.TEXT_SECONDARY)
        )
        items.append(ft.Container(height=Spacing.MD))
    items.append(caption(data["fonte"], color=Palette.TEXT_DISABLED))
    return ft.Column(controls=items, spacing=0)


def build_text_dialog(page, data):
    """Constroi e exibe um dialog com conteudo textual explicativo."""
    content = _build_text_content(data)

    if "imagem" in data:
        import os
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(here, "assets", "info", data["imagem"])
        if os.path.exists(img_path):
            content.controls.append(ft.Container(height=Spacing.MD))
            content.controls.append(
                ft.Container(
                    content=ft.Image(
                        src=img_path,
                        fit=ft.BoxFit.CONTAIN,
                        height=200,
                    ),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda e, path=img_path, t=data["titulo"]: open_image_preview(page, path, t),
                    tooltip="Clique para ampliar",
                )
            )

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.MENU_BOOK, color=Palette.PRIMARY),
                ft.Container(width=Spacing.SM),
                title_medium("Informacao tecnica"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[content],
                scroll=ft.ScrollMode.AUTO,
            ),
            width=520, padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
        ),
        actions=[
            ft.TextButton(
                "Fechar",
                on_click=lambda e: page.pop_dialog(),
                style=ft.ButtonStyle(color=Palette.PRIMARY),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=Palette.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
    )
    page.show_dialog(dialog)


def open_geometria_info(page):
    build_text_dialog(page, INFO_GEOMETRIA)


def open_viga_t_info(page):
    build_text_dialog(page, INFO_VIGA_T)


def open_b1_info(page):
    build_text_dialog(page, INFO_B1)
