"""
Benchmark normativo: cisalhamento (EP-03.1).

Caso de referência com a conta à mão, NBR 6118:2023 (§17.4.2, Modelo I):

    Caso padrão: viga 20×70, fck=30, CAA II (cob=30mm), Øe=5mm, Øl=16mm,
    fyk_estribo=50 kN/cm² (CA-50), Vk=132 kN (γf=1,4 → Vsd=184,8 kN).

    d   = 70 − 3 − 0,5 − 0,8 = 65,7 cm
    fcd = 0,85·30/1,4 = 18,2143 MPa
    λ   = 0,80
    Vrd2 = 0,27·λ·fcd·bw·d = 0,27·0,80·18,2143·20·65,7 = 5169,65 kN·cm
         = 516,97 kN
    fctd = fctk,inf/1,4 = 0,7·0,30·30^(2/3)/1,4 = 0,144824 kN/cm²
    Vc   = 0,6·fctd·bw·d = 0,6·0,144824·20·65,7 = 114,18 kN
    Vsw  = Vsd − Vc = 184,8 − 114,18 = 70,62 kN
    fywd = 50/1,15 = 43,4783 kN/cm² (cap 43,5 não governa)
    Asw/s,req = Vsw/(fywd·d) = 70,62/(43,4783·65,7) = 0,024723 cm²/cm
              = 2,4723 cm²/m
    Asw/s,min (CA-50, fck=30) = 0,1159·bw = 2,318 cm²/m
    Asw/s,adot = max(req, min) = 2,4723 cm²/m
    s  = Asw,ramo/(Asw/s) = (2·0,19635·100)/2,4723 = 15,88 cm
    s_max (Vsd ≤ 0,67·Vrd2) = min(0,6·d, 30) = min(39,42, 30) = 30 cm
    s,adotado = min(s, s_max)  [EP-02.5: o espaçamento adotado é limitado]
"""

import pytest

from core.calculos.engenharia import (
    area_barra,
    calcular_cisalhamento_viga_comum,
)

CASE = dict(
    h_cm=70.0,
    bw_cm=20.0,
    fck_mpa=30.0,
    diam_estribo_mm=5.0,
    diam_barra_mm=16.0,
    fyk_estribo_kn_cm2=50.0,
    fyk_barra_mpa=50.0,
    caa=2,
)


class TestCisalhamentoCasoPadrao:
    """Caso padrão: Vk=132 kN → Vsd=184,8 kN ≤ 0,67·Vrd2 (regime frouxo)."""

    def _r(self, vk=132.0):
        return calcular_cisalhamento_viga_comum(forcas_cortantes=[vk], gamma_f=1.4, **CASE)[0]

    def test_vrd2(self):
        # Vrd2 = 0,27·0,80·18,2143·20·65,7/10 = 516,97 kN
        assert self._r().vrd2_kn == pytest.approx(516.97, abs=0.5)

    def test_vc(self):
        # Vc = 0,6·0,144824·20·65,7 = 114,18 kN
        assert self._r().vc_kn == pytest.approx(114.18, abs=0.05)

    def test_vsw(self):
        # Vsw = 184,8 − 114,18 = 70,62 kN
        assert self._r().vsw_kn == pytest.approx(70.62, abs=0.05)

    def test_asw_s_req(self):
        # Asw/s,req = 70,62/(43,4783·65,7)·100 = 2,4723 cm²/m
        r = self._r()
        asw_req = r.vsw_kn / (50.0 / 1.15 * 65.7) * 100
        assert r.asw_usado_cm2_m == pytest.approx(asw_req, abs=0.01)
        assert r.asw_usado_cm2_m == pytest.approx(2.4723, abs=0.01)

    def test_asw_s_min(self):
        # tabela CA-50, fck=30: 0,1159·20 = 2,318 cm²/m
        assert self._r().asw_s_min_cm2_m == pytest.approx(2.318, abs=0.001)

    def test_dist_estribos(self):
        # s = (2·area_barra(5)·100)/2,4723 = 39,270/2,4723 = 15,88 cm
        asw_ramo = 2 * area_barra(5.0)
        s = asw_ramo * 100 / self._r().asw_usado_cm2_m
        assert self._r().dist_estribos_cm == pytest.approx(s, abs=0.1)
        assert self._r().dist_estribos_cm == pytest.approx(15.9, abs=0.1)

    def test_s_max_regime_frouxo(self):
        # Vsd = 184,8 ≤ 0,67·516,97 = 346,4 → s_max = min(0,6·65,7, 30) = 30 cm
        assert self._r().s_max_cm == pytest.approx(30.0, abs=0.05)

    def test_fywd_cap_nao_governa(self):
        # fywd = 50/1,15 = 43,4783 ≤ 43,5 → cap não governa
        r = self._r()
        fywd = 50.0 / 1.15
        assert fywd < 43.5
        # Asw/s,req recalculado com fywd do motor tem que reproduzir asw_usado
        assert r.vsw_kn / (fywd * 65.7) * 100 == pytest.approx(r.asw_usado_cm2_m, abs=0.01)


