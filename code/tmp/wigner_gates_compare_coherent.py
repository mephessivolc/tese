# -*- coding: utf-8 -*-
"""
Gera figuras da função de Wigner para:
- Deslocamento (gaussiana)
- Compressão (gaussiana)
- Divisor de feixe (gaussiana, 2 modos; plota apenas o modo 0)
- Rotação em pi/4 (gaussiana)
- Fase cúbica (não gaussiana)
- Kerr (não gaussiana)

Formato das figuras:
- painel esquerdo: estado inicial
- painel direito: estado após aplicar a porta
- em cada painel: superfície 3D + projeção de curva de nível no plano inferior

Saída:
- 6 arquivos PNG na pasta "figuras_wigner"
"""

# import os
# import sys
# import types
# from pathlib import Path

# # --------------------------------------------------
# # Ambiente robusto para Matplotlib em servidor/headless
# # --------------------------------------------------
# BASE_DIR = Path(__file__).resolve().parent
# MPL_DIR = BASE_DIR / ".mplconfig"
# MPL_DIR.mkdir(parents=True, exist_ok=True)

# os.environ["MPLCONFIGDIR"] = str(MPL_DIR)
# os.environ["MPLBACKEND"] = "Agg"

# # --------------------------------------------------
# # Compatibilidade opcional para ambientes com problema em pkg_resources
# # --------------------------------------------------
# try:
#     import pkg_resources  # noqa: F401
# except ModuleNotFoundError:
#     import types
#     import importlib

#     pkg_resources = types.ModuleType("pkg_resources")

#     def resource_filename(package_name, resource_name):
#         package = importlib.import_module(package_name)
#         package_dir = Path(package.__file__).resolve().parent
#         return str(package_dir / resource_name)

#     pkg_resources.resource_filename = resource_filename
#     sys.modules["pkg_resources"] = pkg_resources

# # --------------------------------------------------
# # Imports principais
# # --------------------------------------------------
# import numpy as np
# import matplotlib
# matplotlib.use("Agg", force=True)
# import matplotlib.pyplot as plt
# import scipy.integrate

# # Compatibilidade em alguns ambientes
# if not hasattr(scipy.integrate, "simps") and hasattr(scipy.integrate, "simpson"):
#     scipy.integrate.simps = scipy.integrate.simpson

# import strawberryfields as sf
# from strawberryfields.ops import Dgate, Sgate, BSgate, Rgate, Vgate, Kgate

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MPL_DIR = BASE_DIR / ".mplconfig"
MPL_DIR.mkdir(parents=True, exist_ok=True)

os.environ["MPLCONFIGDIR"] = str(MPL_DIR)
os.environ["MPLBACKEND"] = "Agg"

# força cache do Numba para um diretório gravável
NUMBA_DIR = Path("/tmp/numba_cache")
NUMBA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["NUMBA_CACHE_DIR"] = str(NUMBA_DIR)

try:
    import pkg_resources  # noqa: F401
except ModuleNotFoundError:
    import types
    import importlib

    pkg_resources = types.ModuleType("pkg_resources")

    def resource_filename(package_name, resource_name):
        package = importlib.import_module(package_name)
        package_dir = Path(package.__file__).resolve().parent
        return str(package_dir / resource_name)

    pkg_resources.resource_filename = resource_filename
    sys.modules["pkg_resources"] = pkg_resources

import numpy as np
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import scipy.integrate

if not hasattr(scipy.integrate, "simps") and hasattr(scipy.integrate, "simpson"):
    scipy.integrate.simps = scipy.integrate.simpson

import strawberryfields as sf
from strawberryfields.ops import Dgate, Sgate, BSgate, Rgate, Vgate, Kgate, Fock

# --------------------------------------------------
# Configurações globais
# --------------------------------------------------
OUTPUT_DIR = BASE_DIR / "figuras_wigner"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Estado coerente de referência |alpha>
ALPHA_R = 2.5
ALPHA_PHI = np.pi / 6  # fase do deslocamento que cria o estado coerente

