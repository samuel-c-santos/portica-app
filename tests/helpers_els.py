"""
Helper com dados sintéticos bi-apoiados para os testes de ELS (EP-01.6).

O sample `samples/test_deformacoes.txt` não é bi-apoiado (momento ≠ 0 nas
extremidades) — desde o EP-01.6 o motor ELS recusa modelos não bi-apoiados.
Estes helpers geram uma viga bi-apoiada com carga uniforme:
    M(x) = q·x·(L − x)/2,   M_max = q·L²/8 = MMAX em x = L/2
"""

L_M = 7.5
MMAX = 200.0  # kN·m — acima do Mr de 20×70 (≈71 kN·m) para exercitar estádio II
Q_KN_M = 8.0 * MMAX / L_M**2


def momentos_biapoiados(n: int = 76) -> list[tuple[float, float]]:
    pts = []
    for i in range(n):
        x = L_M * i / (n - 1)
        m = Q_KN_M * x * (L_M - x) / 2.0
        pts.append((round(x, 4), m))
    # M = 0 exato nas extremidades (apoios)
    pts[0] = (0.0, 0.0)
    pts[-1] = (L_M, 0.0)
    return pts


def deformacoes_biapoiadas(n: int = 76) -> list[tuple[float, float, float, float]]:
    """(x, d, θ, κ): d = 0 nas extremidades (apoios bi-apoiados)."""
    pts = []
    for i in range(n):
        x = L_M * i / (n - 1)
        d = 0.0 if i in (0, n - 1) else 1e-6
        pts.append((round(x, 4), d, 0.0, 0.0))
    return pts
