"""
Pórtica App - Calculadora estrutural de vigas de concreto armado (NBR 6118:2023).
Interface Flet 0.85 com design Material 3 moderno.
Entry point único da aplicação unificada.
"""

import json
import os
import sys

# Garante que a raiz do projeto está no sys.path
_proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

import flet as ft

from ui.theme import Palette, Spacing, apply_light, apply_dark, is_dark, logo_path_for
from ui.sidebar import build_sidebar, ROUTE_HOME, ROUTE_VIGA, ROUTE_SOBRE
from ui.home import build_home
from ui.viga import build_viga_screen
from ui.sobre import build_sobre


from core.utils_tempfile import resource_path

APP_TITLE = "Pórtica App"

LOGO_LIGHT = resource_path(os.path.join("core", "assets", "logo.png"))
LOGO_DARK = resource_path(os.path.join("core", "assets", "logo_dark.png"))
LOGO_ICO = resource_path(os.path.join("core", "assets", "logo.ico"))


def main(page: ft.Page):
    page.title = f"{APP_TITLE} - Calculadora Estrutural"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = Palette.BG
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 1024
    page.window.min_height = 700
    # Icone da janela (preferir .ico no Windows, .png fallback)
    import platform
    icon_path = LOGO_ICO if (platform.system() == "Windows" and os.path.exists(LOGO_ICO)) else LOGO_LIGHT
    if os.path.exists(icon_path):
        page.window.icon = icon_path

    # Inicializa os FilePickers
    fp_image = ft.FilePicker()
    fp_pdf = ft.FilePicker()
    fp_load_project = ft.FilePicker()
    fp_save_project = ft.FilePicker()
    fp_dxf = ft.FilePicker()
    fp_open_home = ft.FilePicker()
    page.services.append(fp_image)
    page.services.append(fp_pdf)
    page.services.append(fp_load_project)
    page.services.append(fp_save_project)
    page.services.append(fp_dxf)
    page.services.append(fp_open_home)

    # Container de conteudo (a direita da sidebar)
    content = ft.Container(expand=True, bgcolor=Palette.BG)

    # Estado: rota atual + modo de calculo + arquivo pendente
    state = {"route": ROUTE_HOME, "modo": "comum", "pending_file": None}

    async def _open_home_file():
        files = await fp_open_home.pick_files(
            dialog_title="Abrir Projeto (.ptc)",
            allowed_extensions=["ptc"],
            file_type=ft.FilePickerFileType.CUSTOM,
            allow_multiple=False,
        )
        if files:
            navigate_to_file(files[0].path)

    def navigate_to_file(path: str):
        """Abre um projeto .ptc direto da lista de recentes."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            modo = data.get("modo", "comum")
        except Exception:
            modo = "comum"
        state["pending_file"] = path
        navigate(ROUTE_VIGA, modo)

    def navigate(route, modo=None):
        """Troca a tela mostrada no content."""
        state["route"] = route
        if modo:
            state["modo"] = modo

        # Esconde qualquer dialog aberto
        try:
            page.pop_dialog()
        except (AttributeError, RuntimeError):
            # Nenhum dialog aberto, ou Flet nao inicializou
            pass

        if route == ROUTE_HOME:
            content.content = build_home(
                page,
                on_select_mode=lambda m: navigate(ROUTE_VIGA, m),
                on_open_recent=navigate_to_file,
                on_open_file=_open_home_file,
            )
        elif route == ROUTE_VIGA:
            pending = state.pop("pending_file", None)
            content.content = build_viga_screen(
                page, state["modo"],
                on_back=lambda: navigate(ROUTE_HOME),
                fp_image=fp_image,
                fp_pdf=fp_pdf,
                fp_load_project=fp_load_project,
                fp_save_project=fp_save_project,
                fp_dxf=fp_dxf,
                initial_file=pending,
            )
        elif route == ROUTE_SOBRE:
            content.content = build_sobre(page, lambda: navigate(ROUTE_HOME))
        else:
            content.content = build_home(
                page,
                on_select_mode=lambda m: navigate(ROUTE_VIGA, m),
                on_open_recent=navigate_to_file,
                on_open_file=_open_home_file,
            )

        page.update()

    def toggle_theme():
        """Alterna entre tema claro e escuro, reconstruindo a UI."""
        if is_dark(page):
            page.theme_mode = ft.ThemeMode.LIGHT
            apply_light()
        else:
            page.theme_mode = ft.ThemeMode.DARK
            apply_dark()
        # Atualiza fundo da pagina e container principal
        page.bgcolor = Palette.BG
        content.bgcolor = Palette.BG
        # Reconstroi a sidebar (logo troca) e o content atual
        layout.controls[0] = build_sidebar(
            page, state["route"], navigate, on_toggle_theme=toggle_theme,
        )
        navigate(state["route"])

    # Layout principal: sidebar + content
    sidebar = build_sidebar(
        page, ROUTE_HOME, navigate, on_toggle_theme=toggle_theme,
    )
    layout = ft.Row(
        controls=[sidebar, content],
        spacing=0, expand=True,
    )

    page.add(layout)

    # Tela inicial
    navigate(ROUTE_HOME)


if __name__ == "__main__":
    ft.run(main)
