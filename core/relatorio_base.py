"""
Geração de Relatórios PDF - Portica App
Design baseado estritamente no modelo HTML fornecido pelo usuário (relatorio_portica_profissional.html).
Cor principal: #0000CD (Azul Portica). Sem capa separada.
Layout limpo, profissional, moderno e com alto impacto estético.
"""

import math
import os
from datetime import datetime
from typing import List, Optional, Any, Callable

from fpdf import FPDF

from core.utils_tempfile import temp_path, resource_path

from core.calculos.engenharia import (
    ResultadoFlexao,
    ResultadoCisalhamento,
    ResultadoFlexaoT,
    CAA_DATA,
    DIAM_BARRAS,
    area_barra,
    fck_to_kgf_cm2,
)

from core.version import APP_VERSION


# Cores oficiais do design HTML do usuário
C_PORTICA  = (0, 0, 205)      # #0000CD - Azul Portica
C_GRAY900  = (31, 41, 55)     # #1f2937 - Cinza Escuro Textos
C_GRAY800  = (31, 41, 55)     # #1f2937
C_GRAY700  = (55, 65, 81)     # #374151 - Subtítulos
C_GRAY600  = (75, 85, 99)     # #4b5563
C_GRAY500  = (107, 114, 128)  # #6b7280 - Muted
C_GRAY400  = (156, 163, 175)  # #9ca3af
C_GRAY300  = (209, 213, 219)  # #d1d5db - Linhas de grade
C_GRAY200  = (229, 231, 235)  # #e5e7eb - Bordas leves
C_GRAY100  = (243, 244, 246)  # #f3f4f6 - Fundos
C_GRAY50   = (249, 250, 251)  # #f9fafb
C_WHITE    = (255, 255, 255)

C_GREEN800 = (22, 101, 52)    # Text OK
C_GREEN100 = (220, 252, 231)   # Bg OK
C_RED700   = (185, 28, 28)     # Text ALERTA
C_RED100   = (254, 226, 226)    # Bg ALERTA

C_AMBER800 = (146, 64, 14)    # Text Aviso
C_AMBER50  = (255, 251, 235)   # Bg Aviso
C_AMBER500 = (245, 158, 11)   # Border Aviso

C_BLUE50   = (239, 246, 255)   # Bg Destaque Adoptada

# Margens da página A4
ML = 20  # Margem Esquerda de 20mm do HTML
MR = 20  # Margem Direita de 20mm do HTML
MT = 20  # Margem Superior
MB = 20  # Margem Inferior
PW = 210 # Largura da Página A4
IW = PW - ML - MR # Largura Útil = 170mm

def _n(valor, casas: int = 2, fallback: str = "—") -> str:
    if valor is None:
        return fallback
    try:
        s = f"{float(valor):,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(valor)

def _diam(d_mm) -> str:
    if d_mm is None:
        return "—"
    return f"{d_mm:g}".replace(".", ",")

def _caa_nome(caa: int) -> str:
    from core.calculos import CAA_DATA
    romanos = {1: "I", 2: "II", 3: "III", 4: "IV"}
    if caa in CAA_DATA:
        return f"{romanos.get(caa, str(caa))} ({CAA_DATA[caa]['nome']})"
    return str(caa)


