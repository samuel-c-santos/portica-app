"""
Testes para Armadura Dupla (Fase 2.6).
"""

import pytest
from core.calculos.engenharia import calcular_flexao_viga_comum


def test_1_secao_simples_nao_forca_armadura_dupla():
    """1. Testa que para uma solicitação usual, a armadura dupla não é acionada."""
    # Seção 15x50, Mk = 40 kN.m (Md = 56 kN.m)
    resultados = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=15.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fyk_mpa=50.0,
        momentos=[40.0],
        gamma_f=1.4,
    )
    
    assert len(resultados) == 1
    res = resultados[0]
    assert res is not None
    assert res.armadura_dupla is False
    assert res.as_linha_cm2 == 0.0
    assert res.as_linha_adotada == 0.0
    assert res.md_excedente_knm == 0.0


def test_2_secao_pequena_forca_armadura_dupla():
    """2. Testa que seção pequena (12x50) com momento alto (Mk = 139.2 kN.m) força armadura dupla."""
    # Seção 12x50, Mk = 139.2 kN.m
    # Md = 139.2 * 1.4 = 194.88 kN.m
    resultados = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=12.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fyk_mpa=50.0,
        momentos=[139.2],
        gamma_f=1.4,
    )
    
    assert len(resultados) == 1
    res = resultados[0]
    assert res is not None
    assert res.armadura_dupla is True
    assert res.as_linha_cm2 > 0.0
    assert res.as_linha_adotada > 0.0
    assert res.md_limite_knm < res.momento_kNm
    assert res.md_excedente_knm > 0.0
    
    # O momento limite com d convergido é em torno de 46.93 kN.m
    assert res.md_limite_knm == pytest.approx(46.93, abs=1.0)
    # Momento excedente: 194.88 - 46.93 = 147.95
    assert res.md_excedente_knm == pytest.approx(194.88 - res.md_limite_knm, abs=0.1)
    
    assert res.as_linha_cm2 > 0.0
    assert res.as_linha_adotada > 0.0
    assert "Armadura dupla utilizada" in res.alerta


def test_3_limite_neutral_axis_fck_alto():
    """3. Testa limite do bx com fck superior a 50 MPa (bx_limite = 0.35)."""
    # Seção 15x50, fck = 60 MPa (bx_limite = 0.35), momento Mk = 200 kN.m
    resultados = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=15.0,
        caa=2,
        fck_mpa=60.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fyk_mpa=50.0,
        momentos=[200.0],
        gamma_f=1.4,
    )
    
    res = resultados[0]
    assert res.armadura_dupla is True
    assert res.bx == 0.35


def test_4_secao_pequena_fck_alto_armadura_dupla():
    """4. Testa cálculo completo da armadura dupla para fck = 60 MPa e Mk = 200 kN.m."""
    resultados = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=15.0,
        caa=2,
        fck_mpa=60.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fyk_mpa=50.0,
        momentos=[200.0],
        gamma_f=1.4,
    )
    
    res = resultados[0]
    assert res.armadura_dupla is True
    assert res.as_linha_cm2 > 0.0
    assert res.as_linha_adotada > 0.0
    assert res.md_limite_knm < res.momento_kNm


def test_5_armadura_dupla_momento_negativo():
    """5. Testa que a armadura dupla funciona de forma idêntica sob momentos fletores negativos (abs)."""
    # Seção 12x50, Mk = -139.2 kN.m (idêntico ao teste 2, mas negativo)
    resultados = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=12.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fyk_mpa=50.0,
        momentos=[-139.2],
        gamma_f=1.4,
    )
    
    res = resultados[0]
    assert res is not None
    assert res.armadura_dupla is True
    assert res.as_linha_cm2 > 0.0
    assert res.as_linha_adotada > 0.0
    assert res.md_limite_knm < res.momento_kNm
    assert "Armadura dupla utilizada" in res.alerta

