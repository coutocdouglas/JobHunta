"""Gera dist/JobHunta/ (pasta com JobHunta.exe). Rode: python build.py"""
import os

import PyInstaller.__main__

sep = os.pathsep
PyInstaller.__main__.run([
    "launcher.py",
    "--name", "JobHunta",
    "--noconfirm", "--clean",
    "--windowed",                      # sem janela de console (ignorado fora do Windows)
    "--add-data", f"app.py{sep}.",     # o Streamlit executa este arquivo
    "--collect-all", "streamlit",
    "--copy-metadata", "streamlit",
    "--collect-all", "pypdf",
    "--hidden-import", "pandas",
    "--exclude-module", "pkg_resources",   # hook do setuptools quebra no pacote; o app não usa
])
