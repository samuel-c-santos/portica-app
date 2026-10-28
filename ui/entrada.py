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

# ── Valores do eixo "entrada" ───────────────────────────────────────────────
ENTRADA_MANUAL = "manual"
ENTRADA_FTOOL = "ftool"
ENTRADAS_VALIDAS = (ENTRADA_MANUAL, ENTRADA_FTOOL)

# ── Edições de origem reconhecidas ──────────────────────────────────────────
EDICAO_PREMIUM = "premium"
EDICAO_STANDARD = "standard"
EDICOES_ACEITAS = (EDICAO_PREMIUM, EDICAO_STANDARD)


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
    if not isinstance(state, dict):
        return ENTRADA_MANUAL
    return normalizar_entrada(state.get("entrada"))


def aplicar_entrada_projeto(state, proj_data):
    """Aplica no `state` a fonte de entrada contida no .ptc e devolve o valor."""
    entrada = entrada_de_projeto(proj_data)
    if isinstance(state, dict):
        state["entrada"] = entrada
    return entrada


def ftool_visivel(entrada):
    """O painel FTOOL só aparece quando a fonte de entrada é o FTOOL."""
    return normalizar_entrada(entrada) == ENTRADA_FTOOL


def edicao_aceita(edicao):
    """True para as edições conhecidas (standard/premium)."""
    if not isinstance(edicao, str):
        return False
    return edicao.strip().lower() in EDICOES_ACEITAS


def aviso_edicao(edicao):
    """Nota informativa sobre a edição de origem do projeto.

    Devolve None quando não há nada a comentar (projeto "premium") e nunca
    sinaliza bloqueio: as edições standard e premium são aceitas igualmente.
    """
    if not isinstance(edicao, str) or not edicao.strip():
        return (
            "Projeto sem indicação de edição de origem; importado normalmente."
        )
    e = edicao.strip().lower()
    if e == EDICAO_PREMIUM:
        return None
    if e == EDICAO_STANDARD:
        return (
            "Projeto criado no Pórtica Standard. Importado normalmente: "
            "as duas edições compartilham o mesmo formato de arquivo."
        )
    return (
        f"Projeto criado em uma edição desconhecida ({edicao.strip()!r}). "
        "Importado normalmente."
    )
