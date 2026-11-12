"""Testes dos modulos de ui/viga/ (EP-04.3), sem renderizar Flet.

Usam ``montar_contexto`` com uma pagina falsa. Fecham os itens do EP-03.5 que
dependiam da extracao: .ptc com TODOS os campos (inclusive ajustes ELS) e
importacao FTOOL de ponta a ponta.
"""

import asyncio
import json
import os
from types import SimpleNamespace

import pytest

from ui.entrada import ENTRADA_FTOOL, ENTRADA_MANUAL, aplicar_entrada_projeto
from ui.ftool.els import AjustesELS
from ui.ftool.secoes_criticas import SecaoCritica
from ui.viga.actions import desserializar_ajustes_els, serializar_ajustes_els
from ui.viga.form_geometry import (
    erro_campo_trecho,
    erro_numero_nao_negativo,
    erro_numero_positivo,
)
from ui.viga.form_trechos import ler_sinais
from ui.viga.state import ViewContext, VigaState

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "samples")


class FakePage:
    def __init__(self):
        self.services, self.overlay, self.dialogs = [], [], []
        self.tasks = []

    def update(self, *a, **k):
        pass

    def add(self, *a, **k):
        pass

    def run_task(self, handler=None, *a, **k):
        self.tasks.append(handler)

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()

    @property
    def messages(self):
        out = []
        for snack in self.overlay:
            value = getattr(getattr(snack, "content", None), "value", None)
            if isinstance(value, str):
                out.append(value)
        return out


class FakePicker:
    def __init__(self, path=None):
        self.path = path

    async def pick_files(self, **kw):
        return SimpleNamespace(files=[SimpleNamespace(path=self.path)]) if self.path else None

    async def save_file(self, **kw):
        return self.path


@pytest.fixture
def montar(monkeypatch):
    from flet.controls import base_control

    from ui.viga import actions, viga

    monkeypatch.setattr(base_control.BaseControl, "update", lambda s, *a, **k: None, raising=False)
    for modulo in (actions, viga):
        monkeypatch.setattr(modulo, "add_recent", lambda *a, **k: None, raising=False)

    def _montar(modo="comum", load=None, save=None, initial_file=None):
        from ui.viga import montar_contexto

        page = FakePage()
        ctx = montar_contexto(
            page,
            modo,
            lambda e: None,
            None,
            None,
            FakePicker(load),
            FakePicker(save),
            None,
            initial_file,
        )
        return ctx

    return _montar


# ── Estado tipado ─────────────────────────────────────────────────────────────


def test_estado_inicial_por_modo():
    assert VigaState.para_modo("comum").tipo_viga == "V1"
    assert VigaState.para_modo("t").tipo_viga == "VT1"
    assert VigaState().entrada == ENTRADA_MANUAL


def test_estado_protocolo_de_mapeamento():
    st = VigaState()
    st["ftool_path"] = "a.txt"
    assert st["ftool_path"] == st.ftool_path == "a.txt"
    assert st.get("ftool_path") == "a.txt"
    assert "ftool_path" in st
    assert st.get("ftool_momentos") is None  # chave inicial: devolve o valor (None)
    assert st.get("ftool_envelope_momentos", 7) == 7  # chave tardia sem valor: default
    assert "ftool_envelope_momentos" not in st
    assert st.pop("ftool_path") == "a.txt"


def test_estado_chave_desconhecida_levanta_keyerror():
    st = VigaState()
    with pytest.raises(KeyError):
        st["typo_de_chave"] = 1
    with pytest.raises(KeyError):
        st["typo_de_chave"]


def test_estado_compativel_com_helpers_de_entrada():
    st = VigaState()
    assert aplicar_entrada_projeto(st, {"entrada": "ftool"}) == ENTRADA_FTOOL
    assert st.entrada == ENTRADA_FTOOL


def test_contexto_guarda_parametros_e_estado():
    ctx = ViewContext("pagina", "t", None, None, None, None, None, None)
    assert ctx.page == "pagina" and ctx.modo == "t"
    assert ctx.state.tipo_viga == "VT1"


