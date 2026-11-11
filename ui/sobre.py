"""
Pórtica App - Tela Sobre.
"""

import flet as ft

from core import APP_NAME, APP_TITLE
from core.version import APP_VERSION
from ui.theme import (
    Palette,
    Spacing,
    body_large,
    body_medium,
    body_small,
    caption,
    display_large,
    icon_pill,
    overline,
    pad_all,
    pad_only,
    surface_card,
    title_medium,
)


def build_sobre(page, on_back):
    """Constroi a tela Sobre."""

    def info_card(icon_name, title, description, color=Palette.PRIMARY):
        return surface_card(
            ft.Column(
                controls=[
                    icon_pill(icon_name, bg=color, size=24),
                    ft.Container(height=Spacing.SM),
                    title_medium(title, color=Palette.TEXT_PRIMARY),
                    ft.Container(height=Spacing.XS),
                    body_small(description, color=Palette.TEXT_SECONDARY),
                ],
                spacing=0,
            ),
            padding=Spacing.XL,
        )

    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=Palette.TEXT_PRIMARY,
                    on_click=lambda e: on_back(),
                ),
                ft.Container(height=Spacing.LG),
                overline("SOBRE O APLICATIVO", color=Palette.PRIMARY),
                ft.Container(height=Spacing.XS),
                display_large(APP_NAME, color=Palette.TEXT_PRIMARY),
                ft.Container(height=Spacing.SM),
                body_large(
                    "Calculadora estrutural para dimensionamento de vigas de concreto armado. "
                    "Implementa verificações de flexão e cisalhamento conforme a NBR 6118:2023.",
                    color=Palette.TEXT_SECONDARY,
                ),
            ],
            spacing=0,
        ),
        padding=pad_all(Spacing.XXXL),
    )

    cards_row = ft.ResponsiveRow(
        controls=[
            ft.Container(
                info_card(
                    ft.Icons.CALCULATE_OUTLINED,
                    "Cálculo estrutural",
                    "Flexão e cisalhamento para vigas de seção retangular e seção T, com verificação automática dos domínios de deformação, espaçamentos mínimos e taxas de armadura.",
                    Palette.PRIMARY,
                ),
                col={"xs": 12, "md": 6, "lg": 6},
                padding=Spacing.MD,
            ),
            ft.Container(
                info_card(
                    ft.Icons.PICTURE_AS_PDF,
                    "Relatório PDF",
                    "Geração automática de relatório técnico em PDF, com cabeçalho personalizado, tabelas de dimensionamento, esquema da seção e validações visuais.",
                    Palette.SECONDARY,
                ),
                col={"xs": 12, "md": 6, "lg": 6},
                padding=Spacing.MD,
            ),
            ft.Container(
                info_card(
                    ft.Icons.DARK_MODE_OUTLINED,
                    "Interface moderna",
                    "Design Material 3 com suporte a tema claro e escuro, navegação por sidebar e componentes responsivos.",
                    Palette.INFO,
                ),
                col={"xs": 12, "md": 6, "lg": 6},
                padding=Spacing.MD,
            ),
            ft.Container(
                info_card(
                    ft.Icons.WARNING_AMBER,
                    "Aviso legal",
                    "Este software é uma ferramenta auxiliar. NÃO substitui o julgamento técnico de engenheiro civil habilitado. Sempre valide os resultados com o projeto estrutural completo e as normas vigentes.",
                    Palette.WARNING,
                ),
                col={"xs": 12, "md": 6, "lg": 6},
                padding=Spacing.MD,
            ),
        ],
        run_spacing=0,
    )

    cards_section = ft.Container(
        content=cards_row,
        padding=pad_only(left=Spacing.XXXL, right=Spacing.XXXL),
    )

    version_card = surface_card(
        ft.Column(
            controls=[
                title_medium("Informações técnicas", color=Palette.TEXT_PRIMARY),
                ft.Container(height=Spacing.SM),
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    overline("NORMA", color=Palette.TEXT_SECONDARY),
                                    body_medium("ABNT NBR 6118:2023", color=Palette.TEXT_PRIMARY),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    overline("TIPOS DE SEÇÃO", color=Palette.TEXT_SECONDARY),
                                    body_medium("Retangular e T", color=Palette.TEXT_PRIMARY),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    overline("VERSÃO", color=Palette.TEXT_SECONDARY),
                                    body_medium(APP_VERSION, color=Palette.TEXT_PRIMARY),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            expand=True,
                        ),
                    ],
                ),
            ],
            spacing=0,
        ),
        padding=Spacing.XL,
    )

    version_section = ft.Container(
        content=version_card,
        padding=pad_only(left=Spacing.XXXL, right=Spacing.XXXL, top=Spacing.LG, bottom=Spacing.LG),
    )

    # Aviso de responsabilidade (texto curto do Anexo A do planejamento).
    # O texto integral esta em DISCLAIMER.md, no repositorio.
    aviso_card = surface_card(
        ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        icon_pill(ft.Icons.WARNING_AMBER, bg=Palette.WARNING, size=24),
                        ft.Container(width=Spacing.MD),
                        ft.Column(
                            controls=[
                                title_medium(
                                    "Aviso de responsabilidade", color=Palette.TEXT_PRIMARY
                                ),
                                caption(
                                    "Ferramenta de apoio — não substitui verificação de engenheiro",
                                    color=Palette.TEXT_SECONDARY,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=Spacing.SM),
                body_small(
                    f"O {APP_TITLE} é uma ferramenta de apoio ao dimensionamento de vigas de concreto armado "
                    "conforme a ABNT NBR 6118. Os resultados devem ser verificados por engenheiro civil "
                    "habilitado, com ART/RRT, antes de qualquer uso em projeto executivo. O software é "
                    'fornecido "como está", sem garantia de adequação a um caso concreto. Os autores não '
                    "respondem por decisões de projeto tomadas com base nas saídas do programa.",
                    color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                caption(
                    "Aviso completo em DISCLAIMER.md — github.com/samuel-c-santos/portica-app",
                    color=Palette.TEXT_DISABLED,
                ),
            ],
            spacing=0,
        ),
        padding=Spacing.XL,
        bgcolor=Palette.WARNING_BG,
    )

    aviso_section = ft.Container(
        content=aviso_card,
        padding=pad_only(left=Spacing.XXXL, right=Spacing.XXXL, bottom=Spacing.XXXL),
    )

    content = ft.Column(
        controls=[header, cards_section, version_section, aviso_section],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Container(
        content=content,
        bgcolor=Palette.BG,
        expand=True,
    )
