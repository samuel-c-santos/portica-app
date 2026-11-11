"""EP-04.1: BeamModel e definicao unica de d."""

import dataclasses
import math

import pytest

from core.calculos import engenharia as eng
from core.calculos.secao import BeamModel, altura_util_cm, d_linha_cm
from ui.ftool.dimensionamento import d_els_cm, modelo_de_dados_viga
from ui.ftool.els import AjustesELS, _e_modulus


def _m(**kw):
    base = dict(h=60.0, bw=20.0, fck_mpa=30.0, caa=2, diam_estribo_mm=6.3, diam_barra_mm=16.0)
    base.update(kw)
    return BeamModel(**base)


def test_d_definicao_unica():
    m = _m()
    assert m.cob_mm == 30
    assert m.d_linha_cm == pytest.approx(3.0 + 0.63 + 0.8)
    assert m.d_cm == pytest.approx(60 - 4.43)
    assert m.d_cm == altura_util_cm(60, 30, 6.3, 16)
    assert d_linha_cm(30, 6.3, 16) == m.d_linha_cm


def test_modelo_imutavel():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _m().h = 70.0


def test_derivadas_batem_com_engenharia():
    for fck in (20, 30, 50, 60, 90):
        m = _m(fck_mpa=fck)
        assert m.fcd == eng.fcd_mpa(fck)
        assert m.fctm == eng.fctm_mpa(fck)
        assert m.fctd == eng.fctd_kn_cm2(fck)
        assert m.alpha_c == eng.alpha_c(fck)
        assert getattr(m, "lambda") == eng.lambda_f(fck)
        assert m.Ecs == _e_modulus(fck)


def test_ecs_valor_conhecido():
    assert _m(fck_mpa=25).Ecs == pytest.approx(5600 * math.sqrt(25) * (0.8 + 0.2 * 25 / 80) / 1000)


def test_cobrimento_override_e_caa():
    assert _m(caa=3).cob_mm == 40
    assert _m(caa=3, cob_mm_override=35).cob_mm == 35
    assert eng.CAA_DATA[4]["cobrimento"] == _m(caa=4).cob_mm


def test_ajustes_gera_novo_modelo():
    m = _m()
    novo = AjustesELS(h_override_cm=70, phi_minimo_mm=20).aplicar_ao_modelo(m)
    assert novo is not m and m.h == 60
    assert novo.h == 70 and novo.diam_barra_mm == 20
    assert novo.d_cm == altura_util_cm(70, 30, 6.3, 20)
    assert AjustesELS().aplicar_ao_modelo(m) is m


def test_aplicar_ajustes_usa_d_do_modelo():
    h, d, *_ = AjustesELS(h_override_cm=70).aplicar_ajustes(60, 55.0, 5.0, 30, 16, 6.3, 30)
    assert d == altura_util_cm(70, 30, 6.3, 16)


def test_d_els_usa_modelo():
    dados = dict(h_cm=60, bw_cm=20, caa=2, diam_estribo_mm=6.3, diam_barra_mm=16, fck_mpa=30)
    assert d_els_cm(dados) == modelo_de_dados_viga(dados).d_cm
    assert d_els_cm(dados, 52.0) == 52.0
