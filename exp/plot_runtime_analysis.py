import sys

import matplotlib.pyplot as plt

################# Matplotlib Global Conf #########################
FIG_SIZE = (15, 5)
fontsize = 27

# plt.rcParams["text.usetex"] = True
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.weight"] = "bold"
plt.rcParams["xtick.labelsize"] = fontsize - 6
plt.rcParams["ytick.labelsize"] = fontsize - 2
# plt.rcParams['ztick.labelsize'] = fontsize - 2
# plt.rcParams["xtick.major.pad"] = -1
# plt.rcParams["ytick.major.pad"] = -1
plt.rcParams["axes.labelsize"] = fontsize
plt.rcParams["axes.labelweight"] = "bold"
plt.rcParams["legend.fontsize"] = fontsize - 5
## below not working
# plt.rcParams["patch.edgecolor"] = "black"
# plt.rcParams["patch.linewidth"] = 1

################# Matplotlib Global Conf #########################

NQ = [20, 40, 60, 80, 100]

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <path-to-runtime-log-file>")
    sys.exit(1)
file_name = sys.argv[1]


res = []
with open(file_name, "r") as f:
    for line in f:
        if line.startswith("Runtime of mapper is"):
            rt = float(line.strip().split(" ")[-1])
            res.append(rt)


plt.figure(figsize=(10, 4))
plt.plot(
    NQ,
    res,
    marker="o",
    color="#E66F51",
    linewidth=3,
    label="Runtime of Mapper",
    markersize=10,
)

plt.xlabel("Number of Qubits")
plt.ylabel("Runtime (s)")
# plt.title(
#     "Runtime of Mapper Across Different Qubit Sizes", fontsize=27, fontweight="bold"
# )

plt.grid(True, linestyle="--", alpha=0.7)

plt.tight_layout()
plt.show()

plt.savefig("runtime_ctrl_fixed.pdf")