class PorticaPDF(FPDF):
    def __init__(self, nome_viga: str = "Viga V1", subtitulo: str = "Viga de Seção Retangular", dark_mode: bool = False, nome_engenheiro: str = "", crea: str = "",
                 profissao: str = "Engenheiro Civil", responsavel_nome: str = "", responsavel_registro: str = ""):
        super().__init__(orientation="P", unit="mm", format="A4")
        # Fontes core (Helvetica/Courier) em cp1252: permite o travessao (—) e
        # demais caracteres do Windows-1252 no rodape de aviso de responsabilidade.
        self.core_fonts_encoding = "cp1252"
        self._nome_viga = nome_viga
        self._subtitulo = subtitulo
        self._dark_mode = dark_mode
        self._profissao = profissao
        self._nome_engenheiro = nome_engenheiro or responsavel_nome
        self._crea = crea or responsavel_registro
        self._ts_data = datetime.now().strftime("%d/%m/%Y")
        self._ts_hora = datetime.now().strftime("%H:%M:%S")
        self.set_margins(left=ML, top=MT, right=MR)
        self.set_auto_page_break(auto=True, margin=MB + 5)
        
    def normalize_text(self, text: str) -> str:
        # fpdf2 >= 2.5 removeu is_ttf_font/core_fonts_encoding; usa core_fonts
        # fallback com try/except para compatibilidade retroativa
        try:
            if not self.is_ttf_font and self.core_fonts_encoding:
                try:
                    return text.encode(self.core_fonts_encoding).decode("latin-1")
                except UnicodeEncodeError:
                    return text.encode(self.core_fonts_encoding, "replace").decode("latin-1")
        except AttributeError:
            pass
        return text

    def header(self):
        if self.page_no() == 1:
            self._cabecalho_pagina1()
        else:
            self._cabecalho_simplificado()

    def _cabecalho_pagina1(self):
        self.set_y(MT)
        
        # Desenhar o logotipo a partir do arquivo
        logo_x = ML
        logo_y = MT
        logo_w = 12
        logo_h = 12
        
        # M4: logo respeita tema escuro
        logo_name = "logo_dark.png" if self._dark_mode else "logo.png"
        logo_path = os.path.join(os.path.dirname(__file__), "assets", logo_name)
        if not os.path.exists(logo_path):
            # Fallback para logo claro se dark nao existir
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, x=logo_x, y=logo_y, w=logo_w, h=logo_h)        
        # Agora o título "Portica App" e subtítulo
        self.set_xy(ML + 15, MT)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*C_GRAY900)
        self.cell(80, 6, "Portica App", border=0)
        
        self.set_xy(ML + 15, MT + 6.5)
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*C_GRAY500)
        self.cell(80, 3, "CALCULADORA ESTRUTURAL  |  NBR 6118:2023", border=0)
        
        # Lado direito
        self.set_xy(ML + 80, MT)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_GRAY800)
        self.cell(IW - 80, 5, "Relatório de Dimensionamento", border=0, align="R")
        
        self.set_xy(ML + 80, MT + 5.5)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*C_GRAY500)
        self.cell(IW - 80, 4, self._subtitulo, border=0, align="R")
        
        # Linha inferior do header (azul de 2px de espessura)
        y_line = MT + 14
        self.set_draw_color(*C_PORTICA)
        self.set_line_width(0.8)
        self.line(ML, y_line, PW - MR, y_line)
        self.set_line_width(0.2)
        
        # Cursor posicionado para o conteúdo
        self.set_y(y_line + 8)

    def _cabecalho_simplificado(self):
        self.set_y(MT - 8)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*C_PORTICA)
        self.cell(30, 5, "Portica App", border=0)
        self.set_text_color(*C_GRAY500)
        self.set_font("Helvetica", "", 8)
        # Truncar nome para caber antes do timestamp
        max_len = 60
        nome_exib = self._nome_viga if len(self._nome_viga) <= max_len else self._nome_viga[:max_len - 3] + "..."
        self.cell(0, 5, f" | {nome_exib}", border=0, new_x="LMARGIN", new_y="NEXT")
        
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, f"{self._ts_data} - {self._ts_hora[:5]}", border=0, align="R", new_x="LMARGIN", new_y="NEXT")
        
        self.set_draw_color(*C_GRAY200)
        self.set_line_width(0.3)
        self.line(ML, self.get_y(), PW - MR, self.get_y())
        self.set_line_width(0.2)
        self.ln(6)

    def footer(self):
        self.set_y(-(MB + 2))
        self.set_draw_color(*C_GRAY200)
        self.set_line_width(0.3)
        self.line(ML, self.get_y(), PW - MR, self.get_y())
        self.set_line_width(0.2)
        
        self.ln(2)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*C_GRAY400)
        self.cell(IW - 40, 4, "Gerado pelo Portica App - Válido apenas com assinatura do Eng. Responsável.", border=0, align="L")
        
        # Paginação coerente com o HTML
        self.cell(40, 4, f"Pág. {self.page_no()} / {{nb}}", border=0, align="R")

        # Aviso de responsabilidade (2a linha do rodape)
        # Nao chamamos normalize_text() aqui: o fpdf2 normaliza uma unica vez
        # (o texto e convertido para cp1252 pelo proprio `cell`).
        self.ln(4.2)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*C_GRAY400)
        self.cell(IW, 4, "Uso sob responsabilidade do usuário — ver README do projeto", border=0, align="L")

    def section_title(self, numero: int, texto: str):
        # Evita órfãos de títulos de seção
        if self.get_y() + 25 > self.h - MB:
            self.add_page()
            
        y = self.get_y()
        
        # Badge redondo com o número
        r = 2.5
        cx = ML + r
        cy = y + 3.5
        self.set_fill_color(*C_PORTICA)
        self.ellipse(cx - r, cy - r, r * 2, r * 2, style="F")
        
        # Número branco centralizado
        self.set_xy(cx - r, cy - r)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*C_WHITE)
        self.cell(r * 2, r * 2, str(numero), border=0, align="C")
        
        # Texto do título
        self.set_xy(ML + 7, y)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*C_PORTICA)
        self.cell(0, 7, texto, border=0)
        
        # Linha under o título de seção (cinza claro)
        self.set_draw_color(*C_GRAY200)
        self.set_line_width(0.3)
        self.line(ML, y + 7.5, PW - MR, y + 7.5)
        self.set_line_width(0.2)

        self.set_y(y + 11)

    def meta_header(self):
        """Linha de metadados do projeto, ACIMA dos data_cards.

        Mostra nome da viga em destaque, engenheiro, CREA/CAU e data.
        Usa largura total (ML a MR) e quebra de linha automatica, para
        acomodar nomes longos sem passar das margens.
        """
        y0 = self.get_y()

        # Nome da viga (destaque, bold)
        self.set_xy(ML, y0)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*C_GRAY900)
        self.multi_cell(IW, 5.5, self.normalize_text(self._nome_viga), border=0)
        y1 = self.get_y()

        # Linha de meta: Engenheiro | CREA/CAU | Data
        parts = []
        if self._nome_engenheiro:
            rotulo = "Eng." if self._profissao == "Engenheiro Civil" else "Arq." if self._profissao == "Arquiteto" else "Resp."
            parts.append(f"{rotulo}: {self._nome_engenheiro}")
        if self._crea:
            rotulo_reg = "CREA/UF:" if self._profissao == "Engenheiro Civil" else "CAU/UF:" if self._profissao == "Arquiteto" else "Registro:"
            parts.append(f"{rotulo_reg} {self._crea}")
        parts.append(f"Data: {self._ts_data}")

        if parts:
            meta_text = "  |  ".join(parts)
            self.set_xy(ML, y1)
            self.set_font("Helvetica", "", 8.5)
            self.set_text_color(*C_GRAY600)
            self.multi_cell(IW, 4.5, self.normalize_text(meta_text), border=0)
            y2 = self.get_y()
        else:
            y2 = y1

        # Linha separadora sutil
        self.set_draw_color(*C_GRAY200)
        self.set_line_width(0.3)
        self.line(ML, y2 + 1, ML + IW, y2 + 1)
        self.set_y(y2 + 4)

    def data_cards(self, cards: list):
        n = len(cards)
        gap = 4
        card_w = (IW - gap * (n - 1)) / n
        x0 = ML
        y0 = self.get_y()
        max_rows = max(len(c["rows"]) for c in cards)
        # Altura calculada dinamicamente com base nas linhas
        card_h = 6 + 6 + max_rows * 6.5 + 4
        
        if y0 + card_h > self.h - MB:
            self.add_page()
            y0 = self.get_y()
            
        for ci, card in enumerate(cards):
            cx = x0 + ci * (card_w + gap)
            
            # Card Container
            self.set_fill_color(*C_WHITE)
            self.set_draw_color(*C_GRAY200)
            self.set_line_width(0.3)
            self.rect(cx, y0, card_w, card_h, style="FD")
            
            # Título do Card
            self.set_xy(cx + 3, y0 + 3)
            self.set_font("Helvetica", "B", 7.5)
            self.set_text_color(*C_GRAY500)
            self.cell(card_w - 6, 4, card["title"].upper(), border=0)
            
            # Linha separadora do card
            self.set_draw_color(*C_GRAY100)
            self.line(cx + 3, y0 + 8.5, cx + card_w - 3, y0 + 8.5)
            
            ry = y0 + 10.5
            for li, (label, value) in enumerate(card["rows"]):
                # Opcional zebra background leve
                if li % 2 == 1:
                    self.set_fill_color(*C_GRAY50)
                    self.rect(cx + 1, ry - 0.5, card_w - 2, 5.5, style="F")

                self.set_xy(cx + 3, ry)
                self.set_font("Helvetica", "", 8.5)
                self.set_text_color(*C_GRAY600)
                self.cell(card_w / 2, 5, label, border=0)

                self.set_font("Helvetica", "B", 8.5)
                self.set_text_color(*C_GRAY900)
                self.cell(card_w / 2 - 6, 5, value, border=0, align="R")
                ry += 6
                
        self.set_y(y0 + card_h + 8)

    def solicitacoes_2col(self, rows_m: list, rows_v: list):
        half_w = (IW - 8) / 2
        y0 = self.get_y()
        
        # Altura estimada
        max_rows = max(len(rows_m), len(rows_v), 1)
        est_h = 6 + 6 + max_rows * 6.5 + 4
        if y0 + est_h > self.h - MB:
            self.add_page()
            y0 = self.get_y()
            
        # Desenhar lado esquerdo (Flexão)
        self.set_xy(ML, y0)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*C_GRAY700)
        self.cell(half_w, 6, "Momentos Fletores (Md)", border=0)
        
        fy = y0 + 6
        self.set_fill_color(*C_GRAY50)
        self.set_draw_color(*C_GRAY200)
        self.set_line_width(0.3)
        self.rect(ML, fy, half_w, 6, style="FD")
        
        self.set_xy(ML + 3, fy + 0.5)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*C_GRAY500)
        self.cell(20, 5, "TRECHO", border=0)
        self.cell(half_w - 44, 5, "Md (kN.m)", border=0, align="R")
        self.cell(21, 5, "STATUS", border=0, align="R")
        
        ry = fy + 6
        if not rows_m:
            self.set_xy(ML, ry)
            self.set_fill_color(*C_WHITE)
            self.rect(ML, ry, half_w, 18, style="FD")
            self.set_xy(ML + 3, ry + 6)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*C_GRAY400)
            self.cell(half_w - 6, 5, "Nenhum momento fletor calculado.", border=0, align="C")
            max_y_left = ry + 18
        else:
            for ri, (trecho, valor, ok) in enumerate(rows_m):
                # Zebra
                self.set_fill_color(*C_WHITE if ri % 2 == 0 else C_GRAY50)
                self.rect(ML, ry, half_w, 6.5, style="FD")
                
                self.set_xy(ML + 3, ry + 0.8)
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*C_GRAY900)
                self.cell(20, 5, trecho, border=0)
                
                # Fonte mono para valores matemáticos
                self.set_font("Courier", "B", 8.5)
                self.set_text_color(*C_GRAY900)
                self.cell(half_w - 44, 5, valor, border=0, align="R")
                
                # Badge de status
                bx = ML + half_w - 20
                by = ry + 1.2
                self.set_xy(bx, by)
                self._draw_status_badge(bx, by, 16, 4.2, ok)
                
                ry += 6.5
            max_y_left = ry

        # Desenhar lado direito (Cortante)
        rx_start = ML + half_w + 8
        self.set_xy(rx_start, y0)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*C_GRAY700)
        self.cell(half_w, 6, "Forças Cortantes (Vsd)", border=0)
        
        v_fy = y0 + 6
        self.set_fill_color(*C_GRAY50)
        self.set_draw_color(*C_GRAY200)
        self.rect(rx_start, v_fy, half_w, 6, style="FD")
        
        self.set_xy(rx_start + 3, v_fy + 0.5)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*C_GRAY500)
        self.cell(20, 5, "TRECHO", border=0)
        self.cell(half_w - 44, 5, "Vsd (kN)", border=0, align="R")
        self.cell(21, 5, "STATUS", border=0, align="R")
        
        v_ry = v_fy + 6
        if not rows_v:
            self.set_xy(rx_start, v_ry)
            self.set_fill_color(*C_WHITE)
            self.set_draw_color(*C_GRAY200)
            self.rect(rx_start, v_ry, half_w, 18, style="FD")
            self.set_xy(rx_start + 3, v_ry + 6)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(*C_GRAY400)
            self.cell(half_w - 6, 5, "Nenhuma força cortante calculada.", border=0, align="C")
            max_y_right = v_ry + 18
        else:
            for ri, (trecho, valor, ok) in enumerate(rows_v):
                # Zebra
                self.set_fill_color(*C_WHITE if ri % 2 == 0 else C_GRAY50)
                self.rect(rx_start, v_ry, half_w, 6.5, style="FD")
                
                self.set_xy(rx_start + 3, v_ry + 0.8)
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*C_GRAY900)
                self.cell(20, 5, trecho, border=0)
                
                # Fonte mono
                self.set_font("Courier", "B", 8.5)
                self.set_text_color(*C_GRAY900)
                self.cell(half_w - 44, 5, valor, border=0, align="R")
                
                # Badge de status
                bx = rx_start + half_w - 20
                by = v_ry + 1.2
                self.set_xy(bx, by)
                self._draw_status_badge(bx, by, 16, 4.2, ok)
                
                v_ry += 6.5
            max_y_right = v_ry

        self.set_y(max(max_y_left, max_y_right) + 8)

    def _draw_status_badge(self, bx, by, bw, bh, status):
        # desenha o mini card/badge verde ou vermelho
        is_ok = status in ("OK", "SIM", "POSITIVO", True)
        bg = C_GREEN100 if is_ok else C_RED100
        fg = C_GREEN800 if is_ok else C_RED700
        txt = "OK" if is_ok else "ALERTA — verifique detalhes no quadro abaixo"
        
        self.set_fill_color(*bg)
        self.set_draw_color(*fg)
        self.set_line_width(0.15)
        # Cantos levemente arredondados
        self.rect(bx, by, bw, bh, style="FD")
        
        self.set_xy(bx, by - 0.2)
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*fg)
        self.cell(bw, bh, txt, border=0, align="C")
        self.set_line_width(0.2)

    def disclaimer(self):
        y0 = self.get_y()
        bh = 16
        if y0 + bh + 5 > self.h - MB:
            self.add_page()
            y0 = self.get_y()
            
        # Desenha a borda amarela de atenção
        self.set_fill_color(*C_AMBER50)
        self.set_draw_color(*C_AMBER500)
        self.set_line_width(0.4)
        self.rect(ML, y0, IW, bh, style="FD")
        
        # Faixa vertical amarela mais grossa na esquerda (simulando border-l-4)
        self.set_fill_color(*C_AMBER500)
        self.rect(ML, y0, 1.5, bh, style="F")
        
        # Ícone de atenção (vetorial)
        ix = ML + 4
        iy = y0 + 3
        self.set_draw_color(*C_AMBER500)
        self.set_line_width(0.5)
        # Triângulo de atenção
        self.line(ix + 2.5, iy, ix, iy + 5)
        self.line(ix + 2.5, iy, ix + 5, iy + 5)
        self.line(ix, iy + 5, ix + 5, iy + 5)
        # Ponto de exclamação
        self.line(ix + 2.5, iy + 1.5, ix + 2.5, iy + 3.5)
        self.line(ix + 2.5, iy + 4.5, ix + 2.5, iy + 4.6)
        
        self.set_xy(ML + 12, y0 + 1.5)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*C_AMBER800)
        self.cell(IW - 16, 3.5, "Aviso de Responsabilidade Técnica", border=0)
        
        self.set_xy(ML + 12, y0 + 5)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*C_AMBER800)
        self.multi_cell(IW - 16, 2.8,
            "As informações contidas neste relatório são geradas automaticamente para fins de "
            "pré-dimensionamento e apoio. Cabe exclusivamente ao engenheiro responsável a "
            "verificação manual, interpretação e validação dos resultados apresentados, "
            "garantindo a conformidade com a ABNT NBR 6118:2023 e as peculiaridades específicas do projeto estrutural.")
        
        self.set_y(y0 + bh + 3)

    def tabela_flexao(self, headers: list, rows: list, col_widths: list):
        y0 = self.get_y()
        row_h = 8
        header_h = 10
        total_w = sum(col_widths)
        
        est_h = header_h + len(rows) * row_h
        if y0 + est_h > self.h - MB:
            self.add_page()
            y0 = self.get_y()
            
        # Linha superior e inferior do Header
        self.set_fill_color(*C_GRAY100)
        self.set_draw_color(*C_GRAY300)
        self.set_line_width(0.3)
        self.rect(ML, y0, total_w, header_h, style="F")
        
        # Borda inferior dupla ou mais forte no header
        self.line(ML, y0, ML + total_w, y0)
        self.line(ML, y0 + header_h, ML + total_w, y0 + header_h)
        
        cx = ML
        for i, text in enumerate(headers):
            is_last = (i == len(headers) - 1)
            
            # Se for a coluna adotada (última), destacar em azul suave conforme o HTML
            if is_last:
                self.set_fill_color(*C_BLUE50)
                self.rect(cx, y0, col_widths[i], header_h, style="F")
                self.set_font("Helvetica", "B", 7.5)
                self.set_text_color(*C_PORTICA)
            else:
                self.set_font("Helvetica", "B", 7.5)
                self.set_text_color(*C_GRAY700)
                
            self.set_xy(cx, y0 + 1)
            
            # Lidar com duas linhas de texto no header se necessário (ex: Md (kN.m))
            if " " in text and ("(" in text or "A" in text or "M" in text):
                partes = text.split(" ")
                self.cell(col_widths[i], 4, partes[0], border=0, align="C" if i > 0 else "L")
                self.set_xy(cx, y0 + 5)
                self.set_font("Helvetica", "", 6.5)
                self.set_text_color(*C_GRAY500)
                self.cell(col_widths[i], 4, partes[1], border=0, align="C" if i > 0 else "L")
            else:
                self.cell(col_widths[i], 8, text, border=0, align="C" if i > 0 else "L")
                
            cx += col_widths[i]
            
        # Adicionar linha grossa azul na última coluna superior
        last_col_x = ML + sum(col_widths[:-1])
        self.set_draw_color(*C_PORTICA)
        self.set_line_width(0.6)
        self.line(last_col_x, y0 + header_h, last_col_x + col_widths[-1], y0 + header_h)
        self.set_line_width(0.2)
        
        # Linhas do corpo
        ry = y0 + header_h
        for ri, row in enumerate(rows):
            # Zebra
            if ri % 2 == 1:
                self.set_fill_color(*C_GRAY50)
                self.rect(ML, ry, sum(col_widths[:-1]), row_h, style="F")
                
            # Adotada em azul suave sempre
            self.set_fill_color(*C_BLUE50)
            self.rect(last_col_x, ry, col_widths[-1], row_h, style="F")
            
            # Desenha borda inferior da linha
            self.set_draw_color(*C_GRAY200)
            self.line(ML, ry + row_h, ML + total_w, ry + row_h)
            
            cx = ML
            for ci, cell in enumerate(row):
                is_last = (ci == len(row) - 1)
                
                self.set_xy(cx, ry + 1.5)
                if ci == 0:
                    self.set_font("Helvetica", "B", 8.5)
                    self.set_text_color(*C_GRAY800)
                    self.cell(col_widths[ci], 5, str(cell), border=0, align="L")
                elif ci == 1:
                    self.set_font("Helvetica", "", 7.5)
                    self.set_text_color(*C_GRAY500)
                    self.cell(col_widths[ci], 5, str(cell), border=0, align="C")
                elif is_last:
                    self.set_font("Helvetica", "B", 9)
                    self.set_text_color(*C_PORTICA)
                    self.cell(col_widths[ci], 5, str(cell), border=0, align="R")
                else:
                    self.set_font("Courier", "", 8.5)
                    self.set_text_color(*C_GRAY900)
                    self.cell(col_widths[ci], 5, str(cell), border=0, align="C")
                    
                cx += col_widths[ci]
            ry += row_h
            
        self.set_y(ry + 8)

    def validacoes_grid(self, items: list):
        if not items:
            return
            
        y0 = self.get_y()
        row_h = 6.5
        n_rows = math.ceil(len(items) / 2)
        box_h = n_rows * row_h + 8
        
        if y0 + box_h > self.h - MB:
            self.add_page()
            y0 = self.get_y()
            
        self.set_fill_color(*C_WHITE)
        self.set_draw_color(*C_GRAY200)
        self.set_line_width(0.3)
        self.rect(ML, y0, IW, box_h, style="FD")
        
        self.set_xy(ML + 4, y0 + 2.5)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*C_GRAY500)
        self.cell(IW - 8, 4, "VALIDAÇÕES NORMATIVAS (NBR 6118)", border=0)
        
        self.set_draw_color(*C_GRAY100)
        self.line(ML + 4, y0 + 6.5, ML + IW - 4, y0 + 6.5)
        
        half_w = (IW - 12) / 2
        for i, (label, status) in enumerate(items):
            col = i % 2
            row_i = i // 2
            
            cx = ML + 4 + col * (half_w + 4)
            cy = y0 + 8.5 + row_i * row_h
            
            ok = status in ("SIM", "OK", "POSITIVO", True)
            color = C_GREEN800 if ok else C_RED700
            
            # Desenha linha divisória interna horizontal
            if row_i > 0 and col == 0:
                self.set_draw_color(*C_GRAY50)
                self.line(ML + 4, cy - 0.5, ML + IW - 4, cy - 0.5)
                
            self.set_xy(cx, cy)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*C_GRAY600)
            self.cell(half_w - 20, 5, label, border=0)
            
            # Badge "SIM" ou "NÃO"
            bx = cx + half_w - 18
            by = cy + 0.4
            
            self.set_fill_color(*(C_GREEN100 if ok else C_RED100))
            self.set_draw_color(*color)
            self.set_line_width(0.1)
            self.rect(bx, by, 16, 4.2, style="FD")
            
            self.set_xy(bx, by - 0.2)
            self.set_font("Helvetica", "B", 6)
            self.set_text_color(*color)
            self.cell(16, 4.2, "SIM" if ok else "NÃO", border=0, align="C")
            
        self.set_y(y0 + box_h + 8)

    def assinatura_bloco(self):
        if not self._nome_engenheiro:
            return
        
        if self.get_y() + 30 > self.h - MB:
            self.add_page()
            
        self.ln(10)
        y = self.get_y()
        cx = ML + (IW - 100) / 2
        
        self.set_draw_color(*C_GRAY300)
        self.set_line_width(0.3)
        self.line(cx, y, cx + 100, y)
        
        self.ln(2)
        self.set_xy(cx, y + 1)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*C_GRAY900)
        self.cell(100, 5, self.normalize_text(f"{self._profissao}: {self._nome_engenheiro}"), border=0, align="C", new_x="LMARGIN", new_y="NEXT")
        
        if self._crea:
            rotulo = "CREA" if self._profissao == "Engenheiro Civil" else "CAU" if self._profissao == "Arquiteto" else "Reg."
            self.set_x(cx)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*C_GRAY500)
            self.cell(100, 4, self.normalize_text(f"CREA/UF: {self._crea}"), border=0, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def add_memoria_calculo(
        self,
        resultados_flexao,
        resultados_cisalhamento,
        section_num,
        h_cm, bw_cm, cob_mm,
        fck_mpa, fyk_mpa, fyk_estribo_mpa,
        phi_estribo_mm, phi_barra_mm,
        is_t=False,
        bf_cm=None, hf_cm=None,
    ):
        self.add_page()
        self.section_title(section_num, "Memória de Cálculo Detalhada (Apêndice)")
        
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*C_GRAY700)
        self.multi_cell(0, 5, self.normalize_text(
            "Esta seção apresenta o detalhamento passo-a-passo dos cálculos efetuados para o dimensionamento "
            "das armaduras longitudinais (flexão) e transversais (cisalhamento) sob as diretrizes da ABNT NBR 6118:2023."
        ))
        self.ln(4)
        
        # ── MEMÓRIA DE FLEXÃO ──
        if resultados_flexao:
            self.set_font("Helvetica", "B", 10.5)
            self.set_text_color(*C_PORTICA)
            self.cell(0, 6, self.normalize_text("A. Dimensionamento à Flexão"), border=0, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
            
            for i, r in enumerate(resultados_flexao):
                if r is None:
                    continue
                
                # Cabeçalho do Trecho
                self.set_fill_color(*C_GRAY50)
                self.set_draw_color(*C_GRAY200)
                self.rect(ML, self.get_y(), IW, 7, style="FD")
                self.set_x(ML + 3)
                self.set_font("Helvetica", "B", 9)
                self.set_text_color(*C_GRAY900)
                self.cell(0, 7, self.normalize_text(f"Trecho {i+1} — Momento Fletor Md = {r.momento_kNm:.2f} kN.m ({r.tipo})"), border=0, new_x="LMARGIN", new_y="NEXT")
                self.ln(2)
                
                # Vamos escrever as equações com Courier
                self.set_font("Courier", "", 8.5)
                self.set_text_color(*C_GRAY900)
                
                d_lin = cob_mm / 10 + phi_estribo_mm / 10 + r.diametro_mm / 20
                d_cm = h_cm - d_lin
                
                lines = [
                    f"1. Altura util (d):",
                    f"   d' = cobrimento + phi_estribo + phi_barra/2",
                    f"   d' = {cob_mm/10:.2f} + {phi_estribo_mm/10:.2f} + {r.diametro_mm/20:.2f} = {d_lin:.2f} cm",
                    f"   d  = h - d' = {h_cm:.1f} - {d_lin:.2f} = {d_cm:.2f} cm",
                    f""
                ]
                
                b_calc = bw_cm
                b_label = "bw"
                if is_t:
                    if r.tipo == "POSITIVO":
                        b_calc = r.bf_efetivo_cm if hasattr(r, "bf_efetivo_cm") else bf_cm
                        b_label = "bf_efet"
                    else:
                        b_calc = bw_cm
                        b_label = "bw"
                        
                Md_kNcm = r.momento_kNm * 100
                
                lines.extend([
                    f"2. Parametro Kc (NBR 6118):",
                    f"   Kc = ({b_label} * d^2) / Md",
                    f"   Kc = ({b_calc:.1f} * {d_cm:.2f}^2) / {Md_kNcm:.1f} = {r.kc:.3f}",
                    f""
                ])
                
                fck_conv = fck_mpa / 10
                lines.extend([
                    f"3. Relacao da linha neutra (beta_x = x/d):",
                    f"   Equacao: -0.192 * fck_conv * Kc * beta_x^2 + 0.48 * fck_conv * Kc * beta_x - 1 = 0",
                    f"   Onde fck_conv = fck/10 = {fck_conv:.1f} kN/cm^2",
                    f"   Substituindo os valores:",
                    f"   {r.a:.4f} * beta_x^2 + {r.b:.4f} * beta_x - 1 = 0",
                    f"   Resolvendo a equacao quadratica:",
                    f"   beta_x = {r.bx:.3f}",
                    f"   x = beta_x * d = {r.bx:.3f} * {d_cm:.2f} = {r.x_cm:.2f} cm",
                    f"   Verificacao de dominio: beta_x = {r.bx:.3f} <= beta_x_lim = {0.45 if fck_mpa <= 50 else 0.35:.2f} ({'PASSA' if r.bx_passa == 'SIM' else 'ALERTA'})",
                    f""
                ])
                
                fyd = fyk_mpa / 1.15
                lines.extend([
                    f"4. Area de aco necessaria (As,req):",
                    f"   Ks = 1 / (fyd * (1 - 0.5 * beta_x))",
                    f"   Ks = 1 / ({fyd:.3f} * (1 - 0.5 * {r.bx:.3f})) = {r.ks:.3f} cm^2/kN",
                    f"   As,req = Ks * Md / d",
                    f"   As,req = {r.ks:.3f} * {Md_kNcm:.1f} / {d_cm:.2f} = {r.as_req_cm2:.2f} cm^2",
                    f""
                ])
                
                c_cm = cob_mm / 10
                est_cm = phi_estribo_mm / 10
                if is_t and r.tipo == "NEGATIVO":
                    b_disponivel = bf_cm if bf_cm is not None else bw_cm
                else:
                    b_disponivel = bw_cm
                espaco_disp_local = b_disponivel - 2 * c_cm - 2 * est_cm
                
                if r.qtd_barras <= 1:
                    eh_val = espaco_disp_local - (r.diametro_mm / 10)
                else:
                    eh_1 = (espaco_disp_local - r.qtd_barras * (r.diametro_mm / 10)) / (r.qtd_barras - 1)
                    if eh_1 >= 1.95:
                        eh_val = eh_1
                    else:
                        n_max_layer = math.ceil(r.qtd_barras / 2)
                        if n_max_layer <= 1:
                            eh_val = espaco_disp_local - (r.diametro_mm / 10)
                        else:
                            eh_val = (espaco_disp_local - n_max_layer * (r.diametro_mm / 10)) / (n_max_layer - 1)
                
                eh_suportado_val = getattr(r, "eh_suportado", eh_val)

                lines.extend([
                    f"5. Armadura minima e adotada (NBR 6118):",
                    f"   As,min = rho_min * Ac",
                    f"   As,min = {r.asmin_cm2:.2f} cm^2 (rho_min = {r.asmin_cm2 / (bw_cm * h_cm) * 100:.3f}%)",
                    f"   As,adot = max(As,req, As,min) = {r.as_usado_cm2:.2f} cm^2",
                    f"   Bitola escolhida: phi = {r.diametro_mm:g} mm (Area = {area_barra(r.diametro_mm):.3f} cm^2)",
                    f"   Quantidade de barras: N = {r.qtd_barras} barras (As = {r.qtd_barras * area_barra(r.diametro_mm):.2f} cm^2)",
                    f"   Espacamento horizontal livre: eh = {eh_suportado_val:.2f} cm (min 2.0 cm - {'CABE' if r.eh_passa == 'SIM' else 'ALERTA'})",
                ])
                
                if r.requer_pele:
                    lines.extend([
                        f"",
                        f"6. Armadura de pele lateral (h >= 60 cm):",
                        f"   As,pele,min/face = 0.10% * Ac,alma (limitado a 5.0 cm^2/m por face)",
                        f"   As,pele,min/face = {r.as_pele_min_face_cm2:.2f} cm^2 (por face lateral)",
                        f"   Adotado: {r.n_barras_pele_face}x phi {r.phi_pele_mm:g} mm por face (As = {r.as_pele_face_cm2:.2f} cm^2/face)",
                        f"   Espacamento maximo vertical: s_max = min(20 cm, d/3) = {r.s_pele_max_cm:.1f} cm",
                        f"   Espacamento adotado: s = {r.s_pele_cm:.1f} cm <= {r.s_pele_max_cm:.1f} cm (OK)",
                    ])
                    
                for line in lines:
                    if self.get_y() + 4.5 > self.h - MB:
                        self.add_page()
                    self.cell(0, 4.2, self.normalize_text(line), border=0, new_x="LMARGIN", new_y="NEXT")
                    
                self.ln(6)

        # ── MEMÓRIA DE CISALHAMENTO ──
        if resultados_cisalhamento:
            if self.get_y() + 40 > self.h - MB:
                self.add_page()
            else:
                self.ln(4)
                
            self.set_font("Helvetica", "B", 10.5)
            self.set_text_color(*C_PORTICA)
            self.cell(0, 6, self.normalize_text("B. Dimensionamento ao Cisalhamento (Modelo I - NBR 6118)"), border=0, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
            
            for i, r in enumerate(resultados_cisalhamento):
                if r is None:
                    continue
                
                self.set_fill_color(*C_GRAY50)
                self.set_draw_color(*C_GRAY200)
                self.rect(ML, self.get_y(), IW, 7, style="FD")
                self.set_x(ML + 3)
                self.set_font("Helvetica", "B", 9)
                self.set_text_color(*C_GRAY900)
                self.cell(0, 7, self.normalize_text(f"Trecho {i+1} — Força Cortante Vk = {r.vsd_verdadeiro_kn:.2f} kN (Majorada Vsd = {r.vsd_kn:.2f} kN)"), border=0, new_x="LMARGIN", new_y="NEXT")
                self.ln(2)
                
                self.set_font("Courier", "", 8.5)
                self.set_text_color(*C_GRAY900)
                
                d_lin = cob_mm / 10 + phi_estribo_mm / 10 + phi_barra_mm / 20
                d_cm = h_cm - d_lin
                
                lam = min(0.80, 1.0 - fck_mpa / 250.0)
                fcd = 0.85 * fck_mpa / 1.4
                
                fctm = 0.30 * fck_mpa ** (2 / 3)
                fctkinf = 0.7 * fctm
                fctd = fctkinf / 10 / 1.4
                
                vrd2 = 0.27 * lam * fcd * bw_cm * d_cm / 10
                vc = 0.6 * fctd * bw_cm * d_cm
                vsw = r.vsd_kn - vc if r.vsd_kn > vc else 0
                fywd = fyk_estribo_mpa / 1.15
                
                if vsw > 0 and fywd > 0 and d_cm > 0:
                    asw_req_m = (vsw / (fywd * d_cm)) * 100
                else:
                    asw_req_m = 0.0
                    
                area_estribo = area_barra(r.diam_estribo_mm)
                asw_ramo = area_estribo * 2
                
                lines = [
                    f"1. Resistencia do concreto comprimido (Vrd2):",
                    f"   Vrd2 = 0.27 * lambda * fcd * bw * d",
                    f"   lambda = 1 - fck/250 (max 0.80) = {lam:.2f}",
                    f"   fcd = 0.85 * {fck_mpa:g} / 1.4 = {fcd:.2f} MPa = {fcd/10:.3f} kN/cm^2",
                    f"   Vrd2 = 0.27 * {lam:.2f} * {fcd/10:.3f} * {bw_cm:.1f} * {d_cm:.2f} = {vrd2:.2f} kN",
                    f"   Verificacao da biela de compressao: Vsd = {r.vsd_kn:.2f} kN < Vrd2 = {vrd2:.2f} kN ({'PASSA' if r.passa_vrd2 == 'SIM' else 'ALERTA'})",
                    f"",
                    f"2. Parcela resistida pelo concreto (Vc):",
                    f"   Vc = 0.6 * fctd * bw * d",
                    f"   fctkinf = 0.7 * 0.3 * fck^(2/3) = {fctkinf:.2f} MPa = {fctkinf/10:.3f} kN/cm^2",
                    f"   fctd = fctkinf / 1.4 = {fctd:.5f} kN/cm^2",
                    f"   Vc = 0.6 * {fctd:.5f} * {bw_cm:.1f} * {d_cm:.2f} = {vc:.2f} kN",
                    f"",
                    f"3. Parcela a ser resistida pelos estribos (Vsw):",
                    f"   Vsw = Vsd - Vc = {r.vsd_kn:.2f} - {vc:.2f} = {vsw:.2f} kN",
                    f"",
                    f"4. Calculo da armadura transversal (Asw/s):",
                    f"   Asw/s,req = Vsw / (fywd * d)",
                    f"   fywd = fyk_estribo / 1.15 = {fyk_estribo_mpa:g} / 1.15 = {fywd:.2f} kN/cm^2",
                    f"   Asw/s,req = {vsw:.2f} / ({fywd:.2f} * {d_cm:.2f}) * 100 = {asw_req_m:.3f} cm^2/m",
                    f"   Asw/s,min = {r.asw_s_min_cm2_m:.3f} cm^2/m",
                    f"   Asw/s,adot = max(Asw/s,req, Asw/s,min) = {r.asw_usado_cm2_m:.3f} cm^2/m",
                    f"   Bitola adotada: phi = {r.diam_estribo_mm:g} mm (Area de 2 ramos = {asw_ramo:.3f} cm^2)",
                    f"   Espacamento calculado: s = (Asw,ramo * 100) / Asw/s,adot",
                    f"   s = ({asw_ramo:.3f} * 100) / {r.asw_usado_cm2_m:.3f} = {r.dist_estribos_cm:.1f} cm",
                ]
                
                for line in lines:
                    if self.get_y() + 4.5 > self.h - MB:
                        self.add_page()
                    self.cell(0, 4.2, self.normalize_text(line), border=0, new_x="LMARGIN", new_y="NEXT")
                    
                self.ln(6)


def _desenhar_grampos_segunda_camada(
    pdf: PorticaPDF,
    n_camada: int,
    phi_barra: float,
    phi_estribo: float,
    x_left: float,
    x_right: float,
    y_bar: float,
    s: float,
    fechado_para_cima: bool,
) -> int:
    """Desenha um grampo suplementar contínuo na largura do estribo, ao nível da 2ª camada.

    NBR 6118:18.3.2.3: quando a 2ª camada tem 3+ barras, há barras
    intermediárias que não estão encostadas no estribo principal e "voariam"
    durante a concretagem. Um único grampo (estribo complementar) é desenhado
    na MESMA LARGURA do estribo principal, ao nível da 2ª camada.

    Visual: U aberto (3 lados de um retângulo) em laranja, com a mesma
    largura do estribo principal (suas laterais coincidem com as laterais
    do estribo). A parte fechada do U fica do lado da 1ª camada (onde o
    grampo é "amarrado"); a boca aberta fica do lado da face do concreto.
    As pernas têm comprimento 2 × grampo_off (passam pela barra) — a barra
    fica dentro do U.

    Args:
        pdf: Instância PorticaPDF.
        n_camada: número de barras na 2ª camada.
        phi_barra: diâmetro das barras (mm).
        phi_estribo: diâmetro do estribo (mm) — também usado para o grampo.
        x_left: X esquerdo do grampo (= X do lado esquerdo do estribo).
        x_right: X direito do grampo (= X do lado direito do estribo).
        y_bar: Y do centro das barras em coordenadas PDF (Y cresce para baixo).
        s: fator de escala (mm → unidades PDF).
        fechado_para_cima: True se o U é fechado em cima (menor Y, ∩).
                           Usado para 2ª camada de barras SUPERIORES (cuja
                           1ª camada está acima). False se fechado embaixo
                           (maior Y, ∪), para 2ª camada de barras INFERIORES
                           (cuja 1ª camada está abaixo).

    Returns:
        1 se o grampo foi desenhado, 0 se n_camada < 3 (nada a grampar).
    """
    if n_camada <= 2:
        return 0  # sem barras intermediárias; nada a grampar

    # Offset do grampo em relação ao centro da barra — mesmo offset que o
    # estribo principal tem em relação à 1ª camada (phi_estribo/2 + phi_barra/2).
    grampo_off = (phi_estribo / 2 + phi_barra / 2) * s

    # Y range das pernas: passam pela barra. Comprimento total 2*grampo_off,
    # de modo que a barra fique exatamente no meio do U (wrapped).
    y_step = 2 * grampo_off

    pdf.set_draw_color(197, 90, 17)   # laranja (Orange800), igual à armadura de pele
    pdf.set_line_width(0.5)

    if fechado_para_cima:
        # ∩ : fechado em cima (menor Y, lado da 1ª camada superior),
        # aberto embaixo (lado da face do concreto).
        y_closed = y_bar - grampo_off
        y_open = y_closed + y_step   # = y_bar + grampo_off (passa pela barra)
        pdf.line(x_left, y_closed, x_right, y_closed)   # topo (fechado)
        pdf.line(x_left, y_closed, x_left, y_open)      # lateral esq (passa pela barra)
        pdf.line(x_right, y_closed, x_right, y_open)    # lateral dir (passa pela barra)
    else:
        # ∪ : fechado embaixo (maior Y, lado da 1ª camada inferior),
        # aberto em cima (lado da face do concreto).
        y_closed = y_bar + grampo_off
        y_open = y_closed - y_step   # = y_bar - grampo_off (passa pela barra)
        pdf.line(x_left, y_closed, x_right, y_closed)   # base (fechada)
        pdf.line(x_left, y_closed, x_left, y_open)      # lateral esq (passa pela barra)
        pdf.line(x_right, y_closed, x_right, y_open)    # lateral dir (passa pela barra)

    return 1


def _desenhar_nota_cavaletes(pdf: PorticaPDF, x: float, y: float, largura: float = 180.0) -> None:
    """Desenha nota sobre uso de cavaletes quando há 2ª camada de armadura.

    O grampo (U-shape) no esquema previne deslocamento LATERAL das barras
    da 2ª camada, mas não previne deslocamento VERTICAL (afundamento sob
    o peso do concreto fresco). Em obra, esse travamento vertical é feito
    por cavaletes de aço posicionados a cada ~1,0 m ao longo da viga.

    Aparece apenas quando há 2ª camada com 3+ barras (condição para grampo).
    O desenho esquemático omite os cavaletes por simplificação.
    """
    texto = (
        "NOTA: O desenho esquemático omite os espaçadores verticais. "
        "Utilizar cavaletes de aço a cada 1,0 m para garantir o "
        "espaçamento vertical (e_v) normativo entre as camadas."
    )

    pdf.set_draw_color(*C_GRAY400)
    pdf.set_line_width(0.3)
    pdf.set_fill_color(255, 250, 230)
    pdf.rect(x, y, largura, 14, style="FD")

    pdf.set_xy(x + 3, y + 2.5)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(120, 80, 20)
    pdf.cell(12, 4, "NOTA:", border=0)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(*C_GRAY700)
    pdf.cell(largura - 18, 4, " O desenho esquemático omite os espaçadores verticais.",
             border=0, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x + 3)
    pdf.cell(largura - 6, 4,
             "Utilizar cavaletes de aço a cada 1,0 m para garantir o espaçamento "
             "vertical (e_v) normativo entre as camadas.",
             border=0)


def _split_layers(n_barras, phi_mm, bw_cm, cob_mm, phi_est_mm, d_max_agregado_mm=19.0):
    """Retorna o número de barras na camada 1 e na camada 2 para fins de desenho visual."""
    if n_barras <= 1:
        return n_barras, 0
    espaco = bw_cm - 2 * (cob_mm / 10) - 2 * (phi_est_mm / 10)
    
    # NBR 6118: eh_lim = max(2.0 cm, phi, 1.2 * d_max_agregado)
    eh_lim = max(2.0, phi_mm / 10, 1.2 * d_max_agregado_mm / 10)
    
    h_space = espaco * 10.0
    eh_min = eh_lim * 10.0
    if phi_mm > h_space:
        return 1, n_barras - 1
        
    n_max = max(1, int(math.floor((h_space - phi_mm) / (phi_mm + eh_min)) + 1))
    
    if n_barras <= n_max:
        return n_barras, 0
        
    layers = []
    remaining = n_barras
    while remaining > 0:
        count = min(remaining, n_max)
        layers.append(count)
        remaining -= count
        
    if len(layers) >= 2 and layers[-1] == 1 and layers[-2] > 2:
        layers[-1] += 1
        layers[-2] -= 1
        
    c1 = layers[0]
    c2 = sum(layers[1:])
    return c1, c2


def desenhar_secao_retangular(pdf: PorticaPDF, h_cm: float, bw_cm: float, cob_mm: float, phi_estribo: float,
                               phi_barra_inf: float, n_barras_inf: int,
                               phi_barra_sup: float, n_barras_sup: int,
                               n_barras_pele: int = 0, phi_pele: float = 0,
                               layout_convergido=None):
    max_h_mm, max_w_mm = 80, 50
    s = min(max_h_mm / (h_cm * 10), max_w_mm / (bw_cm * 10), 0.5)
    dw = bw_cm * 10 * s
    dh = h_cm * 10 * s
    px = ML + 25
    py = pdf.get_y() + 6

    pdf.set_fill_color(243, 244, 246)
    pdf.set_draw_color(*C_GRAY300)
    pdf.set_line_width(0.4)
    pdf.rect(px, py, dw, dh, style="FD")

    e_off = (cob_mm + phi_estribo / 2) * s
    pdf.set_draw_color(*C_PORTICA)
    pdf.set_line_width(0.6)
    pdf.rect(px + e_off, py + e_off, dw - 2 * e_off, dh - 2 * e_off, style="D")

    pdf.set_fill_color(31, 41, 55)
    pdf.set_draw_color(255, 255, 255)
    pdf.set_line_width(0.15)

    def _bars(n, phi, yc, ref_x, ref_w):
        if n <= 0:
            return
        r = max(phi * s * 0.65, 0.5)
        bar_off = (phi_estribo / 2 + phi / 2) * s
        avail = max(ref_w - 2 * (e_off + bar_off), 0)
        if n == 1 or avail <= 0:
            xs = [ref_x + ref_w / 2]
        else:
            xs = [ref_x + e_off + bar_off + i * avail / (n - 1) for i in range(n)]
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.15)
        for x in xs:
            pdf.ellipse(x - r, yc - r, r * 2, r * 2, style="FD")

    n_ic1, n_ic2 = _split_layers(n_barras_inf, phi_barra_inf, bw_cm, cob_mm, phi_estribo)
    n_sc1, n_sc2 = _split_layers(n_barras_sup, phi_barra_sup, bw_cm, cob_mm, phi_estribo)

    bar_off_inf = (phi_estribo / 2 + phi_barra_inf / 2) * s
    bar_off_sup = (phi_estribo / 2 + phi_barra_sup / 2) * s
    dy_i = py + dh - e_off - bar_off_inf
    dy_s = py + e_off + bar_off_sup
    gap = (max(phi_barra_inf, phi_barra_sup) + 20.0) * s

    x_estribo_left = px + e_off
    x_estribo_right = px + dw - e_off

    _bars(n_sc1, phi_barra_sup, dy_s, px, dw)
    if n_sc2 > 0:
        xs_sc2 = _bars(n_sc2, phi_barra_sup, dy_s + gap, px, dw)
        _desenhar_grampos_segunda_camada(
            pdf, n_sc2, phi_barra_sup, phi_estribo,
            x_estribo_left, x_estribo_right,
            dy_s + gap, s, fechado_para_cima=True,
        )

    if layout_convergido:
        r_inf = max(phi_barra_inf * s * 0.65, 0.5)
        pdf.set_fill_color(31, 41, 55)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.15)
        for bar in layout_convergido.bar_positions:
            if bar.is_corner_bar:
                continue
            if bar.layer >= 0:
                x_c = px + bar.x * s
                y_c = py + dh - bar.y * s
                pdf.ellipse(x_c - r_inf, y_c - r_inf, r_inf * 2, r_inf * 2, style="FD")
        
        for layer in layout_convergido.layers:
            if layer.index >= 1 and layer.bar_count >= 3:
                y_layer_c = py + dh - layer.y_centroid * s
                _desenhar_grampos_segunda_camada(
                    pdf, layer.bar_count, phi_barra_inf, phi_estribo,
                    x_estribo_left, x_estribo_right,
                    y_layer_c, s, fechado_para_cima=False,
                )
    else:
        _bars(n_ic1, phi_barra_inf, dy_i, px, dw)
        if n_ic2 > 0:
            xs_ic2 = _bars(n_ic2, phi_barra_inf, dy_i - gap, px, dw)
            _desenhar_grampos_segunda_camada(
                pdf, n_ic2, phi_barra_inf, phi_estribo,
                x_estribo_left, x_estribo_right,
                dy_i - gap, s, fechado_para_cima=False,
            )

    if n_barras_pele > 0 and phi_pele > 0:
        pdf.set_fill_color(197, 90, 17)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.15)
        r_pele = max(phi_pele * s * 0.65, 0.5)
        x_face_esq = px + e_off + (phi_estribo / 2 + phi_pele / 2) * s
        x_face_dir = px + dw - e_off - (phi_estribo / 2 + phi_pele / 2) * s
        
        # Determinar limites brutos (sem gaps) medidos em cm a partir do topo da viga
        layer_count_inf = layout_convergido.layer_count if layout_convergido else (2 if n_ic2 > 0 else 1 if n_barras_inf > 0 else 0)
        layer_count_sup = 2 if n_sc2 > 0 else 1 if n_barras_sup > 0 else 0
        ev_min_inf_mm = layout_convergido.ev_min if (layout_convergido and hasattr(layout_convergido, 'ev_min')) else max(20.0, phi_barra_inf, 22.8)
        ev_min_sup_mm = max(20.0, phi_barra_sup, 22.8)

        y_top_raw_cm = cob_mm / 10.0 + phi_estribo / 10.0
        if layer_count_sup > 0:
            y_top_raw_cm += layer_count_sup * (phi_barra_sup / 10.0) + (layer_count_sup - 1) * (ev_min_sup_mm / 10.0)

        y_bottom_raw_cm = h_cm - (cob_mm / 10.0 + phi_estribo / 10.0)
        if layout_convergido:
            bottom_bars_tops = []
            for bar in layout_convergido.bar_positions:
                if not bar.is_corner_bar and bar.layer >= 0:
                    bottom_bars_tops.append(h_cm - (bar.y + phi_barra_inf / 2.0) / 10.0)
            if bottom_bars_tops:
                y_bottom_raw_cm = min(bottom_bars_tops)
        elif layer_count_inf > 0:
            y_bottom_raw_cm -= layer_count_inf * (phi_barra_inf / 10.0) + (layer_count_inf - 1) * (ev_min_inf_mm / 10.0)

        ev_min_cm = ev_min_inf_mm / 10.0
        h_free_cm = y_bottom_raw_cm - y_top_raw_cm
        phi_pele_cm = phi_pele / 10.0
        d_livre_cm = (h_free_cm - n_barras_pele * phi_pele_cm) / (n_barras_pele + 1.0)

        if d_livre_cm >= ev_min_cm:
            ys_cm = [y_top_raw_cm + (i + 1) * d_livre_cm + (i + 0.5) * phi_pele_cm for i in range(n_barras_pele)]
        else:
            # Fallback
            y_top_estribo = cob_mm / 10.0 + phi_estribo / 10.0
            y_bottom_estribo = h_cm - (cob_mm / 10.0 + phi_estribo / 10.0)
            s_pele_fb = (y_bottom_estribo - y_top_estribo) / (n_barras_pele + 1.0)
            ys_cm = [y_top_estribo + (i + 1) * s_pele_fb for i in range(n_barras_pele)]

        for face_x in [x_face_esq, x_face_dir]:
            for y_bar_cm in ys_cm:
                y_bar = py + y_bar_cm * 10.0 * s
                pdf.ellipse(face_x - r_pele, y_bar - r_pele, r_pele * 2, r_pele * 2, style="FD")

    pdf.set_draw_color(*C_GRAY400)
    pdf.set_line_width(0.2)

    cy = py + dh + 4
    pdf.line(px, cy, px + dw, cy)
    pdf.line(px, cy - 1, px, cy + 1)
    pdf.line(px + dw, cy - 1, px + dw, cy + 1)
    pdf.set_xy(px, cy + 1.2)
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(*C_GRAY600)
    pdf.cell(dw, 4, f"bw={bw_cm:g} cm", border=0, align="C")

    cxc = px + dw + 4
    pdf.line(cxc, py, cxc, py + dh)
    pdf.line(cxc - 1, py, cxc + 1, py)
    pdf.line(cxc - 1, py + dh, cxc + 1, py + dh)
    pdf.set_xy(cxc + 1.5, py + dh / 2 - 2)
    pdf.cell(14, 4, f"h={h_cm:g} cm", border=0, align="L")


