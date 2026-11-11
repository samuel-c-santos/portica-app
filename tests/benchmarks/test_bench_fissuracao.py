"""
Benchmark normativo: fissuração (EP-03.1).

Mesma seção do benchmark de ELS: 20×70, fck=30, d=65, As=12 cm² (φ12,5),
Mk=200 kN·m, CAA II (w_lim = 0,3 mm).

Conta à mão, NBR 6118:2023 (§17.3.3.2):

    σs = αe·M·(d − x_ii)/I_ii = 7,8247·20000·(65 − 20,4528)/243291
       = 7,8247·20000·44,5472/243291 = 28,658 kN/cm² = 286,58 MPa
    ηb = 2,25 (barras nervuradas); φr = φ = 1,25 cm
    termo1 = φr/(12,5·ηb) = 1,25/28,125 = 0,0444444
    termo2 = σs/Es = 286,58/210000 = 0,00136562

    wk1 = termo1·termo2·(3σs/fctm)·10
        = 0,0444444·0,00136562·(3·286,58/2,89647)·10
        = 0,0444444·0,00136562·296,65·10 = 0,1801 mm

    h_cr = min(2,5·(h−d); (h−x_ii)/3; 0,5·h)
         = min(12,5; 16,5157; 35) = 12,5 cm
    A_cr = bw·h_cr = 20·12,5 = 250 cm²
    ρ_ri = As/A_cr = 12/250 = 0,048
    wk2 = termo1·termo2·(4/ρ_ri + 45)·10
        = 0,0444444·0,00136562·128,333·10 = 0,07789 mm

    wk = min(wk1, wk2) = 0,078 mm ≤ 0,3 mm (CAA II) → PASSA
"""

import pytest

from ui.ftool.els import calcular_fissuracao

SIGMA_S = 286.58
WK1 = 0.1801
WK2 = 0.07789
A_CR = 250.0
H_CR = 12.5


def _fissurar():
    return calcular_fissuracao(
        h_cm=70.0,
        bw_cm=20.0,
        d_cm=65.0,
        caa=2,
        fck_mpa=30.0,
        fyk_mpa=50.0,
        as_tracao_cm2=12.0,
        phi_barra_mm=12.5,
        momentos=[(1.0, 200.0)],
    )


class TestFissuracaoCasoReferencia:
    def test_sigma_s(self):
        assert _fissurar()["sigma_s_mpa"] == pytest.approx(SIGMA_S, rel=0.01)

    def test_wk1(self):
        assert _fissurar()["wk1_mm"] == pytest.approx(WK1, rel=0.02)

    def test_wk2(self):
        assert _fissurar()["wk2_mm"] == pytest.approx(WK2, rel=0.02)

    def test_wk_final_e_menor_wk(self):
        r = _fissurar()
        # wk é arredondado a 2 casas no retorno
        assert r["wk_mm"] == pytest.approx(min(WK1, WK2), abs=0.01)

    def test_acr_e_h_cr(self):
        r = _fissurar()
        assert r["h_cr_cm"] == pytest.approx(H_CR, rel=0.01)
        assert r["acr_cm2"] == pytest.approx(A_CR, rel=0.01)

    def test_wk_dentro_do_limite_caa2(self):
        r = _fissurar()
        assert r["wk_limite_mm"] == 0.3
        assert r["wk_mm"] <= r["wk_limite_mm"]
        assert r["passa"] is True


class TestFissuracaoSecaoT:
    """A_cr da viga T: momento positivo com h_cr > hf envolve a mesa.

    20×70 T (bf=60, hf=8), d=65, As=12, Mk=200:
    x_ii e σs iguais ao retangular (estádio II usa bw quando x > hf...
    não: para positivo com mesa, x_ii usa bf). Com x_ii < hf (mesa
    comprimida), A_cr = bw·h_cr (tração na alma). Com h_cr > hf:
    A_cr = bf·hf + bw·(h_cr − hf).
    """

    def test_acr_t_positivo_com_h_cr_acima_da_mesa(self):
        from ui.ftool.els import _area_envolvida

        # h_cr = 12,5 > hf = 8 → A_cr = 60·8 + 20·(12,5 − 8) = 480 + 90 = 570 cm²
        a_cr = _area_envolvida(
            h_cm=70, bw_cm=20, bf_cm=60, hf_cm=8, h_cr=12.5, is_t=True, positivo=True
        )
        assert a_cr == pytest.approx(570.0, abs=0.1)
