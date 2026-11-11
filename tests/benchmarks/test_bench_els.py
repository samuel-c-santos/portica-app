"""
Benchmark normativo: ELS — rigidez e estádio II (EP-03.1).

Caso de referência com a conta à mão, NBR 6118:2023 (§17.3.2 e §17.3.3):

    Seção retangular 20×70, fck=30, d=65 cm, As=12 cm² (φ12,5), Mk=200 kN·m.

    Ic   = bw·h³/12 = 20·343000/12 = 571666,67 cm⁴
    fctm = 0,30·30^(2/3) = 2,89647 MPa = 0,289647 kN/cm²
    Mr   = 1,5·fct·Ic/yt = 1,5·0,289647·571666,67/35 = 7094,4 kN·cm
    Eci  = 5600·√30 = 30672,5 MPa ; αi = 0,875 ; Ecs = 26838,4 MPa
         = 2683,84 kN/cm²
    αE   = Es/Ecs = 21000/2683,84 = 7,8247

    Estádio II (x_ii, T retangular):
    ρ = As/(bw·d) = 12/1300 = 0,0092308
    x_ii = d·(√(αE²ρ² + 2αEρ) − αEρ)
         = 65·(√(0,0052176 + 0,144465) − 0,072233)
         = 65·(0,386892 − 0,072233) = 65·0,314659 = 20,4528 cm
    I_ii = bw·x³/3 + αE·As·(d − x)²
         = 20·20,4528³/3 + 7,8247·12·(44,5472)²
         = 57035 + 93,897·1984,46 = 57035 + 186,256 = 243,291 cm⁴

    I_eq (M = 20000 kN·cm > Mr, Branson):
    (Mr/M)³ = (7094,4/20000)³ = 0,35472³ = 0,044667
    I_eq = 0,044667·571666,67 + 0,955333·243291 = 25533 + 232,248
         = 257,781 cm⁴
"""

import pytest

from ui.ftool.els import _estadio_ii_viga, _inercia_equivalente, _momento_fissuracao

RATIO_MODULAR = 7.8247
IC = 571666.67
MR = 7094.4
X_II = 20.4528
I_II = 243291.0
IEQ = 257781.0


class TestMomentoFissuracao:
    def test_mr_retangular_20x70_fck30(self):
        # Mr = 1,5·0,289647·571666,67/35 = 7094,4 kN·cm
        mr = _momento_fissuracao(bw_cm=20.0, h_cm=70.0, fctm_mpa=2.89647, is_t=False)
        assert mr == pytest.approx(MR, rel=0.005)


class TestEstadioII:
    def test_x_ii_e_i_ii(self):
        x_ii, i_ii = _estadio_ii_viga(
            h_cm=70.0,
            bw_cm=20.0,
            d_cm=65.0,
            as_cm2=12.0,
            ratio_modular=RATIO_MODULAR,
            is_t=False,
            positivo=True,
        )
        assert x_ii == pytest.approx(X_II, rel=0.005)
        assert i_ii == pytest.approx(I_II, rel=0.005)


class TestInerciaEquivalente:
    def test_ieq_fissurado(self):
        # M = 200 kN·m = 20000 kN·cm > Mr → Branson
        ieq = _inercia_equivalente(200.0, MR, IC, I_II)
        assert ieq == pytest.approx(IEQ, rel=0.005)

    def test_ieq_estadio_i(self):
        # M ≤ Mr → estádio I: I_eq = Ic
        assert _inercia_equivalente(50.0, MR, IC, I_II) == pytest.approx(IC, rel=0.001)

    def test_ieq_piso_estadio_ii(self):
        # M >> Mr: I_eq → I_ii (piso normativo)
        assert _inercia_equivalente(2000.0, MR, IC, I_II) == pytest.approx(I_II, rel=0.001)
