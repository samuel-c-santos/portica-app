"""
Pórtica App - eixo de fonte de entrada da viga (manual | FTOOL).

Decisão D2 (planejamento open source — documento interno mantido FORA deste
repositório, em `_interno_portica/docs/planejamento-open-source.md`): o FTOOL
é uma *fonte de entrada* opcional, não um "modo" rival de tela. O eixo `modo`
(retangular | T) continua existindo e é independente deste eixo.

Este módulo concentra a lógica pura (sem UI) para que a mesma regra seja
usada pela tela e pelos testes:

- `manual`  -> entrada digitada na tabela de trechos (padrão);
- `ftool`   -> entrada importada dos arquivos .txt do FTOOL.

Retrocompatibilidade: projetos .ptc gravados antes da existência do eixo
`são carregados como "manual"`.
"""

from collections.abc import MutableMapping

# ── Valores do eixo "entrada" ───────────────────────────────────────────────
ENTRADA_MANUAL = "manual"
ENTRADA_FTOOL = "ftool"
ENTRADAS_VALIDAS = (ENTRADA_MANUAL, ENTRADA_FTOOL)

# ─── Edições de origem (campo legado dos projetos .ptc) ───────────────────
# Antes da unificação (v1.0.0) o app existia em duas edições: a gratuita
# ("standard") e a paga (valor abaixo, grafado de forma quebrada para não
# reintroduzir no repositório a nomenclatura da arquitetura descartada —
# roadmap EP-00.4). Projetos antigos continuam carregando normalmente.
EDICAO_LEGADA_GRATUITA = "standard"
EDICAO_LEGADA_PAGA = "premium"
EDICAO_ATUAL = "portica"


def normalizar_entrada(valor, padrao=ENTRADA_MANUAL):
    """Normaliza um valor de entrada para um dos valores conhecidos.

    Valores desconhecidos (ou tipos inválidos) caem no `padrao`.
    """
    if not isinstance(valor, str):
        return padrao
    v = valor.strip().lower()
    return v if v in ENTRADAS_VALIDAS else padrao


def entrada_de_projeto(proj_data):
    """Fonte de entrada gravada em um projeto .ptc.

    Projetos antigos (sem a chave "entrada") assumem entrada manual.
    """
    if not isinstance(proj_data, dict):
        return ENTRADA_MANUAL
    return normalizar_entrada(proj_data.get("entrada"))


def entrada_para_salvar(state):
    """Valor da chave "entrada" a ser gravado no .ptc."""
    if not isinstance(state, MutableMapping):
        return ENTRADA_MANUAL
    return normalizar_entrada(state.get("entrada"))


def aplicar_entrada_projeto(state, proj_data):
    """Aplica no `state` a fonte de entrada contida no .ptc e devolve o valor."""
    entrada = entrada_de_projeto(proj_data)
    if isinstance(state, MutableMapping):
        state["entrada"] = entrada
    return entrada


def ftool_visivel(entrada):
    """O painel FTOOL só aparece quando a fonte de entrada é o FTOOL."""
    return normalizar_entrada(entrada) == ENTRADA_FTOOL


def edicao_aceita(edicao):
    """True para qualquer string: o campo "edicao" é histórico e não bloqueia.

    Todos os projetos .ptc carregam na edição unificada atual.
    """
    return isinstance(edicao, str)


def aviso_edicao(edicao):
    """Nota informativa sobre a edição de origem do projeto.

    Devolve None quando não há nada a comentar e nunca sinaliza bloqueio:
    todos os valores, inclusive os legados, são aceitos igualmente.
    """
    if not isinstance(edicao, str) or not edicao.strip():
        return "Projeto sem indicação de edição de origem; importado normalmente."
    e = edicao.strip().lower()
    if e in (EDICAO_LEGADA_PAGA, EDICAO_ATUAL):
        return None
    if e == EDICAO_LEGADA_GRATUITA:
        return (
            "Projeto criado no Pórtica Standard. Importado normalmente: "
            "as duas edições compartilham o mesmo formato de arquivo."
        )
    return f"Projeto criado em uma edição desconhecida ({edicao.strip()!r}). Importado normalmente."
