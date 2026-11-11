"""
Testes de equivalência e validação da consolidação do desenho (EP-04.4).
Verifica que BeamDetailer + BeamSectionCommands são a única fonte de geometria
de armação para PDF retangular, PDF T, Flet e DXF, eliminando discrepâncias.
"""

import pytest
from fpdf import FPDF

from core.detailing import (
    BeamSectionCommands,
    desenhar_secao_com_detailer,
    detalhar_secao_completa,
    posicionar_armadura_pele,
)
from core.detailing.presentation import _C_GRAMPO, CmdPolyline
from core.relatorio_base import (
    desenhar_secao_retangular,
    desenhar_secao_t,
)


def _novo_pdf() -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    return pdf


def test_equivalencia_secao_retangular_detailer_e_relatorio():
    """Valida que desenhar_secao_retangular e desenhar_secao_com_detailer usam a mesma geometria."""
    pdf1 = _novo_pdf()
    pdf2 = _novo_pdf()

    args = dict(
        h_cm=60.0,
        bw_cm=20.0,
        cob_mm=25.0,
        phi_estribo=5.0,
        phi_barra_inf=16.0,
        n_barras_inf=4,
        phi_barra_sup=10.0,
        n_barras_sup=2,
        n_barras_pele=2,
        phi_pele=6.3,
    )

    layout1 = desenhar_secao_retangular(pdf1, **args)
    layout2 = desenhar_secao_com_detailer(
        pdf2,
        h_cm=60.0,
        bw_cm=20.0,
        cob_mm=25.0,
        phi_estribo_mm=5.0,
        phi_barra_inf_mm=16.0,
        n_barras_inf=4,
        phi_barra_sup_mm=10.0,
        n_barras_sup=2,
        n_barras_pele=2,
        phi_pele_mm=6.3,
        is_t=False,
    )

    assert len(layout1.bar_positions) == len(layout2.bar_positions)
    assert len(layout1.skin_bar_positions) == len(layout2.skin_bar_positions)
    for b1, b2 in zip(layout1.bar_positions, layout2.bar_positions, strict=True):
        assert b1.x == pytest.approx(b2.x, abs=1e-3)
        assert b1.y == pytest.approx(b2.y, abs=1e-3)


def test_correcao_bug_viga_t_armadura_superior_na_mesa():
    """EP-04.4: a viga T deve distribuir a armadura superior na largura da MESA (bf), não na alma (bw)."""
    pdf = _novo_pdf()
    bf_cm = 60.0
    bw_cm = 20.0
    layout = desenhar_secao_t(
        pdf,
        h_cm=50.0,
        bw_cm=bw_cm,
        bf_cm=bf_cm,
        hf_cm=10.0,
        cob_mm=25.0,
        phi_estribo=5.0,
        phi_barra_inf=16.0,
        n_barras_inf=3,
        phi_barra_sup=10.0,
        n_barras_sup=4,
    )

    # Identifica as barras superiores (camada negativa / perto do topo)
    barras_sup = [b for b in layout.bar_positions if b.layer < 0 and not b.is_corner_bar]
    assert len(barras_sup) == 4

    xs_sup = [b.x for b in barras_sup]
    span_sup = max(xs_sup) - min(xs_sup)
    # Na alma (bw=200mm), o span seria no máximo 130mm.
    # Na mesa (bf=600mm), o span é muito maior (~520mm).
    assert span_sup > bw_cm * 10.0, (
        f"Span superior {span_sup} mm deve ocupar a mesa (bf), não a alma (bw={bw_cm * 10} mm)"
    )


def test_unificacao_posicionamento_pele():
    """Valida consistência das coordenadas da armadura de pele entre módulo unificado e DXF."""
    x_esq, x_dir, ys = posicionar_armadura_pele(
        h_mm=700.0,
        bw_mm=200.0,
        cob_mm=30.0,
        phi_estribo_mm=5.0,
        n_barras_pele_face=2,
        phi_pele_mm=10.0,
        bar_positions=[
            {"x": 40.0, "y": 45.0, "layer": 0, "phi_mm": 16.0},
            {"x": 160.0, "y": 45.0, "layer": 0, "phi_mm": 16.0},
            {"x": 40.0, "y": 100.0, "layer": 1, "phi_mm": 16.0},
            {"x": 160.0, "y": 100.0, "layer": 1, "phi_mm": 16.0},
            {"x": 40.0, "y": 655.0, "layer": -1, "phi_mm": 16.0},
            {"x": 160.0, "y": 655.0, "layer": -1, "phi_mm": 16.0},
            {"x": 40.0, "y": 600.0, "layer": -2, "phi_mm": 16.0},
            {"x": 160.0, "y": 600.0, "layer": -2, "phi_mm": 16.0},
        ],
        is_t=False,
    )

    assert len(ys) == 2
    # Valores em cm correspondentes: 26.7667 e 43.2333
    assert ys[0] / 10.0 == pytest.approx(26.7667, abs=1e-3)
    assert ys[1] / 10.0 == pytest.approx(43.2333, abs=1e-3)


def test_unificacao_grampos_comandos():
    """Valida que BeamSectionCommands emite grampos suplementares unificados com gancho."""
    layout = detalhar_secao_completa(
        h_cm=60.0,
        bw_cm=30.0,
        cob_mm=30.0,
        phi_estribo_mm=5.0,
        phi_barra_inf_mm=12.5,
        n_barras_inf=10,  # 7+3: 2a camada com 3 barras -> requer grampo
    )
    assert layout.requires_supplementary_stirrup

    cmds = BeamSectionCommands().build(layout)
    grampos = [c for c in cmds if isinstance(c, CmdPolyline) and c.color == _C_GRAMPO]
    assert len(grampos) == 1
    # 6 vertices no grampo unificado
    assert len(grampos[0].points) == 6
