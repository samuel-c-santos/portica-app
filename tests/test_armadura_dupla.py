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

    # EP-02.1: conta à mão pelo equilíbrio NBR (§17.3.2), com a d convergida
    # do motor (45,7 cm):
    #     fcd = 0,85·30/1,4/10 = 1,82143 kN/cm²
    #     x_lim = 0,45·45,7 = 20,565 cm ; z_lim = 45,7 − 0,4·20,565 = 37,474 cm
    #     Md,lim = 1,82143·12·20,565·37,474 = 16844 kN·cm = 168,44 kN·m
    #     As1 = 16844/(43,4783·37,474) = 10,338 cm²
    #     Md,exc = 194,88 − 168,44 = 26,44 kN·m = 2644 kN·cm
    #     As2 = 2644/(43,4783·(45,7−4,3)) = 1,469 cm²
    #     As,req = As1 + As2 = 11,807 cm²
    assert res.status_bitola == "NÃO CABE"
    assert res.md_limite_knm == pytest.approx(168.44, abs=1.0)
    # Momento excedente: 194,88 − 168,44 = 26,44
    assert res.md_excedente_knm == pytest.approx(194.88 - res.md_limite_knm, abs=0.1)

    assert res.as_linha_cm2 > 0.0
    assert res.as_linha_adotada > 0.0
    assert "Armadura dupla utilizada" in res.alerta

    assert res.as_linha_cm2 == pytest.approx(1.469, abs=0.02)
    assert res.as_req_cm2 == pytest.approx(11.807, abs=0.05)


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


def test_6_balanco_as_linha_maior_que_as2_quando_fs_nao_escoa():
    """EP-02.4: com d' grande (CAA IV, Ø20), f_s' < fyd → As' > As2.

    h=30, bw=40, fck=30, cob=50 mm, Ø20, Mk=160/1,4 → Md=160 kN·m.
    d=23,5 cm ; x_lim=0,45·23,5=10,575 cm ; d'=6,5 cm (detalhamento, 1 camada)
    Md,lim = 1,82143·40·10,575·(23,5−4,23) = 148,47 kN·m
    As2 = (160−148,47)·100/(43,4783·(23,5−6,5)) = 1,56 cm²
    ε_s' = 3,5‰·(10,575−6,5)/10,575 = 1,348‰ → f_s' = 28,3 kN/cm² (< fyd)
    As' = 1,56·43,4783/28,3 = 2,40 cm² (ρ''=1,2 cm² não governa)
    """
    res = calcular_flexao_viga_comum(
        h_cm=30.0,
        bw_cm=40.0,
        caa=4,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=20.0,
        fyk_mpa=50.0,
        momentos=[160.0 / 1.4],
        gamma_f=1.4,
    )
    r = res[0]
    assert r is not None
    assert r.armadura_dupla is True
    assert r.as_linha_cm2 == pytest.approx(2.40, abs=0.03)
    # o balanço exige mais compressão que a tração adicional (As2 ≈ 1,56)
    assert r.as_linha_cm2 > 1.56
    assert r.as_linha_adotada >= r.as_linha_cm2


def test_7_rho_linha_minima_governa():
    """EP-02.4: As' ≥ ρ'' = 0,1% da área de concreto.

    h=100, bw=30 → ρ'' = 0,001·3000 = 3,0 cm². Com Md próximo de Md,lim,
    o As' de balanço é menor e o mínimo governa.
    """
    res = calcular_flexao_viga_comum(
        h_cm=100.0,
        bw_cm=30.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fyk_mpa=50.0,
        momentos=[1350.0],
        gamma_f=1.4,
    )
    r = res[0]
    assert r is not None
    assert r.armadura_dupla is True
    assert r.as_linha_cm2 == pytest.approx(3.0, abs=0.01)
    assert r.as_linha_adotada >= 3.0
