"""Locate bundled assets, with live source files available for editable installs."""
from pathlib import Path


def data_path(relative: str) -> Path:
    package = Path(__file__).resolve().parent
    bundled = package / '_data' / relative
    if bundled.exists():
        return bundled
    root = package.parent
    if relative in {'helpers.h', 'helpers.c'}:
        return root / 'resources' / 'plugins' / 'Cpp' / relative
    return root / relative
