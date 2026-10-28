# Executando o Pórtica App

## Pré-requisitos

Python 3.10 ou superior.

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## App único

```bash
python edicoes/main.py
```

## Testes

```bash
python -m pytest tests/ -q
```

## Empacotamento

O empacotamento do executável é feito por um script de build que não é
versionado neste repositório; o binário pronto para download é publicado na
aba **Releases**.
