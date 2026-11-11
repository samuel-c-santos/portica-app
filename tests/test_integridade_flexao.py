"""
Testes de integridade do motor à flexão (EP-01.3).

Invariantes obrigatórias antes de emitir qualquer ResultadoFlexao:
  - as_req_cm2 ≥ 0
  - as_adotado_cm2 ≥ as_req_cm2 (ou status explícito de exceção)
  - d_cm > 0
  - qtd_barras ≥ 1 implica as_adotado_cm2 == qtd_barras · A_φ

Se qualquer invariante falhar → ValueError com contexto, nunca um
resultado "CABE" (subdimensionamento silencioso).
"""

import pytest

from core.calculos.engenharia import (
    _validar_invariantes_flexao,
    area_barra,
    calcular_flexao_viga_comum,
)


class TestInvariantesUnitarias:
    def test_as_req_negativa_levanta_erro(self):
        with pytest.raises(ValueError, match="As,req"):
            _validar_invariantes_flexao(
                contexto="teste",
                as_req_cm2=-8.58,
                as_adotado_cm2=2.01,
                d_cm=45.7,
                qtd_barras=1,
                area_barra_cm2=area_barra(16),
                cabe=True,
                status_bitola="CABE",
            )

    def test_d_nao_positiva_levanta_erro(self):
        with pytest.raises(ValueError, match="d ="):
            _validar_invariantes_flexao(
                contexto="teste",
                as_req_cm2=8.0,
                as_adotado_cm2=8.04,
                d_cm=-0.0,
                qtd_barras=4,
                area_barra_cm2=area_barra(16),
                cabe=True,
                status_bitola="CABE",
            )

    def test_as_adotado_nao_bate_com_qtd_barras(self):
        # 4 barras Ø16 = 8.04 cm², mas as_adotado reportado é 6.0
        with pytest.raises(ValueError, match="qtd_barras"):
            _validar_invariantes_flexao(
                contexto="teste",
                as_req_cm2=6.0,
                as_adotado_cm2=6.0,
                d_cm=45.0,
                qtd_barras=4,
                area_barra_cm2=area_barra(16),
                cabe=True,
                status_bitola="CABE",
            )

    def test_as_adotado_menor_que_req_com_cabe_levanta_erro(self):
        # O bug central: resultado "CABE" com as_adotado < as_req
        with pytest.raises(ValueError, match="subdimensionamento"):
            _validar_invariantes_flexao(
                contexto="teste",
                as_req_cm2=32.67,
                as_adotado_cm2=8.04,
                d_cm=45.0,
                qtd_barras=4,
                area_barra_cm2=area_barra(16),
                cabe=True,
                status_bitola="CABE",
            )

    def test_as_adotado_menor_que_req_com_status_recusado_nao_levanta(self):
        # Status de exceção explícito: recusa é reportada, não levantada
        _validar_invariantes_flexao(
            contexto="teste",
            as_req_cm2=32.67,
            as_adotado_cm2=8.04,
            d_cm=45.0,
            qtd_barras=4,
            area_barra_cm2=area_barra(16),
            cabe=False,
            status_bitola="NÃO CABE",
        )

    def test_invariantes_satisfeitas_nao_levanta(self):
        _validar_invariantes_flexao(
            contexto="teste",
            as_req_cm2=8.0,
            as_adotado_cm2=8.04,
            d_cm=45.0,
            qtd_barras=4,
            area_barra_cm2=area_barra(16),
            cabe=True,
            status_bitola="CABE",
        )

    def test_erro_inclui_contexto(self):
        with pytest.raises(ValueError) as excinfo:
            _validar_invariantes_flexao(
                contexto="Mk=400.0 kN·m, seção 15×50 cm",
                as_req_cm2=32.67,
                as_adotado_cm2=8.04,
                d_cm=45.0,
                qtd_barras=4,
                area_barra_cm2=area_barra(16),
                cabe=True,
                status_bitola="CABE",
            )
        assert "Mk=400.0" in str(excinfo.value)
        assert "15×50" in str(excinfo.value)


class TestFluxoEndToEnd:
    def test_caso_auditoria_h50_bw15_mk400(self):
        """Caso da auditoria: h=50, bw=15, CAA II, fck=30, Ø5/Ø16, Mk=400.

        Ou o motor falha (ValueError), ou reporta as_adotado ≥ as_req com
        status de recusa explícito. Nunca um resultado "CABE" com
        as_adotado < as_req.
        """
        resultados = calcular_flexao_viga_comum(
            h_cm=50.0,
            bw_cm=15.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_kn_cm2=50.0,
            momentos=[400.0],
        )
        res = resultados[0]
        assert res is not None
        # Sempre: invariante de concordância qtd·A_φ
        assert res.as_adotado_cm2 == pytest.approx(res.qtd_barras * area_barra(16.0), abs=0.011)
        if res.as_adotado_cm2 < res.as_req_cm2 - 1e-6:
            # só é aceitável com status de recusa explícito
            assert res.status_bitola in ("NÃO CABE", "NÃO CONVERGIU")

    def test_resultados_normais_satisfazem_invariantes(self):
        """Em seções normais, os invariantes valem para todos os momentos."""
        momentos = [40.0, 80.0, 120.0, 160.0]
        resultados = calcular_flexao_viga_comum(
            h_cm=50.0,
            bw_cm=20.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_kn_cm2=50.0,
            momentos=momentos,
        )
        assert len(resultados) == len(momentos)
        for res in resultados:
            if res is None:
                continue
            assert res.as_req_cm2 >= 0.0
            assert res.d_cm_real > 0.0
            assert res.as_adotado_cm2 == pytest.approx(
                res.qtd_barras * area_barra(res.diametro_mm), abs=0.011
            )
            if res.status_bitola in ("CABE", "2 CAMADAS", "3 CAMADAS"):
                assert res.as_adotado_cm2 >= res.as_req_cm2 - 1e-6

    def test_viga_t_invariantes(self):
        """O caminho da viga T também satisfaz os invariantes."""
        from core.calculos.engenharia import calcular_flexao_viga_t

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
        for res in resultados:
            if res is None:
                continue
            assert res.as_adotado_cm2 == pytest.approx(
                res.qtd_barras * area_barra(res.diametro_mm), abs=0.011
            )
            assert res.d_cm_real > 0.0