# Parâmetros de exemplo das portas
GATE_SPECS = [
    {
        "key": "deslocamento",
        "title": r"Deslocamento $D(3.0, \pi/2)$",
        "num_modes": 1,
        "plot_mode": 0,
        "prepare_state": lambda q, n: prepare_reference_state(q, n),
        "apply_gate": lambda q: Dgate(3.0, np.pi / 2) | q[0],
    },
    {
        "key": "compressao",
        "title": r"Compressao $S(1.0)$",
        "num_modes": 1,
        "plot_mode": 0,
        "prepare_state": lambda q, n: prepare_reference_state(q, n),
        "apply_gate": lambda q: Sgate(1.0, 0.0) | q[0],
    },
    # {
    #     "key": "divisor_de_feixe",
    #     "title": r"Divisor de feixe $BS(\pi/4, 0)$",
    #     "num_modes": 2,
    #     "plot_mode": 1,
    #     "prepare_state": lambda q, n: prepare_reference_state_bs(q),
    #     "apply_gate": lambda q: BSgate(np.pi / 4, 0.0) | (q[0], q[1]),
    # },
    {
        "key": "divisor_de_feixe_fock10",
        "title": r"Divisor de feixe em $|1,0\rangle$",
        "num_modes": 2,
        "plot_mode": 1,  # ou 1
        "prepare_state": lambda q, n: prepare_fock10(q, n),
        "apply_gate": lambda q: BSgate(np.pi / 4, 0.0) | (q[0], q[1]),
    },
    {
        "key": "rotacao_pi_4",
        "title": r"Rotacao $R(\pi/2)$",
        "num_modes": 1,
        "plot_mode": 0,
        "prepare_state": lambda q, n: prepare_reference_state(q, n),
        "apply_gate": lambda q: Rgate(np.pi / 2) | q[0],
    },
    {
        "key": "fase_cubica",
        "title": r"Fase cubica $V(0.18)$",
        "num_modes": 1,
        "plot_mode": 0,
        "prepare_state": lambda q, n: prepare_reference_state(q, n),
        "apply_gate": lambda q: Vgate(0.18) | q[0],
    },
    {
        "key": "kerr",
        "title": r"Kerr $K(0.25)$",
        "num_modes": 1,
        "plot_mode": 0,
        "prepare_state": lambda q, n: prepare_reference_state(q, n),
        "apply_gate": lambda q: Kgate(0.25) | q[0],
    },
]

# Grade da fase
X_MIN, X_MAX = -10.0, 10.0
P_MIN, P_MAX = -10.0, 10.0
N_GRID = 450

xvec = np.linspace(X_MIN, X_MAX, N_GRID)
pvec = np.linspace(P_MIN, P_MAX, N_GRID)
X, P = np.meshgrid(xvec, pvec)

# Backend Fock: necessário para as não gaussianas e suficiente para todas
CUTOFF_DIM = 60

# Estilo da figura
FIGSIZE = (12.5, 5.0)
DPI = 300
CMAP = "RdYlBu_r"
ELEV = 24
AZIM = 35

# --------------------------------------------------
# Funções auxiliares
# --------------------------------------------------

def prepare_fock10(q, n):
    Fock(1) | q[0]
    # q[1] fica no vácuo

def prepare_reference_state(q, num_modes):
    """
    Prepara o mesmo estado coerente de referência em todos os casos.
    Para BSgate, o modo 0 recebe o estado coerente e o modo 1 fica em vácuo.
    """
    Dgate(ALPHA_R, ALPHA_PHI) | q[0]
    # q[1], se existir, permanece no vácuo

def run_program_and_get_wigner(num_modes, plot_mode, prepare_state, apply_gate=None):
    """
    Retorna a função de Wigner antes e depois da aplicação da porta.
    """

    # Estado inicial
    prog_before = sf.Program(num_modes)
    with prog_before.context as q_before:
        prepare_state(q_before, num_modes)

    eng_before = sf.Engine("fock", backend_options={"cutoff_dim": CUTOFF_DIM})
    state_before = eng_before.run(prog_before).state
    W_before = state_before.wigner(mode=plot_mode, xvec=xvec, pvec=pvec)

    # Estado após a porta
    prog_after = sf.Program(num_modes)
    with prog_after.context as q_after:
        prepare_state(q_after, num_modes)
        if apply_gate is not None:
            apply_gate(q_after)

    eng_after = sf.Engine("fock", backend_options={"cutoff_dim": CUTOFF_DIM})
    state_after = eng_after.run(prog_after).state
    W_after = state_after.wigner(mode=plot_mode, xvec=xvec, pvec=pvec)

    return W_before, W_after

