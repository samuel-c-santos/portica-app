"""
Benchmark normativo: flexão — equilíbrio NBR exato (EP-03.1).

Casos de referência com a conta à mão pelo equilíbrio normativo
NBR 6118:2023, §17.3.2 (domínio 2):

    Md = fcd·b·x·(d − 0,4x)   →   0,4x² − d·x + Md/(fcd·b) = 0
    z = d − 0,4x ;  As = Md/(fyd·z) ;  βx = x/d
    fcd = αc·fck/1,4 ;  fyd = fyk/1,15

EP-02.1: o motor passou a usar o equilíbrio normativo (a calibração
empírica da planilha foi removida). Os benchmarks abaixo são asserções
diretas — não há mais xfail.

A conta é feita com a `d` CONVERGIDA do motor (r.d_cm_real) para isolar a
diferença de fórmula da diferença de geometria (nº de camadas).

Exemplo numérico (caso 1, com a d estimada de 1 camada = 55,7 cm):
    fcd = 0,85·30/1,4 = 18,2143 MPa = 1,82143 kN/cm²
    Md/(fcd·b) = 14000/(1,82143·20) = 384,33
    0,4x² − 55,7x + 384,33 = 0 → x² − 139,25x + 960,83 = 0
    Δ = 19390,6 − 3843,3 = 15547,3 → √Δ = 124,688
    x = (139,25 − 124,688)/2 = 7,281 cm ; βx = 7,281/55,7 = 0,13065
    z = 55,7 − 0,4·7,281 = 52,788 cm
    As = 14000/(43,4783·52,788) = 6,0998 cm²
"""

import math

import pytest

from core.calculos.engenharia import (
    alpha_c,
    calcular_flexao_viga_comum,
    rho_min,
)

FYD = 50.0 / 1.15  # 43,4783 kN/cm²


def _x_nbr(md_kncm: float, fck_mpa: float, b_cm: float, d_cm: float) -> float:
    """Resolve 0,4x² − d·x + Md/(fcd·b) = 0 (menor raiz, domínio 2)."""
    fcd_kn_cm2 = alpha_c(fck_mpa) * fck_mpa / 1.4 / 10.0
    c = md_kncm / (fcd_kn_cm2 * b_cm)
    delta = d_cm**2 - 4 * 0.4 * c
    return (d_cm - math.sqrt(delta)) / (2 * 0.4)


CASOS = {
    1: dict(
        doc="20×60, fck=30, Ø16, Mk=100 (Md=140): d=55,7 → x=7,281, βx=0,13065, "
        "z=52,788, As=6,0998 cm²",
        h_cm=60.0,
        bw_cm=20.0,
        fck_mpa=30.0,
        diam_barra_mm=16.0,
        Mk=100.0,
    ),
    2: dict(
        doc="20×40, fck=25, Ø16, Mk=60 (Md=84): d=36,2 → x=11,707, βx=0,32350, "
        "z=31,517, As=6,1332 cm²",
        h_cm=40.0,
        bw_cm=20.0,
        fck_mpa=25.0,
        diam_barra_mm=16.0,
        Mk=60.0,
    ),
    3: dict(
        doc="20×50, fck=50, Ø25, Mk=150 (Md=210): d=45,75 → x=8,140, βx=0,17792, "
        "z=42,494, As=11,3628 cm²",
        h_cm=50.0,
        bw_cm=20.0,
        fck_mpa=50.0,
        diam_barra_mm=25.0,
        Mk=150.0,
    ),
}


def _resultado(idx):
    caso = CASOS[idx]
    return calcular_flexao_viga_comum(
        h_cm=caso["h_cm"],
        bw_cm=caso["bw_cm"],
        caa=2,
        fck_mpa=caso["fck_mpa"],
        diam_estribo_mm=5.0,
        diam_barra_mm=caso["diam_barra_mm"],
        fyk_kn_cm2=50.0,
        momentos=[caso["Mk"]],
        gamma_f=1.4,
    )[0]


