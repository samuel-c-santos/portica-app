"""
Testes para o loop de convergência iterativa de dimensionamento à flexão.
Verifica a integração do BeamDetailer com o motor de cálculo à flexão.
"""

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
        fyk_kn_cm2=50.0,
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
        fyk_kn_cm2=50.0,
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
        fyk_kn_cm2=50.0,
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


def test_nao_convergencia_por_max_iter_e_recusada():
    """EP-01.2: o laço que não fecha a tolerância em max_iter deve recusar.

    A partir do EP-02.1 a fórmula de equilíbrio mudou e o caso 15×60/Ø10
    deixou de oscilar. O caminho de recusa é exercitado de forma direta:
    com max_iter=1 o laço não tem como satisfazer |d₀ − d_real| < tol.
    """
    res = dimensionar_bitola_iterativa(
        h_cm=60.0,
        bw_calculo_cm=15.0,
        cob_mm=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=10.0,
        fck_mpa=30.0,
        fyk_kn_cm2=50.0,
        Md_kNm=50.0 * 1.4,
        bw_detalhamento_cm=15.0,
        max_iter=1,
    )
    assert res.convergiu is False
    assert res.cabe is False
    assert res.status_bitola == "NÃO CONVERGIU"
    # nunca devolver o último iterado como se fosse resultado
    assert res.layout is None


def test_deteccao_de_oscilacao_de_d():
    """EP-01.2: sequência de d que troca de sinal é oscilação."""
    from core.calculos.engenharia import _d_sem_oscilacao

    assert _d_sem_oscilacao([54.24, 54.59, 54.24, 54.59]) is False
    assert _d_sem_oscilacao([55.0, 54.5, 54.4, 54.4]) is True


def test_caso_h50_bw15_mk400_oscilador_e_recusado():
    """EP-01.2: caso da auditoria (h=50, bw=15, Mk=400) não emite resultado.

    No código pré-EP-01 a última iteração era adotada com as_req = −8,58
    cm² (ou +116,58 cm², alternando). Com a recusa por camadas (EP-01.1)
    ou por não-convergência (EP-01.2), o motor não devolve bitola válida.
    """
    res = dimensionar_bitola_iterativa(
        h_cm=50.0,
        bw_calculo_cm=15.0,
        cob_mm=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fck_mpa=30.0,
        fyk_kn_cm2=50.0,
        Md_kNm=400.0 * 1.4,
        bw_detalhamento_cm=15.0,
    )
    assert res.cabe is False
    assert res.status_bitola in ("NÃO CABE", "NÃO CONVERGIU")
    assert res.layout is None


def test_convergencia_normal_expone_flag():
    """Caso que converge deve expor convergiu=True (e o resultado normal)."""
    res = dimensionar_bitola_iterativa(
        h_cm=50.0,
        bw_calculo_cm=20.0,
        cob_mm=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fck_mpa=30.0,
        fyk_kn_cm2=50.0,
        Md_kNm=45.0,
        bw_detalhamento_cm=20.0,
    )
    assert res.convergiu is True
    assert res.cabe is True
    assert res.status_bitola == "CABE"


def test_resultado_flexao_expone_convergencia():
    """ResultadoFlexao deve expor a convergência do laço de forma verificável."""
    resultados = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=20.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fyk_kn_cm2=50.0,
        momentos=[60.0],
    )
    res = resultados[0]
    assert res.convergiu is True


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
        fyk_kn_cm2=50.0,
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
