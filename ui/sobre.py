"""
Pórtica App - Tela Sobre.
"""

import json
import re
import threading
import urllib.request
import webbrowser

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
    outlined_button,
    overline,
    pad_all,
    pad_only,
    primary_button,
    surface_card,
    title_medium,
)

SITE_URL = "https://samuel-c-santos.github.io/portica-app/"
REPO_URL = "https://github.com/samuel-c-santos/portica-app"
RELEASES_URL = "https://github.com/samuel-c-santos/portica-app/releases"
RELEASES_LATEST_URL = "https://github.com/samuel-c-santos/portica-app/releases/latest"
RELEASES_API_LATEST_URL = "https://api.github.com/repos/samuel-c-santos/portica-app/releases/latest"
DOI_URL = "https://doi.org/10.5281/zenodo.23733497"
KOFI_URL = "https://ko-fi.com/samuelsantosportica"
PIX_KEY = "samuelsantosambiental@gmail.com"


def _parse_semver(versao: str) -> tuple[int, int, int] | None:
    """Extrai (major, minor, patch) de uma string como 'v1.0.1' ou '1.0.1'."""
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(versao or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def verificar_atualizacao_github(versao_atual: str = APP_VERSION, timeout: float = 3.0) -> dict:
    """Consulta de forma não-intrusiva a última release no GitHub Releases.

    Retorna dict com:
    - 'disponivel': True se houver tag mais recente que `versao_atual`
    - 'versao_remota': string semver da última release (ou None se offline/erro)
    - 'url': URL da página da release
    """
    atual = _parse_semver(versao_atual)
    req = urllib.request.Request(
        RELEASES_API_LATEST_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"PorticaApp/{versao_atual}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        tag = str(dados.get("tag_name") or "").lstrip("v")
        html_url = str(dados.get("html_url") or RELEASES_LATEST_URL)
        remota = _parse_semver(tag)
        if atual and remota and remota > atual:
            return {"disponivel": True, "versao_remota": tag, "url": html_url}
        return {"disponivel": False, "versao_remota": tag or None, "url": html_url}
    except Exception:
        return {"disponivel": False, "versao_remota": None, "url": RELEASES_LATEST_URL}


def _abrir_url(page, url: str) -> None:
    """Abre uma URL externa no navegador padrão com fallback seguro."""
    try:
        if page is not None and hasattr(page, "launch_url"):
            res = page.launch_url(url)
            if res is not None:
                return
    except Exception:
        pass
    try:
        webbrowser.open(url)
    except Exception:
        pass


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
                    tooltip="Voltar para o início",
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

    update_notice = caption(
        f"Versão instalada: v{APP_VERSION}. Verificação de atualização sob demanda ou automática.",
        color=Palette.TEXT_SECONDARY,
    )

    def _checar_versao_async():
        def _worker():
            info = verificar_atualizacao_github(APP_VERSION)
            if info["disponivel"] and info["versao_remota"]:
                update_notice.value = (
                    f"Nova versão v{info['versao_remota']} disponível no GitHub Releases "
                    f"(instalada: v{APP_VERSION})."
                )
                update_notice.color = Palette.PRIMARY
            elif info["versao_remota"]:
                update_notice.value = (
                    f"Você já está na versão mais recente publicada (v{APP_VERSION})."
                )
                update_notice.color = Palette.SUCCESS
            else:
                update_notice.value = f"Versão instalada: v{APP_VERSION} (sem conexão no momento para consultar o GitHub)."
                update_notice.color = Palette.TEXT_SECONDARY
            try:
                if getattr(update_notice, "page", None) is not None:
                    update_notice.update()
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    # Dispara verificação não-intrusiva em background ao abrir a tela Sobre
    if page is not None:
        _checar_versao_async()

    version_card = surface_card(
        ft.Column(
            controls=[
                title_medium("Informações técnicas e atualização", color=Palette.TEXT_PRIMARY),
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
                ft.Container(height=Spacing.MD),
                update_notice,
                ft.Container(height=Spacing.SM),
                ft.Row(
                    controls=[
                        primary_button(
                            "Baixar a versão mais recente",
                            icon=ft.Icons.DOWNLOAD,
                            on_click=lambda e: _abrir_url(page, RELEASES_LATEST_URL),
                        ),
                        outlined_button(
                            "Verificar atualizações",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda e: _checar_versao_async(),
                        ),
                    ],
                    wrap=True,
                    spacing=Spacing.SM,
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

    links_card = surface_card(
        ft.Column(
            controls=[
                title_medium(
                    "Página oficial, código-fonte, citação e doação", color=Palette.TEXT_PRIMARY
                ),
                ft.Container(height=Spacing.XS),
                body_small(
                    "Acesse a documentação do modelo de cálculo, o repositório auditável sob licença Apache-2.0, "
                    "o registro acadêmico no Zenodo (DOI) e os canais de apoio ao projeto.",
                    color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.MD),
                ft.Row(
                    controls=[
                        outlined_button(
                            "Página pública (site)",
                            icon=ft.Icons.PUBLIC,
                            on_click=lambda e: _abrir_url(page, SITE_URL),
                        ),
                        outlined_button(
                            "Repositório no GitHub",
                            icon=ft.Icons.CODE,
                            on_click=lambda e: _abrir_url(page, REPO_URL),
                        ),
                        outlined_button(
                            "Releases e downloads",
                            icon=ft.Icons.FOLDER_ZIP_OUTLINED,
                            on_click=lambda e: _abrir_url(page, RELEASES_URL),
                        ),
                        outlined_button(
                            "DOI / Citação (Zenodo)",
                            icon=ft.Icons.SCHOOL_OUTLINED,
                            on_click=lambda e: _abrir_url(page, DOI_URL),
                        ),
                        outlined_button(
                            "Doar via Ko-fi",
                            icon=ft.Icons.FAVORITE_BORDER,
                            on_click=lambda e: _abrir_url(page, KOFI_URL),
                        ),
                    ],
                    wrap=True,
                    spacing=Spacing.SM,
                ),
                ft.Container(height=Spacing.MD),
                caption(
                    f"DOI: 10.5281/zenodo.23733497 · Chave Pix (e-mail): {PIX_KEY} · "
                    "Privacidade: sem rastreadores, sem cookies e sem telemetria.",
                    color=Palette.TEXT_SECONDARY,
                ),
            ],
            spacing=0,
        ),
        padding=Spacing.XL,
    )

    links_section = ft.Container(
        content=links_card,
        padding=pad_only(left=Spacing.XXXL, right=Spacing.XXXL, bottom=Spacing.LG),
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
                    "habilitado, com ART, antes de qualquer uso em projeto executivo. O software é "
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
        controls=[header, cards_section, version_section, links_section, aviso_section],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Container(
        content=content,
        bgcolor=Palette.BG,
        expand=True,
    )
