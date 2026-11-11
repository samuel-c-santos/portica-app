"""Formatação numérica única em português do Brasil (pt-BR) compartilhada entre UI e PDF.

EP-05.2: vírgula decimal, separador de milhar opcional, casas por grandeza,
unidade e espaçamento fino.
"""

from __future__ import annotations

from typing import Any

# Casas decimais e unidade padrão por grandeza de engenharia estrutural
GRANDEZAS: dict[str, tuple[int, str]] = {
    "area": (2, "cm²"),
    "as": (2, "cm²"),
    "cm2": (2, "cm²"),
    "taxa": (2, "cm²/m"),
    "asw_s": (2, "cm²/m"),
    "comprimento_m": (2, "m"),
    "m": (2, "m"),
    "comprimento_cm": (1, "cm"),
    "cm": (1, "cm"),
    "espacamento_cm": (0, "cm"),
    "flecha_cm": (2, "cm"),
    "fissura_mm": (2, "mm"),
    "fissura_lim_mm": (1, "mm"),
    "mm": (1, "mm"),
    "momento": (2, "kN·m"),
    "momento_1": (1, "kN·m"),
    "cortante": (1, "kN"),
    "cortante_2": (2, "kN"),
    "tensao": (0, "MPa"),
    "inercia": (0, "cm⁴"),
    "mr_kncm": (1, "kN·cm"),
    "kc": (2, ""),
    "bx": (3, ""),
    "ks": (3, ""),
}


def fmt_num(
    valor: Any,
    casas: int = 2,
    *,
    sinal: bool = False,
    milhar: bool = True,
    fallback: str = "—",
    unidade: str = "",
    espaco: str = " ",
) -> str:
    """Formata um número no padrão pt-BR (vírgula decimal e ponto de milhar)."""
    if valor is None:
        return fallback
    try:
        num = float(valor)
        sep = "," if milhar else ""
        sign = "+" if sinal else ""
        spec = f"{sign}{sep}.{casas}f"
        s = format(num, spec)
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(valor)
    if unidade:
        return f"{s}{espaco}{unidade}"
    return s


def fmt_grandeza(
    valor: Any,
    grandeza: str,
    *,
    sinal: bool = False,
    milhar: bool = True,
    fallback: str = "—",
    incluir_unidade: bool = True,
    espaco: str = " ",
) -> str:
    """Formata um número segundo as casas decimais e unidade padrão da grandeza."""
    casas, unidade = GRANDEZAS.get(grandeza, (2, ""))
    return fmt_num(
        valor,
        casas=casas,
        sinal=sinal,
        milhar=milhar,
        fallback=fallback,
        unidade=unidade if incluir_unidade else "",
        espaco=espaco,
    )


def fmt_diam(
    d_mm: Any,
    *,
    prefixo: str = "",
    unidade: str = "",
    espaco: str = " ",
    fallback: str = "—",
) -> str:
    """Formata bitola comercial em mm (ex.: 5 -> '5', 6.3 -> '6,3', 12.5 -> '12,5', 16.0 -> '16')."""
    if d_mm is None:
        return fallback
    try:
        s = f"{float(d_mm):g}".replace(".", ",")
    except (TypeError, ValueError):
        s = str(d_mm)
    out = f"{prefixo}{s}" if prefixo else s
    if unidade:
        return f"{out}{espaco}{unidade}"
    return out


# Aliases diretos compatíveis com core/relatorio_base.py
def _n(valor: Any, casas: int = 2, fallback: str = "—") -> str:
    return fmt_num(valor, casas=casas, milhar=True, fallback=fallback)


def _diam(d_mm: Any) -> str:
    return fmt_diam(d_mm)


__all__ = [
    "GRANDEZAS",
    "_diam",
    "_n",
    "fmt_diam",
    "fmt_grandeza",
    "fmt_num",
]