def desenhar_secao_t(pdf: PorticaPDF, h_cm: float, bw_cm: float, bf_cm: float, hf_cm: float, cob_mm: float, phi_estribo: float,
                      phi_barra_inf: float, n_barras_inf: int, phi_barra_sup: float, n_barras_sup: int,
                      n_barras_pele: int = 0, phi_pele: float = 0, layout_convergido=None):
    s = min(80.0 / (h_cm * 10.0), 60.0 / (bf_cm * 10.0), 0.5)
    h = h_cm * 10.0; bw = bw_cm * 10.0; bf = bf_cm * 10.0; hf = hf_cm * 10.0; c = cob_mm
    ox = ML + 30.0; py = pdf.get_y() + 6; oy = py + h * s
    def sx(x): return ox + x * s
    def sy(y): return oy - y * s

    # 1. Contorno concreto (polígono 8 vértices)
    pdf.set_fill_color(243, 244, 246)
    pdf.rect(sx(-bf/2), sy(h), bf*s, hf*s, style='F')
    pdf.rect(sx(-bw/2), sy(h-hf), bw*s, (h-hf)*s, style='F')
    pdf.set_draw_color(*C_GRAY300)
    pdf.set_line_width(0.4)
    pts = [(-bw/2, 0), (bw/2, 0), (bw/2, h-hf), (bf/2, h-hf), (bf/2, h), (-bf/2, h), (-bf/2, h-hf), (-bw/2, h-hf)]
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i+1)%len(pts)]
        pdf.line(sx(x1), sy(y1), sx(x2), sy(y2))

    # 2. Estribo (usando convenção do sample: ex_start = -bw/2 + c, cover to centerline)
    ex_start = -bw/2 + c
    estribo_w = bw - 2*c
    estribo_h = h - 2*c
    pdf.set_draw_color(*C_PORTICA)
    pdf.set_line_width(0.6)
    pdf.rect(sx(ex_start), sy(c + estribo_h), estribo_w*s, estribo_h*s, style="D")

    # 3. Barras principais
    pdf.set_fill_color(31, 41, 55)
    pdf.set_draw_color(255, 255, 255)
    pdf.set_line_width(0.15)
    def _circle(xc, yc, r):
        pdf.ellipse(xc-r, yc-r, r*2, r*2, style="FD")

    n_i1, n_i2 = _split_layers(n_barras_inf, phi_barra_inf, bw_cm, cob_mm, phi_estribo)
    n_s1, n_s2 = _split_layers(n_barras_sup, phi_barra_sup, bw_cm, cob_mm, phi_estribo)

    gap = (max(phi_barra_inf, phi_barra_sup) + 20) * s
    r_inf = max(phi_barra_inf*s*0.65, 0.5)
    r_sup = max(phi_barra_sup*s*0.65, 0.5)

    # Y das barras (convenção sample: c + phi_est + phi/2)
    y_inf = sy(c + phi_estribo + phi_barra_inf/2)
    y_sup = sy(h - c - phi_estribo - phi_barra_sup/2)

    # X: barras distribuídas dentro do estribo
    x_left = sx(ex_start)
    x_right = sx(ex_start + estribo_w)

    def _bar_xs(n, phi):
        """Retorna lista de X em PDF para n barras de diâmetro phi."""
        if n <= 0: return []
        if n == 1: return [sx(0.0)]
        first = x_left + (phi_estribo + phi/2) * s
        last = x_right - (phi_estribo + phi/2) * s
        return [first + i * (last - first) / (n - 1) for i in range(n)]

    # Draw top bars
    for xs, yc, r in [
        (_bar_xs(n_s1, phi_barra_sup), y_sup, r_sup),
        (_bar_xs(n_s2, phi_barra_sup), y_sup + gap, r_sup),
    ]:
        for x in xs:
            _circle(x, yc, r)

    if n_s2 > 0:
        _desenhar_grampos_segunda_camada(pdf, n_s2, phi_barra_sup, phi_estribo, x_left, x_right, y_sup + gap, s, True)

    # Draw bottom bars
    if layout_convergido:
        pdf.set_fill_color(31, 41, 55)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.15)
        for bar in layout_convergido.bar_positions:
            if bar.is_corner_bar:
                continue
            if bar.layer >= 0:
                x_c = sx(bar.x - layout_convergido.bf / 2.0)
                y_c = sy(bar.y)
                _circle(x_c, y_c, r_inf)
        
        for layer in layout_convergido.layers:
            if layer.index >= 1 and layer.bar_count >= 3:
                y_layer_c = sy(layer.y_centroid)
                _desenhar_grampos_segunda_camada(
                    pdf, layer.bar_count, phi_barra_inf, phi_estribo,
                    x_left, x_right, y_layer_c, s, False
                )
    else:
        for xs, yc, r in [
            (_bar_xs(n_i1, phi_barra_inf), y_inf, r_inf),
            (_bar_xs(n_i2, phi_barra_inf), y_inf - gap, r_inf),
        ]:
            for x in xs:
                _circle(x, yc, r)
        
        if n_i2 > 0:
            _desenhar_grampos_segunda_camada(pdf, n_i2, phi_barra_inf, phi_estribo, x_left, x_right, y_inf - gap, s, False)

    # 4. Armadura de pele (na alma)
    if n_barras_pele > 0 and phi_pele > 0:
        pdf.set_fill_color(197, 90, 17)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.15)
        r_p = max(phi_pele*s*0.65, 0.5)
        x_pe = x_left + (phi_estribo + phi_pele/2)*s
        x_pd = x_right - (phi_estribo + phi_pele/2)*s
        
        # Determinar limites brutos (sem gaps) medidos em mm a partir do fundo da viga
        layer_count_inf = layout_convergido.layer_count if layout_convergido else (2 if n_i2 > 0 else 1 if n_barras_inf > 0 else 0)
        ev_min_inf_mm = layout_convergido.ev_min if (layout_convergido and hasattr(layout_convergido, 'ev_min')) else max(20.0, phi_barra_inf, 22.8)

        y_bottom_raw_mm = cob_mm + phi_estribo
        if layout_convergido:
            bottom_bars_tops = []
            for bar in layout_convergido.bar_positions:
                if not bar.is_corner_bar and bar.layer >= 0:
                    bottom_bars_tops.append(bar.y + phi_barra_inf / 2.0)
            if bottom_bars_tops:
                y_bottom_raw_mm = max(bottom_bars_tops)
        elif layer_count_inf > 0:
            y_bottom_raw_mm += layer_count_inf * phi_barra_inf + (layer_count_inf - 1) * ev_min_inf_mm

        y_top_raw_mm = (h_cm - hf_cm) * 10.0 - (cob_mm + phi_estribo)
        
        ev_min_mm = ev_min_inf_mm
        h_free_mm = y_top_raw_mm - y_bottom_raw_mm
        phi_pele_mm = phi_pele
        d_livre_mm = (h_free_mm - n_barras_pele * phi_pele_mm) / (n_barras_pele + 1.0)

        if d_livre_mm >= ev_min_mm:
            ys_mm = [y_bottom_raw_mm + (i + 1) * d_livre_mm + (i + 0.5) * phi_pele_mm for i in range(n_barras_pele)]
        else:
            # Fallback
            y_top_estribo = (h_cm - hf_cm) * 10.0 - (cob_mm + phi_estribo)
            y_bottom_estribo = cob_mm + phi_estribo
            s_pele_fb = (y_top_estribo - y_bottom_estribo) / (n_barras_pele + 1.0)
            ys_mm = [y_bottom_estribo + (i + 1) * s_pele_fb for i in range(n_barras_pele)]

        for fx in [x_pe, x_pd]:
            for y_bar_domain in ys_mm:
                _circle(fx, sy(y_bar_domain), r_p)

    # 5. Armadura de costura (mesa)
    y_cs = sy(h - c)
    y_ci = sy(h - hf + c)
    x_me = sx(-bf/2 + c)
    x_md = sx(bf/2 - c)
    pdf.set_draw_color(44, 160, 44)
    pdf.set_line_width(0.5)
    pdf.set_dash_pattern(dash=2, gap=2)
    pdf.line(x_me, y_cs, x_md, y_cs)
    pdf.line(x_me, y_ci, x_md, y_ci)
    pdf.set_dash_pattern()

    # 6. Cotas
    pdf.set_draw_color(*C_GRAY400)
    pdf.set_line_width(0.2)
    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(*C_GRAY600)
    y_cota = oy + 4
    pdf.line(sx(-bw/2), y_cota, sx(bw/2), y_cota)
    pdf.set_xy(sx(-bw/2), y_cota + 1.2)
    pdf.cell(bw*s, 4, f"bw={bw_cm:g} cm", border=0, align="C")
    x_ch = sx(bf/2) + 4
    pdf.line(x_ch, sy(h), x_ch, sy(0))
    pdf.set_xy(x_ch + 1.5, sy(h/2) - 2)
    pdf.cell(15, 4, f"h={h_cm:g} cm", border=0, align="L")
    cx_hf = sx(-bf/2) - 4
    pdf.line(cx_hf, sy(h), cx_hf, sy(h - hf))
    pdf.set_xy(cx_hf - 15.5, sy(h - hf/2) - 2)
    pdf.cell(15, 4, f"hf={hf_cm:g} cm", border=0, align="R")
    cy_bf = py - 4
    pdf.line(sx(-bf/2), cy_bf, sx(bf/2), cy_bf)
    pdf.set_xy(sx(-bf/2), cy_bf - 4.5)
    pdf.cell(bf*s, 4, f"bf={bf_cm:g} cm", border=0, align="C")
    cx_c = sx(-bw/2) - 4
    pdf.line(cx_c, sy(0), cx_c, sy(c))
    pdf.set_xy(cx_c - 15.5, sy(c/2) - 2)
    pdf.cell(15, 4, f"c={c/10:.1f} cm", border=0, align="R")
    return None


