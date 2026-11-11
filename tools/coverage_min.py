"""
EP-03.6 — Gate de cobertura de código com mínimos POR MÓDULO.

Uso no CI (após `pytest --cov=... --cov-report=json:coverage.json`):

    python tools/coverage_min.py coverage.json

Falha (exit 1) se qualquer grupo não atingir o mínimo da Tabela de metas
do ROADMAP (EP-03.6):

    core/calculos/         ≥ 90%
    core/detailing/        ≥ 90%
    ui/ftool/              ≥ 90%
    core/relatorio_base.py ≥ 70%
    ui/ (exceto ui/ftool)  ≥ 70%  — meta "após EP-04": enquanto ui/viga.py
                            não for dividido (EP-04.3), o mínimo é APENAS
                            REPORTADO, não aplicado (gate desativado
                            explicitamente aqui).

O relatório coverage.json vai para o CI como artefato.
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# (nome do grupo, prefixo de caminho, mínimo %, aplicado?)
GRUPOS = [
    ("core/calculos/", "core/calculos/", 90.0, True),
    ("core/detailing/", "core/detailing/", 90.0, True),
    ("ui/ftool/", "ui/ftool/", 90.0, True),
    ("core/relatorio_base.py", "core/relatorio_base.py", 70.0, True),
    # Meta do roadmap é "após EP-04" (ui/viga.py dividido em ui/viga/).
    # Gate desativado até lá: apenas reporta, não falha.
    ("ui/ (sem ui/ftool; meta pós-EP-04)", "ui/", 70.0, False),
]


def _grupo_do(caminho: str, prefixo: str) -> bool:
    c = caminho.replace("\\", "/")
    return c.startswith(prefixo)


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: python tools/coverage_min.py <coverage.json>")
        return 2
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    files = data["files"]

    agregados: dict[str, tuple[int, int, bool]] = {}
    for _, prefixo, _, _ in GRUPOS:
        stmts = miss = 0
        for caminho, info in files.items():
            if _grupo_do(caminho, prefixo):
                s = info["summary"]
                stmts += s["num_statements"]
                miss += s["missing_lines"]
        agregados[prefixo] = (stmts, miss, 100.0 * (stmts - miss) / stmts if stmts else 0.0)

    # ui/ sem ui/ftool: subtrai o grupo ui/ftool do agregado de ui/
    p_ui, m_ui, _ = agregados["ui/"]
    p_ft, m_ft, _ = agregados["ui/ftool/"]
    if p_ui:
        p_rest = p_ui - p_ft
        m_rest = m_ui - m_ft
        pct_rest = 100.0 * (p_rest - m_rest) / p_rest if p_rest else 0.0
    else:
        p_rest = m_rest = pct_rest = 0.0

    falhou = False
    print("┌ Gate de cobertura por módulo (EP-03.6) ─────────────────────")
    for nome, prefixo, minimo, aplicado in GRUPOS:
        if prefixo == "ui/":
            p, m, pct = p_rest, m_rest, pct_rest
        else:
            p, m, pct = agregados[prefixo]
        ok = pct >= minimo
        if aplicado and not ok:
            falhou = True
        exigencia = f"min {minimo:.0f}%" if aplicado else "informativo (pós-EP-04)"
        print(
            f"│ {nome:<28s} {pct:6.2f}%  ({p} stmts, {m} miss)  [{exigencia}] {'✓' if ok else '✗'}"
        )
        if aplicado and not ok:
            print(
                f"│   → abaixo do mínimo de {minimo:.0f}% "
                f"(faltam {m - (p - minimo * p / 100.0):.1f} linhas para cobrir)"
            )
    print("└─────────────────────────────────────────────────────────────")

    if falhou:
        print("Cobertura abaixo do mínimo exigido (EP-03.6).")
        return 1
    print("Cobertura dentro dos mínimos por módulo (EP-03.6).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