class TestEquilibrioNBR:
    """βx, x e As contra o equilíbrio NBR — 3 casos de referência."""

    @pytest.mark.parametrize("idx", [1, 2, 3])
    def test_beta_x_e_x_contra_equilibrio_nbr(self, idx):
        caso = CASOS[idx]
        r = _resultado(idx)
        assert r.armadura_dupla is False
        d = r.d_cm_real
        x = _x_nbr(r.momento_kNm * 100, caso["fck_mpa"], caso["bw_cm"], d)
        beta_x = x / d
        assert r.bx == pytest.approx(beta_x, rel=0.005)
        assert r.x_cm == pytest.approx(x, rel=0.005)

    @pytest.mark.parametrize("idx", [1, 2, 3])
    def test_as_contra_equilibrio_nbr(self, idx):
        caso = CASOS[idx]
        r = _resultado(idx)
        assert r.armadura_dupla is False
        d = r.d_cm_real
        x = _x_nbr(r.momento_kNm * 100, caso["fck_mpa"], caso["bw_cm"], d)
        z = d - 0.4 * x
        as_nbr = r.momento_kNm * 100 / (FYD * z)
        assert r.as_req_cm2 == pytest.approx(as_nbr, rel=0.005)


class TestAsMin:
    """As,min = ρ_min·bw·h/100 — NBR 6118:2023, Tabela 17.3.

    ρ_min = 0,150% para fck ≤ 32 MPa (vale para 20/25/30).
    """

    def test_as_min_retangular_fck30(self):
        # As,min = 0,150/100 · 20·70 = 0,15·14 = 2,10 cm²
        assert rho_min(30) == pytest.approx(0.150, abs=1e-9)
        r = calcular_flexao_viga_comum(
            h_cm=70.0,
            bw_cm=20.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_kn_cm2=50.0,
            momentos=[20.0],
            gamma_f=1.4,
        )[0]
        assert r.asmin_cm2 == pytest.approx(2.10, abs=0.01)

    def test_as_min_fck40(self):
        # Tabela 17.3: fck=40 → ρ_min = 0,179% ; As,min = 0,179/100·20·70 = 2,506 cm²
        assert rho_min(40) == pytest.approx(0.179, abs=1e-9)


class TestDEfetiva:
    """d efetiva do detalhamento: d = h − y_cg do layout convergido."""

    def test_d_uma_camada(self):
        from core.detailing.domain import BeamDetailer, BeamDetailingInput

        layout = BeamDetailer().detail(
            BeamDetailingInput(
                bw=300.0,
                h=500.0,
                c_nom=25.0,
                phi_estribo=6.3,
                phi_barra=16.0,
                d_max_agregado=19.0,
                total_bars=4,
            )
        )
        assert layout.layer_count == 1
        # y_cg = c + φe + φ/2 = 25 + 6,3 + 8 = 39,3 mm
        assert layout.y_cg == pytest.approx(39.3, abs=0.1)
        assert layout.d_efetiva == pytest.approx(500.0 - 39.3, abs=0.1)

    def test_d_duas_camadas(self):
        """8Ø16 em 30×50 (n_max por camada = 6): camadas 6+2.

        e_v,min = max(20; 16; 1,33·19) = 25,27 mm
        camada 0 (6 barras): y = 25 + 6,3 + 8 = 39,3
        camada 1 (2 barras): y = 39,3 + 16 + 25,27 = 80,57
        y_cg = (6·39,3 + 2·80,57)/8 = (235,8 + 161,14)/8 = 49,6175
        d = 500 − 49,6175 = 450,3825 mm
        """
        from core.detailing.domain import BeamDetailer, BeamDetailingInput

        layout = BeamDetailer().detail(
            BeamDetailingInput(
                bw=300.0,
                h=500.0,
                c_nom=25.0,
                phi_estribo=6.3,
                phi_barra=16.0,
                d_max_agregado=19.0,
                total_bars=8,
            )
        )
        assert layout.layer_count == 2
        assert layout.layers[0].bar_count == 6
        assert layout.layers[1].bar_count == 2
        y_cg = (6 * 39.3 + 2 * (39.3 + 16 + 25.27)) / 8
        assert layout.y_cg == pytest.approx(y_cg, abs=0.1)
        assert layout.d_efetiva == pytest.approx(500.0 - y_cg, abs=0.1)
