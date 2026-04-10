import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import scipy.integrate
scipy.integrate.simps = scipy.integrate.simpson

import strawberryfields as sf
from strawberryfields.ops import Sgate

# --------------------------------------------------
# Quantum circuit
# --------------------------------------------------

prog = sf.Program(1)

with prog.context as q:
    Sgate(0.8) | q[0]



eng = sf.Engine("fock", backend_options={"cutoff_dim": 5})
state = eng.run(prog).state

# --------------------------------------------------
# Phase-space grid
# --------------------------------------------------
xvec = np.linspace(-5, 5, 300)
pvec = np.linspace(-5, 5, 300)
W = state.wigner(mode=0, xvec=xvec, pvec=pvec)

# Meshgrid for 3D plot
X, P = np.meshgrid(xvec, pvec)

# --------------------------------------------------
# 2D plot
# --------------------------------------------------
plt.figure(figsize=(6, 5))
plt.contourf(X, P, W, levels=100)
plt.xlabel("x")
plt.ylabel("p")
plt.colorbar(label="W(x,p)")
plt.tight_layout()
plt.show()

# --------------------------------------------------
# 3D surface plot
# --------------------------------------------------
fig = plt.figure(figsize=(8, 6))
ax = fig.add_subplot(111, projection="3d")

surf = ax.plot_surface(
    X,
    P,
    W,
    cmap="RdBu_r",
    linewidth=0,
    antialiased=True
)

ax.set_xlabel("x")
ax.set_ylabel("p")
ax.set_zlabel("W(x,p)")

fig.colorbar(surf, shrink=0.7, aspect=15, label="W(x,p)")
plt.tight_layout()
plt.savefig("fig.png")
plt.show()