class TestCisalhamentoRegimeRestritivo:
    """EP-03.3: Vsd > 0,67·Vrd2 → s_max = min(0,3·d, 20).

    Vk=350 → Vsd = 490 kN > 0,67·516,97 = 346,4 (e 490 < Vrd2 ✓).
    Vsw = 490 − 114,18 = 375,82 kN
    Asw/s,req = 375,82/(43,4783·65,7)·100 = 13,157 cm²/m
    s = 39,270/13,157 = 2,98 cm
    s_max = min(0,3·65,7, 20) = min(19,71, 20) = 19,7 cm
    """

    def test_s_max_ramo_restritivo(self):
        r = calcular_cisalhamento_viga_comum(forcas_cortantes=[350.0], gamma_f=1.4, **CASE)[0]
        assert 350.0 * 1.4 > 0.67 * r.vrd2_kn
        assert r.s_max_cm == pytest.approx(19.7, abs=0.05)

    def test_asw_e_s_restritivo(self):
        r = calcular_cisalhamento_viga_comum(forcas_cortantes=[350.0], gamma_f=1.4, **CASE)[0]
        vsw = 350.0 * 1.4 - r.vc_kn
        assert r.vsw_kn == pytest.approx(vsw, abs=0.05)
        asw_req = vsw / (50.0 / 1.15 * 65.7) * 100
        assert r.asw_usado_cm2_m == pytest.approx(asw_req, abs=0.01)
        s = 2 * area_barra(5.0) * 100 / asw_req
        assert r.dist_estribos_cm == pytest.approx(s, abs=0.1)


class TestCisalhamentoCA60:
    """Estribo CA-60: fywd cru = 60/1,15 = 52,17 > 43,5 → cap governa.

    Asw/s,req = 70,62/(43,5·65,7)·100 = 2,4674 cm²/m (fywd capado).
    """

    def test_fywd_cap_435(self):
        r = calcular_cisalhamento_viga_comum(
            forcas_cortantes=[132.0],
            gamma_f=1.4,
            **{**CASE, "fyk_estribo_kn_cm2": 60.0},
        )[0]
        asw_req_capado = r.vsw_kn / (43.5 * 65.7) * 100
        assert r.asw_usado_cm2_m == pytest.approx(asw_req_capado, abs=0.01)
        # com o fywd cru (52,17) o resultado seria MENOR — o cap é essencial
        asw_req_sem_cap = r.vsw_kn / (60.0 / 1.15 * 65.7) * 100
        assert asw_req_sem_cap < asw_req_capado
        assert r.asw_usado_cm2_m == pytest.approx(2.4674, abs=0.01)


def test_espacamento_adotado_limitado_por_smax():
    """EP-02.5: com Ø8 e Vk baixa, o s requerido (~43 cm) é cortado em s_max."""
    from core.calculos.engenharia import area_barra

    r = calcular_cisalhamento_viga_comum(
        forcas_cortantes=[30.0],
        gamma_f=1.4,
        **{**CASE, "diam_estribo_mm": 8.0, "fyk_estribo_kn_cm2": 50.0},
    )[0]
    s_requerido = 2 * area_barra(8.0) * 100 / r.asw_usado_cm2_m
    assert s_requerido > r.s_max_cm
    assert r.dist_estribos_cm == pytest.approx(r.s_max_cm, abs=0.05)
    assert r.passa_smax == "SIM"
