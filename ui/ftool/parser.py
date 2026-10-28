"""
Módulo de parsing para arquivos exportados pelo FTOOL.
Fase 2.1 — Parser FTOOL TXT
"""

import os
from typing import List, Tuple, Dict, Any, Literal


def _read_and_clean_lines(filepath: str) -> List[str]:
    """
    Lê as linhas de um arquivo de texto testando múltiplos encodings (UTF-8, ANSI/CP1252, Latin-1).
    Remove linhas vazias e espaços em branco nas extremidades.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
    
    if os.path.getsize(filepath) == 0:
        raise ValueError("Arquivo vazio")
        
    encodings = ['utf-8', 'cp1252', 'latin-1']
    content = None
    
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
            
    if content is None:
        # Fallback para o default do sistema se nenhum dos encodings funcionar
        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"Não foi possível ler o arquivo com os encodings suportados: {e}")
            
    lines = [line.strip() for line in content.splitlines()]
    # Filtrar linhas vazias
    lines = [line for line in lines if line]
    
    if not lines:
        raise ValueError("Arquivo não contém dados válidos ou está vazio")
        
    return lines


def _parse_first_line_as_n(lines: List[str]) -> int:
    """
    Valida e converte a primeira linha como o número de pontos (N).
    """
    first_line = lines[0]
    try:
        N = int(first_line)
    except ValueError:
        raise ValueError(f"A primeira linha do arquivo deve ser o número de pontos (inteiro válido). Encontrado: '{first_line}'")
        
    if N <= 0:
        raise ValueError(f"O número de pontos declarado deve ser maior que zero. Encontrado: {N}")
        
    return N


def parse_momento(filepath: str) -> List[Tuple[float, float]]:
    """
    Lê arquivo TXT de momentos fletores exportado pelo FTOOL.
    Retorna uma lista de tuplas (x, M) onde:
    - x: posição na viga (metros)
    - M: momento fletor (kN·m)
    """
    lines = _read_and_clean_lines(filepath)
    N = _parse_first_line_as_n(lines)
    
    # O total de linhas de dados deve ser igual a N
    data_lines = lines[1:]
    if len(data_lines) != N:
        raise ValueError(f"O número de pontos declarado ({N}) não corresponde ao número de linhas de dados encontradas ({len(data_lines)})")
        
    resultados = []
    for idx, line in enumerate(data_lines, start=1):
        # Tenta separar por tabulação primeiro, senão por qualquer espaço em branco
        parts = line.split('\t')
        if len(parts) < 2:
            parts = line.split()
            
        if len(parts) < 2:
            raise ValueError(f"Linha {idx + 1} possui menos colunas que o esperado (mínimo 2). Encontrado: '{line}'")
            
        try:
            x = float(parts[0])
            M = float(parts[1])
        except ValueError:
            raise ValueError(f"Linha {idx + 1} contém valores numéricos inválidos: '{line}'")
            
        resultados.append((x, M))
        
    return resultados


def parse_cortante(filepath: str) -> List[Tuple[float, float]]:
    """
    Lê arquivo TXT de esforços cortantes exportado pelo FTOOL.
    Retorna uma lista de tuplas (x, V) onde:
    - x: posição na viga (metros)
    - V: esforço cortante (kN)
    """
    lines = _read_and_clean_lines(filepath)
    N = _parse_first_line_as_n(lines)
    
    data_lines = lines[1:]
    if len(data_lines) != N:
        raise ValueError(f"O número de pontos declarado ({N}) não corresponde ao número de linhas de dados encontradas ({len(data_lines)})")
        
    resultados = []
    for idx, line in enumerate(data_lines, start=1):
        parts = line.split('\t')
        if len(parts) < 2:
            parts = line.split()
            
        if len(parts) < 2:
            raise ValueError(f"Linha {idx + 1} possui menos colunas que o esperado (mínimo 2). Encontrado: '{line}'")
            
        try:
            x = float(parts[0])
            V = float(parts[1])
        except ValueError:
            raise ValueError(f"Linha {idx + 1} contém valores numéricos inválidos: '{line}'")
            
        resultados.append((x, V))
        
    return resultados


def parse_deformacao(filepath: str) -> List[Tuple[float, float, float, float]]:
    """
    Lê arquivo TXT de deformações/deslocamentos exportado pelo FTOOL.
    Retorna uma lista de tuplas (x, d, θ, κ) onde:
    - x: posição na viga (metros)
    - d: deslocamento (metros)
    - θ: rotação (radianos)
    - κ: curvatura (1/metros)
    """
    lines = _read_and_clean_lines(filepath)
    N = _parse_first_line_as_n(lines)
    
    data_lines = lines[1:]
    if len(data_lines) != N:
        raise ValueError(f"O número de pontos declarado ({N}) não corresponde ao número de linhas de dados encontradas ({len(data_lines)})")
        
    resultados = []
    for idx, line in enumerate(data_lines, start=1):
        parts = line.split('\t')
        if len(parts) < 4:
            parts = line.split()
            
        if len(parts) < 4:
            raise ValueError(f"Linha {idx + 1} possui menos colunas que o esperado (mínimo 4). Encontrado: '{line}'")
            
        try:
            x = float(parts[0])
            d = float(parts[1])
            theta = float(parts[2])
            kappa = float(parts[3])
        except ValueError:
            raise ValueError(f"Linha {idx + 1} contém valores numéricos inválidos: '{line}'")
            
        resultados.append((x, d, theta, kappa))
        
    return resultados


def parse_tudo(pasta: str) -> Dict[str, Any]:
    """
    Lê os 3 arquivos de uma pasta (momentos, cortantes, deformacoes) e retorna
    um dicionário com chaves:
    - 'momentos' -> List[Tuple[float, float]]
    - 'cortantes' -> List[Tuple[float, float]]
    - 'deformacoes' -> List[Tuple[float, float, float, float]]
    """
    if not os.path.isdir(pasta):
        raise NotADirectoryError(f"O caminho fornecido não é um diretório válido: {pasta}")
        
    arquivos = os.listdir(pasta)
    
    momento_file = None
    cortante_file = None
    deformacao_file = None
    
    for arq in arquivos:
        arq_lower = arq.lower()
        if arq_lower.endswith(".txt"):
            if "momento" in arq_lower:
                momento_file = os.path.join(pasta, arq)
            elif "cortante" in arq_lower:
                cortante_file = os.path.join(pasta, arq)
            elif "deformac" in arq_lower or "deformaç" in arq_lower:
                deformacao_file = os.path.join(pasta, arq)
                
    if not momento_file:
        raise FileNotFoundError(f"Arquivo de momentos não encontrado na pasta '{pasta}' (deve conter 'momento' no nome e extensão '.txt')")
    if not cortante_file:
        raise FileNotFoundError(f"Arquivo de cortantes não encontrado na pasta '{pasta}' (deve conter 'cortante' no nome e extensão '.txt')")
    if not deformacao_file:
        raise FileNotFoundError(f"Arquivo de deformações não encontrado na pasta '{pasta}' (deve conter 'deformac' ou 'deformaç' no nome e extensão '.txt')")
        
    return {
        "momentos": parse_momento(momento_file),
        "cortantes": parse_cortante(cortante_file),
        "deformacoes": parse_deformacao(deformacao_file)
    }


def validate_file_type(filepath: str, tipo_esperado: Literal["momento", "cortante", "deformacao"]) -> Tuple[bool, str]:
    """
    Valida se o arquivo FTOOL TXT corresponde ao tipo esperado.
    
    Retorna:
        (True, "") se o arquivo for válido e do tipo correto.
        (False, "mensagem de erro") caso ocorra alguma falha ou incompatibilidade.
    """
    try:
        lines = _read_and_clean_lines(filepath)
    except Exception as e:
        return False, f"Falha ao ler arquivo: {e}"

    if len(lines) < 2:
        return False, "O arquivo deve conter pelo menos duas linhas (N e dados)."

    try:
        N = _parse_first_line_as_n(lines)
    except ValueError as e:
        return False, str(e)

    data_lines = lines[1:]
    if len(data_lines) != N:
        return False, f"O número de pontos declarado ({N}) não corresponde ao número de linhas encontradas ({len(data_lines)})."

    colunas_esperadas = 4 if tipo_esperado == "deformacao" else 2
    pontos = []

    for idx, line in enumerate(data_lines, start=1):
        parts = line.split('\t')
        if len(parts) < colunas_esperadas:
            parts = line.split()

        if len(parts) < colunas_esperadas:
            return False, f"Linha {idx + 1} possui menos colunas que o esperado ({colunas_esperadas}). Linha: '{line}'"

        # Se tipo esperado é momento ou cortante, mas o arquivo tem mais colunas, rejeita
        if tipo_esperado in ("momento", "cortante") and len(parts) >= 4:
            return False, f"O arquivo possui {len(parts)} colunas (característico de Deformação), mas esperava-se 2 colunas."

        try:
            row_vals = [float(p.replace(',', '.')) for p in parts[:colunas_esperadas]]
        except ValueError:
            return False, f"Linha {idx + 1} contém valores numéricos inválidos: '{line}'"
        
        pontos.append(row_vals)

    # Validação rápida de Deformação
    if tipo_esperado == "deformacao":
        # Se esperava deformação e o arquivo tem 4 colunas estruturadas, está correto.
        return True, ""

    # Separação para diferenciação Momento vs Cortante
    x_to_y = {}
    for x, y in pontos:
        if x not in x_to_y:
            x_to_y[x] = []
        x_to_y[x].append(y)

    # Heurística 1: Descontinuidade vertical (dois valores de y para um mesmo x)
    tem_descontinuidade = False
    for x, values in x_to_y.items():
        if len(values) > 1:
            if max(values) - min(values) > 1e-4:
                tem_descontinuidade = True
                break

    if tem_descontinuidade:
        if tipo_esperado == "momento":
            return False, "O arquivo contém descontinuidades verticais (típico de Esforço Cortante), mas o campo selecionado é Momento Fletor."
        return True, ""

    # Heurística 2: Curvatura via Segunda Derivada
    sorted_x = sorted(list(x_to_y.keys()))
    if len(sorted_x) >= 3:
        derivadas_2 = []
        for i in range(1, len(sorted_x) - 1):
            x0, x1, x2 = sorted_x[i-1], sorted_x[i], sorted_x[i+1]
            y0 = x_to_y[x0][0]
            y1 = x_to_y[x1][0]
            y2 = x_to_y[x2][0]

            h1 = x1 - x0
            h2 = x2 - x1
            if h1 > 0 and h2 > 0:
                d1 = (y1 - y0) / h1
                d2 = (y2 - y1) / h2
                d2y = (d2 - d1) / ((h1 + h2) / 2)
                derivadas_2.append(abs(d2y))

        avg_d2 = sum(derivadas_2) / len(derivadas_2) if derivadas_2 else 0.0
        is_momento = avg_d2 > 0.1
    else:
        is_momento = True

    if is_momento and tipo_esperado == "cortante":
        return False, "O arquivo apresenta curvatura contínua (típico de Momento Fletor), mas o campo selecionado é Esforço Cortante."
    
    if not is_momento and tipo_esperado == "momento":
        return False, "O diagrama é linear/nulo (típico de Esforço Cortante), mas o campo selecionado é Momento Fletor."

    return True, ""

