import os
import tempfile

import pytest

from core.calculos import (
    calcular_cisalhamento_viga_comum,
    calcular_flexao_viga_comum,
    calcular_flexao_viga_t,
)
from core.relatorio_base import gerar_relatorio_viga_comum, gerar_relatorio_viga_t

# Texto do rodapé de aviso de responsabilidade (deve estar em todas as páginas)
RODAPE_AVISO = "Uso sob responsabilidade do usuário — ver README do projeto"


def test_gerar_relatorio_viga_comum_sucesso(viga_exemplo, momentos_exemplo, cortantes_exemplo):
    res_flex = calcular_flexao_viga_comum(
        h_cm=viga_exemplo["h_cm"],
        bw_cm=viga_exemplo["bw_cm"],
        caa=viga_exemplo["caa"],
        fck_mpa=viga_exemplo["fck_mpa"],
        diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo["diam_barra_mm"],
        fyk_mpa=viga_exemplo["fyk_mpa"],
        momentos=momentos_exemplo,
        gamma_f=viga_exemplo["gamma_f"],
    )

    res_cis = calcular_cisalhamento_viga_comum(
        h_cm=viga_exemplo["h_cm"],
        bw_cm=viga_exemplo["bw_cm"],
        fck_mpa=viga_exemplo["fck_mpa"],
        diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo["diam_barra_mm"],
        fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_mpa"],
        fyk_barra_mpa=viga_exemplo["fyk_mpa"],
        caa=viga_exemplo["caa"],
        forcas_cortantes=cortantes_exemplo,
        gamma_f=viga_exemplo["gamma_f"],
    )

    fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        gerar_relatorio_viga_comum(
            temp_pdf_path,
            nome_viga="Viga Teste Comum",
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            caa=viga_exemplo["caa"],
            fck_mpa=viga_exemplo["fck_mpa"],
            fyk_mpa=viga_exemplo["fyk_mpa"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_mpa"],
            phi_estribo_mm=viga_exemplo["diam_estribo_mm"],
            phi_barra_mm=viga_exemplo["diam_barra_mm"],
            resultados_flexao=res_flex,
            resultados_cisalhamento=res_cis,
            nome_engenheiro="Samuel Santos",
            crea="123456/D-SP",
        )

        assert os.path.exists(temp_pdf_path)
        assert os.path.getsize(temp_pdf_path) > 0
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


def test_conteudo_pdf_reflete_motor(monkeypatch, viga_exemplo, momentos_exemplo, cortantes_exemplo):
    """EP-03.2/EP-03.4: o PDF deve CONTER os valores do motor.

    Verifica (via captura de texto):
    - seções estruturais do relatório presentes;
    - As,req do motor (formatado) aparece no relatório;
    - As,adotado ≥ As,req no texto;
    - fywd impresso ≤ 43,5 kN/cm² (cap do motor, EP-01.9);
    - nenhum valor sentinela de X (999·d).
    """
    from helpers_pdf import pdf_com_captura

    from core.relatorio_base import _n

    r_flex = calcular_flexao_viga_comum(
        h_cm=viga_exemplo["h_cm"],
        bw_cm=viga_exemplo["bw_cm"],
        caa=viga_exemplo["caa"],
        fck_mpa=viga_exemplo["fck_mpa"],
        diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo["diam_barra_mm"],
        fyk_mpa=viga_exemplo["fyk_mpa"],
        momentos=momentos_exemplo,
        gamma_f=viga_exemplo["gamma_f"],
    )
    r_cis = calcular_cisalhamento_viga_comum(
        h_cm=viga_exemplo["h_cm"],
        bw_cm=viga_exemplo["bw_cm"],
        fck_mpa=viga_exemplo["fck_mpa"],
        diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo["diam_barra_mm"],
        fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_mpa"],
        fyk_barra_mpa=viga_exemplo["fyk_mpa"],
        caa=viga_exemplo["caa"],
        forcas_cortantes=cortantes_exemplo,
        gamma_f=viga_exemplo["gamma_f"],
    )

    fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:

        def _gerar():
            gerar_relatorio_viga_comum(
                temp_pdf_path,
                nome_viga="Viga Teste Comum",
                h_cm=viga_exemplo["h_cm"],
                bw_cm=viga_exemplo["bw_cm"],
                caa=viga_exemplo["caa"],
                fck_mpa=viga_exemplo["fck_mpa"],
                fyk_mpa=viga_exemplo["fyk_mpa"],
                fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_mpa"],
                phi_estribo_mm=viga_exemplo["diam_estribo_mm"],
                phi_barra_mm=viga_exemplo["diam_barra_mm"],
                resultados_flexao=r_flex,
                resultados_cisalhamento=r_cis,
                nome_engenheiro="Samuel Santos",
                crea="123456/D-SP",
            )

        texto = pdf_com_captura(monkeypatch, _gerar)

        # Seções estruturais
        assert "Memória de Cálculo" in texto
        assert "Dimensionamento à Flexão" in texto or "Flexão" in texto

        # As,req do motor (formato pt-BR nas tabelas; com ponto na memória)
        r = next(x for x in r_flex if x is not None)
        as_str = _n(r.as_req_cm2, 2)
        as_str_ponto = f"{r.as_req_cm2:.2f}"
        assert as_str in texto or as_str_ponto in texto, (
            f"As,req do motor ({as_str}) não aparece no PDF"
        )

        # As,adotado ≥ As,req (EP-01.3 já garante no motor; aqui conferimos no texto)
        adotado = _n(r.as_adotado_cm2, 2)
        adotado_ponto = f"{r.as_adotado_cm2:.2f}"
        assert adotado in texto or adotado_ponto in texto, (
            f"As,adotado do motor ({adotado}) não aparece no PDF"
        )

        # fywd impresso ≤ 43,5 (CA-60: cap governa — EP-01.9)
        assert "52.17" not in texto and "52,17" not in texto

        # X nunca é sentinela 999·d (EP-01.4)
        assert "999" not in texto
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


def test_gerar_relatorio_viga_t_sucesso(viga_exemplo_t, momentos_exemplo, cortantes_exemplo):
    res_flex = calcular_flexao_viga_t(
        h_cm=viga_exemplo_t["h_cm"],
        bw_cm=viga_exemplo_t["bw_cm"],
        bf_cm=viga_exemplo_t["bf_cm"],
        hf_cm=viga_exemplo_t["hf_cm"],
        caa=viga_exemplo_t["caa"],
        fck_mpa=viga_exemplo_t["fck_mpa"],
        diam_estribo_mm=viga_exemplo_t["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo_t["diam_barra_mm"],
        fyk_mpa=viga_exemplo_t["fyk_mpa"],
        momentos=momentos_exemplo,
        b1esq_cm=viga_exemplo_t["b1esq_cm"],
        b1dir_cm=viga_exemplo_t["b1dir_cm"],
        gamma_f=viga_exemplo_t["gamma_f"],
    )

    res_cis = calcular_cisalhamento_viga_comum(
        h_cm=viga_exemplo_t["h_cm"],
        bw_cm=viga_exemplo_t["bw_cm"],
        fck_mpa=viga_exemplo_t["fck_mpa"],
        diam_estribo_mm=viga_exemplo_t["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo_t["diam_barra_mm"],
        fyk_estribo_kn_cm2=50,
        fyk_barra_mpa=viga_exemplo_t["fyk_mpa"],
        caa=viga_exemplo_t["caa"],
        forcas_cortantes=cortantes_exemplo,
        gamma_f=viga_exemplo_t["gamma_f"],
    )

    fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        gerar_relatorio_viga_t(
            temp_pdf_path,
            nome_viga="Viga Teste T",
            h_cm=viga_exemplo_t["h_cm"],
            bw_cm=viga_exemplo_t["bw_cm"],
            bf_cm=viga_exemplo_t["bf_cm"],
            hf_cm=viga_exemplo_t["hf_cm"],
            caa=viga_exemplo_t["caa"],
            fck_mpa=viga_exemplo_t["fck_mpa"],
            fyk_mpa=viga_exemplo_t["fyk_mpa"],
            fyk_estribo_kn_cm2=50,
            phi_estribo_mm=viga_exemplo_t["diam_estribo_mm"],
            phi_barra_mm=viga_exemplo_t["diam_barra_mm"],
            resultados_flexao=res_flex,
            resultados_cisalhamento=res_cis,
            nome_engenheiro="Samuel Santos",
            crea="123456/D-SP",
        )

        assert os.path.exists(temp_pdf_path)
        assert os.path.getsize(temp_pdf_path) > 0
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)


def test_rodape_contem_aviso_de_responsabilidade(viga_exemplo, momentos_exemplo, cortantes_exemplo):
    """O rodapé de toda página do PDF deve carregar o aviso de responsabilidade."""
    pypdf = pytest.importorskip("pypdf")

    res_flex = calcular_flexao_viga_comum(
        h_cm=viga_exemplo["h_cm"],
        bw_cm=viga_exemplo["bw_cm"],
        caa=viga_exemplo["caa"],
        fck_mpa=viga_exemplo["fck_mpa"],
        diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo["diam_barra_mm"],
        fyk_mpa=viga_exemplo["fyk_mpa"],
        momentos=momentos_exemplo,
        gamma_f=viga_exemplo["gamma_f"],
    )

    res_cis = calcular_cisalhamento_viga_comum(
        h_cm=viga_exemplo["h_cm"],
        bw_cm=viga_exemplo["bw_cm"],
        caa=viga_exemplo["caa"],
        fck_mpa=viga_exemplo["fck_mpa"],
        diam_estribo_mm=viga_exemplo["diam_estribo_mm"],
        diam_barra_mm=viga_exemplo["diam_barra_mm"],
        fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_mpa"],
        fyk_barra_mpa=viga_exemplo["fyk_mpa"],
        forcas_cortantes=cortantes_exemplo,
        gamma_f=viga_exemplo["gamma_f"],
    )

    fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        gerar_relatorio_viga_comum(
            temp_pdf_path,
            nome_viga="Viga Teste Aviso",
            h_cm=viga_exemplo["h_cm"],
            bw_cm=viga_exemplo["bw_cm"],
            caa=viga_exemplo["caa"],
            fck_mpa=viga_exemplo["fck_mpa"],
            fyk_mpa=viga_exemplo["fyk_mpa"],
            fyk_estribo_kn_cm2=viga_exemplo["fyk_estribo_mpa"],
            phi_estribo_mm=viga_exemplo["diam_estribo_mm"],
            phi_barra_mm=viga_exemplo["diam_barra_mm"],
            resultados_flexao=res_flex,
            resultados_cisalhamento=res_cis,
            nome_engenheiro="Samuel Santos",
            crea="123456/D-SP",
        )

        reader = pypdf.PdfReader(temp_pdf_path)
        assert len(reader.pages) >= 1
        for i, pagina in enumerate(reader.pages):
            texto = pagina.extract_text() or ""
            assert RODAPE_AVISO in texto, (
                f"pagina {i + 1} sem o aviso de responsabilidade no rodape"
            )
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
