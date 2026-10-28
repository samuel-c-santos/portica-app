"""
Testes para verificar que ajustes manuais de barras extras são aplicados aos resultados de flexão.
"""

import os
import pytest

from ui.ftool.els import AjustesELS
from ui.ftool.dimensionamento import dimensionar_trechos_ftool
from ui.ftool.secoes_criticas import SecaoCritica

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")


def _ler_dados():
    """Lê momentos e deformações dos arquivos de amostra."""
    from ui.ftool.parser import parse_momento, parse_deformacao
    mom = parse_momento(os.path.join(SAMPLES_DIR, "test_momento_fletor.txt"))
    deform = parse_deformacao(os.path.join(SAMPLES_DIR, "test_deformacoes.txt"))
    return mom, deform


def test_barras_extras_atualizam_qtd_barras():
    """Verifica que barras extras são adicionadas ao qtd_barras dos resultados de flexão."""
    momentos, deformacoes = _ler_dados()
    
    # Dados da viga
    dados_viga = {
        "h_cm": 70.0,
        "bw_cm": 20.0,
        "caa": 2,
        "fck_mpa": 30.0,
        "diam_estribo_mm": 5.0,
        "diam_barra_mm": 12.5,
        "fyk_mpa": 50.0,
        "fyk_estribo_mpa": 60.0,
        "fyk_barra_mpa": 50.0,
        "gamma_f": 1.4,
    }
    
    # Seções críticas (uma seção com momento positivo)
    secoes = [
        SecaoCritica(x=3.0, momento=150.0, cortante=50.0, tipo="MÁX", descricao="Momento máximo")
    ]
    
    # Dimensionar sem ajustes
    resultados_base = dimensionar_trechos_ftool(
        dados_viga, secoes,
        momentos=momentos, deformacoes=deformacoes
    )
    
    # Dimensionar com 3 barras extras
    ajustes = AjustesELS(barras_extras=3)
    resultados_ajustados = dimensionar_trechos_ftool(
        dados_viga, secoes,
        momentos=momentos, deformacoes=deformacoes,
        ajustes_els=ajustes
    )
    
    # Verificar que qtd_barras foi atualizado
    rf_base = resultados_base["secoes"][0]["resultado_flexao"]
    rf_ajustado = resultados_ajustados["secoes"][0]["resultado_flexao"]
    
    assert rf_base is not None
    assert rf_ajustado is not None
    
    # qtd_barras deve ser maior com ajustes
    assert rf_ajustado.qtd_barras == rf_base.qtd_barras + 3, \
        f"qtd_barras deve ser {rf_base.qtd_barras + 3}, mas é {rf_ajustado.qtd_barras}"
    
    # as_usado_cm2 deve ser maior com ajustes
    assert rf_ajustado.as_usado_cm2 > rf_base.as_usado_cm2, \
        f"as_usado_cm2 deve ser maior com ajustes: {rf_ajustado.as_usado_cm2} vs {rf_base.as_usado_cm2}"


def test_barras_extras_recalcula_armadura_pele():
    """Verifica que armadura de pele é recalculada quando há barras extras."""
    momentos, deformacoes = _ler_dados()
    
    # Dados da viga (h >= 60cm para exigir armadura de pele)
    dados_viga = {
        "h_cm": 70.0,
        "bw_cm": 20.0,
        "caa": 2,
        "fck_mpa": 30.0,
        "diam_estribo_mm": 5.0,
        "diam_barra_mm": 12.5,
        "fyk_mpa": 50.0,
        "fyk_estribo_mpa": 60.0,
        "fyk_barra_mpa": 50.0,
        "gamma_f": 1.4,
    }
    
    # Seções críticas
    secoes = [
        SecaoCritica(x=3.0, momento=150.0, cortante=50.0, tipo="MÁX", descricao="Momento máximo")
    ]
    
    # Dimensionar com 3 barras extras
    ajustes = AjustesELS(barras_extras=3)
    resultados = dimensionar_trechos_ftool(
        dados_viga, secoes,
        momentos=momentos, deformacoes=deformacoes,
        ajustes_els=ajustes
    )
    
    rf = resultados["secoes"][0]["resultado_flexao"]
    assert rf is not None
    
    # Se a viga exige armadura de pele, verificar que foi recalculada
    if hasattr(rf, 'requer_pele') and rf.requer_pele:
        # Armadura de pele deve existir
        assert rf.n_barras_pele_face > 0, "Armadura de pele deve existir para h >= 60cm"
        assert rf.phi_pele_mm > 0, "Diâmetro da armadura de pele deve ser > 0"


