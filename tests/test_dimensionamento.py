"""
Testes para o módulo de dimensionamento automático (Fase 2.3).
"""

import os
import pytest
from typing import Tuple, List

from ui.ftool.parser import parse_momento, parse_cortante
from ui.ftool.secoes_criticas import detectar_todas_secoes, SecaoCritica
from ui.ftool.dimensionamento import (
    dimensionar_trechos_ftool,
    gerar_relatorio_premium,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA_DIR = os.path.join(BASE_DIR, "samples")
MOMENTO_FILE = os.path.join(TEST_DATA_DIR, "test_momento_fletor.txt")
CORTANTE_FILE = os.path.join(TEST_DATA_DIR, "test_esforcos_cortantes.txt")


@pytest.fixture
def secoes_reais() -> Tuple[dict, List[SecaoCritica]]:
    """Fixture que fornece a viga padrão de teste e as seções críticas detectadas."""
    dados_viga = {
        "h_cm": 70.0,
        "bw_cm": 20.0,
        "caa": 2,
        "fck_mpa": 30.0,
        "diam_estribo_mm": 5.0,
        "diam_barra_mm": 16.0,
        "fyk_mpa": 50.0,
        "fyk_estribo_mpa": 60.0,
        "gamma_f": 1.4,
    }
    momentos = parse_momento(MOMENTO_FILE)
    cortantes = parse_cortante(CORTANTE_FILE)
    secoes = detectar_todas_secoes(momentos, cortantes)
    return dados_viga, secoes


def test_1_dimensionamento_completo_secoes(secoes_reais):
    """1. Testa o dimensionamento completo das seções críticas extraídas."""
    dados_viga, secoes = secoes_reais
    resultados = dimensionar_trechos_ftool(dados_viga, secoes)["secoes"]

    assert len(resultados) == len(secoes)
    for res in resultados:
        assert "x" in res
        assert "Mk" in res
        assert "Vk" in res
        assert "resultado_flexao" in res
        assert "resultado_cisalhamento" in res
        assert "tipo" in res
        assert "descricao" in res


def test_2_secao_momento_maximo(secoes_reais):
    """2. Testa o dimensionamento na seção de momento máximo local (vão)."""
    dados_viga, secoes = secoes_reais
    resultados = dimensionar_trechos_ftool(dados_viga, secoes)["secoes"]
    
    # Encontra a seção correspondente ao momento máximo
    sec_max_m = [r for r in resultados if r["tipo"] == "MÁX"][0]
    
    assert pytest.approx(sec_max_m["x"], abs=0.1) == 3.1
    rf = sec_max_m["resultado_flexao"]
    assert rf is not None
    assert rf.as_req_cm2 > 0.0
    assert rf.as_usado_cm2 >= rf.as_req_cm2
    assert rf.qtd_barras > 0


def test_3_secao_momento_minimo(secoes_reais):
    """3. Testa o dimensionamento na seção de momento mínimo local (apoio de extremo x=0)."""
    dados_viga, secoes = secoes_reais
    resultados = dimensionar_trechos_ftool(dados_viga, secoes)["secoes"]
    
    # x=0.0 é o mínimo e extremo
    sec_x0 = [r for r in resultados if r["x"] == 0.0][0]
    rf = sec_x0["resultado_flexao"]
    assert rf is not None
    assert rf.momento_kNm == pytest.approx(135.6 * 1.4, abs=1e-5)
    # O momento negativo traciona a face superior, as_req deve ser calculado
    assert rf.as_req_cm2 > 0.0


def test_4_secao_apoio_interno_cisalhamento(secoes_reais):
    """4. Testa o dimensionamento ao cisalhamento no apoio interno (x=3.0)."""
    dados_viga, secoes = secoes_reais
    resultados = dimensionar_trechos_ftool(dados_viga, secoes)["secoes"]
    
    sec_apoio = [r for r in resultados if r["x"] == 3.0][0]
    rc = sec_apoio["resultado_cisalhamento"]
    assert rc is not None
    # Deve calcular com o cortante crítico em x=3.0 (48.4 kN, maior absoluto da descontinuidade)
    assert rc.vsd_kn == pytest.approx(48.4 * 1.4, abs=1e-5)
    assert rc.asw_usado_cm2_m > 0.0
    assert rc.dist_estribos_cm > 0.0


def test_5_gerar_relatorio_premium(secoes_reais):
    """5. Testa a geração do relatório resumo textual e seus elementos."""
    dados_viga, secoes = secoes_reais
    sec_results = dimensionar_trechos_ftool(dados_viga, secoes)["secoes"]
    
    relatorio = gerar_relatorio_premium(dados_viga, sec_results)
    assert isinstance(relatorio, str)
    assert "PÓRTICA APP" in relatorio
    assert "RESUMO DE DIMENSIONAMENTO" in relatorio
    assert "Geometria" in relatorio
    assert "Seção em x =" in relatorio
    assert "FLEXÃO (As)" in relatorio
    assert "CISALHAMENTO (Asw/s)" in relatorio


def test_secoes_vazias():
    """Garante retorno limpo para uma lista de seções vazia."""
    dados_viga = {"h_cm": 70.0, "bw_cm": 20.0, "caa": 2, "fck_mpa": 30.0, "diam_estribo_mm": 5.0, "diam_barra_mm": 16.0, "fyk_mpa": 50.0}
    res = dimensionar_trechos_ftool(dados_viga, [])
    assert res["secoes"] == []
