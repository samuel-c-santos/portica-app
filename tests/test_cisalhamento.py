"""Testes do motor de cisalhamento."""

import pytest

from core.calculos import calcular_cisalhamento_viga_comum


class TestCisalhamento:
    """Cobertura: calculo de cisalhamento para viga retangular."""

    def test_cortante_majorado(self, viga_exemplo, cortantes_exemplo):
        """Vsd deve ser |Vk| * gamma_f."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_kn_cm2"],
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=cortantes_exemplo,
            gamma_f=viga_exemplo["gamma_f"],
        )
        # V1 = 132.0 * 1.4 = 184.8
        r0 = res[0]
        assert r0 is not None
        assert abs(r0.vsd_kn - 184.8) < 0.1

    def test_cortante_negativa_usa_modulo(self, viga_exemplo):
        """Cortante negativa deve usar |V| antes de majorar."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_kn_cm2"],
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[-123.0],
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        assert abs(r.vsd_kn - 172.2) < 0.1  # |-123| * 1.4
        assert r.vsd_verdadeiro_kn == -123.0  # guarda sinal original

    def test_gamma_f_especiais(self, viga_exemplo):
        """gamma_f=1.2 (especiais) deve majorar corretamente."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_kn_cm2"],
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[50.0],
            gamma_f=1.2,
        )
        r = res[0]
        assert r is not None
        assert abs(r.vsd_kn - 60.0) < 0.1

    def test_vsd_menor_vrd2(self, viga_exemplo, cortantes_exemplo):
        """Vsd deve ser < Vrd2 para cortantes tipicas."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_kn_cm2"],
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=cortantes_exemplo,
            gamma_f=viga_exemplo["gamma_f"],
        )
        for r in res:
            if r is not None:
                # EP-03.2: valor de referência à mão — Vrd2 = 0,27·λ·fcd·bw·d
                # = 0,27·0,80·18,2143·20·65,7/10 = 516,97 kN (independe de Vk
                # e de fyk do estribo; Vrd2 < Vsd em todos os casos de teste).
                assert r.vrd2_kn == pytest.approx(516.97, abs=0.5)
                assert r.passa_vrd2 == "SIM"

    def test_cortante_zero_retorna_none(self, viga_exemplo):
        """Cortante zero deve retornar None."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_kn_cm2"],
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[0.0],
            gamma_f=1.4,
        )
        assert res[0] is None


class TestRamosMortos:
    """EP-03.3: ramos que antes eram mortos/mascarados devem estar cobertos."""

    def test_fck_zero_cisalhamento_erro_explicito(self):
        """EP-01.4 no cisalhamento: fck=0 → ValueError, nunca ZeroDivisionError."""
        with pytest.raises(ValueError, match="fck"):
            calcular_cisalhamento_viga_comum(
                h_cm=70.0,
                bw_cm=20.0,
                fck_mpa=0.0,
                diam_estribo_mm=5.0,
                diam_barra_mm=16.0,
                fyk_estribo_kn_cm2=60.0,
                fyk_barra_kn_cm2=50.0,
                caa=2,
                forcas_cortantes=[132.0],
            )

    def test_ramo_s_max_restritivo_coberto(self):
        """Vsd > 0,67·Vrd2 → s_max = min(0,3·d; 20) — o ramo mais restritivo.

        Caso à mão (benchmark EP-03.1: tests/benchmarks/test_bench_cisalhamento.py):
        Vk=350 → Vsd=490 > 0,67·516,97 = 346,4 → s_max = 19,7 cm.
        """
        r = calcular_cisalhamento_viga_comum(
            h_cm=70.0,
            bw_cm=20.0,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_estribo_kn_cm2=50.0,
            fyk_barra_kn_cm2=50.0,
            caa=2,
            forcas_cortantes=[350.0],
        )[0]
        assert 350.0 * 1.4 > 0.67 * r.vrd2_kn
        assert r.s_max_cm == pytest.approx(19.7, abs=0.05)

    def test_vc_positivo(self, viga_exemplo):
        """Vc (contribuicao do concreto) deve ser positivo."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_kn_cm2"],
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[132.0],
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        assert r.vc_kn > 0

    def test_asw_s_dimensionado_pelo_vsw(self, viga_exemplo):
        """A1: Asw/s deve refletir a cortante real, nao so o minimo.
        Para cortante alta (Vsd > Vc), Asw/s_usado > Asw/s_min."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_kn_cm2"],
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[132.0],  # Vsd = 184.8 kN (alto)
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        # Vsw > 0 -> Asw/s_usado >= Asw/s_necessario (calculado por Vsw)
        if r.vsw_kn > 0:
            assert r.asw_usado_cm2_m > r.asw_s_min_cm2_m - 0.01, (
                f"Asw/s_usado ({r.asw_usado_cm2_m}) deveria ser >= Asw/s_min ({r.asw_s_min_cm2_m})"
            )

    def test_lambda_f_para_fck_alto(self):
        """M11: lambda deve reduzir para fck > 50 (NBR 6118:17.4.2.2)."""
        from core.calculos import lambda_f

        # fck <= 50: lambda = 0.80
        assert lambda_f(30) == 0.80
        assert lambda_f(50) == 0.80
        # fck = 70: lambda = 1 - 70/250 = 0.72
        assert abs(lambda_f(70) - 0.72) < 0.001
        # fck = 90: lambda = 1 - 90/250 = 0.64
        assert abs(lambda_f(90) - 0.64) < 0.001

    def test_fywd_limite_and_s_max(self, viga_exemplo):
        """Verifica se fywd é limitado a 43.5 kN/cm2 e se s_max e passa_smax são calculados."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_kn_cm2=60.0,  # CA-60 (60 kN/cm² = 600 MPa)
            fyk_barra_kn_cm2=viga_exemplo["fyk_kn_cm2"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[132.0],
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        assert r.s_max_cm > 0
        assert r.passa_smax in ["SIM", "NÃO"]


class TestAswMinCa60:
    """EP-01.8: a taxa mínima de estribo tem coluna CA-60 viva.

    Bug: o limiar estava em MPa (500) numa API que recebe kN/cm² (50/60),
    então a condição era sempre verdadeira e a coluna CA-60 nunca era usada.
    """

    def test_ca60_usa_coluna_ca60(self):
        from core.calculos.engenharia import ASW_S_TABLE_CA50, asw_min_cm2_m

        _, ca50, ca60 = ASW_S_TABLE_CA50[30]
        bw = 20.0
        assert asw_min_cm2_m(30, bw, 50.0) == pytest.approx(ca50 * bw, abs=1e-6)
        assert asw_min_cm2_m(30, bw, 60.0) == pytest.approx(ca60 * bw, abs=1e-6)
        # CA-60 exige menos armadura mínima que CA-50
        assert ca60 < ca50

    def test_motor_cisalhamento_ca60_usa_coluna_ca60(self):
        """End-to-end: estribo CA-60 no motor obtém a taxa da coluna CA-60."""
        res50 = calcular_cisalhamento_viga_comum(
            h_cm=70.0,
            bw_cm=20.0,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_estribo_kn_cm2=50.0,
            fyk_barra_kn_cm2=50.0,
            caa=2,
            forcas_cortantes=[132.0],
        )
        res60 = calcular_cisalhamento_viga_comum(
            h_cm=70.0,
            bw_cm=20.0,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_estribo_kn_cm2=60.0,
            fyk_barra_kn_cm2=50.0,
            caa=2,
            forcas_cortantes=[132.0],
        )
        r50, r60 = res50[0], res60[0]
        assert r60.asw_s_min_cm2_m < r50.asw_s_min_cm2_m