def test_sem_ajustes_nao_altera_qtd_barras():
    """Verifica que sem ajustes, qtd_barras não é alterado."""
    momentos, deformacoes = _ler_dados()
    
    dados_viga = {
        "h_cm": 70.0,
        "bw_cm": 20.0,
        "caa": 2,
        "fck_mpa": 30.0,
        "diam_estribo_mm": 5.0,
        "diam_barra_mm": 12.5,
        "fyk_mpa": 50.0,
        "fyk_estribo_mpa": 60.0,
        "fyk_barra_mpa": 50.0,
        "gamma_f": 1.4,
    }
    
    secoes = [
        SecaoCritica(x=3.0, momento=150.0, cortante=50.0, tipo="MÁX", descricao="Momento máximo")
    ]
    
    # Dimensionar sem ajustes
    resultados1 = dimensionar_trechos_ftool(
        dados_viga, secoes,
        momentos=momentos, deformacoes=deformacoes
    )
    
    # Dimensionar novamente sem ajustes
    resultados2 = dimensionar_trechos_ftool(
        dados_viga, secoes,
        momentos=momentos, deformacoes=deformacoes
    )
    
    rf1 = resultados1["secoes"][0]["resultado_flexao"]
    rf2 = resultados2["secoes"][0]["resultado_flexao"]
    
    assert rf1 is not None
    assert rf2 is not None
    
    # qtd_barras deve ser igual
    assert rf1.qtd_barras == rf2.qtd_barras


def test_barras_extras_recalcula_layout_convergido():
    """Verifica que o layout convergido e propriedades associadas são recalculados com barras extras."""
    momentos, deformacoes = _ler_dados()
    
    dados_viga = {
        "h_cm": 70.0,
        "bw_cm": 20.0,
        "caa": 2,
        "fck_mpa": 30.0,
        "diam_estribo_mm": 5.0,
        "diam_barra_mm": 12.5,
        "fyk_mpa": 50.0,
        "fyk_estribo_mpa": 60.0,
        "fyk_barra_mpa": 50.0,
        "gamma_f": 1.4,
    }
    
    # Seção com momento grande para forçar 6 barras (que cabem em 2 camadas de 4 barras max)
    # E adicionar 3 barras extras via ELS para total de 9 barras, forçando 3 camadas (3+3+3)
    secoes = [
        SecaoCritica(x=3.0, momento=180.0, cortante=50.0, tipo="MÁX", descricao="Momento máximo")
    ]
    
    # Dimensionar sem ajustes
    resultados_base = dimensionar_trechos_ftool(
        dados_viga, secoes,
        momentos=momentos, deformacoes=deformacoes
    )
    
    # Dimensionar com 3 barras extras
    ajustes = AjustesELS(barras_extras=3)
    resultados_ajustados = dimensionar_trechos_ftool(
        dados_viga, secoes,
        momentos=momentos, deformacoes=deformacoes,
        ajustes_els=ajustes
    )
    
    rf_base = resultados_base["secoes"][0]["resultado_flexao"]
    rf_ajustado = resultados_ajustados["secoes"][0]["resultado_flexao"]
    
    assert rf_base is not None
    assert rf_ajustado is not None
    
    # Verificar que o layout convergido foi recalculado
    assert rf_ajustado.layout_convergido is not None
    assert rf_ajustado.layout_convergido.total_bars == rf_ajustado.qtd_barras
    
    # Verificar que camadas_adotadas e as posições de barras foram atualizadas
    assert rf_ajustado.camadas_adotadas == rf_ajustado.layout_convergido.layer_count
    assert rf_ajustado.barras_suportadas == rf_ajustado.layout_convergido.layers[0].bar_count
    assert rf_ajustado.barras_cima == rf_ajustado.qtd_barras - rf_ajustado.barras_suportadas


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
