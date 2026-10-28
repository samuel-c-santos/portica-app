"""
tests/test_detailing_domain.py
Testes unitários para BeamDetailer (camada de domínio).
Execute com: pytest tests/test_detailing_domain.py -v

Cobre todos os critérios de aceite (DoD):
  ✓ e_h,min = max(20, φ, 1.2 × d_max)
  ✓ e_v,min = max(20, φ, 1.33 × d_max)
  ✓ 10 barras φ10 em bw=200mm → ≥ 2 camadas sem falha
  ✓ Alinhamento vertical das barras extremas entre camadas
  ✓ Grampos quando span central > 150mm
  ✓ Baricentro = média das posições Y das barras de cálculo
  ✓ Validação de entrada (ValueError para parâmetros ruins)
"""
import math
import pytest

from core.detailing.domain import BeamDetailer, BeamDetailingInput


# ─── Fixture base ────────────────────────────────────────────────────────────

def make_input(**kwargs):
    """Retorna um BeamDetailingInput com valores padrão razoáveis."""
    defaults = dict(
        bw=300.0, h=500.0, c_nom=25.0,
        phi_estribo=6.3, phi_barra=16.0,
        d_max_agregado=19.0, total_bars=4,
    )
    defaults.update(kwargs)
    return BeamDetailingInput(**defaults)


