"""
Módulo para geração de diagramas de esforços diretamente no PDF.
Fase 2.4 — Diagrama de Esforços no PDF
"""

from typing import List, Tuple
from fpdf import FPDF
from ui.ftool.secoes_criticas import SecaoCritica


def _desenhar_grafico(
    pdf: FPDF,
    x_origin: float,
    y_origin: float,
    largura: float,
    altura: float,
    pontos: List[Tuple[float, float]],
    cor_linha: Tuple[int, int, int],
    titulo: str,
    unidade_y: str,
    secoes_criticas: List[SecaoCritica],
    tipo_esforco: str,  # "M" ou "V"
) -> None:
    """
    Desenha um único gráfico (Momento ou Cortante) no PDF usando fpdf2.
    """
    is_envelope = isinstance(pontos, dict)
    if is_envelope:
        pontos_max = pontos.get("max", [])
        pontos_min = pontos.get("min", [])
        pontos_combined = pontos_max + pontos_min
    else:
        pontos_combined = pontos

    if not pontos_combined:
        return

    # Inverter sinal do momento para convenção brasileira (negativo = tração superior = para cima)
    inverter = tipo_esforco == "M"
    if inverter:
        pontos_combined = [(p[0], -p[1]) for p in pontos_combined]
        if is_envelope:
            pontos_max = [(p[0], -p[1]) for p in pontos_max]
            pontos_min = [(p[0], -p[1]) for p in pontos_min]

    # 1. Encontrar limites reais da viga
    L = max(p[0] for p in pontos_combined)
    if L <= 0:
        L = 1.0

    y_vals = [p[1] for p in pontos_combined]
    y_min = min(y_vals)
    y_max = max(y_vals)

    # Garantir que o eixo zero esteja na área visível
    y_min = min(0.0, y_min)
    y_max = max(0.0, y_max)

    # Adicionar margem de 12% no eixo Y para rótulos/respiro
    y_span = y_max - y_min
    if y_span == 0:
        y_span = 1.0
    y_min_padded = y_min - 0.12 * y_span
    y_max_padded = y_max + 0.12 * y_span
    y_span_padded = y_max_padded - y_min_padded

    # 2. Desenhar Fundo e Borda do Gráfico
    pdf.set_draw_color(220, 220, 220)  # Cinza bem claro
    pdf.set_fill_color(255, 255, 255)  # Branco
    pdf.rect(x_origin, y_origin, largura, altura, style="DF")

    # 3. Desenhar Grid Leve
    pdf.set_draw_color(242, 242, 242)
    pdf.set_line_width(0.15)

    # Grid vertical a cada 1m
    for mx in range(int(L) + 1):
        px = x_origin + (mx / L) * largura
        pdf.line(px, y_origin, px, y_origin + altura)

    # Grid horizontal (4 faixas)
    for i in range(5):
        py = y_origin + altura - (i / 4) * altura
        pdf.line(x_origin, py, x_origin + largura, py)

    # 4. Desenhar Eixo Y = 0 (Linha mais forte)
    py_zero = y_origin + altura - ((0.0 - y_min_padded) / y_span_padded) * altura
    pdf.set_draw_color(120, 120, 120)
    pdf.set_line_width(0.4)
    pdf.line(x_origin, py_zero, x_origin + largura, py_zero)

    # 5. Desenhar Curva de Esforços
    pdf.set_draw_color(*cor_linha)
    pdf.set_line_width(0.7)
    
    def desenhar_curva_fpdf(pts):
        pontos_ordenados = sorted(pts, key=lambda p: p[0])
        for idx in range(len(pontos_ordenados) - 1):
            x1, y1 = pontos_ordenados[idx]
            x2, y2 = pontos_ordenados[idx + 1]

            px1 = x_origin + (x1 / L) * largura
            py1 = y_origin + altura - ((y1 - y_min_padded) / y_span_padded) * altura
            px2 = x_origin + (x2 / L) * largura
            py2 = y_origin + altura - ((y2 - y_min_padded) / y_span_padded) * altura

            pdf.line(px1, py1, px2, py2)

    if is_envelope:
        desenhar_curva_fpdf(pontos_max)
        desenhar_curva_fpdf(pontos_min)
    else:
        pontos_plot = [(p[0], -p[1]) for p in pontos] if inverter else pontos
        desenhar_curva_fpdf(pontos_plot)

    # 6. Desenhar Linhas Verticais Pontilhadas e Rótulos nas Seções Críticas
    # Agrupar seções próximas para evitar sobreposição de rótulos
    secoes_ordenadas = sorted(secoes_criticas, key=lambda s: s.x)
    labels_pos = []  # armazena (px, py_pt, val_esforco, lbl, sec) para cada seção
    for sec in secoes_ordenadas:
        px = x_origin + (sec.x / L) * largura
        
        # Desenhar linha vertical pontilhada (Tracejada)
        pdf.set_draw_color(160, 160, 160)
        pdf.set_line_width(0.2)
        y_curr = y_origin
        while y_curr < y_origin + altura:
            pdf.line(px, y_curr, px, min(y_curr + 1.2, y_origin + altura))
            y_curr += 2.4

        # Determinar esforço correspondente da seção
        val_esforco = sec.momento if tipo_esforco == "M" else sec.cortante
        val_plot = -val_esforco if inverter else val_esforco
        py_pt = y_origin + altura - ((val_plot - y_min_padded) / y_span_padded) * altura

        # Desenhar um ponto na curva
        pdf.set_fill_color(*cor_linha)
        pdf.circle(px - 0.9, py_pt - 0.9, 1.8, style="F")

        # Rótulo de texto formatado
        if sec.tipo == "MÁX":
            lbl = f"Máx {val_esforco:+.1f}"
        elif sec.tipo == "MÍN":
            lbl = f"Mín {val_esforco:+.1f}"
        elif sec.tipo == "APOIO":
            lbl = f"Apoio {val_esforco:+.1f}"
        elif sec.tipo == "M_NULO":
            lbl = "M=0"
        else:
            lbl = f"{val_esforco:+.1f}"

        labels_pos.append((px, py_pt, val_esforco, lbl, sec))

    # Desenhar rótulos com posicionamento inteligente para evitar sobreposição
    pdf.set_font("Helvetica", "B", 7)
    for i, (px, py_pt, val_esforco, lbl, sec) in enumerate(labels_pos):
        pdf.set_text_color(60, 60, 60)
        
        # Verificar se há outra seção muito próxima (< 12mm no PDF)
        tem_proximo = False
        if i < len(labels_pos) - 1:
            prox_px = labels_pos[i + 1][0]
            if abs(prox_px - px) < 12:
                tem_proximo = True

        # Posicionar rótulo: alternar acima/abaixo para evitar colisão
        if tem_proximo or py_pt < y_origin + 8:
            offset_y = 4.0  # abaixo
        else:
            offset_y = -2.5  # acima

        # Ajustar horizontal para não cortar na borda direita
        offset_x = 2.0
        if px > x_origin + largura - 15:
            offset_x = -pdf.get_string_width(lbl) - 2.0  # texto à esquerda do ponto

        # Fundo branco atrás do rótulo para garantir legibilidade
        lbl_w = pdf.get_string_width(lbl) + 1.0
        lbl_h = 2.5
        lbl_x = px + offset_x - 0.5
        lbl_y = py_pt + offset_y - lbl_h + 0.5
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(lbl_x, lbl_y, lbl_w, lbl_h, style="F")

        pdf.text(px + offset_x, py_pt + offset_y, lbl)

    # 7. Desenhar Escala nos Eixos (Rótulos de eixos)
    pdf.set_text_color(120, 120, 120)
    pdf.set_font("Helvetica", "", 7)
    
    # Rótulos do Eixo Y (Valores de esforços)
    for i in range(5):
        val_y = y_min_padded + (i / 4) * y_span_padded
        if inverter:
            val_y = -val_y  # Mostra valor original (não invertido) nos rótulos
        py = y_origin + altura - (i / 4) * altura
        pdf.text(x_origin - 12, py + 1.5, f"{val_y:.1f}")

    # Rótulos do Eixo X (Metragem)
    for mx in range(int(L) + 1):
        px = x_origin + (mx / L) * largura
        pdf.text(px - 2.5, y_origin + altura + 4.0, f"{mx}m")
    
    # Adicionar o ponto final se for decimal (ex: 7.50m)
    if abs(L - int(L)) > 1e-3:
        px_end = x_origin + largura
        pdf.text(px_end - 4.5, y_origin + altura + 4.0, f"{L:.2f}m")

    # 8. Título do Gráfico e Legenda do Eixo Y
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(50, 50, 50)
    pdf.text(x_origin, y_origin - 4.0, f"{titulo} ({unidade_y})")


