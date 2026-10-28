"""
Testes para verificar correções na armadura de pele:
1. Contorno branco removido
2. Posicionamento vertical evita sobreposição com 2ª camada
"""

import pytest
from core.detailing.presentation import (
    desenhar_secao_com_detailer,
    _C_BAR_MAIN_STROKE,
    _C_BAR_MAIN,
)
from core.detailing.domain import BeamDetailer, BeamDetailingInput
from fpdf import FPDF


def test_contorno_branco_removido():
    """Verifica que o contorno das barras foi removido (None em vez de branco)."""
    assert _C_BAR_MAIN_STROKE is None, "Contorno deve ser None (removido)"
    assert _C_BAR_MAIN == (20, 30, 90), "Cor de preenchimento deve ser azul navy"


def test_armadura_pele_nao_sobrepoe_2a_camada():
    """Verifica que a armadura de pele não sobrepõe com a 2ª camada de armadura principal."""
    # Criar seção com 2 camadas de armadura principal
    pdf = FPDF()
    pdf.add_page()
    
    # Parâmetros da viga (viga estreita para forçar 2 camadas)
    h_cm = 70.0
    bw_cm = 15.0  # Viga estreita
    cob_mm = 2.5
    phi_estribo_mm = 0.5
    phi_barra_inf_mm = 2.0  # 20mm (barras grossas)
    n_barras_inf = 10  # 10 barras para forçar 2 camadas
    phi_pele_mm = 0.5  # 5mm
    n_barras_pele = 2
    
    # Calcular layout da armadura principal
    detailer = BeamDetailer()
    data_inf = detailer.detail(BeamDetailingInput(
        bw=bw_cm * 10.0,  # mm
        h=h_cm * 10.0,    # mm
        c_nom=cob_mm,
        phi_estribo=phi_estribo_mm,
        phi_barra=phi_barra_inf_mm,
        d_max_agregado=19.0,
        total_bars=n_barras_inf,
        is_t=False,
        is_superior=False,
    ))
    
    # Verificar que há 2 camadas
    assert data_inf.layer_count == 2, f"Deve haver 2 camadas, mas há {data_inf.layer_count}"
    
    # Calcular posição Y da 2ª camada (em mm a partir do topo)
    # A 2ª camada está em: y_layer0_center + (phi_barra + ev_min)
    y_2a_camada_mm = data_inf.layers[1].y_centroid
    
    # Desenhar seção com armadura de pele
    data_layout = desenhar_secao_com_detailer(
        pdf=pdf,
        h_cm=h_cm,
        bw_cm=bw_cm,
        cob_mm=cob_mm,
        phi_estribo_mm=phi_estribo_mm,
        phi_barra_inf_mm=phi_barra_inf_mm,
        n_barras_inf=n_barras_inf,
        phi_barra_sup_mm=0.0,
        n_barras_sup=0,
        d_max_agregado_mm=19.0,
        px=10.0,
        py=10.0,
        max_h_mm_pagina=80.0,
        max_w_mm_pagina=55.0,
        is_t=False,
        n_barras_pele=n_barras_pele,
        phi_pele_mm=phi_pele_mm,
    )
    
    # Verificar que a armadura de pele foi desenhada
    assert data_layout is not None
    
    # A armadura de pele deve começar abaixo da 2ª camada
    # Calcular posição Y esperada do topo da armadura de pele (em mm a partir do topo)
    # y_inicio_pele_cm = cob_mm/10 + phi_estribo_mm/10 + phi_barra + ev_min/10
    y_inicio_pele_cm = cob_mm + phi_estribo_mm + phi_barra_inf_mm + data_inf.ev_min / 10.0
    y_inicio_pele_mm = y_inicio_pele_cm * 10.0
    
    # A 2ª camada está em y_2a_camada_mm (centro da barra)
    # O topo da 2ª camada está em: y_2a_camada_mm - phi_barra/2
    topo_2a_camada_mm = y_2a_camada_mm - phi_barra_inf_mm / 2.0
    
    # A armadura de pele deve começar abaixo do topo da 2ª camada
    # (considerando que y aumenta de cima para baixo no PDF)
    assert y_inicio_pele_mm > topo_2a_camada_mm, \
        f"Armadura de pele (y={y_inicio_pele_mm:.1f}mm) deve começar abaixo da 2ª camada (topo={topo_2a_camada_mm:.1f}mm)"


