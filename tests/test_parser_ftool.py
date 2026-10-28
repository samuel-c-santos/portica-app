"""
Testes para o parser de arquivos FTOOL (Fase 2.1).
"""

import os
import tempfile
import pytest

from ui.ftool.parser import (
    parse_momento,
    parse_cortante,
    parse_deformacao,
    parse_tudo,
    validate_file_type,
)


# Caminho para o diretório de arquivos de teste reais
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA_DIR = os.path.join(BASE_DIR, "samples")

# Arquivos reais
MOMENTO_FILE = os.path.join(TEST_DATA_DIR, "test_momento_fletor.txt")
CORTANTE_FILE = os.path.join(TEST_DATA_DIR, "test_esforcos_cortantes.txt")
DEFORMACAO_FILE = os.path.join(TEST_DATA_DIR, "test_deformacoes.txt")


def test_parse_momento_real():
    """Valida o parsing do arquivo real de momentos fletores e seus valores de referência."""
    momentos = parse_momento(MOMENTO_FILE)
    
    # 1. Total de pontos (76)
    assert len(momentos) == 76
    
    # 2. Tipos de retorno
    for x, M in momentos:
        assert isinstance(x, float)
        assert isinstance(M, float)
        
    # 3. Valores extremos e posições específicas
    # M min ≈ -135,6 kN·m (apoio, x=0)
    # M máx ≈ +135,9 kN·m (vão, x≈3,1 m)
    pos_x = [pt[0] for pt in momentos]
    valores_M = [pt[1] for pt in momentos]
    
    m_min = min(valores_M)
    m_max = max(valores_M)
    
    assert pytest.approx(m_min, abs=0.2) == -135.6
    assert pytest.approx(m_max, abs=0.2) == 135.9
    
    # Encontrar posição do máximo
    idx_max = valores_M.index(m_max)
    x_max = pos_x[idx_max]
    assert pytest.approx(x_max, abs=0.15) == 3.1
    
    # Primeiro e último ponto
    assert pos_x[0] == 0.0
    assert valores_M[0] == -135.6
    assert pos_x[-1] == 7.5
    assert valores_M[-1] == -132.4


def test_parse_cortante_real():
    """Valida o parsing do arquivo real de esforços cortantes e seus valores de referência."""
    cortantes = parse_cortante(CORTANTE_FILE)
    
    # 1. Total de pontos (77 devido à descontinuidade no apoio)
    assert len(cortantes) == 77
    
    pos_x = [pt[0] for pt in cortantes]
    valores_V = [pt[1] for pt in cortantes]
    
    # 2. V máx ≈ +132,4 kN (apoio esquerdo, x=0)
    # V min ≈ -122,6 kN (engaste direito, x=7,5)
    v_max = max(valores_V)
    v_min = min(valores_V)
    
    assert pytest.approx(v_max, abs=0.2) == 132.4
    assert pytest.approx(v_min, abs=0.2) == -122.6
    
    # 3. Descontinuidade V: +48,4 → +3,4 no apoio interno (x=3,0)
    pontos_x_3 = [pt for pt in cortantes if pytest.approx(pt[0], abs=1e-5) == 3.0]
    assert len(pontos_x_3) == 2
    
    valores_no_apoio = [pt[1] for pt in pontos_x_3]
    assert 48.4 in valores_no_apoio
    assert 3.4 in valores_no_apoio


def test_parse_deformacao_real():
    """Valida o parsing do arquivo real de deformações."""
    deformacoes = parse_deformacao(DEFORMACAO_FILE)
    
    # 1. Total de pontos (76)
    assert len(deformacoes) == 76
    
    # 2. Estrutura do retorno (x, d, θ, κ)
    for x, d, theta, kappa in deformacoes:
        assert isinstance(x, float)
        assert isinstance(d, float)
        assert isinstance(theta, float)
        assert isinstance(kappa, float)
        
    # 3. Exemplo do primeiro ponto para validar o formato científico
    # 0.00	7.335e-002	-2.496e-001	-9.336e-004
    x0, d0, theta0, kappa0 = deformacoes[0]
    assert x0 == 0.0
    assert pytest.approx(d0, abs=1e-5) == 7.335e-2
    assert pytest.approx(theta0, abs=1e-5) == -2.496e-1
    assert pytest.approx(kappa0, abs=1e-7) == -9.336e-4


def test_parse_tudo_real():
    """Valida a leitura unificada dos três arquivos a partir de uma pasta."""
    dados = parse_tudo(TEST_DATA_DIR)
    
    assert "momentos" in dados
    assert "cortantes" in dados
    assert "deformacoes" in dados
    
    assert len(dados["momentos"]) in (76, 77)
    assert len(dados["cortantes"]) in (76, 77)
    assert len(dados["deformacoes"]) in (76, 77)


def test_erro_arquivo_inexistente():
    """Garante erro apropriado quando arquivo não existe."""
    with pytest.raises(FileNotFoundError):
        parse_momento("caminho_inexistente.txt")


