"""
Testes para geração de diagramas no PDF (Fase 2.4).
"""

import os
import tempfile
import pytest
from fpdf import FPDF

from ui.ftool.parser import parse_momento, parse_cortante
from ui.ftool.secoes_criticas import detectar_todas_secoes, SecaoCritica
from ui.ftool.diagrama import gerar_diagrama_esforcos
from ui.ftool.dimensionamento import (
    dimensionar_trechos_ftool,
    gerar_relatorio_viga_comum_premium,
    gerar_relatorio_viga_t_premium,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA_DIR = os.path.join(BASE_DIR, "samples")
MOMENTO_FILE = os.path.join(TEST_DATA_DIR, "test_momento_fletor.txt")
CORTANTE_FILE = os.path.join(TEST_DATA_DIR, "test_esforcos_cortantes.txt")


@pytest.fixture
def ftool_data():
    """Lê os dados FTOOL de teste e detecta as seções."""
    momentos = parse_momento(MOMENTO_FILE)
    cortantes = parse_cortante(CORTANTE_FILE)
    secoes = detectar_todas_secoes(momentos, cortantes)
    return momentos, cortantes, secoes


def test_1_desenhar_diagrama_direto_no_pdf(ftool_data):
    """1. Testa a geração dos diagramas desenhados diretamente em um FPDF em branco."""
    momentos, cortantes, secoes = ftool_data
    
    pdf = FPDF()
    pdf.add_page()
    
    # Executa o desenho dos diagramas
    gerar_diagrama_esforcos(
        pdf=pdf,
        momentos=momentos,
        cortantes=cortantes,
        secoes_criticas=secoes,
    )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name
        
    try:
        pdf.output(pdf_path)
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 1000  # PDF não deve estar vazio
    finally:
        os.remove(pdf_path)


def test_2_gerar_relatorio_viga_comum_premium(ftool_data):
    """2. Testa o wrapper premium da viga comum para garantir que ele gera o PDF com os diagramas."""
    momentos, cortantes, secoes = ftool_data
    
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
    
    resultados = dimensionar_trechos_ftool(dados_viga, secoes)
    sec_results = resultados["secoes"]

    res_flex = [r["resultado_flexao"] for r in sec_results]
    res_cis = [r["resultado_cisalhamento"] for r in sec_results]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name
        
    try:
        gerar_relatorio_viga_comum_premium(
            pdf_path,
            nome_viga="Viga Teste Premium",
            h_cm=70.0,
            bw_cm=20.0,
            caa=2,
            fck_mpa=30.0,
            fyk_mpa=50.0,
            fyk_estribo_mpa=60.0,
            phi_estribo_mm=5.0,
            phi_barra_mm=16.0,
            resultados_flexao=res_flex,
            resultados_cisalhamento=res_cis,
            imagem_ftool=None,
            gamma_f=1.4,
            dark_mode=False,
            nome_engenheiro="Samuel Engenheiro",
            crea="12345/D",
            momentos=momentos,
            cortantes=cortantes,
            secoes_criticas=secoes,
        )
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 2000
    finally:
        os.remove(pdf_path)


def test_3_gerar_relatorio_viga_t_premium(ftool_data):
    """3. Testa o wrapper premium da viga T para garantir que o PDF seja gerado corretamente."""
    momentos, cortantes, secoes = ftool_data
    
    # Para viga T, precisamos adaptar os resultados de flexão para ResultadoFlexaoT
    # Para fins de teste de PDF, vamos simular ou chamar o dimensionamento de viga T.
    from core.calculos.engenharia import calcular_flexao_viga_t
    
    res_flex_t = []
    for sec in secoes:
        rf_list = calcular_flexao_viga_t(
            h_cm=70.0, bw_cm=20.0, bf_cm=60.0, hf_cm=12.0,
            caa=2, fck_mpa=30.0,
            diam_estribo_mm=5.0, diam_barra_mm=16.0,
            fyk_mpa=50.0, momentos=[sec.momento],
            b1esq_cm=20.0, b1dir_cm=20.0,
            gamma_f=1.4,
        )
        res_flex_t.append(rf_list[0])
        
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
    sec_results = dimensionar_trechos_ftool(dados_viga, secoes)["secoes"]
    res_cis = [r["resultado_cisalhamento"] for r in sec_results]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name
        
    try:
        gerar_relatorio_viga_t_premium(
            pdf_path,
            nome_viga="Viga T Teste Premium",
            h_cm=70.0,
            bw_cm=20.0,
            bf_cm=60.0,
            hf_cm=12.0,
            caa=2,
            fck_mpa=30.0,
            fyk_mpa=50.0,
            fyk_estribo_mpa=60.0,
            phi_estribo_mm=5.0,
            phi_barra_mm=16.0,
            resultados_flexao=res_flex_t,
            resultados_cisalhamento=res_cis,
            imagem_ftool=None,
            gamma_f=1.4,
            dark_mode=False,
            nome_engenheiro="Samuel Engenheiro",
            crea="12345/D",
            momentos=momentos,
            cortantes=cortantes,
            secoes_criticas=secoes,
        )
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 2000
    finally:
        os.remove(pdf_path)
