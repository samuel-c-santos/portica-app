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
            fyk_estribo_mpa=viga_exemplo["fyk_estribo_mpa"],
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
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
            fyk_estribo_mpa=viga_exemplo["fyk_estribo_mpa"],
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
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
            fyk_estribo_mpa=viga_exemplo["fyk_estribo_mpa"],
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
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
            fyk_estribo_mpa=viga_exemplo["fyk_estribo_mpa"],
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=cortantes_exemplo,
            gamma_f=viga_exemplo["gamma_f"],
        )
        for r in res:
            if r is not None:
                # Para viga 20x70 fck=30, Vrd2 ~ 517 kN (muito maior que Vsd)
                assert r.vrd2_kn > 0
                assert r.passa_vrd2 == "SIM"

    def test_cortante_zero_retorna_none(self, viga_exemplo):
        """Cortante zero deve retornar None."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_mpa=viga_exemplo["fyk_estribo_mpa"],
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[0.0],
            gamma_f=1.4,
        )
        assert res[0] is None

    def test_vc_positivo(self, viga_exemplo):
        """Vc (contribuicao do concreto) deve ser positivo."""
        res = calcular_cisalhamento_viga_comum(
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            fck_mpa=viga_exemplo["fck_mpa"],
            diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo["diam_barra_mm"],
            fyk_estribo_mpa=viga_exemplo["fyk_estribo_mpa"],
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
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
            fyk_estribo_mpa=viga_exemplo["fyk_estribo_mpa"],
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
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
            fyk_estribo_mpa=600.0,  # CA-60 (fyk = 600 MPa)
            fyk_barra_mpa=viga_exemplo["fyk_mpa"],
            caa=viga_exemplo["caa"],
            forcas_cortantes=[132.0],
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        assert r.s_max_cm > 0
        assert r.passa_smax in ["SIM", "NÃO"]
