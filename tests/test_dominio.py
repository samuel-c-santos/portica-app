"""EP-02.2 — domínio de deformação: limites de ductilidade e domínio 4.

A NBR 6118:2023 trata `bx_min = 0,45/0,35` como limite de ductilidade
(item 14.6.4.3, δ=1,0) e `η = 0,8/0,8−(fck−50)/400` como profundidade do
diagrama retangular (item 17.2.2-e). São grandezas distintas; o motor
centraliza as duas com referência normativa.

O domínio 4 (bx > 0,628) é recusa explícita: o resultado nunca pode sair
com As,req = 0 e apenas As,min como se a seção fosse válida.
"""

import pytest

from core.calculos.engenharia import (
    BX_DOMINIO_4,
    BX_LIM_DUCTILIDADE_ACIMA_50,
    BX_LIM_DUCTILIDADE_ATE_50,
    ETA_ACIMA_50,
    ETA_ATE_50,
    _resolver_ln,
    calcular_flexao_viga_comum,
    classificar_dominio,
)


class TestConstantesNormativas:
    def test_limites_de_ductilidade(self):
        # 14.6.4.3 com δ=1,0: (1,0−0,44)/1,25 ≈ 0,45; (1,0−0,56)/1,25 ≈ 0,35
        assert BX_LIM_DUCTILIDADE_ATE_50 == 0.45
        assert BX_LIM_DUCTILIDADE_ACIMA_50 == 0.35

    def test_eta_do_diagrama_retangular(self):
        # 17.2.2-e: λ = 0,8 (fck ≤ 50) e 0,8 − (fck−50)/400 (fck > 50)
        assert ETA_ATE_50 == 0.80
        assert ETA_ACIMA_50(60.0) == pytest.approx(0.775, abs=1e-9)
        assert ETA_ACIMA_50(90.0) == pytest.approx(0.70, abs=1e-9)

    def test_fronteira_dominio_4(self):
        # Fronteira 3/4 para CA-50: 3,5‰/(3,5‰+2,07‰) = 0,628
        assert BX_DOMINIO_4 == pytest.approx(0.628, abs=1e-9)


class TestClassificacaoDominio:
    def test_dominio_2(self):
        assert classificar_dominio(0.15) == "DOMINIO_2"

    def test_dominio_3(self):
        assert classificar_dominio(0.50) == "DOMINIO_3"

    def test_dominio_4(self):
        assert classificar_dominio(0.6281) == "DOMINIO_4"


class TestRecusaDominio4:
    def test_momento_que_exigiria_dominio_4_nao_emite_as_req_zero(self):
        """15×50, fck=30, Mk=220: o bx bruto do equilíbrio é 0,789 (domínio 4).

        O motor não pode devolver As,req = 0 + As,min com status CABE. Com
        armadura dupla ele mantém bx no limite de ductilidade (0,45) e a
        bitola é recusada explicitamente; o As,req real continua > 0.
        """
        res = calcular_flexao_viga_comum(
            h_cm=50.0,
            bw_cm=15.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_kn_cm2=50.0,
            momentos=[220.0],
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None

        # reprodução do bx bruto (sem armadura de compressão): domínio 4
        d = r.d_cm_real
        x_bruto, _, _ = _resolver_ln(220.0 * 1.4 * 100, 30.0, 15.0, d)
        assert x_bruto is not None
        assert classificar_dominio(x_bruto / d) == "DOMINIO_4"

        # o resultado não pode fingir uma seção válida com As,req = 0
        assert r.as_req_cm2 > 0.0
        assert r.status_bitola != "CABE"
        assert r.status_bitola in ("NÃO CABE", "NÃO CONVERGIU")
        assert r.alerta != ""