def draw_panel(ax, W, title, global_vmin, global_vmax, zoffset):
    """
    Desenha um painel no estilo:
    - superfície 3D
    - projeção contourf no plano inferior
    """
    ax.plot_surface(
        X, P, W,
        cmap=CMAP,
        vmin=global_vmin,
        vmax=global_vmax,
        linewidth=0.1,
        edgecolor="#00A8A8",
        antialiased=True,
        rstride=10, 
        cstride=10
    )

    ax.contourf(
        X, P, W,
        zdir="z",
        offset=zoffset,
        levels=np.linspace(global_vmin, global_vmax, 100),
        cmap=CMAP,
        vmin=global_vmin,
        vmax=global_vmax,
    )

    ax.contour(
        X, P, W,
        zdir="z",
        offset=zoffset,
        levels=12,
        colors="k",
        linewidths=0.35,
        alpha=0.45,
    )

    ax.set_title(title, pad=8, fontsize=11)
    ax.set_xlabel("x", labelpad=6)
    ax.set_ylabel("p", labelpad=6)
    ax.set_zlabel("W", labelpad=4)

    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(P_MIN, P_MAX)

    ax.set_xticks(np.arange(X_MIN, X_MAX + 0.1, 5.0))
    ax.set_yticks(np.arange(P_MIN, P_MAX + 0.1, 5.0))
    ax.set_zticks(np.arange(-0.10, 0.11, 0.05))

    ax.set_zlim(zoffset, global_vmax * 1.05)
    ax.view_init(elev=ELEV, azim=AZIM)
    ax.grid(True)


def plot_gate_pair(W_before, W_after, gate_title, filename, global_vmin, global_vmax):
    """
    Gera a figura lado a lado:
    - esquerda: estado inicial
    - direita: após a porta
    """
    zoffset = global_vmin - 0.35 * (global_vmax - global_vmin)

    fig = plt.figure(figsize=FIGSIZE)

    ax1 = fig.add_subplot(1, 2, 1, projection="3d")
    ax2 = fig.add_subplot(1, 2, 2, projection="3d")

    draw_panel(ax1, W_before, "Estado inicial", global_vmin, global_vmax, zoffset)
    draw_panel(ax2, W_after, "Estado resultante", global_vmin, global_vmax, zoffset)

    fig.suptitle(gate_title, fontsize=14, y=0.97)

    plt.tight_layout()
    plt.savefig(filename, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

# --------------------------------------------------
# Programa principal
# --------------------------------------------------
def main():
    results = []

    # 1) calcula todas as funções de Wigner
    for spec in GATE_SPECS:
        W_before, W_after = run_program_and_get_wigner(
            num_modes=spec["num_modes"],
            plot_mode=spec["plot_mode"],
            prepare_state=spec["prepare_state"],
            apply_gate=spec["apply_gate"],
        )

        results.append(
            {
                "key": spec["key"],
                "title": spec["title"],
                "W_before": W_before,
                "W_after": W_after,
            }
        )

    # 2) escala global única para TODAS as figuras
    all_arrays = []
    for item in results:
        all_arrays.append(item["W_before"])
        all_arrays.append(item["W_after"])

    global_vmin = min(float(np.min(a)) for a in all_arrays)
    global_vmax = max(float(np.max(a)) for a in all_arrays)

    # 3) gera e salva cada figura
    for item in results:
        out_file = OUTPUT_DIR / f"wigner_{item['key']}.png"
        plot_gate_pair(
            W_before=item["W_before"],
            W_after=item["W_after"],
            gate_title=item["title"],
            filename=out_file,
            global_vmin=global_vmin,
            global_vmax=global_vmax,
        )
        print(f"Figura salva em: {out_file}")

    print("\nConcluido.")


if __name__ == "__main__":
    main()