def gerar_diagrama_esforcos(
    pdf: FPDF,
    momentos: List[Tuple[float, float]],
    cortantes: List[Tuple[float, float]],
    secoes_criticas: List[SecaoCritica],
    largura_mm: float = 160,
    altura_mm: float = 60,
) -> None:
    """
    Desenha os dois diagramas empilhados (Momento em cima, Cortante embaixo) no PDF atual.
    """
    # Obter posição inicial na página
    # Se não houver espaço suficiente para os dois gráficos mais margens (~140mm),
    # adicionamos uma nova página
    margem_necessaria = 2 * altura_mm + 25.0
    if pdf.get_y() + margem_necessaria > pdf.h - 25.0:
        pdf.add_page()
        
    y_start = pdf.get_y() + 8.0
    
    # Alinhamento preciso com as margens do PDF
    ML = getattr(pdf, "l_margin", 20.0)
    MR = getattr(pdf, "r_margin", 20.0)
    PW = getattr(pdf, "w", 210.0)
    x_start = ML + 12.0
    largura_real = PW - ML - MR - 12.0

    # 1. Gráfico de Momentos (Azul)
    _desenhar_grafico(
        pdf=pdf,
        x_origin=x_start,
        y_origin=y_start,
        largura=largura_real,
        altura=altura_mm,
        pontos=momentos,
        cor_linha=(0, 90, 180),  # Azul
        titulo="Diagrama de Momentos Fletores",
        unidade_y="kN·m",
        secoes_criticas=secoes_criticas,
        tipo_esforco="M",
    )

    # 2. Gráfico de Cortantes (Vermelho)
    y_start_cortante = y_start + altura_mm + 18.0
    _desenhar_grafico(
        pdf=pdf,
        x_origin=x_start,
        y_origin=y_start_cortante,
        largura=largura_real,
        altura=altura_mm,
        pontos=cortantes,
        cor_linha=(200, 30, 30),  # Vermelho
        titulo="Diagrama de Esforços Cortantes",
        unidade_y="kN",
        secoes_criticas=secoes_criticas,
        tipo_esforco="V",
    )
    
    # Atualizar cursor y da página do PDF para após os gráficos
    pdf.set_y(y_start_cortante + altura_mm + 12.0)