def _legenda_secao(pdf: PorticaPDF, cob_mm: float, phi_est: float, n_inf: int, phi_inf: float, n_sup: int, phi_sup: float, lx: float, ly: float,
                   n_pele: int = 0, phi_pele: float = 0, tem_grampo: bool = False):
    pdf.set_xy(lx, ly)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*C_GRAY700)
    pdf.cell(80, 5, "Legenda", border=0, new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(*C_GRAY200)
    pdf.line(lx, pdf.get_y(), lx + 70, pdf.get_y())
    pdf.ln(3)

    itens = [
        ("Concreto", f"Cobrimento nom. {cob_mm:g} mm", C_GRAY100, C_GRAY600, False),
        ("Estribo", f"Estribo phi {phi_est:g} mm", C_WHITE, C_PORTICA, True),
        ("Barras Inferiores", f"{n_inf} x phi {_diam(phi_inf)} mm", (31, 41, 55), C_PORTICA, False),
        ("Barras Superiores", f"{n_sup} x phi {_diam(phi_sup)} mm", (31, 41, 55), C_PORTICA, False),
    ]
    if n_pele > 0 and phi_pele > 0:
        itens.append(("Armadura de Pele", f"{n_pele} x phi {_diam(phi_pele)} mm/face", (197, 90, 17), C_PORTICA, False))
    if tem_grampo:
        itens.append(("Grampo Suplementar", f"1 x phi {_diam(phi_est)} mm", (197, 90, 17), (197, 90, 17), True))
    
    for label, detail, fill, color_detail, is_line in itens:
        cy = pdf.get_y()
        pdf.set_xy(lx, cy)
        
        # Desenha marcador
        if is_line:
            pdf.set_draw_color(*color_detail)
            pdf.set_line_width(0.7)
            pdf.line(lx, cy + 2.5, lx + 4, cy + 2.5)
        else:
            pdf.set_fill_color(*fill)
            pdf.set_draw_color(*C_GRAY300)
            pdf.set_line_width(0.15)
            if "Barras" in label or "Pele" in label:
                # Marcador circular
                pdf.ellipse(lx, cy + 1, 3.5, 3.5, style="FD")
            else:
                # Marcador retangular
                pdf.rect(lx, cy + 1, 4, 4, style="FD")
                
        # Texto
        pdf.set_xy(lx + 6, cy)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*C_GRAY600)
        pdf.cell(32, 5, label, border=0)
        
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(*color_detail)
        pdf.cell(35, 5, detail, border=0, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)


