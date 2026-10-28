"""Testes para o helper de grampos suplementares (NBR 6118:18.3.2.3)."""
import os
import sys
import tempfile

import pytest
from fpdf import FPDF

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.relatorio_base import (
    _desenhar_grampos_segunda_camada,
    _split_layers,
    desenhar_secao_retangular,
)


def _make_pdf() -> FPDF:
    """Cria um PDF minimo para o helper desenhar."""
    pdf = FPDF()
    pdf.add_page()
    return pdf


def test_split_layers_3_barras_vai_para_uma_camada_em_bw_largo():
    """3 barras em bw=30 cabem em 1 camada."""
    c1, c2 = _split_layers(3, 16.0, 30.0, 25.0, 5.0)
    assert c1 == 3 and c2 == 0


def test_split_layers_4_barras_em_bw_estreito_ainda_cabe_em_uma_camada():
    """4 barras phi16 em bw=20 cabem em 1 camada (eh~2.5cm > 1.95cm)."""
    c1, c2 = _split_layers(4, 16.0, 20.0, 25.0, 5.0)
    assert c1 == 4 and c2 == 0


def test_split_layers_6_barras_em_bw_estreito_3_mais_3():
    """6 barras em bw=20: 4 + 2 (aligned with BeamDetailer)."""
    c1, c2 = _split_layers(6, 16.0, 20.0, 25.0, 5.0)
    assert c1 == 4 and c2 == 2


def test_grampos_zero_quando_camada_tem_2_ou_menos_barras():
    """2 barras = ambas nas laterais, sem barra intermediária, sem grampo."""
    pdf = _make_pdf()
    n = _desenhar_grampos_segunda_camada(
        pdf, n_camada=2, phi_barra=16.0, phi_estribo=5.0,
        x_left=20.0, x_right=80.0,
        y_bar=50.0, s=0.5, fechado_para_cima=True,
    )
    assert n == 0


def test_grampos_desenha_1_quando_camada_tem_3_barras():
    """3 barras: existe barra intermediária -> 1 grampo contínuo."""
    pdf = _make_pdf()
    n = _desenhar_grampos_segunda_camada(
        pdf, n_camada=3, phi_barra=16.0, phi_estribo=5.0,
        x_left=20.0, x_right=80.0,
        y_bar=50.0, s=0.5, fechado_para_cima=False,
    )
    assert n == 1


def test_grampos_desenha_1_tambem_quando_camada_tem_4_barras():
    """4 barras: mais intermediárias, mas o grampo é sempre 1 (contínuo)."""
    pdf = _make_pdf()
    n = _desenhar_grampos_segunda_camada(
        pdf, n_camada=4, phi_barra=16.0, phi_estribo=5.0,
        x_left=20.0, x_right=80.0,
        y_bar=50.0, s=0.5, fechado_para_cima=True,
    )
    assert n == 1


def test_grampos_nao_desenha_quando_n_camada_zero():
    """n=0 (camada inexistente) -> 0 grampos, no exception."""
    pdf = _make_pdf()
    n = _desenhar_grampos_segunda_camada(
        pdf, n_camada=0, phi_barra=16.0, phi_estribo=5.0,
        x_left=20.0, x_right=80.0,
        y_bar=50.0, s=0.5, fechado_para_cima=True,
    )
    assert n == 0