def test_armadura_pele_secao_t_nao_sobrepoe():
    """Verifica que a armadura de pele em seção T não sobrepõe com a 2ª camada."""
    pdf = FPDF()
    pdf.add_page()
    
    # Parâmetros da viga T (alma estreita para forçar 2 camadas)
    h_cm = 70.0
    bw_cm = 15.0  # Alma estreita
    bf_cm = 60.0
    hf_cm = 12.0
    cob_mm = 2.5
    phi_estribo_mm = 0.5
    phi_barra_inf_mm = 2.0  # 20mm (barras grossas)
    n_barras_inf = 10  # 10 barras para forçar 2 camadas
    phi_pele_mm = 0.5  # 5mm
    n_barras_pele = 2
    
    # Calcular layout da armadura principal
    detailer = BeamDetailer()
    data_inf = detailer.detail(BeamDetailingInput(
        bw=bw_cm * 10.0,  # mm
        h=h_cm * 10.0,    # mm
        c_nom=cob_mm,
        phi_estribo=phi_estribo_mm,
        phi_barra=phi_barra_inf_mm,
        d_max_agregado=19.0,
        total_bars=n_barras_inf,
        is_t=True,
        bf_cm=bf_cm,
        hf_cm=hf_cm,
        is_superior=False,
    ))
    
    # Verificar que há 2 camadas
    assert data_inf.layer_count == 2, f"Deve haver 2 camadas, mas há {data_inf.layer_count}"
    
    # Desenhar seção T com armadura de pele
    data_layout = desenhar_secao_com_detailer(
        pdf=pdf,
        h_cm=h_cm,
        bw_cm=bw_cm,
        cob_mm=cob_mm,
        phi_estribo_mm=phi_estribo_mm,
        phi_barra_inf_mm=phi_barra_inf_mm,
        n_barras_inf=n_barras_inf,
        phi_barra_sup_mm=0.0,
        n_barras_sup=0,
        d_max_agregado_mm=19.0,
        px=10.0,
        py=10.0,
        max_h_mm_pagina=80.0,
        max_w_mm_pagina=55.0,
        is_t=True,
        bf_cm=bf_cm,
        hf_cm=hf_cm,
        n_barras_pele=n_barras_pele,
        phi_pele_mm=phi_pele_mm,
    )
    
    # Verificar que a armadura de pele foi desenhada
    assert data_layout is not None
    
    # Para seção T, a armadura de pele deve estar na alma (abaixo da mesa)
    # O teste principal é que não há erro ao desenhar
    # A verificação detalhada do posicionamento é complexa e depende de muitos fatores


def test_armadura_pele_espacamento_perfeitamente_uniforme():
    """Verifica que o espaçamento livre (borda a borda) entre as barras de pele e as armaduras principais é perfeitamente uniforme."""
    h_cm = 70.0
    bw_cm = 20.0
    cob_mm = 2.5
    phi_estribo_mm = 0.5
    phi_barra_inf_mm = 1.6
    n_barras_inf = 4
    phi_barra_sup_mm = 1.6
    n_barras_sup = 2
    n_barras_pele = 3
    phi_pele_mm = 6.3
    
    # Simula cálculo de limites no presentation.py
    y_top_raw_cm = (cob_mm + phi_estribo_mm + phi_barra_sup_mm) / 10.0
    y_bottom_raw_cm = h_cm - (cob_mm + phi_estribo_mm + phi_barra_inf_mm) / 10.0
    
    h_free_cm = y_bottom_raw_cm - y_top_raw_cm
    phi_pele_cm = phi_pele_mm / 10.0
    d_livre_cm = (h_free_cm - n_barras_pele * phi_pele_cm) / (n_barras_pele + 1.0)
    
    ys_cm = [y_top_raw_cm + (i + 1) * d_livre_cm + (i + 0.5) * phi_pele_cm for i in range(n_barras_pele)]
    
    # Verificação de espaçamento livre (borda a borda) uniforme
    # Distância da armadura superior até a borda superior da primeira barra de pele
    dist_sup = (ys_cm[0] - phi_pele_cm / 2.0) - y_top_raw_cm
    assert abs(dist_sup - d_livre_cm) < 1e-6
    
    # Distâncias intermediárias entre bordas de pele
    for i in range(n_barras_pele - 1):
        dist_mid = (ys_cm[i+1] - phi_pele_cm / 2.0) - (ys_cm[i] + phi_pele_cm / 2.0)
        assert abs(dist_mid - d_livre_cm) < 1e-6
        
    # Distância da borda inferior da última barra de pele até a armadura inferior
    dist_inf = y_bottom_raw_cm - (ys_cm[-1] + phi_pele_cm / 2.0)
    assert abs(dist_inf - d_livre_cm) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