def _converter_svg_para_png(svg_path: str) -> Optional[str]:
    """Converte SVG para PNG temporario. Retorna caminho PNG ou None se falhar."""
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        import re

        # Sanitizar dash arrays invalidos (FTOOL gera stroke-dasharray:0
        # em style CSS que rlPyCairo rejeita)
        with open(svg_path, "r", encoding="utf-8", errors="ignore") as f:
            svg_content = f.read()
        svg_clean = svg_content
        # Atributos: stroke-dasharray="..."
        svg_clean = re.sub(r'stroke-dasharray\s*=\s*"[^"]*"', 'stroke-dasharray="1"', svg_clean)
        svg_clean = re.sub(r"stroke-dasharray\s*=\s*'[^']*'", "stroke-dasharray='1'", svg_clean)
        # CSS inline: stroke-dasharray:...
        svg_clean = re.sub(r'stroke-dasharray\s*:\s*[^;"\']+', 'stroke-dasharray:1', svg_clean)

        temp_svg = temp_path(suffix=".svg")
        with open(temp_svg, "w", encoding="utf-8") as f:
            f.write(svg_clean)

        drawing = svg2rlg(temp_svg)
        if drawing is None:
            return None
        png_path = temp_path(suffix=".png")
        renderPM.drawToFile(drawing, png_path, fmt="PNG", dpi=300)

        try:
            os.remove(temp_svg)
        except OSError:
            pass
        return png_path
    except Exception:
        return None


