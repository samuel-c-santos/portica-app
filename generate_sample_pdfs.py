import os
import sys

# Ensure the root of the project is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.relatorio_base import gerar_relatorio_viga_comum, gerar_relatorio_viga_t
from core.calculos import (
    calcular_flexao_viga_comum,
    calcular_flexao_viga_t,
    calcular_cisalhamento_viga_comum
)

viga_comum = {
    "h_cm": 70,
    "bw_cm": 20,
    "caa": 2,
    "fck_mpa": 30,
    "diam_estribo_mm": 5.0,
    "diam_barra_mm": 16.0,
    "fyk_mpa": 50.0,
    "fyk_estribo_mpa": 50.0,
    "gamma_f": 1.4,
}

viga_t = {
    "h_cm": 70,
    "bw_cm": 20,
    "bf_cm": 60,
    "hf_cm": 12,
    "caa": 2,
    "fck_mpa": 30,
    "diam_estribo_mm": 5.0,
    "diam_barra_mm": 16.0,
    "fyk_mpa": 50.0,
    "b1esq_cm": 20,
    "b1dir_cm": 20,
    "gamma_f": 1.4,
}

momentos = [96.9, -96.9, 50.0]
cortantes = [132.0, 48.0, 3.0, -123.0]

# Flexão e cisalhamento retangular
res_flex_comum = calcular_flexao_viga_comum(
    h_cm=viga_comum["h_cm"],
    bw_cm=viga_comum["bw_cm"],
    caa=viga_comum["caa"],
    fck_mpa=viga_comum["fck_mpa"],
    diam_estribo_mm=viga_comum["diam_estribo_mm"],
    diam_barra_mm=viga_comum["diam_barra_mm"],
    fyk_mpa=viga_comum["fyk_mpa"],
    momentos=momentos,
    gamma_f=viga_comum["gamma_f"],
)

res_cis_comum = calcular_cisalhamento_viga_comum(
    h_cm=viga_comum["h_cm"],
    bw_cm=viga_comum["bw_cm"],
    fck_mpa=viga_comum["fck_mpa"],
    diam_estribo_mm=viga_comum["diam_estribo_mm"],
    diam_barra_mm=viga_comum["diam_barra_mm"],
    fyk_estribo_mpa=viga_comum["fyk_estribo_mpa"],
    fyk_barra_mpa=viga_comum["fyk_mpa"],
    caa=viga_comum["caa"],
    forcas_cortantes=cortantes,
    gamma_f=viga_comum["gamma_f"],
)

# Flexão e cisalhamento T
res_flex_t = calcular_flexao_viga_t(
    h_cm=viga_t["h_cm"],
    bw_cm=viga_t["bw_cm"],
    bf_cm=viga_t["bf_cm"],
    hf_cm=viga_t["hf_cm"],
    caa=viga_t["caa"],
    fck_mpa=viga_t["fck_mpa"],
    diam_estribo_mm=viga_t["diam_estribo_mm"],
    diam_barra_mm=viga_t["diam_barra_mm"],
    fyk_mpa=viga_t["fyk_mpa"],
    momentos=momentos,
    b1esq_cm=viga_t["b1esq_cm"],
    b1dir_cm=viga_t["b1dir_cm"],
    gamma_f=viga_t["gamma_f"],
)

res_cis_t = calcular_cisalhamento_viga_comum(
    h_cm=viga_t["h_cm"],
    bw_cm=viga_t["bw_cm"],
    fck_mpa=viga_t["fck_mpa"],
    diam_estribo_mm=viga_t["diam_estribo_mm"],
    diam_barra_mm=viga_t["diam_barra_mm"],
    fyk_estribo_mpa=50.0,
    fyk_barra_mpa=viga_t["fyk_mpa"],
    caa=viga_t["caa"],
    forcas_cortantes=cortantes,
    gamma_f=viga_t["gamma_f"],
)

artifact_dir = r"C:\Users\usuario\.gemini\antigravity-cli\brain\e6ecb6ce-b4e5-4cfd-8c76-9d6a2bbedcd3"
path_comum = os.path.join(artifact_dir, "viga_retangular_exemplo.pdf")
path_t = os.path.join(artifact_dir, "viga_t_exemplo.pdf")

print("Gerando PDF retangular...")
gerar_relatorio_viga_comum(
    path_comum,
    nome_viga="Viga Retangular V1",
    h_cm=viga_comum["h_cm"],
    bw_cm=viga_comum["bw_cm"],
    caa=viga_comum["caa"],
    fck_mpa=viga_comum["fck_mpa"],
    fyk_mpa=viga_comum["fyk_mpa"],
    fyk_estribo_mpa=viga_comum["fyk_estribo_mpa"],
    phi_estribo_mm=viga_comum["diam_estribo_mm"],
    phi_barra_mm=viga_comum["diam_barra_mm"],
    resultados_flexao=res_flex_comum,
    resultados_cisalhamento=res_cis_comum,
    nome_engenheiro="Samuel Santos",
    crea="123456/D-SP",
)

print("Gerando PDF Viga T...")
gerar_relatorio_viga_t(
    path_t,
    nome_viga="Viga T V2",
    h_cm=viga_t["h_cm"],
    bw_cm=viga_t["bw_cm"],
    bf_cm=viga_t["bf_cm"],
    hf_cm=viga_t["hf_cm"],
    caa=viga_t["caa"],
    fck_mpa=viga_t["fck_mpa"],
    fyk_mpa=viga_t["fyk_mpa"],
    fyk_estribo_mpa=50.0,
    phi_estribo_mm=viga_t["diam_estribo_mm"],
    phi_barra_mm=viga_t["diam_barra_mm"],
    resultados_flexao=res_flex_t,
    resultados_cisalhamento=res_cis_t,
    nome_engenheiro="Samuel Santos",
    crea="123456/D-SP",
)
print("Concluído!")
