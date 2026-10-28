"""Testes da fonte de entrada da viga (manual | FTOOL) - F1b / decisao D2.

Cobre:
- .ptc antigo (sem a chave "entrada") carrega como "manual" (retrocompatibilidade);
- .ptc com "entrada": "ftool" ajusta estado e visibilidade do painel FTOOL;
- "edicao": "standard" e "edicao": "premium" sao ambos aceitos na carga;
- o painel FTOOL fica recolhido por padrao e pode ser revelado/fechado;
- o caminho manual (tabela de trechos + Calcular) continua acessivel.
"""
import asyncio
import json
import os
from types import SimpleNamespace

import pytest

from ui.entrada import (
    ENTRADA_FTOOL,
    ENTRADA_MANUAL,
    aplicar_entrada_projeto,
    aviso_edicao,
    edicao_aceita,
    entrada_de_projeto,
    entrada_para_salvar,
    ftool_visivel,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(ROOT, "samples")

# Amostra real do repositorio (projeto gravado antes do eixo "entrada")
AMOSTRA_STANDARD = os.path.join(SAMPLES_DIR, "exemplo_projeto.ptc")
AMOSTRA_PREMIUM = AMOSTRA_STANDARD


# ── Logica pura (sem UI) ─────────────────────────────────────────────────────

def test_entrada_de_projeto_ausente_assume_manual():
    """Projeto antigo (sem a chave "entrada") e lido como manual."""
    assert entrada_de_projeto({}) == ENTRADA_MANUAL
    assert entrada_de_projeto({"modo": "comum"}) == ENTRADA_MANUAL
    assert entrada_de_projeto(None) == ENTRADA_MANUAL


def test_entrada_de_projeto_valores_desconhecidos_caem_para_manual():
    assert entrada_de_projeto({"entrada": "ftool"}) == ENTRADA_FTOOL
    assert entrada_de_projeto({"entrada": "FTOOL"}) == ENTRADA_FTOOL
    assert entrada_de_projeto({"entrada": "desconhecido"}) == ENTRADA_MANUAL
    assert entrada_de_projeto({"entrada": 42}) == ENTRADA_MANUAL


@pytest.mark.parametrize("arquivo", [AMOSTRA_STANDARD, AMOSTRA_PREMIUM])
def test_amostras_ptc_sem_entrada_carregam_como_manual(arquivo):
    with open(arquivo, "r", encoding="utf-8") as f:
        proj_data = json.load(f)
    assert "entrada" not in proj_data
    assert entrada_de_projeto(proj_data) == ENTRADA_MANUAL


def test_aplicar_entrada_projeto_atualiza_o_state():
    state = {}
    assert aplicar_entrada_projeto(state, {"entrada": "ftool"}) == ENTRADA_FTOOL
    assert state["entrada"] == ENTRADA_FTOOL
    assert ftool_visivel(state["entrada"]) is True

    assert aplicar_entrada_projeto(state, {}) == ENTRADA_MANUAL
    assert state["entrada"] == ENTRADA_MANUAL
    assert ftool_visivel(state["entrada"]) is False


def test_entrada_para_salvar_normaliza_o_state():
    assert entrada_para_salvar({}) == ENTRADA_MANUAL
    assert entrada_para_salvar({"entrada": "ftool"}) == ENTRADA_FTOOL
    assert entrada_para_salvar({"entrada": "x"}) == ENTRADA_MANUAL


def test_ftool_visivel_depende_da_fonte_de_entrada():
    assert ftool_visivel(ENTRADA_FTOOL) is True
    assert ftool_visivel(ENTRADA_MANUAL) is False


def test_edicoes_standard_e_premium_sao_aceitas():
    assert edicao_aceita("standard") is True
    assert edicao_aceita("premium") is True
    assert edicao_aceita("Standard") is True


def test_aviso_edicao_e_informativo_e_nao_bloqueia():
    assert aviso_edicao("premium") is None
    aviso_standard = aviso_edicao("standard")
    assert aviso_standard is not None
    assert "Standard" in aviso_standard
    # Uma edicao desconhecida tambem nao bloqueia: apenas informa.
    assert aviso_edicao("outra") is not None


# ── UI (pagina Flet minima, sem servidor) ────────────────────────────────────

class _FakePage:
    """Pagina Flet minima para exercitar a UI em teste."""

    def __init__(self):
        self.services = []
        self.overlay = []
        self.dialogs = []

    def update(self, *args, **kwargs):
        pass

    def add(self, *args, **kwargs):
        pass

    def run_task(self, handler, *args, **kwargs):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()

    @property
    def messages(self):
        """Textos exibidos nos SnackBars (mensagens de erro/aviso)."""
        out = []
        for snack in self.overlay:
            content = getattr(snack, "content", None)
            value = getattr(content, "value", None)
            if isinstance(value, str):
                out.append(value)
        return out


class _FakePicker:
    """FilePicker minimo: devolve sempre o mesmo caminho."""

    def __init__(self, path=None):
        self.path = path

    async def pick_files(self, **kwargs):
        if not self.path:
            return None
        return SimpleNamespace(files=[SimpleNamespace(path=self.path)])

    async def save_file(self, **kwargs):
        return self.path


@pytest.fixture
def ui(monkeypatch):
    """Prepara o ambiente de UI: update() de controles e add_recent sem efeito."""
    from flet.controls import base_control
    monkeypatch.setattr(
        base_control.BaseControl, "update", lambda self, *a, **k: None, raising=False
    )
    import ui.viga as viga_mod
    monkeypatch.setattr(viga_mod, "add_recent", lambda *a, **k: None)
    return viga_mod


def _build_screen(ui_mod, modo="comum", load_path=None, save_path=None):
    page = _FakePage()
    fp_load = _FakePicker(load_path)
    fp_save = _FakePicker(save_path)
    screen = ui_mod.build_viga_screen(
        page, modo, lambda e: None, None, None, fp_load, fp_save, None
    )
    return page, screen, fp_load, fp_save


def _iter_controls(control):
    if not isinstance(control, _ft_control_cls()):
        return
    yield control
    for attr in ("controls", "content"):
        value = getattr(control, attr, None)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                yield from _iter_controls(item)
        else:
            yield from _iter_controls(value)


def _ft_control_cls():
    import flet as ft
    return ft.Control


def _label(control):
    for attr in ("text", "content", "value"):
        value = getattr(control, attr, None)
        if isinstance(value, str):
            return value
    return None


def _find_button(screen, label):
    for control in _iter_controls(screen):
        if _label(control) == label and getattr(control, "on_click", None) is not None:
            return control
    return None


def _has_label(screen, label):
    return any(_label(control) == label for control in _iter_controls(screen))


def _find_textfield(screen, label):
    for control in _iter_controls(screen):
        if getattr(control, "label", None) == label:
            return control
    return None

def test_ftool_recolhido_por_padrao(ui):
    """O painel FTOOL nao aparece ate o usuario pedir a importacao."""
    page, screen, _, _ = _build_screen(ui)

    assert _find_button(screen, "Importar do FTOOL") is not None
    assert _find_button(screen, "Voltar para entrada manual") is None
    assert not _has_label(screen, "Arquivos .txt exportados do FTOOL:")


def test_importar_do_ftool_revela_o_painel_e_volta_ao_manual(ui):
    page, screen, _, _ = _build_screen(ui)

    _find_button(screen, "Importar do FTOOL").on_click(None)
    assert _find_button(screen, "Voltar para entrada manual") is not None
    assert _find_button(screen, "Importar do FTOOL") is None
    assert _has_label(screen, "Arquivos .txt exportados do FTOOL:")

    _find_button(screen, "Voltar para entrada manual").on_click(None)
    assert _find_button(screen, "Importar do FTOOL") is not None
    assert _find_button(screen, "Voltar para entrada manual") is None
    assert not _has_label(screen, "Arquivos .txt exportados do FTOOL:")


def test_caminho_manual_permanece_acessivel(ui):
    """A entrada manual (tabela de trechos + Calcular) continua disponivel."""
    page, screen, _, _ = _build_screen(ui)

    assert _has_label(screen, "Trechos de flexão (M1 a M20)")
    assert _has_label(screen, "Trechos de cisalhamento (V1 a V20)")
    assert _find_button(screen, "Adicionar trecho") is not None


def test_calculo_manual_gera_resultados(ui):
    """O botao Calcular da entrada manual produz o modal de resultados."""
    page, screen, _, _ = _build_screen(ui)

    _find_textfield(screen, "d (cm)").value = "70"
    _find_textfield(screen, "tw (cm)").value = "20"
    _find_textfield(screen, "Barra phi_l (mm)").value = "16"

    botao_calcular = _find_button(screen, "Calcular")
    assert botao_calcular is not None
    botao_calcular.on_click(None)

    assert not [m for m in page.messages if m.startswith("Erro")]
    assert page.dialogs, "o modal de resultados deveria ter sido aberto"


def test_salvar_grava_a_fonte_de_entrada(ui, tmp_path):
    out_manual = tmp_path / "projeto_manual.ptc"
    page, screen, _, fp_save = _build_screen(ui, save_path=str(out_manual))

    asyncio.run(_find_button(screen, "Salvar Projeto").on_click(None))
    with open(out_manual, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["entrada"] == ENTRADA_MANUAL
    assert data["edicao"] == "premium"
    assert data["modo"] == "comum"

    # Alterna para a fonte FTOOL e salva de novo
    out_ftool = tmp_path / "projeto_ftool.ptc"
    fp_save.path = str(out_ftool)
    _find_button(screen, "Importar do FTOOL").on_click(None)
    asyncio.run(_find_button(screen, "Salvar Projeto").on_click(None))
    with open(out_ftool, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["entrada"] == ENTRADA_FTOOL


def test_carregar_ptc_antigo_sem_entrada_abre_sem_erro(ui):
    """Amostra real (edicao standard, sem a chave "entrada") abre normalmente."""
    page, screen, fp_load, _ = _build_screen(ui, load_path=AMOSTRA_STANDARD)

    asyncio.run(_find_button(screen, "Carregar Projeto").on_click(None))

    assert not [m for m in page.messages if m.startswith("Erro ao carregar projeto")]
    # A carga realmente ocorreu (mensagem de sucesso ou nota informativa)
    assert page.messages
    # Sem a chave "entrada" a fonte passa a ser manual
    assert _find_button(screen, "Importar do FTOOL") is not None
    assert _find_button(screen, "Voltar para entrada manual") is None


def test_carregar_ptc_com_entrada_ftool_revela_o_painel(ui, tmp_path):
    with open(AMOSTRA_PREMIUM, "r", encoding="utf-8") as f:
        proj_data = json.load(f)
    proj_data["entrada"] = ENTRADA_FTOOL
    destino = tmp_path / "projeto_ftool.ptc"
    destino.write_text(json.dumps(proj_data, ensure_ascii=False), encoding="utf-8")

    page, screen, fp_load, _ = _build_screen(ui, modo="t", load_path=str(destino))

    asyncio.run(_find_button(screen, "Carregar Projeto").on_click(None))

    assert not [m for m in page.messages if m.startswith("Erro ao carregar projeto")]
    assert _find_button(screen, "Voltar para entrada manual") is not None
    assert _find_button(screen, "Importar do FTOOL") is None


@pytest.mark.parametrize("edicao", ["standard", "premium"])
def test_edicao_standard_e_premium_sao_ambos_aceitos(ui, tmp_path, edicao):
    with open(AMOSTRA_STANDARD, "r", encoding="utf-8") as f:
        proj_data = json.load(f)
    proj_data["edicao"] = edicao
    proj_data["modo"] = "comum"
    destino = tmp_path / f"projeto_{edicao}.ptc"
    destino.write_text(json.dumps(proj_data, ensure_ascii=False), encoding="utf-8")

    page, screen, fp_load, _ = _build_screen(ui, load_path=str(destino))

    asyncio.run(_find_button(screen, "Carregar Projeto").on_click(None))

    # Nenhum erro e nenhuma mensagem de bloqueio; no maximo uma nota.
    assert not [m for m in page.messages if m.startswith("Erro ao carregar projeto")]
    for mensagem in page.messages:
        assert "licença Premium" not in mensagem
    if edicao == "standard":
        assert any("Standard" in m for m in page.messages)
    else:
        assert any("importado com sucesso" in m for m in page.messages)


def test_carregar_ptc_manual_nao_toca_painel_ftool_recolhido(ui, monkeypatch):
    """Regressao (bug de producao): carregar um .ptc manual com o painel FTOOL
    recolhido nao pode chamar update() em controles fora da pagina.

    No Flet real, ``Control.update()`` em um controle que ainda nao foi
    adicionado a pagina levanta "Control must be added to the page first".
    O mock do fixture ``ui`` neutraliza o update(), escondendo esse erro; aqui
    o update() vira um guardiao que reproduz o erro para controles que nao
    estao na arvore montada (caso dos rotulos do painel FTOOL recolhido).
    """
    from flet.controls import base_control

    page, screen, fp_load, _ = _build_screen(ui, load_path=AMOSTRA_STANDARD)
    montados = {id(c) for c in _iter_controls(screen)}

    def guard_update(self, *args, **kwargs):
        if id(self) not in montados:
            raise AssertionError(f"{self} Control must be added to the page first")
        return None

    monkeypatch.setattr(base_control.BaseControl, "update", guard_update, raising=False)

    asyncio.run(_find_button(screen, "Carregar Projeto").on_click(None))

    assert not [m for m in page.messages if m.startswith("Erro ao carregar projeto")]
    assert page.messages
