"""Plot stored four-bar positional error; does not run Newton."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np

from analyze_experiments import geometry

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p/"manifests/source-lock.json").exists())


def main():
    initial = json.loads((HERE/"analysis.json").read_text())
    refined = json.loads((HERE/"refinement-analysis.json").read_text())
    cases = [initial["cases"][1]] + refined["cases"]
    protocols = [json.loads((HERE/p).read_text()) for p in ("protocol.json","protocol-refinement.json")]
    fig, axes = plt.subplots(1,2,figsize=(12,4.8),constrained_layout=True)
    table = []
    for variant,color in (("A","#ca6702"),("B","#0077b6")):
        steps, maxima = [], []
        for i,case in enumerate(cases):
            entry = next(r for r in case["runs"] if r["variant"] == variant and r["repeat"] == 1)
            data = dict(np.load(ROOT/entry["raw_file"],allow_pickle=False))
            protocol = protocols[0 if i == 0 else 1]
            dt = float(data["time"][1]-data["time"][0])
            geo = geometry(data,protocol,variant=="B")
            retained = geo["all_gaps"] if variant=="B" else geo["all_gaps"][:,:3]
            fixed = np.linalg.norm(data["body_q"][:,0,:3]-np.array(protocol["scene"]["body_centers_m"])[0],axis=1)
            max_gap = np.maximum(retained.max(axis=1),fixed)*1000
            steps.append(dt*1000)
            maxima.append(float(max_gap.max()))
            axes[1].plot(data["time"],max_gap,color=color,linestyle=["-","--",":"][i],label=f"{variant}, dt=1/{round(1/dt)}s")
            table.append({"variant":variant,"dt_seconds":dt,"max_retained_gap_mm":float(max_gap.max()),"case_status":case["status"]})
        axes[0].loglog(steps,maxima,"o-",color=color,label="A: open chain" if variant=="A" else "B: closed loop")
    for ax in axes:
        ax.axhline(.5,color="#b00020",linestyle="--",linewidth=1,label="Frozen 0.5 mm gate")
        ax.grid(alpha=.25,which="both")
        ax.set_ylabel("Maximum retained-joint anchor gap (mm)")
        ax.legend(fontsize=8)
    axes[0].set_xlabel("Timestep (ms), log scale")
    axes[0].set_xticks([1000/3840,1000/960,1000/240], ["0.2604", "1.0417", "4.1667"])
    axes[0].xaxis.set_minor_formatter(NullFormatter())
    axes[0].set_title("Fixed gate across timestep refinement")
    axes[1].set_xlabel("Simulation time (s)")
    axes[1].set_title("Saved trajectory errors (repeat 1)")
    fig.suptitle("Kamino PADMM CPU | fixed-base four-bar | 0.5 s | no contacts")
    fig.savefig(HERE/"timestep-refinement.png",dpi=170)
    fig.savefig(HERE/"timestep-refinement.svg")
    plt.close(fig)
    (HERE/"timestep-trend.json").write_text(json.dumps({"points":table,"scope":"Trend only; no integrator convergence order or cross-backend performance claim."},indent=2)+"\n")


if __name__ == "__main__":
    main()
