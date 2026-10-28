"""
Pórtica App - Gerenciamento de projetos recentes.
Persiste até MAX_RECENT caminhos de projetos .ptc em um arquivo JSON local.
"""

import json
import os
from datetime import datetime

MAX_RECENT = 10
_RECENT_FILE = os.path.join(
    os.path.expanduser("~"), ".portica_recent.json"
)


def _load_raw() -> list[dict]:
    """Carrega a lista bruta do disco (pode ser vazia se nao existir)."""
    try:
        with open(_RECENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return []


def _save_raw(entries: list[dict]) -> None:
    try:
        with open(_RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def get_recent() -> list[dict]:
    """
    Retorna lista de projetos recentes (mais novo primeiro).
    Cada item: {"path": str, "name": str, "accessed": str (ISO)}
    Entradas cujo arquivo nao existe mais sao filtradas.
    """
    raw = _load_raw()
    valid = [e for e in raw if os.path.isfile(e.get("path", ""))]
    return valid


def add_recent(path: str, modo: str = None) -> None:
    """Adiciona (ou move para o topo) um projeto na lista de recentes."""
    path = os.path.abspath(path)
    raw = _load_raw()

    # Remove entrada anterior com mesmo caminho
    raw = [e for e in raw if e.get("path") != path]

    # Se modo não for especificado, tenta ler do arquivo
    if not modo:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                modo = data.get("modo", "comum")
        except Exception:
            modo = "comum"

    entry = {
        "path": path,
        "name": os.path.splitext(os.path.basename(path))[0],
        "accessed": datetime.now().isoformat(timespec="seconds"),
        "modo": modo,
    }
    raw.insert(0, entry)
    raw = raw[:MAX_RECENT]
    _save_raw(raw)


def remove_recent(path: str) -> None:
    """Remove um projeto especifico da lista de recentes."""
    path = os.path.abspath(path)
    raw = _load_raw()
    raw = [e for e in raw if e.get("path") != path]
    _save_raw(raw)