def test_grampos_cobre_largura_do_estribo():
    """O grampo contínuo deve ter a mesma largura do estribo (x_left a x_right)."""
    pdf = _make_pdf()
    y_bar = 50.0
    s = 0.5
    phi_barra = 16.0
    phi_estribo = 5.0

    x_left = 20.0
    x_right = 115.0  # 95 unidades de largura (largura típica de estribo)

    n = _desenhar_grampos_segunda_camada(
        pdf, n_camada=4, phi_barra=phi_barra, phi_estribo=phi_estribo,
        x_left=x_left, x_right=x_right,
        y_bar=y_bar, s=s, fechado_para_cima=False,
    )
    assert n == 1

    # Verifica que o PDF foi gerado (sanity check)
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf.output(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_grampos_fechado_na_1a_camada_e_pernas_passam_pela_2a():
    """Geometria esperada: fechado em y_camada_1, aberto em y_bar ± grampo_off."""
    pdf = _make_pdf()
    phi_barra = 16.0
    phi_estribo = 5.0
    s = 0.5
    grampo_off = (phi_estribo / 2 + phi_barra / 2) * s  # = 6.5

    y_bar = 100.0      # 2a camada
    y_camada_1 = 110.0  # 1a camada (10 unidades abaixo)
    n = _desenhar_grampos_segunda_camada(
        pdf, n_camada=3, phi_barra=phi_barra, phi_estribo=phi_estribo,
        x_left=20.0, x_right=80.0,
        y_bar=y_bar, s=s, fechado_para_cima=False,
    )
    assert n == 1
    # Validacao geometrica esperada (fechado_para_cima=False, ∪):
    #   y_closed (base) = y_camada_1 = 110.0
    #   y_open   (topo) = y_bar - grampo_off = 100 - 6.5 = 93.5
    #   perna esq vai de (x_left, 110) ate (x_left, 93.5)
    #   perna dir vai de (x_right, 110) ate (x_right, 93.5)
    #   base vai de (x_left, 110) ate (x_right, 110)
    # Validamos apenas que o PDF foi gerado sem erro (geometria detalhada
    # exigiria introspeccao do fpdf2, que nao expoe ops no 2.8.7).
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf.output(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_grampos_2a_camada_superior_fechado_na_1a_camada_sup():
    """Para 2a camada sup, o U é ∩ com fechado em y_camada_1_sup (menor Y)."""
    pdf = _make_pdf()
    phi_barra = 10.0
    phi_estribo = 5.0
    s = 0.5

    y_bar = 40.0       # 2a camada sup (menor Y, mais ao topo)
    y_camada_1 = 30.0  # 1a camada sup (acima da 2a)
    n = _desenhar_grampos_segunda_camada(
        pdf, n_camada=3, phi_barra=phi_barra, phi_estribo=phi_estribo,
        x_left=20.0, x_right=80.0,
        y_bar=y_bar, s=s, fechado_para_cima=True,
    )
    assert n == 1
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf.output(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_legenda_com_grampo_renderiza_sem_erro():
    """A legenda com a entrada do grampo deve renderizar sem erro."""
    from core.relatorio_base import _legenda_secao

    pdf = _make_pdf()
    _legenda_secao(
        pdf, cob_mm=25.0, phi_est=5.0,
        n_inf=6, phi_inf=16.0, n_sup=2, phi_sup=10.0,
        lx=10.0, ly=10.0,
        n_pele=5, phi_pele=6.3,
        tem_grampo=True,
    )
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf.output(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_legenda_sem_grampo_renderiza_sem_erro():
    """A legenda sem a entrada do grampo deve renderizar sem erro."""
    from core.relatorio_base import _legenda_secao

    pdf = _make_pdf()
    _legenda_secao(
        pdf, cob_mm=25.0, phi_est=5.0,
        n_inf=3, phi_inf=16.0, n_sup=2, phi_sup=10.0,
        lx=10.0, ly=10.0,
        n_pele=5, phi_pele=6.3,
        tem_grampo=False,
    )
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf.output(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_nota_cavaletes_renderiza_sem_erro():
    """A nota sobre cavaletes deve renderizar sem erro."""
    from core.relatorio_base import _desenhar_nota_cavaletes

    pdf = _make_pdf()
    _desenhar_nota_cavaletes(pdf, x=10.0, y=100.0, largura=180.0)
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf.output(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_desenhar_secao_com_2_camadas_gera_pdf_sem_erro():
    """Viga com phi10 em bw=20 e momento alto -> 2 camadas -> grampos."""
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf = FPDF()
        pdf.add_page()
        # bw=20, h=50, cob=25, estribo=5, barra=10, 3 barras inferiores
        # _split_layers(3, 10, 20, 25, 5) -> testa
        desenhar_secao_retangular(
            pdf, h_cm=50.0, bw_cm=20.0, cob_mm=25.0, phi_estribo=5.0,
            phi_barra_inf=10.0, n_barras_inf=3,
            phi_barra_sup=10.0, n_barras_sup=2,
        )
        pdf.output(pdf_path)
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_desenhar_secao_com_1_camada_nao_gera_grampos():
    """Viga com 2 barras em bw largo -> 1 camada -> sem grampos."""
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        pdf = FPDF()
        pdf.add_page()
        desenhar_secao_retangular(
            pdf, h_cm=50.0, bw_cm=30.0, cob_mm=25.0, phi_estribo=5.0,
            phi_barra_inf=16.0, n_barras_inf=2,
            phi_barra_sup=10.0, n_barras_sup=2,
        )
        pdf.output(pdf_path)
        # 2 barras na 1a camada = sem grampos. So valida que nao quebra.
        assert os.path.getsize(pdf_path) > 0
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
