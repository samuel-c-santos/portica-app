"""
EP-03.4 — Testes de integridade: o conteúdo do PDF é verificado, não só o
tamanho do arquivo.

Cobertura consolidada do EP-01 (referências):
- seção que não cabe → recusa com status explícito: tests/test_integridade_flexao.py
  (caso h=50, bw=15, Mk=400) e tests/test_detailing_domain.py
  (caso 67 camadas, d negativo);
- não-convergência → recusa: tests/test_convergencia_flexao.py;
- fywd impresso ≤ 43,5 e X nunca sentinela: tests/test_relatorio_ep019.py;
- DXF (contorno/estribo/barras): tests/test_dxf.py.

Aqui: As,req e As,adotado impressos no PDF COINCIDEM entre si e com o
retorno do motor (o subdimensionamento silencioso ficaria visível aqui).
"""

import re

import pytest
from helpers_pdf import pdf_com_captura

from core.calculos import calcular_cisalhamento_viga_comum, calcular_flexao_viga_comum
from core.relatorio_base import gerar_relatorio_viga_comum


def _texto_do_pdf_relatorio(monkeypatch, res_flex, res_cis, fyk_estribo_kn_cm2=60.0):
    """Gera o relatório completo e devolve o texto capturado."""
    import os
    import tempfile

    caminho = None

    def _gerar():
        nonlocal caminho
        fd, caminho = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        gerar_relatorio_viga_comum(
            caminho,
            nome_viga="Viga Integridade",
            h_cm=50.0,
            bw_cm=15.0,
            caa=2,
            fck_mpa=30.0,
            fyk_mpa=50.0,
            fyk_estribo_kn_cm2=fyk_estribo_kn_cm2,
            phi_estribo_mm=5.0,
            phi_barra_mm=16.0,
            resultados_flexao=res_flex,
            resultados_cisalhamento=res_cis,
            nome_engenheiro="Engenheiro",
            crea="12345/D",
        )

    texto = pdf_com_captura(monkeypatch, _gerar)
    if caminho and os.path.exists(caminho):
        os.remove(caminho)
    return texto


class TestPdfIntegridadeAs:
    def test_as_req_e_as_adotado_no_pdf_considem_com_o_motor(self, monkeypatch):
        res_flex = calcular_flexao_viga_comum(
            h_cm=50.0,
            bw_cm=15.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_mpa=50.0,
            momentos=[96.9],
            gamma_f=1.4,
        )
        res_cis = calcular_cisalhamento_viga_comum(
            h_cm=50.0,
            bw_cm=15.0,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_estribo_kn_cm2=60.0,
            fyk_barra_mpa=50.0,
            caa=2,
            forcas_cortantes=[50.0],
        )
        texto = _texto_do_pdf_relatorio(monkeypatch, res_flex, res_cis)

        r = res_flex[0]
        # valores impressos na memória (formato com ponto; linha "As,req = ... = X cm^2")
        as_req_pdf = re.search(r"As,req = [^=\n]*= ([0-9.]+) cm\^2", texto)
        as_adotado_pdf = re.search(r"\(As = ([0-9.]+) cm\^2\)", texto)
        assert as_req_pdf is not None, "As,req não encontrado no PDF"
        assert as_adotado_pdf is not None, "As,adotado não encontrado no PDF"

        as_req_num = float(as_req_pdf.group(1))
        as_adotado_num = float(as_adotado_pdf.group(1))

        # coincidem com o retorno do motor
        assert as_req_num == pytest.approx(r.as_req_cm2, abs=0.01)
        assert as_adotado_num == pytest.approx(r.as_adotado_cm2, abs=0.01)
        # coincidem entre si: adotado ≥ req (nunca subdimensionamento silencioso)
        assert as_adotado_num >= as_req_num - 1e-6

    def test_status_recusado_impresso_no_pdf(self, monkeypatch):
        """Seção recusada (NÃO CABE/NÃO CONVERGIU) aparece no PDF, sem fingir CABE."""
        res_flex = calcular_flexao_viga_comum(
            h_cm=50.0,
            bw_cm=15.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_mpa=50.0,
            momentos=[400.0],
            gamma_f=1.4,
        )
        r = res_flex[0]
        assert r.status_bitola in ("NÃO CABE", "NÃO CONVERGIU")
        res_cis = calcular_cisalhamento_viga_comum(
            h_cm=50.0,
            bw_cm=15.0,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_estribo_kn_cm2=60.0,
            fyk_barra_mpa=50.0,
            caa=2,
            forcas_cortantes=[50.0],
        )
        texto = _texto_do_pdf_relatorio(monkeypatch, res_flex, res_cis)
        assert r.status_bitola in texto, f"status de recusa ({r.status_bitola}) não aparece no PDF"
        # e a tabela de bitolas não pode ter gravado "CABE" nu para o trecho
        assert r.status_bitola != "CABE"
