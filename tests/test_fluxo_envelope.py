"""
Teste end-to-end do fluxo de envelope de combinações (EP-01.5).

Bug verificado por execução (auditoria 2026-11-11): a UI gravava
state["ftool_momentos"] = {"max": …, "min": …} (dict) e passava isso para
dimensionar_trechos_ftool(), que espera lista de tuplas → ValueError
"too many values to unpack (expected 2)". O Envelope — headline do README
e da landing page — nunca produzia resultado.

A gravação agora está em aplicar_envelope_ao_state() (função de módulo,
testável sem Flet): state["ftool_momentos"/"ftool_cortantes"] são SEMPRE
listas de tuplas; as curvas max/min ficam em chaves próprias.
"""

import os

from ui.ftool.envelope import (
    aplicar_curvas_envelope_ao_state,
    calcular_envelope,
    detectar_secoes_envelope,
    gerar_relatorio_envelope,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

DADOS_VIGA = {
    "h_cm": 70.0,
    "bw_cm": 20.0,
    "caa": 2,
    "fck_mpa": 30.0,
    "diam_estribo_mm": 5.0,
    "diam_barra_mm": 12.5,
    "fyk_mpa": 50.0,
    "fyk_estribo_mpa": 60.0,
    "fyk_barra_mpa": 50.0,
    "gamma_f": 1.4,
}


def _ler_combinacoes():
    from ui.ftool.parser import parse_cortante, parse_momento

    m = parse_momento(os.path.join(SAMPLES_DIR, "test_momento_fletor.txt"))
    v = parse_cortante(os.path.join(SAMPLES_DIR, "test_esforcos_cortantes.txt"))
    return [{"nome": "C1", "momentos": m, "cortantes": v}]


def test_state_recebe_listas_de_tuplas_e_curvas_separadas():
    """O state nunca recebe dict max/min em ftool_momentos/ftool_cortantes."""
    combs = _ler_combinacoes()
    env = calcular_envelope(combs)

    state = {}
    aplicar_curvas_envelope_ao_state(state, env)

    # shape correto: listas de tuplas (x, valor)
    assert isinstance(state["ftool_momentos"], list)
    assert isinstance(state["ftool_cortantes"], list)
    assert all(isinstance(p, tuple) and len(p) == 2 for p in state["ftool_momentos"])
    assert all(isinstance(p, tuple) and len(p) == 2 for p in state["ftool_cortantes"])
    assert len(state["ftool_momentos"]) > 0

    # curvas do envelope em chaves separadas
    assert state["ftool_envelope_momentos"]["max"] == env["momentos_max"]
    assert state["ftool_envelope_momentos"]["min"] == env["momentos_min"]
    assert state["ftool_envelope_cortantes"]["max"] == env["cortantes_max"]
    assert state["ftool_envelope_cortantes"]["min"] == env["cortantes_min"]


def test_fluxo_envelope_end_to_end_produz_resultado():
    """parse → envelope → seções críticas → dimensionamento → relatório."""
    combs = _ler_combinacoes()
    env = calcular_envelope(combs)
    secoes = detectar_secoes_envelope(combs, env)
    assert len(secoes) > 0

    state = {}
    aplicar_curvas_envelope_ao_state(state, env)

    from ui.ftool.dimensionamento import dimensionar_trechos_ftool

    resultados = dimensionar_trechos_ftool(
        DADOS_VIGA,
        secoes,
        momentos=state["ftool_momentos"],
        cortantes=state["ftool_cortantes"],
    )
    sec_results = resultados["secoes"]
    assert len(sec_results) > 0
    assert any(r["resultado_flexao"] is not None for r in sec_results)
    assert any(r["resultado_cisalhamento"] is not None for r in sec_results)

    relatorio = gerar_relatorio_envelope(DADOS_VIGA, env, secoes)
    assert "RELATÓRIO DO ENVELOPE" in relatorio
    assert "Seções Críticas" in relatorio


def test_fluxo_envelope_com_ajustes_els_recalculo():
    """O recálculo com ajustes ELS também funciona com curvas de envelope."""
    combs = _ler_combinacoes()
    env = calcular_envelope(combs)
    secoes = detectar_secoes_envelope(combs, env)

    state = {}
    aplicar_curvas_envelope_ao_state(state, env)

    from ui.ftool.dimensionamento import dimensionar_trechos_ftool
    from ui.ftool.els import AjustesELS

    resultados = dimensionar_trechos_ftool(
        DADOS_VIGA,
        secoes,
        momentos=state["ftool_momentos"],
        cortantes=state["ftool_cortantes"],
        ajustes_els=AjustesELS(barras_extras=1),
    )
    assert resultados["secoes"]
    assert resultados["secoes"][0]["resultado_flexao"] is not None
