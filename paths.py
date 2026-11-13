"""Onde ficam os dados do usuário. Fora da pasta de instalação, para que
atualizações nunca apaguem o banco, o currículo ou as chaves."""
import os
import sys
from pathlib import Path

APP_NAME = "JobHunta"


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
    else:
        base = Path.home() / ".jobhunta"
    base.mkdir(parents=True, exist_ok=True)
    return base


def resource_dir() -> Path:
    """Pasta com os arquivos do programa (dentro do executável quando empacotado)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))