# ── Logica pura dos formularios ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("", "Campo obrigatório"),
        ("  ", "Campo obrigatório"),
        ("abc", "Use número com vírgula (ex: 50,0)"),
        ("0", "Deve ser maior que 0"),
        ("-3", "Deve ser maior que 0"),
        ("50,5", None),
        ("50.5", None),
    ],
)
def test_erro_numero_positivo(texto, esperado):
    assert erro_numero_positivo(texto) == esperado


def test_erro_numero_nao_negativo():
    assert erro_numero_nao_negativo("0") is None
    assert erro_numero_nao_negativo("-1") == "Não pode ser negativo"
    assert erro_numero_nao_negativo("") == "Campo obrigatório"


def test_erro_campo_trecho():
    assert erro_campo_trecho("") is None
    assert erro_campo_trecho("12,5") is None
    assert erro_campo_trecho("x") == "Inválido"


def test_ler_sinais_vazio_e_virgula():
    rows = [SimpleNamespace(value=v) for v in ("135,9", "", "-20.5", "lixo")]
    assert ler_sinais(rows) == [135.9, 0.0, -20.5, 0.0]


def test_ajustes_els_roundtrip_json():
    aj = AjustesELS(barras_extras=2, phi_minimo_mm=20.0, h_override_cm=70.0, fck_override_mpa=35.0)
    data = json.loads(json.dumps(serializar_ajustes_els(aj)))
    assert desserializar_ajustes_els(data) == aj
    assert serializar_ajustes_els(None) is None
    assert desserializar_ajustes_els(None) is None


# ── Fluxos (pagina falsa) ────────────────────────────────────────────────────


def _preencher(ctx, h="70", bw="20", phi="16"):
    ctx.h_tf.control.value = h
    ctx.bw_tf.control.value = bw
    ctx.phi_bar_dd.control.value = phi


def test_ptc_completo_roundtrip_com_ajustes_els(montar, tmp_path):
    destino = tmp_path / "completo.ptc"
    ctx = montar(save=str(destino))
    _preencher(ctx, h="65", bw="22", phi="20")
    ctx.fck_dd.control.value = "35"
    ctx.caa_dd.control.value = "3"
    ctx.viga_nome_tf.control.value = "V9"
    ctx.resp_nome_tf.control.value = "Fulano"
    ctx.state.entrada = ENTRADA_FTOOL
    ctx.state.ftool_momentos = [(0.0, 1.0), (1.0, -2.5)]
    ctx.state.ftool_cortantes = [(0.0, 10.0), (1.0, -10.0)]
    ctx.state.ftool_secoes_criticas = [SecaoCritica(0.5, 12.0, 3.0, "POSITIVO", "vao")]
    ctx.state.ftool_ajustes_els = AjustesELS(barras_extras=1, phi_minimo_mm=25.0)

    asyncio.run(ctx.on_save_project_click(None))
    assert not [m for m in ctx.page.messages if m.startswith("Erro")]
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert dados["entrada"] == ENTRADA_FTOOL
    assert dados["ftool"]["ajustes_els"]["barras_extras"] == 1
    assert dados["materiais"]["fck_mpa"] == "35"

    novo = montar(load=str(destino))
    asyncio.run(novo.on_load_project_click(None))
    assert not [m for m in novo.page.messages if m.startswith("Erro")]
    assert novo.h_tf.control.value == "65" and novo.bw_tf.control.value == "22"
    assert novo.fck_dd.control.value == "35" and novo.caa_dd.control.value == "3"
    assert novo.viga_nome_tf.control.value == "V9"
    assert novo.resp_nome_tf.control.value == "Fulano"
    assert novo.state.entrada == ENTRADA_FTOOL
    assert novo.state.ftool_momentos == [(0.0, 1.0), (1.0, -2.5)]
    assert novo.state.ftool_ajustes_els == AjustesELS(barras_extras=1, phi_minimo_mm=25.0)
    sec = novo.state.ftool_secoes_criticas[0]
    assert (sec.x, sec.tipo) == (0.5, "POSITIVO")


def test_carregar_projeto_com_painel_ftool_recolhido_mantem_dados(montar, tmp_path):
    """Projeto manual (painel recolhido) carrega sem erro e nao toca nos controles FTOOL."""
    destino = tmp_path / "manual.ptc"
    ctx = montar(save=str(destino))
    _preencher(ctx)
    asyncio.run(ctx.on_save_project_click(None))

    novo = montar(load=str(destino))
    asyncio.run(novo.on_load_project_click(None))
    assert not [m for m in novo.page.messages if m.startswith("Erro")]
    assert novo.state.entrada == ENTRADA_MANUAL
    assert novo.h_tf.control.value == "70"


