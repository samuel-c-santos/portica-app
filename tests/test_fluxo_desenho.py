"""
EP-03.6: cobertura de fluxos de desenho com o BeamDetailer (PDF) e ramos de
viga T com momento negativo do motor de flexão.
"""

import os
import tempfile

import pytest

from core.calculos.engenharia import calcular_flexao_viga_t
from core.detailing.presentation import desenhar_secao_com_detailer


class TestDesenharComDetailer:
    """Wrapper de desenho: barras superiores, pele, seção T e grampos."""

    def _pdf(self):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        return pdf

    def test_retangular_com_barras_superiores_e_pele(self):
        pdf = self._pdf()
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            layout = desenhar_secao_com_detailer(
                pdf,
                h_cm=50.0,
                bw_cm=20.0,
                cob_mm=25.0,
                phi_estribo_mm=5.0,
                phi_barra_inf_mm=16.0,
                n_barras_inf=4,
                phi_barra_sup_mm=10.0,
                n_barras_sup=2,
                n_barras_pele=2,
                phi_pele_mm=6.3,
            )
            pdf.output(path)
            assert os.path.getsize(path) > 0
            assert layout.layer_count >= 1
        finally:
            os.remove(path)

    def test_viga_t_com_barras_superiores(self):
        pdf = self._pdf()
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            layout = desenhar_secao_com_detailer(
                pdf,
                h_cm=60.0,
                bw_cm=20.0,
                cob_mm=30.0,
                phi_estribo_mm=5.0,
                phi_barra_inf_mm=16.0,
                n_barras_inf=3,
                phi_barra_sup_mm=12.5,
                n_barras_sup=3,
                is_t=True,
                bf_cm=60.0,
                hf_cm=15.0,
            )
            pdf.output(path)
            assert os.path.getsize(path) > 0
            assert layout.is_t
        finally:
            os.remove(path)

    def test_viga_t_com_pele_densa_cai_no_fallback(self):
        """T com 6 barras de pele por face: d_livre < ev_min → fallback uniforme.

        EP-03.6: cobre os ramos de fallback do posicionamento de pele do
        wrapper com detailer (presentation.py).
        """
        pdf = self._pdf()
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            layout = desenhar_secao_com_detailer(
                pdf,
                h_cm=60.0,
                bw_cm=20.0,
                cob_mm=30.0,
                phi_estribo_mm=5.0,
                phi_barra_inf_mm=16.0,
                n_barras_inf=4,
                n_barras_pele=10,
                phi_pele_mm=8.0,
                is_t=True,
                bf_cm=60.0,
                hf_cm=15.0,
            )
            pdf.output(path)
            assert os.path.getsize(path) > 0
            assert layout.is_t
        finally:
            os.remove(path)

    def test_viga_t_pele_sem_superiores(self):
        """T com pele e SEM barras superiores: ramos de limites por camadas."""
        pdf = self._pdf()
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            layout = desenhar_secao_com_detailer(
                pdf,
                h_cm=70.0,
                bw_cm=20.0,
                cob_mm=30.0,
                phi_estribo_mm=5.0,
                phi_barra_inf_mm=16.0,
                n_barras_inf=5,
                n_barras_pele=4,
                phi_pele_mm=8.0,
                is_t=True,
                bf_cm=60.0,
                hf_cm=12.0,
            )
            pdf.output(path)
            assert os.path.getsize(path) > 0
            assert layout.is_t
        finally:
            os.remove(path)

    def test_renderer_ramos_defensivos(self):
        """EP-03.6: ramos defensivos do FpdfRenderer com comandos sintéticos."""
        from core.detailing.presentation import (
            CmdArcPath,
            CmdCircle,
            CmdLine,
            CmdPolygon,
            CmdPolyline,
            FpdfRenderer,
        )

        pdf = self._pdf()
        renderer = FpdfRenderer(pdf=pdf, px=10.0, py=10.0, scale=1.0, section_height_mm=100.0)
        renderer.render(
            [
                CmdLine(
                    x1=0, y1=0, x2=10, y2=10, color=None
                ),  # cor None → early return em _set_color
                CmdCircle(cx=5, cy=5, r=2, fill=None, stroke=(0, 0, 0)),  # só stroke
                CmdPolyline(points=[(1, 1)], color=(0, 0, 0)),  # < 2 pontos → skip
                CmdPolygon(points=[(1, 1), (2, 2)], fill=(0, 0, 0)),  # < 3 pontos → skip
                CmdArcPath(cx=5, cy=5, radius=3, start_angle_deg=0, sweep_angle_deg=90),
            ]
        )
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            pdf.output(path)
            assert os.path.getsize(path) > 0
        finally:
            os.remove(path)

    def test_com_grampos_suplementares(self):
        """10Ø12,5 em bw=30: camadas 7+3 → 2ª camada com 3 barras e span > 15 cm → grampo."""
        pdf = self._pdf()
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            layout = desenhar_secao_com_detailer(
                pdf,
                h_cm=60.0,
                bw_cm=30.0,
                cob_mm=30.0,
                phi_estribo_mm=5.0,
                phi_barra_inf_mm=12.5,
                n_barras_inf=10,
            )
            pdf.output(path)
            assert os.path.getsize(path) > 0
            assert layout.layer_count == 2
            assert layout.layers[1].bar_count == 3
            assert layout.requires_supplementary_stirrup
        finally:
            os.remove(path)


class TestFlexaoTMomentoNegativo:
    """Ramos de momento negativo da viga T (EP-03.3/EP-03.6)."""

    def test_momento_negativo_simples(self):
        # T 15×50 (bf=60, hf=10), Mk=−80 (Md=112): seção com alma 15 → LN na
        # alma; bx < bx_min → armadura simples.
        res = calcular_flexao_viga_t(
            h_cm=50.0,
            bw_cm=15.0,
            bf_cm=60.0,
            hf_cm=10.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_kn_cm2=50.0,
            momentos=[-80.0],
        )
        r = res[0]
        assert r.tipo == "NEGATIVO"
        assert r.as_linha_cm2 == 0.0
        assert r.as_req_cm2 > 0.0

    def test_momento_negativo_armadura_dupla(self):
        """Mk=−130 (Md=182) em bw=15: com a d convergida Md supera Md,lim →
        armadura dupla no limite de ductilidade (bx = 0,45), nunca sentinela."""
        res = calcular_flexao_viga_t(
            h_cm=50.0,
            bw_cm=15.0,
            bf_cm=60.0,
            hf_cm=10.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_kn_cm2=50.0,
            momentos=[-130.0],
        )
        r = res[0]
        assert r.tipo == "NEGATIVO"
        assert r.bx == pytest.approx(0.45, abs=1e-9)
        assert r.x_cm is not None and r.x_cm < r.d_cm_real
        assert r.as_req_cm2 > 0.0
        assert r.as_linha_cm2 > 0.0
        assert "armadura dupla" in r.alerta.lower()

    def test_momento_negativo_d_positivo_e_invariantes(self):
        res = calcular_flexao_viga_t(
            h_cm=50.0,
            bw_cm=15.0,
            bf_cm=60.0,
            hf_cm=10.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=12.5,
            fyk_kn_cm2=50.0,
            momentos=[-120.0],
        )
        r = res[0]
        assert r.d_cm_real > 0
        assert r.as_adotado_cm2 == pytest.approx(
            r.qtd_barras * 3.14159 * (r.diametro_mm / 20.0) ** 2, abs=0.05
        )
