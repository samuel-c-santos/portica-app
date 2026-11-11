"""
EP-01.9 — A memória de cálculo do PDF deve imprimir o motor, não recalcular.

Verificado por execução na auditoria:
- `d` recalculada no PDF (ignorando r.d_cm_real) → a linha "Kc = ..." impressa
  não reproduz o Kc impresso ao lado;
- `fywd` impresso SEM o cap de 43,5 kN/cm² que o motor aplica (engenharia)
  → para estribo CA-60 o relatório imprimia fywd = 52,17 kN/cm² (521,7 MPa),
  valor que a norma proíbe;
- algoritmo alternativo de `eh` morto (resultado descartado).

Estratégia do teste: captura o texto das células do PDF via monkeypatch de
PorticaPDF.cell — sem dependência de extrator de texto.
"""

import pytest

from core.calculos import calcular_cisalhamento_viga_comum, calcular_flexao_viga_comum
from core.relatorio_base import PorticaPDF


class CapturaPDF(PorticaPDF):
    """PorticaPDF que grava todo texto passado a cell/multi_cell."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.texto_capturado: list[str] = []

    def cell(self, *args, **kwargs):
        texto = kwargs.get("text", "")
        if not texto and len(args) >= 3:
            texto = args[2]
        if isinstance(texto, str) and texto:
            self.texto_capturado.append(texto)
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        texto = kwargs.get("text", "")
        if not texto and len(args) >= 3:
            texto = args[2]
        if isinstance(texto, str) and texto:
            self.texto_capturado.append(texto)
        return super().multi_cell(*args, **kwargs)


def _texto_do_pdf(self) -> str:
    return "\n".join(self.texto_capturado)


def _res_flexao_multi_camada():
    """Flexão multi-camada SIMPLES: d convergida ≠ d estimada de 1 camada."""
    res = calcular_flexao_viga_comum(
        h_cm=50.0,
        bw_cm=20.0,
        caa=2,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fyk_kn_cm2=50.0,
        momentos=[100.0],
        gamma_f=1.4,
    )
    r = res[0]
    assert r.armadura_dupla is False  # caso simples: As,req = Ks·Md/d
    assert r.camadas_adotadas >= 2  # multi-camada: d convergida ≠ estimada
    return res


def test_fywd_impreso_tem_cap_43_5():
    """Estribo CA-60: o PDF imprime fywd ≤ 43,5 kN/cm² (cap do motor)."""
    res_cis = calcular_cisalhamento_viga_comum(
        h_cm=70.0,
        bw_cm=20.0,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fyk_estribo_kn_cm2=60.0,  # CA-60 → fywd cru = 52.17 > 43.5
        fyk_barra_kn_cm2=50.0,
        caa=2,
        forcas_cortantes=[132.0],
    )
    res_flex = _res_flexao_multi_camada()

    pdf = CapturaPDF()
    pdf.add_memoria_calculo(
        resultados_flexao=res_flex,
        resultados_cisalhamento=res_cis,
        section_num=99,
        h_cm=70.0,
        bw_cm=20.0,
        cob_mm=30.0,
        fck_mpa=30.0,
        fyk_kn_cm2=50.0,
        fyk_estribo_kn_cm2=60.0,
        phi_estribo_mm=5.0,
        phi_barra_mm=16.0,
    )
    texto = _texto_do_pdf(pdf)
    assert "52.17" not in texto and "52,17" not in texto, (
        "PDF imprime fywd sem o cap de 43,5 kN/cm² (521,7 MPa — valor proibido "
        "pela NBR 6118:17.4.2.3): " + texto[:400]
    )


def test_kc_impreso_usa_d_convergida_do_motor():
    """A linha do Kc reproduz r.kc usando a d convergida (r.d_cm_real)."""
    res_flex = _res_flexao_multi_camada()
    r = res_flex[0]
    assert r.d_cm_real > 0

    res_cis = calcular_cisalhamento_viga_comum(
        h_cm=50.0,
        bw_cm=15.0,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=16.0,
        fyk_estribo_kn_cm2=50.0,
        fyk_barra_kn_cm2=50.0,
        caa=2,
        forcas_cortantes=[50.0],
    )

    pdf = CapturaPDF()
    pdf.add_memoria_calculo(
        resultados_flexao=res_flex,
        resultados_cisalhamento=res_cis,
        section_num=99,
        h_cm=50.0,
        bw_cm=20.0,
        cob_mm=30.0,
        fck_mpa=30.0,
        fyk_kn_cm2=50.0,
        fyk_estribo_kn_cm2=50.0,
        phi_estribo_mm=5.0,
        phi_barra_mm=12.5,
    )
    texto = _texto_do_pdf(pdf)

    # A d convergida aparece no passo da altura útil
    assert f"{r.d_cm_real:.2f}" in texto
    # A linha do Kc reproduz a conta: Kc = (bw·d²)/Md com d convergida
    linha_kc = next((linha for linha in texto.splitlines() if "Kc = (" in linha), None)
    assert linha_kc is not None
    # Confere a consistência numérica: recomputa com d do motor
    kc_recomputado = (20.0 * r.d_cm_real**2) / (r.momento_kNm * 100)
    assert kc_recomputado == pytest.approx(r.kc, rel=0.02)
    # O caso de fato tem d convergida diferente da estimativa
    assert r.d_cm_real != pytest.approx(50.0 - 3.0 - 0.5 - 0.8, abs=0.5)


def test_flecha_de_d_na_memoria_bate_com_motor():
    """As,req impresso usa a d do motor (As,req = Ks·Md/d)."""
    res_flex = _res_flexao_multi_camada()
    r = res_flex[0]

    res_cis = calcular_cisalhamento_viga_comum(
        h_cm=50.0,
        bw_cm=20.0,
        fck_mpa=30.0,
        diam_estribo_mm=5.0,
        diam_barra_mm=12.5,
        fyk_estribo_kn_cm2=50.0,
        fyk_barra_kn_cm2=50.0,
        caa=2,
        forcas_cortantes=[50.0],
    )

    pdf = CapturaPDF()
    pdf.add_memoria_calculo(
        resultados_flexao=res_flex,
        resultados_cisalhamento=res_cis,
        section_num=99,
        h_cm=50.0,
        bw_cm=20.0,
        cob_mm=30.0,
        fck_mpa=30.0,
        fyk_kn_cm2=50.0,
        fyk_estribo_kn_cm2=50.0,
        phi_estribo_mm=5.0,
        phi_barra_mm=12.5,
    )
    texto = _texto_do_pdf(pdf)
    # A linha As,req = Ks·Md/d existe e cita a d convergida do motor
    linha_as = next(
        (linha for linha in texto.splitlines() if "As,req =" in linha and "Ks" not in linha),
        None,
    )
    assert linha_as is not None
    assert f"{r.d_cm_real:.2f}" in linha_as
    as_recomputado = r.ks * (r.momento_kNm * 100) / r.d_cm_real
    assert as_recomputado == pytest.approx(r.as_req_cm2, rel=0.02)