def _importar_ftool(montar, modo, arquivos):
    ctx = montar(modo=modo)
    ctx.state.entrada = ENTRADA_FTOOL
    ctx.state.ftool_momento_path = os.path.join(SAMPLES, arquivos[0])
    ctx.state.ftool_cortante_path = os.path.join(SAMPLES, arquivos[1])
    ctx.state.ftool_deformacao_path = os.path.join(SAMPLES, arquivos[2])
    _preencher(ctx, h="60", bw="20", phi="16")
    if modo == "t":
        ctx.bf_tf.control.value = "80"
        ctx.hf_tf.control.value = "12"
    ctx.processar_ftool()
    # dialogo "Secoes Detectadas": o botao Calcular dispara o dimensionamento
    dialogo = ctx.page.dialogs[-1]
    calcular = next(
        a
        for a in dialogo.actions
        if getattr(a, "content", None) == "Calcular" or getattr(a, "text", None) == "Calcular"
    )
    calcular.on_click(None)
    return ctx


@pytest.mark.parametrize(
    "modo,arquivos",
    [
        (
            "comum",
            ("test_momento_fletor.txt", "test_esforcos_cortantes.txt", "test_deformacoes.txt"),
        ),
        ("t", ("test-t-momento.txt", "test-t-cortantes.txt", "test-t-deformacoes.txt")),
    ],
)
def test_importacao_ftool_ponta_a_ponta(montar, modo, arquivos):
    """parser -> secoes criticas -> dimensionamento -> ELS, sem erro visivel."""
    ctx = _importar_ftool(montar, modo, arquivos)

    erros = [m for m in ctx.page.messages if m.lower().startswith("erro")]
    assert not erros, erros
    assert ctx.state.ftool_momentos and ctx.state.ftool_cortantes
    assert ctx.state.ftool_secoes_criticas
    assert ctx.state.resultados_flex, "o dimensionamento deve produzir resultados"
    assert len(ctx.state.resultados_flex) == len(ctx.state.ftool_secoes_criticas)
    assert ctx.state.resultados_cis


# ── Abertura de projeto pela lista de recentes ──────────────────────────────


def test_abrir_projeto_pela_lista_de_recentes(montar):
    """Abrir um .ptc da lista de recentes carrega o projeto (EP-04.3).

    Regressao: o contexto chamava ``run_task(ctx._auto_load)``, mas a corotina
    era local e nunca foi vinculada ao contexto, derrubando a tela com
    ``'ViewContext' object has no attribute '_auto_load'``.
    """
    ctx = montar(modo="t", initial_file=os.path.join(SAMPLES, "exemplo_projeto.ptc"))

    assert ctx.initial_file, "o contexto deveria guardar o arquivo inicial"
    assert ctx.page.tasks, "nenhuma carga inicial agendada"

    asyncio.run(ctx.page.tasks[-1]())

    assert "Projeto importado com sucesso" in ctx.page.messages


def test_modal_resultados_nao_envia_shadow_invalido(montar):
    """Nenhum controle do modal pode levar `shadow` booleano para o cliente.

    Regressao: `result_card(..., shadow=False)` mandava `False` no campo
    `Container.shadow`, o Flet nao deserializava e o modal aparecia como um
    retangulo cinza (ErrorWidget do Flutter) em vez dos cards de resultado.
    """
    ctx = _importar_ftool(
        montar,
        "comum",
        ("test_momento_fletor.txt", "test_esforcos_cortantes.txt", "test_deformacoes.txt"),
    )
    modal = ctx.page.dialogs[-1]
    invalidos = []

    def walk(control):
        if control is None:
            return
        if isinstance(getattr(control, "shadow", None), bool):
            invalidos.append(type(control).__name__)
        for attr in ("controls", "content", "title", "actions"):
            filho = getattr(control, attr, None)
            if isinstance(filho, list):
                for item in filho:
                    walk(item)
            elif filho is not None:
                walk(filho)

    walk(modal)
    assert not invalidos, f"shadow booleano em: {invalidos}"
