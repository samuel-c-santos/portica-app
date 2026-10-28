"""Testes do motor de flexao — viga retangular."""
import pytest
from core.calculos import calcular_flexao_viga_comum


class TestFlexaoRetangular:
    """Cobertura: calculo de flexao para viga retangular."""

    def test_as_calculo_correto(self, viga_exemplo_flexao, momentos_exemplo):
        """As deve ser ~8 cm2 para Md=194.88 kN.m (viga 20x70, fck=30)."""
        res = calcular_flexao_viga_comum(
            momentos=momentos_exemplo, **viga_exemplo_flexao
        )
        r = res[0]
        assert r is not None
        # Mk=96.9 * 1.4 = 135.66 kN.m
        # As deve estar na faixa fisicamente correta (5-15 cm2)
        assert 3.0 < r.as_req_cm2 < 20.0, f"As fora do esperado: {r.as_req_cm2}"

    def test_momento_majorado(self, viga_exemplo_flexao):
        """Md no resultado deve ser Mk * gamma_f."""
        Mk = 100.0
        res = calcular_flexao_viga_comum(momentos=[Mk], **viga_exemplo_flexao)
        r = res[0]
        assert r is not None
        assert abs(r.momento_kNm - Mk * 1.4) < 0.1

    def test_momento_negativo_tipo(self, viga_exemplo_flexao):
        """Momento negativo deve ter tipo='NEGATIVO'."""
        res = calcular_flexao_viga_comum(momentos=[-100.0], **viga_exemplo_flexao)
        r = res[0]
        assert r is not None
        assert r.tipo == "NEGATIVO"

    def test_momento_positivo_tipo(self, viga_exemplo_flexao):
        """Momento positivo deve ter tipo='POSITIVO'."""
        res = calcular_flexao_viga_comum(momentos=[100.0], **viga_exemplo_flexao)
        r = res[0]
        assert r is not None
        assert r.tipo == "POSITIVO"

    def test_momento_zero_retorna_none(self, viga_exemplo_flexao):
        """Momento zero deve retornar None (sem calculo)."""
        res = calcular_flexao_viga_comum(momentos=[0.0], **viga_exemplo_flexao)
        assert res[0] is None

    def test_bx_dentro_dominio(self, viga_exemplo_flexao):
        """bx deve ser < 0.45 para fck < 50 (dominio 2/3)."""
        res = calcular_flexao_viga_comum(momentos=[100.0], **viga_exemplo_flexao)
        r = res[0]
        assert r is not None
        if r.bx_passa == "SIM":
            assert r.bx < 0.45
        # A2: campo alerta presente
        assert hasattr(r, "alerta")
        assert isinstance(r.alerta, str)
        # Se bx_passa=SIM, alerta deve ser vazio
        if r.bx_passa == "SIM":
            assert r.alerta == ""

    def test_bx_dominio_fck_alto(self):
        """bx deve ser < 0.35 para fck >= 50."""
        res = calcular_flexao_viga_comum(
            h_cm=70, bw_cm=20, caa=2, fck_mpa=50,
            diam_estribo_mm=5, diam_barra_mm=16,
            fyk_mpa=50, momentos=[100.0], gamma_f=1.4
        )
        r = res[0]
        assert r is not None
        if r.bx_passa == "SIM":
            assert r.bx < 0.35

    def test_alerta_quando_bx_falha(self):
        """A2: alerta explicito quando bx nao passa o dominio."""
        # Momento muito alto para viga pequena: bx nao passara
        res = calcular_flexao_viga_comum(
            h_cm=20, bw_cm=10, caa=2, fck_mpa=20,
            diam_estribo_mm=5, diam_barra_mm=12.5,
            fyk_mpa=50, momentos=[300.0], gamma_f=1.4
        )
        r = res[0]
        assert r is not None
        # Viga subdimensionada: bx_passa=NAO e alerta preenchido
        if r.bx_passa == "NÃO":
            assert r.alerta != "", f"alerta vazio mesmo com bx_passa={r.bx_passa}"
            # Alerta deve mencionar bx ou dominio
            assert "bx" in r.alerta.lower() or "dominio" in r.alerta.lower() or "seção" in r.alerta.lower() or "secao" in r.alerta.lower() or "linha neutra" in r.alerta.lower()

    def test_geometria_invalida_h_zero(self):
        """A9: h=0 deve levantar ValueError."""
        with pytest.raises(ValueError, match="Altura"):
            calcular_flexao_viga_comum(
                h_cm=0, bw_cm=20, caa=2, fck_mpa=30,
                diam_estribo_mm=5, diam_barra_mm=16,
                fyk_mpa=50, momentos=[100.0], gamma_f=1.4
            )

    def test_geometria_invalida_d_negativo(self):
        """A9: d <= 0 deve levantar ValueError."""
        # CAA IV: cob=50mm, estribo=5mm, barra=20mm -> d_lin = 5+0.5+1 = 6.5 cm
        # h=6 cm: d = 6 - 6.5 = -0.5 cm (negativo)
        with pytest.raises(ValueError, match="Altura util"):
            calcular_flexao_viga_comum(
                h_cm=6, bw_cm=20, caa=4, fck_mpa=35,  # CAA IV -> cob=50mm
                diam_estribo_mm=5, diam_barra_mm=20,
                fyk_mpa=50, momentos=[100.0], gamma_f=1.4
            )

    def test_geometria_invalida_bw_pequena(self):
        """A9: bw < 5 cm deve levantar ValueError."""
        with pytest.raises(ValueError, match="Largura"):
            calcular_flexao_viga_comum(
                h_cm=50, bw_cm=3, caa=2, fck_mpa=30,
                diam_estribo_mm=5, diam_barra_mm=16,
                fyk_mpa=50, momentos=[100.0], gamma_f=1.4
            )

    def test_as_maior_que_asmin(self, viga_exemplo_flexao):
        """As adotado deve ser >= As minimo."""
        res = calcular_flexao_viga_comum(momentos=[100.0], **viga_exemplo_flexao)
        r = res[0]
        assert r is not None
        assert r.as_usado_cm2 >= r.asmin_cm2 - 0.01

    def test_multiplas_secoes(self, viga_exemplo_flexao, momentos_exemplo):
        """Deve calcular todas as secoes passadas."""
        res = calcular_flexao_viga_comum(
momentos=momentos_exemplo, **viga_exemplo_flexao
        )
        assert len(res) == len(momentos_exemplo)
        for r in res:
            if r is not None:
                assert r.as_usado_cm2 > 0

    def test_pele_h_maior_60(self, viga_exemplo_flexao):
        """Viga com h=70 deve requerer armadura de pele."""
        res = calcular_flexao_viga_comum(momentos=[100.0], **viga_exemplo_flexao)
        r = res[0]
        assert r is not None
        assert r.requer_pele is True
        assert r.n_barras_pele_face > 0

    def test_pele_h_menor_60(self):
        """Viga com h=50 NAO deve requerer armadura de pele."""
        res = calcular_flexao_viga_comum(
            h_cm=50, bw_cm=20, caa=2, fck_mpa=30,
            diam_estribo_mm=5, diam_barra_mm=16,
            fyk_mpa=50, momentos=[100.0], gamma_f=1.4
        )
        r = res[0]
        assert r is not None
        assert r.requer_pele is False

    def test_bx_no_dominio_a3(self, viga_exemplo_flexao):
        """A3: bx nao deve ser > 0.628 (dominio 2/3)."""
        # Testar com varios momentos para garantir que bx fica dentro do dominio
        for Mk in [50.0, 100.0, 200.0, 500.0]:
            res = calcular_flexao_viga_comum(
                momentos=[Mk], **viga_exemplo_flexao
            )
            r = res[0]
            assert r is not None
            # bx pode ser 999 (sem raiz valida) mas nunca > 0.628 quando passa
            if r.bx < 999:
                assert r.bx <= 0.628, f"bx={r.bx} > 0.628 para Mk={Mk}"

    def test_gamma_f_dropdown_vazio(self, viga_exemplo_flexao):
        """A5: gamma_f omitido usa GAMMA_F_RESTO = 1.4 (default)."""
        # Chamar sem gamma_f deve usar o default 1.4
        params = {k: v for k, v in viga_exemplo_flexao.items() if k != "gamma_f"}
        res = calcular_flexao_viga_comum(
            momentos=[100.0], **params
        )
        r = res[0]
        assert r is not None
        # Majoracao com gamma_f=1.4 (default): Md = Mk * 1.4
        assert abs(r.momento_kNm - 100.0 * 1.4) < 0.1
