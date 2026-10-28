"""
Testes para o loop de convergência iterativa de dimensionamento à flexão.
Verifica a integração do BeamDetailer com o motor de cálculo à flexão.
"""

import pytest
from core.calculos.engenharia import (
    calcular_flexao_viga_comum,
    calcular_flexao_viga_t,
    dimensionar_bitola_iterativa,
)
from core.detailing import SectionLayoutData


def test_convergencia_bitola_1_camada():
    """Testa convergência para uma situação com pouca armadura (1 camada)."""
    res = dimensionar_bitola_iterativa(
        h_cm=50.0,
        bw_calculo_cm=20.0,
        cob_mm=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fck_mpa=30.0,
        fyk_mpa=50.0,
        Md_kNm=45.0,
        bw_detalhamento_cm=20.0,
    )
    assert res.camadas == 1
    assert res.status_bitola == "CABE"
    assert res.cabe is True
    assert res.layout is not None
    assert isinstance(res.layout, SectionLayoutData)
    assert res.d_real_cm > 0.0
    assert abs(res.d_real_cm - (res.layout.d_efetiva / 10.0)) < 1e-2


def test_convergencia_bitola_multiplas_camadas():
    """Testa convergência quando a armadura requer mais de 1 camada na largura da viga."""
    res = dimensionar_bitola_iterativa(
        h_cm=50.0,
        bw_calculo_cm=14.0,
        cob_mm=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fck_mpa=30.0,
        fyk_mpa=50.0,
        Md_kNm=100.0,
        bw_detalhamento_cm=14.0,
    )
    # Com 14cm de largura e cobrimento de 3cm, cabem poucas barras por camada
    assert res.camadas >= 2
    assert res.status_bitola in ("2 CAMADAS", "3 CAMADAS")
    assert res.d_real_cm < res.d_inicial_cm  # d real deve ser menor que o estimado em 1 camada


def test_integ_flexao_comum_retorna_layout_e_tabela():
    """Verifica que calcular_flexao_viga_comum retorna os novos campos preenchidos."""
    resultados = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=20.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fyk_mpa=50.0,
        momentos=[60.0],
    )
    assert len(resultados) == 1
    res = resultados[0]
    assert res is not None
    assert res.d_cm_real > 0.0
    assert res.camadas_adotadas >= 1
    assert res.status_bitola in ("CABE", "2 CAMADAS", "3 CAMADAS", "NÃO CABE")
    assert res.layout_convergido is not None
    assert isinstance(res.tabela_bitolas, list)
    assert len(res.tabela_bitolas) > 0


def test_integ_flexao_viga_t_retorna_layout_e_tabela():
    """Verifica que calcular_flexao_viga_t retorna os novos campos preenchidos."""
    resultados = calcular_flexao_viga_t(
        h_cm=50.0,
        bw_cm=15.0,
        bf_cm=60.0,
        hf_cm=10.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fyk_mpa=50.0,
        momentos=[80.0],
    )
    assert len(resultados) == 1
    res = resultados[0]
    assert res is not None
    assert res.d_cm_real > 0.0
    assert res.camadas_adotadas >= 1
    assert res.status_bitola in ("CABE", "2 CAMADAS", "3 CAMADAS", "NÃO CABE")
    assert res.layout_convergido is not None
    assert isinstance(res.tabela_bitolas, list)
    assert len(res.tabela_bitolas) > 0