def gerar_relatorio_viga_comum(
    filepath: str,
    *,
    nome_viga: str = "Viga V1",
    h_cm: float, bw_cm: float,
    caa: int,
    fck_mpa: float,
    fyk_mpa: float,
    fyk_estribo_mpa: float,
    phi_estribo_mm: float,
    phi_barra_mm: float,
    resultados_flexao: List[Optional[ResultadoFlexao]],
    resultados_cisalhamento: List[Optional[ResultadoCisalhamento]],
    imagem_ftool: Optional[str] = None,
    gamma_f: float = 1.4,
    dark_mode: bool = False,
    nome_engenheiro: str = "",
    crea: str = "",
    profissao: str = "Engenheiro Civil",
    on_add_diagrams: Optional[Any] = None,
) -> str:
    cob_mm = CAA_DATA[caa]["cobrimento"]
    pdf = PorticaPDF(nome_viga=nome_viga, subtitulo="Viga de Seção Retangular", dark_mode=dark_mode,
                     nome_engenheiro=nome_engenheiro, crea=crea, profissao=profissao)
    pdf.alias_nb_pages()
    
    # ── PÁGINA 1 ──
    pdf.add_page()
    
    # 1. Dados de Entrada
    pdf.section_title(1, "Dados de Entrada")
    # Metadados do projeto (nome da viga, engenheiro, CREA, data)
    # em linha separada ACIMA dos cards, com quebra de linha automatica
    # e largura total (ML a MR), para acomodar nomes longos
    pdf.meta_header()
    pdf.data_cards([
        {"title": "Geometria", "rows": [
            ("Altura (h)", f"{_n(h_cm, 1)} cm"),
            ("Largura (bw)", f"{_n(bw_cm, 1)} cm"),
            ("Cobrimento (c)", f"{cob_mm:g} mm"),
        ]},
        {"title": "Materiais", "rows": [
            ("Classe (CAA)", _caa_nome(caa)),
            ("Concreto (fck)", f"{fck_mpa:g} MPa"),
            ("Aço Long. (fyk)", f"{fyk_mpa:g} kN/cm²"),
            ("Coef. gf", f"{gamma_f:g}"),
        ]},
        {"title": "Bitolas Base", "rows": [
            ("phi Long. Est.", f"{_diam(phi_barra_mm)} mm"),
            ("phi Estribo", f"{_diam(phi_estribo_mm)} mm"),
        ]},
    ])
    
    # 2. Solicitações de Cálculo
    pdf.section_title(2, "Solicitações de Cálculo")
    
    rows_m = []
    for i, r in enumerate(resultados_flexao):
        if r is None:
            continue
        sinal = "+" if r.tipo == "POSITIVO" else "-"
        rows_m.append((f"Trecho {i+1}", f"{sinal}{_n(abs(r.momento_kNm), 2)}", r.bx_passa == "SIM"))
        
    rows_v = []
    for i, r in enumerate(resultados_cisalhamento):
        if r is None:
            continue
        rows_v.append((f"Trecho {i+1}", f"{_n(r.vsd_kn, 2)}", r.passa_vrd2 == "SIM"))
        
    pdf.solicitacoes_2col(rows_m, rows_v)
    
    # Imagem do Ftool se houver (fica na página 1 se couber, senão empurra)
    if imagem_ftool and os.path.exists(imagem_ftool):
        # Converter SVG para PNG se necessario
        img_path = imagem_ftool
        png_temp = None
        if imagem_ftool.lower().endswith(".svg"):
            png_temp = _converter_svg_para_png(imagem_ftool)
            if png_temp:
                img_path = png_temp

        # Reservar espaço mínimo
        if pdf.get_y() + 75 > pdf.h - MB:
            pdf.add_page()
            
        y_img = pdf.get_y()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_GRAY700)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_GRAY700)
        pdf.cell(0, 5, "Diagrama de Esforços (Ftool)", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        try:
            # Imagem centralizada
            w_img = 135
            pdf.image(img_path, x=ML + (IW - w_img) / 2, w=w_img)
            pdf.ln(5)
        except Exception as e:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*C_RED700)
            pdf.cell(0, 5, f"Erro ao inserir imagem: {e}", border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        finally:
            # Limpar PNG temporario
            if png_temp and os.path.exists(png_temp):
                try:
                    os.remove(png_temp)
                except OSError:
                    pass

    # Disclaimer no final da página 1
    pdf.disclaimer()

    # Determinar se ha Premium. Se sim, as secoes Premium (3, 4, 5)
    # vem ANTES das comuns, e as comuns sao renumeradas (+3).
    tem_premium = on_add_diagrams is not None
    if tem_premium:
        # Premium usa secoes 3, 4, 5 (Diagramas, Detalhamento, ELS)
        on_add_diagrams(pdf, sec_num_inicial=3)
        sec_comum = 6   # Flexao, Secao Transversal, Cisalhamento, Memoria
    else:
        # Sem Premium, secoes comuns comecam em 3
        sec_comum = 3

    # Flexao
    pdf.section_title(sec_comum, "Dimensionamento à Flexão")
    sec_comum += 1

    headers_flex = ["Trecho", "Tipo", "Md (kN.m)", "Kc", "\u03b2x", "X (cm)", "As,req (cm²)", "As,min (cm²)", "Armadura Adotada"]
    col_w_flex = [15, 20, 22, 14, 14, 15, 22, 22, 26]
    
    rows_flex = []
    max_bars_inf = 0
    max_bars_sup = 0
    phi_inf_adot = phi_barra_mm
    phi_sup_adot = phi_barra_mm
    
    for i, r in enumerate(resultados_flexao):
        if r is None:
            continue
            
        rows_flex.append([
            f"T{i+1}",
            r.tipo,
            f"{_n(r.momento_kNm, 2)}",
            f"{_n(r.kc, 3)}",
            f"{_n(r.bx, 3)}",
            f"{_n(r.x_cm, 2)}",
            f"{_n(r.as_req_cm2, 2)}",
            f"{_n(r.asmin_cm2, 2)}",
            f"{r.qtd_barras} phi {_diam(r.diametro_mm)}"
        ])
        
        # Encontrar armadura máxima para o desenho da seção transversal representativa
        if r.tipo == "POSITIVO":
            if r.qtd_barras > max_bars_inf:
                max_bars_inf = r.qtd_barras
                phi_inf_adot = r.diametro_mm
        else:
            if r.qtd_barras > max_bars_sup:
                max_bars_sup = r.qtd_barras
                phi_sup_adot = r.diametro_mm
                
    if rows_flex:
        pdf.tabela_flexao(headers_flex, rows_flex, col_w_flex)
        
    # Validações normativas
    val_items = []
    lim_bx = 0.45 if fck_mpa <= 50 else 0.35
    for i, r in enumerate(resultados_flexao):
        if r is None:
            continue
        val_items.append((f"Trecho {i+1} - Domínio (\u03b2x \u2264 {lim_bx})", r.bx_passa == "SIM"))
        val_items.append((f"Trecho {i+1} - Espaçamento Horiz. (eh \u2265 2cm)", r.eh_passa == "SIM"))
        # A2: alerta explicito quando bx nao passa
        if getattr(r, "alerta", ""):
            val_items.append((f"ALERTA Trecho {i+1}: {r.alerta}", False))

    # Validacao armadura de pele (NBR 6118:17.3.5.2.3)
    pele_item = next((r for r in resultados_flexao if r is not None and hasattr(r, "requer_pele")), None)
    if pele_item is not None:
        if pele_item.requer_pele:
            val_items.append((
                f"Armadura de pele (h \u2265 60cm): {pele_item.n_barras_pele_face}x \u03d5{pele_item.phi_pele_mm:g}mm/face (s={pele_item.s_pele_cm:.0f}cm)",
                True
            ))
        else:
            val_items.append(("Armadura de pele (h < 60cm): não exigida", True))

    if val_items:
        pdf.validacoes_grid(val_items)
        
    # Secao Transversal (Esquema)
    pdf.add_page()
    pdf.section_title(sec_comum, "Seção Transversal (Esquema)")
    sec_comum += 1
    
    # Altura para o desenho da seção
    y_sec = pdf.get_y()
        
    # Desenhar
    n_inf_desenho = max_bars_inf if max_bars_inf > 0 else 3
    n_sup_desenho = max_bars_sup if max_bars_sup > 0 else 2
    
    # Armadura de pele do primeiro resultado valido
    n_pele = 0
    phi_pele = 0
    for r in resultados_flexao:
        if r is not None and hasattr(r, "requer_pele") and r.requer_pele:
            n_pele = r.n_barras_pele_face
            phi_pele = r.phi_pele_mm
            break

    layout_c = None
    for r in resultados_flexao:
        if r is not None and r.tipo == "POSITIVO" and r.qtd_barras == n_inf_desenho:
            if getattr(r, 'layout_convergido', None) is not None:
                layout_c = r.layout_convergido
                break
    if layout_c is None:
        for r in resultados_flexao:
            if r is not None and getattr(r, 'layout_convergido', None) is not None:
                layout_c = r.layout_convergido
                break
    
    desenhar_secao_retangular(
        pdf, h_cm, bw_cm, cob_mm, phi_estribo_mm,
        phi_barra_inf=phi_inf_adot, n_barras_inf=n_inf_desenho,
        phi_barra_sup=phi_sup_adot, n_barras_sup=n_sup_desenho,
        n_barras_pele=n_pele, phi_pele=phi_pele,
        layout_convergido=layout_c
    )
    
    # Legenda ao lado do desenho
    # Determina se havera grampo (2a camada de sup ou inf com 3+ barras)
    n_ic1_leg, n_ic2_leg = _split_layers(n_inf_desenho, phi_inf_adot, bw_cm, cob_mm, phi_estribo_mm)
    n_sc1_leg, n_sc2_leg = _split_layers(n_sup_desenho, phi_sup_adot, bw_cm, cob_mm, phi_estribo_mm)
    tem_grampo = (n_ic2_leg >= 3) or (n_sc2_leg >= 3)
    _legenda_secao(
        pdf, cob_mm, phi_estribo_mm,
        n_inf=n_inf_desenho, phi_inf=phi_inf_adot,
        n_sup=n_sup_desenho, phi_sup=phi_sup_adot,
        lx=ML + 78, ly=y_sec + 4,
        n_pele=n_pele, phi_pele=phi_pele,
        tem_grampo=tem_grampo,
    )

    # Nota sobre cavaletes (apenas quando ha 2a camada com grampo)
    if tem_grampo:
        # Posiciona abaixo das dimensoes bw/h com folga suficiente
        # para nao sobrepor a cota bw (que fica em y_sec+6+dh+4 ≈ y_sec+90 para h=70)
        pdf.set_y(y_sec + 110)
        _desenhar_nota_cavaletes(pdf, ML, pdf.get_y())
    
    # Cisalhamento (se houver)
    if any(r is not None for r in resultados_cisalhamento):
        pdf.add_page()
        pdf.section_title(sec_comum, "Dimensionamento ao Cisalhamento")
        sec_comum += 1
        
        headers_cis = ["Trecho", "Vsd (kN)", "Vrd2 (kN)", "Verif. Vrd2", "Vc (kN)", "Vsw (kN)", "Asw/s,min (cm²/m)", "s (cm)"]
        col_w_cis = [18, 22, 22, 22, 20, 20, 26, 20]
        
        rows_cis = []
        for i, r in enumerate(resultados_cisalhamento):
            if r is None:
                continue
            rows_cis.append([
                f"V{i+1}",
                f"{_n(r.vsd_kn, 2)}",
                f"{_n(r.vrd2_kn, 2)}",
                "OK" if r.passa_vrd2 == "SIM" else "ALERTA",
                f"{_n(r.vc_kn, 2)}",
                f"{_n(r.vsw_kn, 2)}",
                f"{_n(r.asw_s_min_cm2_m, 3)}",
                f"{_n(r.dist_estribos_cm, 1)}"
            ])
            
        if rows_cis:
            pdf.tabela_flexao(headers_cis, rows_cis, col_w_cis)
            
    # Memoria de Calculo (Apêndice)
    pdf.add_memoria_calculo(
        resultados_flexao,
        resultados_cisalhamento,
        sec_comum,
        h_cm, bw_cm, cob_mm,
        fck_mpa, fyk_mpa, fyk_estribo_mpa,
        phi_estribo_mm, phi_barra_mm,
        is_t=False,
    )
    
    # Assinatura
    pdf.assinatura_bloco()

    # Salvar
    pdf.output(filepath)
    return filepath


def gerar_relatorio_viga_t(
    filepath: str,
    *,
    nome_viga: str = "Viga V1",
    h_cm: float, bw_cm: float, bf_cm: float, hf_cm: float,
    caa: int,
    fck_mpa: float,
    fyk_mpa: float,
    fyk_estribo_mpa: float,
    phi_estribo_mm: float,
    phi_barra_mm: float,
    resultados_flexao: List[Optional[ResultadoFlexaoT]],
    resultados_cisalhamento: List[Optional[ResultadoCisalhamento]],
    imagem_ftool: Optional[str] = None,
    gamma_f: float = 1.4,
    dark_mode: bool = False,
    nome_engenheiro: str = "",
    crea: str = "",
    profissao: str = "Engenheiro Civil",
    on_add_diagrams: Optional[Any] = None,
) -> str:
    cob_mm = CAA_DATA[caa]["cobrimento"]
    pdf = PorticaPDF(nome_viga=nome_viga, subtitulo="Viga de Seção T", dark_mode=dark_mode,
                     nome_engenheiro=nome_engenheiro, crea=crea, profissao=profissao)
    pdf.alias_nb_pages()
    
    # ── PÁGINA 1 ──
    pdf.add_page()
    
    # 1. Dados de Entrada
    pdf.section_title(1, "Dados de Entrada")
    # Metadados do projeto (nome da viga, engenheiro, CREA, data)
    # em linha separada ACIMA dos cards, com quebra de linha automatica
    # e largura total (ML a MR), para acomodar nomes longos
    pdf.meta_header()
    pdf.data_cards([
        {"title": "Geometria T", "rows": [
            ("Altura (h)", f"{_n(h_cm, 1)} cm"),
            ("Largura Alma (bw)", f"{_n(bw_cm, 1)} cm"),
            ("Largura Mesa (bf)", f"{_n(bf_cm, 1)} cm"),
            ("Altura Mesa (hf)", f"{_n(hf_cm, 1)} cm"),
            ("Cobrimento (c)", f"{cob_mm:g} mm"),
        ]},
        {"title": "Materiais", "rows": [
            ("Classe (CAA)", _caa_nome(caa)),
            ("Concreto (fck)", f"{fck_mpa:g} MPa"),
            ("Aço Long. (fyk)", f"{fyk_mpa:g} kN/cm²"),
            ("Coef. gf", f"{gamma_f:g}"),
        ]},
        {"title": "Bitolas Base", "rows": [
            ("phi Long. Est.", f"{_diam(phi_barra_mm)} mm"),
            ("phi Estribo", f"{_diam(phi_estribo_mm)} mm"),
        ]},
    ])
    
    # 2. Solicitações de Cálculo
    pdf.section_title(2, "Solicitações de Cálculo")
    
    rows_m = []
    for i, r in enumerate(resultados_flexao):
        if r is None:
            continue
        sinal = "+" if r.tipo == "POSITIVO" else "-"
        rows_m.append((f"Trecho {i+1}", f"{sinal}{_n(abs(r.momento_kNm), 2)}", r.bx_passa == "SIM"))
        
    rows_v = []
    for i, r in enumerate(resultados_cisalhamento):
        if r is None:
            continue
        rows_v.append((f"Trecho {i+1}", f"{_n(r.vsd_kn, 2)}", r.passa_vrd2 == "SIM"))
        
    pdf.solicitacoes_2col(rows_m, rows_v)
    
    # Imagem do Ftool
    if imagem_ftool and os.path.exists(imagem_ftool):
        # Converter SVG para PNG se necessario
        img_path = imagem_ftool
        png_temp = None
        if imagem_ftool.lower().endswith(".svg"):
            png_temp = _converter_svg_para_png(imagem_ftool)
            if png_temp:
                img_path = png_temp

        if pdf.get_y() + 75 > pdf.h - MB:
            pdf.add_page()
            
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_GRAY700)
        pdf.cell(0, 5, "Diagrama de Esforços (Ftool)", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        try:
            w_img = 135
            pdf.image(img_path, x=ML + (IW - w_img) / 2, w=w_img)
            pdf.ln(5)
        except Exception as e:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(*C_RED700)
            pdf.cell(0, 5, f"Erro ao inserir imagem: {e}", border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        finally:
            if png_temp and os.path.exists(png_temp):
                try:
                    os.remove(png_temp)
                except Exception:
                    pass

    # Disclaimer
    pdf.disclaimer()

    # Determinar se ha Premium. Se sim, as secoes Premium (3, 4, 5)
    # vem ANTES das comuns, e as comuns sao renumeradas (+3).
    tem_premium = on_add_diagrams is not None
    if tem_premium:
        on_add_diagrams(pdf, sec_num_inicial=3)
        sec_comum = 6
    else:
        sec_comum = 3

    # Flexao
    pdf.section_title(sec_comum, "Dimensionamento à Flexão (Seção T)")
    sec_comum += 1

    headers_flex = ["Trecho", "Tipo", "Md (kN.m)", "Kc", "\u03b2x", "X (cm)", "As,req (cm²)", "As,min (cm²)", "Armadura Adotada"]
    col_w_flex = [15, 20, 22, 14, 14, 15, 22, 22, 26]
    
    rows_flex = []
    max_bars_inf = 0
    max_bars_sup = 0
    phi_inf_adot = phi_barra_mm
    phi_sup_adot = phi_barra_mm
    
    for i, r in enumerate(resultados_flexao):
        if r is None:
            continue
            
        rows_flex.append([
            f"T{i+1}",
            r.tipo,
            f"{_n(r.momento_kNm, 2)}",
            f"{_n(r.kc, 3)}",
            f"{_n(r.bx, 3)}",
            f"{_n(r.x_cm, 2)}",
            f"{_n(r.as_req_cm2, 2)}",
            f"{_n(r.asmin_cm2, 2)}",
            f"{r.qtd_barras} phi {_diam(r.diametro_mm)}"
        ])
        
        if r.tipo == "POSITIVO":
            if r.qtd_barras > max_bars_inf:
                max_bars_inf = r.qtd_barras
                phi_inf_adot = r.diametro_mm
        else:
            if r.qtd_barras > max_bars_sup:
                max_bars_sup = r.qtd_barras
                phi_sup_adot = r.diametro_mm
                
    if rows_flex:
        pdf.tabela_flexao(headers_flex, rows_flex, col_w_flex)
        
    # Validações normativas
    val_items = []
    lim_bx = 0.45 if fck_mpa <= 50 else 0.35
    for i, r in enumerate(resultados_flexao):
        if r is None:
            continue
        val_items.append((f"Trecho {i+1} - Domínio (\u03b2x \u2264 {lim_bx})", r.bx_passa == "SIM"))
        val_items.append((f"Trecho {i+1} - Linha Neutra na Mesa", r.linha_neutra_condiz == "SIM"))
        val_items.append((f"Trecho {i+1} - Espaçamento Horiz. (eh \u2265 2cm)", r.eh_passa == "SIM"))
        # A2: alerta explicito quando bx nao passa
        if getattr(r, "alerta", ""):
            val_items.append((f"ALERTA Trecho {i+1}: {r.alerta}", False))

    # Validacao armadura de pele (NBR 6118:17.3.5.2.3)
    pele_item = next((r for r in resultados_flexao if r is not None and hasattr(r, "requer_pele")), None)
    if pele_item is not None:
        if pele_item.requer_pele:
            val_items.append((
                f"Armadura de pele (h \u2265 60cm): {pele_item.n_barras_pele_face}x \u03d5{pele_item.phi_pele_mm:g}mm/face (s={pele_item.s_pele_cm:.0f}cm)",
                True
            ))
        else:
            val_items.append(("Armadura de pele (h < 60cm): não exigida", True))

    if val_items:
        pdf.validacoes_grid(val_items)
        
    # Secao Transversal T (Esquema)
    pdf.add_page()
    pdf.section_title(sec_comum, "Seção Transversal T (Esquema)")
    sec_comum += 1
    
    y_sec = pdf.get_y()
        
    n_inf_desenho = max_bars_inf if max_bars_inf > 0 else 3
    n_sup_desenho = max_bars_sup if max_bars_sup > 0 else 2
    
    # Armadura de pele do primeiro resultado valido
    n_pele = 0
    phi_pele = 0
    for r in resultados_flexao:
        if r is not None and hasattr(r, "requer_pele") and r.requer_pele:
            n_pele = r.n_barras_pele_face
            phi_pele = r.phi_pele_mm
            break

    layout_c = None
    for r in resultados_flexao:
        if r is not None and r.tipo == "POSITIVO" and r.qtd_barras == n_inf_desenho:
            if getattr(r, 'layout_convergido', None) is not None:
                layout_c = r.layout_convergido
                break
    if layout_c is None:
        for r in resultados_flexao:
            if r is not None and getattr(r, 'layout_convergido', None) is not None:
                layout_c = r.layout_convergido
                break
    
    desenhar_secao_t(
        pdf, h_cm, bw_cm, bf_cm, hf_cm, cob_mm, phi_estribo_mm,
        phi_barra_inf=phi_inf_adot, n_barras_inf=n_inf_desenho,
        phi_barra_sup=phi_sup_adot, n_barras_sup=n_sup_desenho,
        n_barras_pele=n_pele, phi_pele=phi_pele,
        layout_convergido=layout_c
    )
    
    n_ic1_leg, n_ic2_leg = _split_layers(n_inf_desenho, phi_inf_adot, bw_cm, cob_mm, phi_estribo_mm)
    n_sc1_leg, n_sc2_leg = _split_layers(n_sup_desenho, phi_sup_adot, bw_cm, cob_mm, phi_estribo_mm)
    tem_grampo = (n_ic2_leg >= 3) or (n_sc2_leg >= 3)
    
    _legenda_secao(
        pdf, cob_mm, phi_estribo_mm,
        n_inf=n_inf_desenho, phi_inf=phi_inf_adot,
        n_sup=n_sup_desenho, phi_sup=phi_sup_adot,
        lx=ML + 78, ly=y_sec + 4,
        n_pele=n_pele, phi_pele=phi_pele,
        tem_grampo=tem_grampo,
    )
    
    if tem_grampo:
        pdf.set_y(y_sec + 110)
        _desenhar_nota_cavaletes(pdf, ML, pdf.get_y())
    
    # Cisalhamento
    if any(r is not None for r in resultados_cisalhamento):
        pdf.add_page()
        pdf.section_title(sec_comum, "Dimensionamento ao Cisalhamento")
        sec_comum += 1
        
        headers_cis = ["Trecho", "Vsd (kN)", "Vrd2 (kN)", "Verif. Vrd2", "Vc (kN)", "Vsw (kN)", "Asw/s,min (cm²/m)", "s (cm)"]
        col_w_cis = [18, 22, 22, 22, 20, 20, 26, 20]
        
        rows_cis = []
        for i, r in enumerate(resultados_cisalhamento):
            if r is None:
                continue
            rows_cis.append([
                f"V{i+1}",
                f"{_n(r.vsd_kn, 2)}",
                f"{_n(r.vrd2_kn, 2)}",
                "OK" if r.passa_vrd2 == "SIM" else "ALERTA",
                f"{_n(r.vc_kn, 2)}",
                f"{_n(r.vsw_kn, 2)}",
                f"{_n(r.asw_s_min_cm2_m, 3)}",
                f"{_n(r.dist_estribos_cm, 1)}"
            ])
            
        if rows_cis:
            pdf.tabela_flexao(headers_cis, rows_cis, col_w_cis)
            
    # Memoria de Calculo (Apêndice)
    pdf.add_memoria_calculo(
        resultados_flexao,
        resultados_cisalhamento,
        sec_comum,
        h_cm, bw_cm, cob_mm,
        fck_mpa, fyk_mpa, fyk_estribo_mpa,
        phi_estribo_mm, phi_barra_mm,
        is_t=True,
        bf_cm=bf_cm, hf_cm=hf_cm,
    )
    
    # Assinatura
    pdf.assinatura_bloco()

    pdf.output(filepath)
    return filepath
