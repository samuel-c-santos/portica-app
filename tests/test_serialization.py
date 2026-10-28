import os
import tempfile
import pytest
import json
from ui import recent_projects

@pytest.fixture(autouse=True)
def mock_recent_file(monkeypatch):
    # Cria um arquivo temporário e faz o mock de recent_projects._RECENT_FILE
    temp_fd, temp_path = tempfile.mkstemp(suffix=".json")
    os.close(temp_fd)
    # Remove para começar limpo
    if os.path.exists(temp_path):
        os.remove(temp_path)
    monkeypatch.setattr(recent_projects, "_RECENT_FILE", temp_path)
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)

def test_add_and_get_recent():
    # Cria arquivos temporários para simular projetos válidos (get_recent filtra arquivos inexistentes)
    temp_fd1, path1 = tempfile.mkstemp(suffix=".ptc")
    temp_fd2, path2 = tempfile.mkstemp(suffix=".ptc")
    os.close(temp_fd1)
    os.close(temp_fd2)

    try:
        recent_projects.add_recent(path1, modo="comum")
        recent_projects.add_recent(path2, modo="t")

        recent_list = recent_projects.get_recent()
        assert len(recent_list) == 2
        
        # O mais recente fica no topo
        assert recent_list[0]["path"] == os.path.abspath(path2)
        assert recent_list[0]["modo"] == "t"
        
        assert recent_list[1]["path"] == os.path.abspath(path1)
        assert recent_list[1]["modo"] == "comum"
        
        # Testa a remoção
        recent_projects.remove_recent(path1)
        recent_list = recent_projects.get_recent()
        assert len(recent_list) == 1
        assert recent_list[0]["path"] == os.path.abspath(path2)
    finally:
        if os.path.exists(path1):
            os.remove(path1)
        if os.path.exists(path2):
            os.remove(path2)

def test_ptc_json_structure():
    # Valida estrutura do dicionário de persistência do projeto
    proj_data = {
        "viga_nome": "Viga Teste",
        "modo": "comum",
        "geometria": {
            "h_cm": "50",
            "bw_cm": "20",
        },
        "materiais": {
            "caa": "2",
            "fck_mpa": "30",
        },
    }
    serialized = json.dumps(proj_data, indent=2, ensure_ascii=False)
    loaded = json.loads(serialized)
    assert loaded["viga_nome"] == "Viga Teste"
    assert loaded["modo"] == "comum"
    assert loaded["geometria"]["h_cm"] == "50"
