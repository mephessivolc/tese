from pathlib import Path
from typing import Union

# Ancora o projeto no diretório onde este arquivo get_paths.py reside
ROOT_DIR = Path(__file__).resolve().parent


def get_path(is_result: bool = False) -> Path:
    """
    Retorna o diretório base para saída de arquivos ('images' ou 'results').
    Cria a pasta automaticamente caso não exista.

    Parameters
    ----------
    is_result : bool, optional
        Se True, retorna a pasta 'results'. Caso contrário, 'images'.

    Returns
    -------
    Path
        Caminho absoluto para o diretório solicitado.
    """
    folder_name = "results" if is_result else "images"
    target_path = ROOT_DIR / folder_name
    target_path.mkdir(parents=True, exist_ok=True)

    return target_path


def get_images_path() -> Path:
    """Atalho para obter a pasta de imagens."""
    return get_path(is_result=False)


def get_results_path(subfolder: Union[str, Path] = None) -> Path:
    """
    Retorna o caminho da pasta 'results', permitindo criar subpastas
    específicas para organizar os dados da tese (ex: 'qa_qaoa', 'ca_bruteforce').

    Parameters
    ----------
    subfolder : Union[str, Path], optional
        Nome de uma subpasta dentro de 'results' (ex: 'ca_solutions' ou 'qa_qaoa/run_1').

    Returns
    -------
    Path
        Caminho absoluto para a pasta de resultados.
    """
    base_path = get_path(is_result=True)
    
    if subfolder:
        target_path = base_path / subfolder
        target_path.mkdir(parents=True, exist_ok=True)
        return target_path

    return base_path


if __name__ == "__main__":
    print("--- TESTANDO ESTRUTURA DE DIRETÓRIOS ---")

    tests = [
        ("Imagens", lambda: get_images_path()),
        ("Resultados Base", lambda: get_results_path()),
        ("Resultados (Subpasta 'teste')", lambda: get_results_path("teste")),
        ("Resultados (Subpastas Aninhadas 'qa_qaoa/run_01')", lambda: get_results_path("qa_qaoa/run_01"))
    ]

    for name, func in tests:
        try:
            path_created = func()
            print(f"[OK] {name}: {path_created}")
        except Exception as e:
            print(f"[ERRO] Falha ao criar diretório para '{name}': {e}")
            raise e

    print("---------------------------------------")
    print("Todos os diretórios de suporte foram validados com sucesso!")