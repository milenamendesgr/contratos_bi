"""Distribuição de código sem bancos, credenciais ou histórico Git."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def empacotar() -> Path:
    arquivos = [ROOT / nome for nome in (
        "main.py", "app.py", "__init__.py", "README.md", "requirements.txt",
        ".gitignore", "instalar.bat", "iniciar_contratos.bat", ".streamlit/config.toml",
    )]
    for pasta, extensao in (("modules", ".py"), ("components", ".py"), ("utils", ".py"),
                            ("queries", ".sql"), ("tests", ".py"), ("docs", ".md"), ("scripts", ".py")):
        arquivos.extend(sorted((ROOT / pasta).glob(f"*{extensao}")))
    arquivos.extend(ROOT / "config" / nome for nome in
                    ("__init__.py", "settings.py", "local_settings.example.py"))
    destino = ROOT / "contratos_bi_publico.zip"
    with ZipFile(destino, "w", ZIP_DEFLATED) as pacote:
        for arquivo in arquivos:
            pacote.write(arquivo, arquivo.relative_to(ROOT).as_posix())
    return destino


if __name__ == "__main__":
    print(empacotar())
