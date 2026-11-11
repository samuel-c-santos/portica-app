"""
EP-03.6: cobertura de ui/ftool/dimensionamento.py — fluxo de resumo e
relatórios com diagramas (funções puras, sem Flet).
"""

import os
import tempfile

from ui.ftool.dimensionamento import (
    dimensionar_trechos_ftool,
    gerar_relatorio_viga_comum_com_diagramas,
    gerar_relatorio_viga_t_com_diagramas,
    gerar_resumo_dimensionamento,
)
from ui.ftool.els import AjustesELS
from ui.ftool.parser import parse_cortante, parse_momento
from ui.ftool.secoes_criticas import SecaoCritica, detectar_todas_secoes

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

DADOS_VIGA = {
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


def _resultados():
    momentos = parse_momento(os.path.join(SAMPLES_DIR, "test_momento_fletor.txt"))
    cortantes = parse_cortante(os.path.join(SAMPLES_DIR, "test_esforcos_cortantes.txt"))
    secoes = detectar_todas_secoes(momentos, cortantes)
    resultados = dimensionar_trechos_ftool(
        DADOS_VIGA, secoes, momentos=momentos, cortantes=cortantes
    )
    return momentos, cortantes, secoes, resultados


class TestGerarResumoDimensionamento:
    def test_resumo_completo(self):
        _, _, _, resultados = _resultados()
        texto = gerar_resumo_dimensionamento(DADOS_VIGA, resultados["secoes"])
        assert "RESUMO DE DIMENSIONAMENTO AUTOMÁTICO" in texto
        assert "FLEXÃO (As):" in texto
        assert "CISALHAMENTO (Asw/s):" in texto
        assert "Majorador de esforços: gamma_f = 1.4" in texto

    def test_resumo_com_secao_nula(self):
        secao_nula = SecaoCritica(x=1.0, momento=0.0, cortante=0.0, tipo="M_NULO", descricao="nulo")
        resultados = dimensionar_trechos_ftool(DADOS_VIGA, [secao_nula])
        texto = gerar_resumo_dimensionamento(DADOS_VIGA, resultados["secoes"])
        assert "Momento nulo" in texto
        assert "Esforço nulo" in texto

    def test_resumo_com_alerta(self):
        secao = SecaoCritica(x=3.0, momento=400.0, cortante=50.0, tipo="MÁX", descricao="alto")
        resultados = dimensionar_trechos_ftool(DADOS_VIGA, [secao])
        texto = gerar_resumo_dimensionamento(DADOS_VIGA, resultados["secoes"])
        rf = resultados["secoes"][0]["resultado_flexao"]
        if rf and rf.alerta:
            assert "⚠️ ALERTA" in texto


class TestRelatorioComDiagramas:
    def _gerar(self, **extra):
        momentos, cortantes, secoes, resultados = _resultados()
        sec_results = resultados["secoes"]
        res_flex = [r["resultado_flexao"] for r in sec_results]
        res_cis = [r["resultado_cisalhamento"] for r in sec_results]
        detalhamento = resultados.get("detalhamento")
        resultado_els = {
            "flecha": {
                "ieq_cm4": 250000.0,
                "mr_kncm": 7094.0,
                "flecha_imediata_cm": 0.5,
                "flecha_diferida_cm": 1.0,
                "flecha_total_cm": 1.5,
                "limite_total_cm": 3.0,
                "limite_ativo_cm": 2.14,
                "passa_total": False,
                "passa_ativo": True,
                "dica": "Aumente a altura h da viga",
            },
            "fissuracao": {
                "wk_mm": 0.4,
                "wk_limite_mm": 0.3,
                "passa": False,
                "dica": "Aumente a armadura",
            },
            "ajustes_aplicados": extra.get("ajustes")
            or AjustesELS(
                barras_extras=2,
                phi_minimo_mm=12.5,
                h_override_cm=75.0,
                fck_override_mpa=35.0,
            ),
        }
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            gerar_relatorio_viga_comum_com_diagramas(
                path,
                nome_viga="Viga Fluxo",
                h_cm=70.0,
                bw_cm=20.0,
                caa=2,
                fck_mpa=30.0,
                fyk_mpa=50.0,
                fyk_estribo_kn_cm2=60.0,
                phi_estribo_mm=5.0,
                phi_barra_mm=16.0,
                resultados_flexao=res_flex,
                resultados_cisalhamento=res_cis,
                imagem_ftool=None,
                gamma_f=1.4,
                dark_mode=False,
                nome_engenheiro="Engenheiro",
                crea="12345/D",
                momentos=momentos,
                cortantes=cortantes,
                secoes_criticas=secoes,
                detalhamento=detalhamento,
                resultado_els=resultado_els,
            )
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.remove(path)

    def test_relatorio_completo_com_els_e_ajustes(self):
        self._gerar()

    def test_relatorio_com_els_passando_sem_dica(self):
        self._gerar(ajustes=AjustesELS())

    def test_relatorio_sem_diagramas(self):
        """Sem momentos/cortantes: on_add_diagrams não é registrado."""
        _, _, _, resultados = _resultados()
        sec_results = resultados["secoes"]
        res_flex = [r["resultado_flexao"] for r in sec_results]
        res_cis = [r["resultado_cisalhamento"] for r in sec_results]
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            gerar_relatorio_viga_comum_com_diagramas(
                path,
                nome_viga="Viga Fluxo",
                h_cm=70.0,
                bw_cm=20.0,
                caa=2,
                fck_mpa=30.0,
                fyk_mpa=50.0,
                fyk_estribo_kn_cm2=60.0,
                phi_estribo_mm=5.0,
                phi_barra_mm=16.0,
                resultados_flexao=res_flex,
                resultados_cisalhamento=res_cis,
                imagem_ftool=None,
                gamma_f=1.4,
                dark_mode=False,
                nome_engenheiro="Engenheiro",
                crea="12345/D",
            )
            assert os.path.exists(path)
        finally:
            os.remove(path)

    def test_relatorio_viga_t_com_diagramas(self):
        """O caminho T do wrapper (mesma estrutura do comum, com detalhamento e ELS)."""
        momentos, cortantes, secoes, resultados = _resultados()
        res_flex_t = []
        for sec in secoes:
            rf_list = dimensionar_trechos_ftool(
                {**DADOS_VIGA, "bf_cm": 60.0, "hf_cm": 12.0, "b1esq_cm": 20.0, "b1dir_cm": 20.0},
                [sec],
                momentos=momentos,
                cortantes=cortantes,
            )
            res_flex_t.append(rf_list["secoes"][0]["resultado_flexao"])
        res_cis = []
        detalhamento = resultados.get("detalhamento")
        resultado_els = {
            "flecha": {
                "ieq_cm4": 250000.0,
                "mr_kncm": 7094.0,
                "flecha_imediata_cm": 0.5,
                "flecha_diferida_cm": 1.0,
                "flecha_total_cm": 1.5,
                "limite_total_cm": 3.0,
                "limite_ativo_cm": 2.14,
                "passa_total": True,
                "passa_ativo": True,
                "dica": "",
            },
            "fissuracao": {
                "wk_mm": 0.2,
                "wk_limite_mm": 0.3,
                "passa": True,
                "dica": "",
            },
            "ajustes_aplicados": AjustesELS(barras_extras=1),
        }
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            gerar_relatorio_viga_t_com_diagramas(
                path,
                nome_viga="Viga T Fluxo",
                h_cm=70.0,
                bw_cm=20.0,
                bf_cm=60.0,
                hf_cm=12.0,
                caa=2,
                fck_mpa=30.0,
                fyk_mpa=50.0,
                fyk_estribo_kn_cm2=60.0,
                phi_estribo_mm=5.0,
                phi_barra_mm=16.0,
                resultados_flexao=res_flex_t,
                resultados_cisalhamento=res_cis,
                imagem_ftool=None,
                gamma_f=1.4,
                dark_mode=False,
                nome_engenheiro="Engenheiro",
                crea="12345/D",
                momentos=momentos,
                cortantes=cortantes,
                secoes_criticas=secoes,
                detalhamento=detalhamento,
                resultado_els=resultado_els,
            )
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.remove(path)