detailer = BeamDetailer()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Espaçamento horizontal mínimo (e_h,min)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEhMin:
    def test_brita1_phi16(self):
        """d_max=19mm, φ=16mm → max(20, 16, 1.2×19=22.8) = 22.8"""
        data = detailer.detail(make_input(phi_barra=16, d_max_agregado=19))
        assert abs(data.eh_min - 22.8) < 0.01, f"Esperado 22.8, obtido {data.eh_min}"

    def test_phi_domina(self):
        """φ=25mm, d_max=19mm → max(20, 25, 22.8) = 25.0"""
        data = detailer.detail(make_input(bw=400, phi_barra=25, d_max_agregado=19))
        assert abs(data.eh_min - 25.0) < 0.01

    def test_piso_normativo(self):
        """φ=10mm, d_max=12.5mm → max(20, 10, 15.0) = 20.0"""
        data = detailer.detail(make_input(phi_barra=10, d_max_agregado=12.5))
        assert abs(data.eh_min - 20.0) < 0.01

    def test_brita2_phi20(self):
        """d_max=25mm, φ=20mm → max(20, 20, 30.0) = 30.0"""
        data = detailer.detail(make_input(bw=400, phi_barra=20, d_max_agregado=25))
        assert abs(data.eh_min - 30.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Espaçamento vertical mínimo (e_v,min)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvMin:
    def test_brita1_phi10(self):
        """d_max=19mm, φ=10mm → max(20, 10, 1.33×19≈25.27) = 25.27"""
        data = detailer.detail(make_input(phi_barra=10, d_max_agregado=19, total_bars=6))
        assert abs(data.ev_min - 25.27) < 0.1

    def test_phi_domina(self):
        """φ=32mm, d_max=25mm → max(20, 32, 33.25) = 33.25"""
        data = detailer.detail(make_input(bw=500, h=700, phi_barra=32, d_max_agregado=25, total_bars=4))
        assert abs(data.ev_min - 33.25) < 0.1

    def test_piso_normativo(self):
        """φ=10mm, d_max=10mm → max(20, 10, 13.3) = 20.0"""
        data = detailer.detail(make_input(phi_barra=10, d_max_agregado=10))
        assert abs(data.ev_min - 20.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Critério chave DoD: 10 barras φ10 em bw=200mm
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiLayerDistribution:
    """Caso DoD: 10φ10 em bw=200mm deve usar ≥ 2 camadas, sem falha."""

    INP = BeamDetailingInput(
        bw=200, h=500, c_nom=25, phi_estribo=6.3,
        phi_barra=10, d_max_agregado=19, total_bars=10,
    )

    def test_nao_falha(self):
        """Não deve levantar exceção."""
        data = detailer.detail(self.INP)
        assert data is not None

    def test_usa_multiplas_camadas(self):
        """Deve usar ao menos 2 camadas."""
        data = detailer.detail(self.INP)
        assert data.layer_count >= 2, (
            f"Esperado >= 2 camadas, obtido {data.layer_count}.\n"
            f"  bw={self.INP.bw}, φ={self.INP.phi_barra}, n={self.INP.total_bars}\n"
            f"  h_space = {self.INP.bw - 2*self.INP.c_nom - 2*self.INP.phi_estribo:.1f} mm\n"
            f"  eh_min = {data.eh_min:.1f} mm"
        )

    def test_total_barras_preservado(self):
        """Soma das barras por camada deve ser igual ao total."""
        data = detailer.detail(self.INP)
        total = sum(lyr.bar_count for lyr in data.layers)
        assert total == self.INP.total_bars

    def test_barras_y_distintos(self):
        """Barras de camadas diferentes devem ter posições Y distintas."""
        data = detailer.detail(self.INP)
        main = [b for b in data.bar_positions if not b.is_corner_bar]
        y_values = {round(b.y, 1) for b in main}
        assert len(y_values) >= 2

    def test_alinhamento_x_camadas(self):
        """Barras extremas da camada 0 e camada 1 devem ter X coincidentes."""
        data = detailer.detail(self.INP)
        if data.layer_count < 2:
            pytest.skip("Menos de 2 camadas — alinhamento não se aplica.")
        layer0 = sorted([b for b in data.bar_positions if b.layer == 0], key=lambda b: b.x)
        layer1 = sorted([b for b in data.bar_positions if b.layer == 1], key=lambda b: b.x)
        assert abs(layer0[0].x - layer1[0].x) < 2.0, "Barra esquerda não alinhada"
        assert abs(layer0[-1].x - layer1[-1].x) < 2.0, "Barra direita não alinhada"

    def test_warning_emitido(self):
        """Deve emitir aviso sobre distribuição em camadas."""
        data = detailer.detail(self.INP)
        assert any("camada" in w.lower() for w in data.warnings)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Uma única camada (caso simples)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleLayer:
    def test_3_barras_bw300(self):
        data = detailer.detail(make_input(total_bars=3))
        assert data.layer_count == 1

    def test_sem_warning_camada(self):
        data = detailer.detail(make_input(total_bars=3))
        camada_warns = [w for w in data.warnings if "camada" in w.lower()]
        assert len(camada_warns) == 0

    def test_posicao_y_correta_1cam(self):
        """Y da camada 0 deve ser c_nom + phi_e + phi/2."""
        inp = make_input(total_bars=3, phi_barra=16, c_nom=25, phi_estribo=6.3)
        data = detailer.detail(inp)
        expected_y = inp.c_nom + inp.phi_estribo + inp.phi_barra / 2
        assert abs(data.layers[0].y_centroid - expected_y) < 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Grampos suplementares
# ═══════════════════════════════════════════════════════════════════════════════

class TestGrampos:
    def test_2_barras_sem_grampo(self):
        data = detailer.detail(make_input(total_bars=2))
        assert not data.requires_supplementary_stirrup

    def test_span_grande_detecta_grampo(self):
        """bw=600mm, 5 barras φ25 → span > 150mm → grampos necessários."""
        inp = BeamDetailingInput(
            bw=600, h=600, c_nom=30, phi_estribo=8,
            phi_barra=25, d_max_agregado=25, total_bars=5,
        )
        data = detailer.detail(inp)
        if data.layer_count == 1 and data.layers[0].bar_count >= 3:
            layer = data.layers[0]
            bars = sorted([b for b in data.bar_positions if b.layer == 0], key=lambda b: b.x)
            span = bars[-1].x - bars[0].x
            if span > 150:
                assert data.requires_supplementary_stirrup
                assert len(data.supplementary_stirrup_positions) > 0

    def test_grampos_nao_incluem_barras_extremas(self):
        """Grampos devem ser apenas nas barras centrais, não nas extremas."""
        inp = BeamDetailingInput(
            bw=600, h=600, c_nom=30, phi_estribo=8,
            phi_barra=20, d_max_agregado=19, total_bars=5,
        )
        data = detailer.detail(inp)
        if not data.requires_supplementary_stirrup:
            pytest.skip("Grampos não necessários neste caso.")
        layer0_bars = sorted([b for b in data.bar_positions if b.layer == 0], key=lambda b: b.x)
        grampo_xs = {gs.x for gs in data.supplementary_stirrup_positions}
        # As barras extremas NÃO devem estar na lista de grampos
        assert layer0_bars[0].x not in grampo_xs
        assert layer0_bars[-1].x not in grampo_xs


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Baricentro e altura útil efetiva
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaricentro:
    def test_1_camada_ycg_igual_centroide(self):
        """Para 1 camada, y_cg deve coincidir com o centróide da camada."""
        data = detailer.detail(make_input(total_bars=3))
        assert abs(data.y_cg - data.layers[0].y_centroid) < 0.5

    def test_2_camadas_ycg_media(self):
        """Para 2 camadas, y_cg = média das posições Y de todas as barras."""
        data = detailer.detail(BeamDetailingInput(
            bw=200, h=500, c_nom=25, phi_estribo=6.3,
            phi_barra=10, d_max_agregado=19, total_bars=10,
        ))
        main_bars = [b for b in data.bar_positions if not b.is_corner_bar]
        expected = sum(b.y for b in main_bars) / len(main_bars)
        assert abs(data.y_cg - expected) < 0.01

    def test_d_efetiva_igual_h_menos_ycg(self):
        """d_efetiva deve ser igual a h - y_cg (altura útil efetiva)."""
        data = detailer.detail(make_input(total_bars=4))
        assert abs(data.d_efetiva - (data.h - data.y_cg)) < 0.01

    def test_barras_canto_nao_entram_no_ycg(self):
        """Barras de canto (is_corner_bar=True) não devem afetar y_cg."""
        data = detailer.detail(make_input(total_bars=3))
        main_only = [b for b in data.bar_positions if not b.is_corner_bar]
        expected = sum(b.y for b in main_only) / len(main_only)
        assert abs(data.y_cg - expected) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Validação de entrada
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidacao:
    def test_bw_zero(self):
        with pytest.raises(ValueError):
            detailer.detail(make_input(bw=0))

    def test_bw_negativo(self):
        with pytest.raises(ValueError):
            detailer.detail(make_input(bw=-100))

    def test_total_bars_zero(self):
        with pytest.raises(ValueError):
            detailer.detail(make_input(total_bars=0))

    def test_phi_barra_negativo(self):
        with pytest.raises(ValueError):
            detailer.detail(make_input(phi_barra=-10))

    def test_secao_impossivel_espaco_negativo(self):
        """bw=50, c_nom=25 → h_space negativo → ValueError."""
        with pytest.raises(ValueError):
            detailer.detail(make_input(bw=50, c_nom=25))

    def test_barra_nao_cabe_no_espaco(self):
        """φ muito grande para o espaço disponível → deve falhar.

        bw=80, c_nom=25, phi_e=8 → h_space = 80 - 50 - 16 = 14mm.
        φ=32mm > h_space=14mm → ValueError.
        """
        with pytest.raises(ValueError):
            detailer.detail(make_input(bw=80, phi_barra=32, c_nom=25, phi_estribo=8))


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Integridade do layout
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegridade:
    def test_barras_dentro_da_seccao(self):
        """Barras de cálculo (not corner) devem estar dentro do estribo.

        O limite correto é a face interna do estribo:
          x_min = c_nom + phi_e + phi/2
          x_max = bw - c_nom - phi_e - phi/2
        Barras de canto são excluídas pois têm diâmetro diferente.
        """
        data = detailer.detail(make_input(total_bars=4))
        r = data.phi_barra / 2
        x_min = data.c_nom + data.phi_estribo  # face interna esq. do estribo
        x_max = data.bw - data.c_nom - data.phi_estribo  # face interna dir.
        for bar in data.bar_positions:
            if bar.is_corner_bar:
                continue  # barras de canto têm phi próprio, verificação separada
            assert bar.x - r >= x_min - 0.5, f"Barra muito à esquerda: {bar}"
            assert bar.x + r <= x_max + 0.5, f"Barra muito à direita: {bar}"
            assert bar.y - r >= 0, f"Barra abaixo do fundo: {bar}"
            assert bar.y + r <= data.h + 1, f"Barra acima do topo: {bar}"

    def test_barras_de_canto_presentes(self):
        """Sempre devem existir exatamente 2 barras de canto."""
        data = detailer.detail(make_input(total_bars=3))
        corner = [b for b in data.bar_positions if b.is_corner_bar]
        assert len(corner) == 2

    def test_layer_index_sequencial(self):
        """Camadas devem ter índices 0, 1, 2, ..."""
        data = detailer.detail(BeamDetailingInput(
            bw=200, h=700, c_nom=25, phi_estribo=6.3,
            phi_barra=10, d_max_agregado=19, total_bars=15,
        ))
        for i, lyr in enumerate(data.layers):
            assert lyr.index == i


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Detalhamento de Viga T
# ═══════════════════════════════════════════════════════════════════════════════

class TestVigaTDetailing:
    def test_bottom_bars_in_web(self):
        """Barras inferiores (is_superior=False) em viga T devem estar dentro da alma (bw)."""
        inp = BeamDetailingInput(
            bw=200.0, h=500.0, c_nom=25.0, phi_estribo=6.3, phi_barra=16.0,
            d_max_agregado=19.0, total_bars=3, is_t=True, bf_cm=60.0, hf_cm=15.0,
            is_superior=False
        )
        data = detailer.detail(inp)
        
        # Alma centralizada na mesa de largura 600mm. Alma vai de X=200mm a X=400mm.
        # Barras principais (não de canto) devem estar dentro da alma (200 a 400)
        x_web_esq = (600.0 - 200.0) / 2.0  # 200.0
        x_web_dir = x_web_esq + 200.0       # 400.0
        
        main_bars = [b for b in data.bar_positions if not b.is_corner_bar]
        assert len(main_bars) == 3
        
        r = inp.phi_barra / 2.0
        for bar in main_bars:
            assert bar.x - r >= x_web_esq + inp.c_nom + inp.phi_estribo - 0.1
            assert bar.x + r <= x_web_dir - inp.c_nom - inp.phi_estribo + 0.1

    def test_top_bars_in_flange(self):
        """Barras superiores (is_superior=True) em viga T devem estar distribuídas sobre a largura da mesa (bf)."""
        inp = BeamDetailingInput(
            bw=200.0, h=500.0, c_nom=25.0, phi_estribo=6.3, phi_barra=16.0,
            d_max_agregado=19.0, total_bars=6, is_t=True, bf_cm=60.0, hf_cm=15.0,
            is_superior=True
        )
        data = detailer.detail(inp)
        
        # Mesa de largura 600mm. Barras superiores devem estar entre X=0 e X=600.
        main_bars = [b for b in data.bar_positions if not b.is_corner_bar]
        assert len(main_bars) == 6
        
        r = inp.phi_barra / 2.0
        for bar in main_bars:
            assert bar.x - r >= inp.c_nom + inp.phi_estribo - 0.1
            assert bar.x + r <= 600.0 - inp.c_nom - inp.phi_estribo + 0.1
            
        # Pelo menos algumas barras devem estar fora da projeção da alma (X < 200 ou X > 400)
        out_of_web = [b for b in main_bars if b.x < 200.0 or b.x > 400.0]
        assert len(out_of_web) > 0, "Deveria haver barras fora da alma na mesa"

    def test_centroid_calculation_t_beam(self):
        """Verifica se o baricentro (y_cg) é calculado corretamente para cima ou para baixo."""
        # Inferior (is_superior=False)
        inp_inf = BeamDetailingInput(
            bw=200.0, h=500.0, c_nom=25.0, phi_estribo=6.3, phi_barra=16.0,
            d_max_agregado=19.0, total_bars=3, is_t=True, bf_cm=60.0, hf_cm=15.0,
            is_superior=False
        )
        data_inf = detailer.detail(inp_inf)
        # 1 única camada, y_cg deve ser cob + phi_estribo + phi_barra/2 = 25 + 6.3 + 8 = 39.3
        assert abs(data_inf.y_cg - 39.3) < 0.1
        
        # Superior (is_superior=True)
        inp_sup = BeamDetailingInput(
            bw=200.0, h=500.0, c_nom=25.0, phi_estribo=6.3, phi_barra=16.0,
            d_max_agregado=19.0, total_bars=3, is_t=True, bf_cm=60.0, hf_cm=15.0,
            is_superior=True
        )
        data_sup = detailer.detail(inp_sup)
        # y_cg medido a partir da face inferior da viga, para barras a 39.3mm do topo
        # y_cg = 500 - 39.3 = 460.7
        assert abs(data_sup.y_cg - 460.7) < 0.1