def test_erro_arquivo_vazio():
    """Garante erro apropriado quando arquivo está vazio."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp_path = tmp.name
        
    try:
        with pytest.raises(ValueError, match="Arquivo vazio"):
            parse_momento(tmp_path)
    finally:
        os.remove(tmp_path)


def test_erro_primeira_linha_invalida():
    """Garante erro apropriado quando primeira linha não é um número de pontos válido."""
    # Caso 1: Não é inteiro
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write("texto_invalido\n0.0\t10.0\n")
        tmp_path = tmp.name
    try:
        with pytest.raises(ValueError, match="primeira linha"):
            parse_momento(tmp_path)
    finally:
        os.remove(tmp_path)

    # Caso 2: Inteiro negativo ou zero
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write("0\n0.0\t10.0\n")
        tmp_path = tmp.name
    try:
        with pytest.raises(ValueError, match="deve ser maior que zero"):
            parse_momento(tmp_path)
    finally:
        os.remove(tmp_path)


def test_erro_linhas_de_dados_insuficientes():
    """Garante erro se o arquivo tem menos linhas de dados que o declarado."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write("5\n0.0\t10.0\n1.0\t15.0\n")
        tmp_path = tmp.name
    try:
        with pytest.raises(ValueError, match="não corresponde ao número de linhas de dados"):
            parse_momento(tmp_path)
    finally:
        os.remove(tmp_path)


def test_erro_menos_colunas_que_o_esperado():
    """Garante erro se uma linha de dados tem menos colunas que o esperado."""
    # Momentos precisa de 2 colunas
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write("1\n0.0\n")
        tmp_path = tmp.name
    try:
        with pytest.raises(ValueError, match="menos colunas que o esperado"):
            parse_momento(tmp_path)
    finally:
        os.remove(tmp_path)

    # Deformações precisa de 4 colunas
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write("1\n0.0\t1.0\t2.0\n")
        tmp_path = tmp.name
    try:
        with pytest.raises(ValueError, match="menos colunas que o esperado"):
            parse_deformacao(tmp_path)
    finally:
        os.remove(tmp_path)


def test_erro_valores_nao_numericos():
    """Garante erro se valores na tabela não forem numéricos."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write("1\n0.0\ttexto\n")
        tmp_path = tmp.name
    try:
        with pytest.raises(ValueError, match="contém valores numéricos inválidos"):
            parse_momento(tmp_path)
    finally:
        os.remove(tmp_path)


def test_suporte_encodings():
    """Verifica que o parser suporta UTF-8 e ANSI/CP1252."""
    conteudo = "2\n0.0\t-135.6\n1.0\t120.0\n"
    
    # 1. Testando UTF-8
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write(conteudo)
        utf8_path = tmp.name
        
    # 2. Testando ANSI / CP1252
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="cp1252") as tmp:
        tmp.write(conteudo)
        ansi_path = tmp.name
        
    try:
        res_utf8 = parse_momento(utf8_path)
        res_ansi = parse_momento(ansi_path)
        
        assert res_utf8 == [(0.0, -135.6), (1.0, 120.0)]
        assert res_ansi == [(0.0, -135.6), (1.0, 120.0)]
    finally:
        os.remove(utf8_path)
        os.remove(ansi_path)


def test_parse_tudo_erros_pasta():
    """Valida erros de diretório ou ausência de arquivos específicos em parse_tudo."""
    # 1. Caminho que não é pasta
    with pytest.raises(NotADirectoryError):
        parse_tudo("arquivo_inexistente.txt")
        
    # 2. Pasta vazia
    with tempfile.TemporaryDirectory() as empty_dir:
        with pytest.raises(FileNotFoundError, match="Arquivo de momentos não encontrado"):
            parse_tudo(empty_dir)
            
        # Cria apenas momentos
        with open(os.path.join(empty_dir, "momento_fletor.txt"), "w") as f:
            f.write("1\n0.0\t10.0\n")
            
        with pytest.raises(FileNotFoundError, match="Arquivo de cortantes não encontrado"):
            parse_tudo(empty_dir)
            
        # Cria cortantes também
        with open(os.path.join(empty_dir, "esforcos_cortantes.txt"), "w") as f:
            f.write("1\n0.0\t10.0\n")
            
        with pytest.raises(FileNotFoundError, match="Arquivo de deformações não encontrado"):
            parse_tudo(empty_dir)


def test_validate_file_type_real():
    """Valida a função validate_file_type usando os arquivos de teste reais."""
    # 1. Validações corretas
    ok_m, _ = validate_file_type(MOMENTO_FILE, "momento")
    assert ok_m is True

    ok_v, _ = validate_file_type(CORTANTE_FILE, "cortante")
    assert ok_v is True

    ok_d, _ = validate_file_type(DEFORMACAO_FILE, "deformacao")
    assert ok_d is True

    # 2. Rejeição de tipos errados
    # Deformação em momento/cortante (tem 4 colunas)
    ok, err = validate_file_type(DEFORMACAO_FILE, "momento")
    assert ok is False
    assert "colunas" in err

    ok, err = validate_file_type(DEFORMACAO_FILE, "cortante")
    assert ok is False
    assert "colunas" in err

    # Cortante em momento (tem descontinuidade no apoio)
    ok, err = validate_file_type(CORTANTE_FILE, "momento")
    assert ok is False
    assert "descontinuidades" in err

    # Momento em cortante (não tem descontinuidade e tem curvatura)
    ok, err = validate_file_type(MOMENTO_FILE, "cortante")
    assert ok is False
    assert "curvatura" in err


def test_validate_file_type_erros():
    """Valida rejeição de arquivos inválidos (não FTOOL, vazios, etc)."""
    # Arquivo não existente
    ok, err = validate_file_type("inexistente.txt", "momento")
    assert ok is False
    assert "Falha ao ler" in err

    # Arquivo com cabeçalho inválido
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write("texto_invalido\n0.0\t10.0\n")
        tmp_path = tmp.name
    try:
        ok, err = validate_file_type(tmp_path, "momento")
        assert ok is False
        assert "primeira linha" in err
    finally:
        os.remove(tmp_path)

