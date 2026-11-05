"""L4DC paper figures (PMLR template): Figures 3, 4 and 5, each one row of four panels.

Usage:
    python paper/l4dc/make_figures.py --placeholder   # write synthetic data/*.json, then plot
    python paper/l4dc/make_figures.py                 # plot from paper/l4dc/data/*.json

The plotting reads only the JSON files in ``data/`` (format: see ``DATA CONTRACT`` below and
``STUDENT_PROMPT.md``). Every format decision lives in the ``FORMAT`` block, so the look is
tuned there and applies to all three figures at once. A JSON file with ``"_placeholder": true``
gets a faint "placeholder" mark in every panel.

Outputs ``figures/fig{3,4,5}.pdf`` (usetex, Computer Modern like the jmlr class), a PNG preview
of each (ghostscript), and ``figures/legend.pdf`` (the common legend alone).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "figures"

# ==================================================================================== FORMAT
TEXT_WIDTH = 6.0          # in, \textwidth of jmlr.cls with [pmlr] on letter paper
FONT_SIZE = 8             # pt, every text element (ticks, labels, titles, legend)
N_PANELS = 4

# Absolute geometry in inches. Panels are exactly square and the same size in every figure.
# A panel whose y quantity differs from its left neighbor gets a y label and the wide gap; a
# panel with the same y quantity has no y label and sits closer (narrow gap, tick labels
# only). Every figure has the pattern "one wide + two narrow gaps", so all figures are
# exactly TEXT_WIDTH wide.
MARGIN_LEFT = 0.38        # room for the y tick labels + y label of the first panel
MARGIN_RIGHT = 0.10       # half of the last x tick label sticks out
GAP_LABEL = 0.42          # y tick labels + y label of the next panel
GAP_SHARED = 0.27         # y tick labels only (same y quantity as the left neighbor)
N_LABEL_GAPS = 1          # wide gaps per figure (the rest are narrow)
PANEL_SIZE = (TEXT_WIDTH - MARGIN_LEFT - MARGIN_RIGHT - N_LABEL_GAPS * GAP_LABEL
              - (N_PANELS - 1 - N_LABEL_GAPS) * GAP_SHARED) / N_PANELS
MARGIN_BOTTOM = 0.33      # x tick labels + x label
TITLE_HEIGHT = 0.19       # panel titles "(a) ..."
LEGEND_HEIGHT = 0.20      # the legend row above everything
FIG_HEIGHT = MARGIN_BOTTOM + PANEL_SIZE + TITLE_HEIGHT + LEGEND_HEIGHT

LINE_WIDTH = 1.0
HERO_LINE_WIDTH = 1.5     # CAT-PFN is drawn thicker and on top
BAND_ALPHA = 0.15         # 25/75 % bands
FAINT_ALPHA = 0.45        # N = 0 variants in Figure 3
Y_TICKS = 4               # at most this many y tick intervals, labels without trailing ".0"
TICK_FORMAT = matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:g}$")

#: The six methods, in legend order (ours last). Same color/style for a method in every figure.
#: matplotlib tab10 colors, all solid except the dashed oracle reference. Checked for
#: color-vision deficiency (Machado simulation, OKLab Delta E x100): every pair is >= 9.1 for
#: protan-, deutan- and tritanopia (FT-PFN cyan >= 14.4 against all others). tab:green is
#: avoided because it coincides with tab:orange for protanopes (Delta E 0.7).
METHODS: dict[str, dict] = {
    "FT-PFN":      dict(color="#17becf", ls="-"),                      # tab:cyan
    "ESBO":        dict(color="#ff7f0e", ls="-"),                      # tab:orange
    "ESRS":        dict(color="#7f7f7f", ls="-"),                      # tab:gray
    "ESBO-Oracle": dict(color="#000000", ls=(0, (4, 1.5))),            # black, dashed
    "BO":          dict(color="#8c564b", ls="-"),                      # tab:brown
    "CAT-PFN":     dict(color="#1f77b4", ls="-", hero=True,            # tab:blue
                        label="CAT-PFN (ours)"),
}

#: Legend entries per figure (same order and style everywhere). The prediction figure only
#: lists the methods that have a predictor.
LEGEND_METHODS: dict[str, list[str]] = {
    "fig3": ["FT-PFN", "ESBO", "CAT-PFN"],
    "fig4": list(METHODS),
    "fig5": list(METHODS),
}

# Capitalization: titles and axis labels start with a capital letter.
PROBLEM_TITLES = {"pooled": "All problems", "pt2_deadtime": "PT2",
                  "cartpole": "Cartpole", "furuta": "Furuta"}
RIG_TITLES = {"without_weight": "W/o weight", "with_weight": "With weight"}
CRASH_PROBLEMS = ("pt2_deadtime", "cartpole", "furuta")


def better(label: str, higher: bool) -> str:
    """Axis label with the 'better' direction (rotated y label: up arrow = higher is better)."""
    return label + (r" ($\rightarrow$)" if higher else r" ($\leftarrow$)")


def usetex_ok() -> bool:
    """usetex needs latex plus cm-super (type1ec.sty); otherwise the bundled cmr10 is used."""
    if not shutil.which("latex") or not shutil.which("kpsewhich"):
        return False
    out = subprocess.run(["kpsewhich", "type1ec.sty"], capture_output=True, text=True)
    return bool(out.stdout.strip())


def rc() -> dict:
    p = {
        "font.size": FONT_SIZE, "axes.labelsize": FONT_SIZE, "axes.titlesize": FONT_SIZE,
        "xtick.labelsize": FONT_SIZE, "ytick.labelsize": FONT_SIZE,
        "legend.fontsize": FONT_SIZE,
        "lines.linewidth": LINE_WIDTH, "axes.linewidth": 0.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "xtick.major.pad": 2.0, "ytick.major.pad": 2.0,
        "axes.labelpad": 2.0, "axes.titlepad": 3.0,
        "axes.unicode_minus": False, "pdf.fonttype": 42,
    }
    if usetex_ok():
        p.update({"text.usetex": True, "font.family": "serif",
                  "font.serif": ["Computer Modern Roman"],
                  "text.latex.preamble": r"\usepackage{amsmath}"})
    else:
        p.update({"font.family": "serif", "mathtext.fontset": "cm",
                  "font.serif": ["cmr10"], "axes.formatter.use_mathtext": True})
    return p


# ==================================================================================== LAYOUT
def sheet(name: str, titles: list[str], ylabels: list[str | None]
          ) -> tuple[plt.Figure, list[plt.Axes]]:
    """Figure of TEXT_WIDTH x FIG_HEIGHT with four square panels, titles "(a) ...", the y
    labels (``None``: same quantity as the left neighbor, no label, narrow gap) and the
    legend of figure ``name`` on top."""
    if ylabels[0] is None or sum(y is not None for y in ylabels[1:]) != N_LABEL_GAPS:
        raise ValueError(f"{name}: need a y label on panel (a) and {N_LABEL_GAPS} more")
    fig = plt.figure(figsize=(TEXT_WIDTH, FIG_HEIGHT))
    axes = []
    x0 = MARGIN_LEFT
    for k, (title, ylabel) in enumerate(zip(titles, ylabels)):
        if k:
            x0 += PANEL_SIZE + (GAP_LABEL if ylabel is not None else GAP_SHARED)
        ax = fig.add_axes((x0 / TEXT_WIDTH, MARGIN_BOTTOM / FIG_HEIGHT,
                           PANEL_SIZE / TEXT_WIDTH, PANEL_SIZE / FIG_HEIGHT))
        ax.set_title(f"({'abcd'[k]}) {title}")
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(Y_TICKS, steps=[1, 2, 5, 10]))
        ax.yaxis.set_major_formatter(TICK_FORMAT)
        if ylabel is not None:
            ax.set_ylabel(ylabel)
        axes.append(ax)
    legend(fig, LEGEND_METHODS[name])
    return fig, axes


def legend_handles(methods: list[str]) -> list[Line2D]:
    return [Line2D([], [], color=METHODS[n]["color"], ls=METHODS[n]["ls"],
                   lw=HERO_LINE_WIDTH if METHODS[n].get("hero") else LINE_WIDTH,
                   label=METHODS[n].get("label", n))
            for n in methods]


def legend(fig: plt.Figure, methods: list[str]) -> None:
    y = 1.0 - (LEGEND_HEIGHT / 2) / FIG_HEIGHT
    fig.legend(handles=legend_handles(methods), loc="center", bbox_to_anchor=(0.5, y),
               ncol=len(methods), frameon=False, handlelength=1.6, handletextpad=0.4,
               columnspacing=1.1, borderaxespad=0.0)


def line_kw(name: str, faint: bool = False) -> dict:
    m = METHODS[name]
    return dict(color=m["color"], ls=m["ls"], alpha=FAINT_ALPHA if faint else 1.0,
                lw=HERO_LINE_WIDTH if m.get("hero") else LINE_WIDTH,
                zorder=4 if m.get("hero") else 3)


def ordered(d: dict) -> list[str]:
    """Methods present in ``d`` in legend order (hero drawn last by zorder)."""
    unknown = set(d) - set(METHODS)
    if unknown:
        raise KeyError(f"unknown method names {sorted(unknown)}, expected {list(METHODS)}")
    return [m for m in METHODS if m in d]


def watermark(axes: list[plt.Axes], on: bool) -> None:
    if on:
        for ax in axes:
            ax.text(0.5, 0.5, "placeholder", transform=ax.transAxes, ha="center",
                    va="center", rotation=25, color="#000000", alpha=0.10, zorder=0)


# ==================================================================================== FIGURES
def fig3(d: dict) -> plt.Figure:
    """(a) accuracy vs inference time, (b-d) crash anticipation per crashing system."""
    fig, axes = sheet(
        "fig3", [PROBLEM_TITLES["pooled"]] + [PROBLEM_TITLES[p] for p in CRASH_PROBLEMS],
        [better("Median norm. LL", higher=True), better("Steps saved", higher=True),
         None, None])
    ax = axes[0]
    ylim = d.get("ll_ylim", (-1.0, 2.0))
    for name in ordered(d["ll_vs_time"]):
        pts = sorted(d["ll_vs_time"][name], key=lambda q: q["time_s"])
        t = np.array([q["time_s"] for q in pts])
        ll = np.array([q["ll"] for q in pts])
        front = np.maximum.accumulate(ll)          # Pareto front over context sizes
        on = (ll >= front - 1e-12) & (ll >= ylim[0])
        kw = line_kw(name)
        ax.step(t, front, where="post", **kw)
        sizes = np.array([3.0 + 1.1 * np.log2(max(q["n"], 1)) for q in pts])
        ax.scatter(t[on], ll[on], s=sizes[on] ** 2, color=kw["color"], zorder=kw["zorder"] + 1,
                   edgecolor="white", linewidth=0.5)
    ax.set_xscale("log")
    ax.set_xlim(*d.get("ll_xlim", (2e-3, 2.5)))
    ax.set_xticks([0.01, 0.1, 1], ["0.01", "0.1", "1"])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_ylim(*ylim)
    ax.set_xlabel("Inference time / s")

    for ax, p in zip(axes[1:], CRASH_PROBLEMS):
        curves = d["stop_curves"][p]
        for name in ordered(curves):
            for n, c in sorted(curves[name].items(), key=lambda kv: int(kv[0])):
                faint = int(n) == 0
                kw = line_kw(name, faint=faint)
                if faint:
                    kw.update(ls=":", zorder=2)
                ax.plot(c["false_stop_rate"], c["steps_saved"], **kw)
        ax.set_xlim(0, 0.1)
        ax.set_xticks([0, 0.05, 0.1], ["0", "0.05", "0.1"])
        ax.set_ylim(bottom=0)
        ax.set_xlabel("False-stop rate")
    watermark(axes, d.get("_placeholder", False))
    return fig


def fig4(d: dict) -> plt.Figure:
    """(a) pooled regret over sim. time, (b-d) mean crashes per crashing system."""
    fig, axes = sheet(
        "fig4", [PROBLEM_TITLES["pooled"]] + [PROBLEM_TITLES[p] for p in CRASH_PROBLEMS],
        [better(r"$\log_{10}$ regret", higher=False), better("Mean crashes", higher=False),
         None, None])
    r = d["regret_pooled"]
    for name in ordered(r["methods"]):
        axes[0].plot(r["pct"], r["methods"][name], **line_kw(name))
    for ax, p in zip(axes[1:], CRASH_PROBLEMS):
        c = d["crashes"][p]
        for name in ordered(c["methods"]):
            ax.plot(c["pct"], c["methods"][name], **line_kw(name))
        ax.set_ylim(bottom=0)
    for ax in axes:
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 50, 100])
        ax.set_xlabel(r"Sim. time / \%" if usetex_ok() else "Sim. time / %")
    watermark(axes, d.get("_placeholder", False))
    return fig


def fig5(d: dict) -> plt.Figure:
    """Hardware: (a, b) regret, (c, d) crashes over wall-clock, without and with weight.
    Panels with the same quantity are neighbors and share their y range."""
    rigs = ("without_weight", "with_weight")
    fig, axes = sheet(
        "fig5", [RIG_TITLES[r] for r in rigs] * 2,
        [better(r"$\log_{10}$ regret", higher=False), None,
         better("Mean crashes", higher=False), None])
    t_max = 0.0
    for row, (key, mid) in enumerate((("regret", "median"), ("crashes", "mean"))):
        for k, rig in enumerate(rigs):
            ax = axes[2 * row + k]
            for name in ordered(d[rig][key]):
                s = d[rig][key][name]
                kw = line_kw(name)
                ax.step(s["t"], s[mid], where="post", **kw)
                if "q25" in s:
                    ax.fill_between(s["t"], s["q25"], s["q75"], step="post",
                                    color=kw["color"], alpha=BAND_ALPHA, lw=0, zorder=1)
                t_max = max(t_max, float(np.max(s["t"])))
    ylo = min(a.get_ylim()[0] for a in axes[:2])
    yhi = max(a.get_ylim()[1] for a in axes[:2])
    yc = max(a.get_ylim()[1] for a in axes[2:])
    for ax in axes[:2]:
        ax.set_ylim(ylo, yhi)                    # shared regret scale across rigs
    for ax in axes[2:]:
        ax.set_ylim(0, yc)                       # shared crash scale across rigs
    for ax in axes:
        ax.set_xlim(0, t_max)
        ax.set_xlabel("Wall-clock / s")
    watermark(axes, d.get("_placeholder", False))
    return fig


def legend_only() -> plt.Figure:
    fig = plt.figure(figsize=(TEXT_WIDTH, LEGEND_HEIGHT))
    fig.legend(handles=legend_handles(list(METHODS)), loc="center", ncol=len(METHODS),
               frameon=False, handlelength=1.6, handletextpad=0.4, columnspacing=1.1)
    return fig


# ==================================================================================== PLACEHOLDER
def placeholder_data() -> dict[str, dict]:
    """Synthetic data in the DATA CONTRACT format. Shapes and end points follow the thesis
    figures (fig3_cross, fig2_sheet, optplay_crashes, hwplay_optimization__*); the curves in
    between are invented."""
    rng = np.random.default_rng(0)

    # -- Figure 3 (a): pooled numbers from assets/figures/prediction_summary/fig3_cross.md
    ns = [0, 2, 4, 8, 16, 32, 64]
    ll = {
        "FT-PFN": ([0.173, 1.086, 1.133, 1.375, 1.458, 1.504, 1.590],
                   [0.003336, 0.003391, 0.003496, 0.003553, 0.003715, 0.003871, 0.004515]),
        "CAT-PFN": ([0.611, 1.086, 1.207, 1.284, 1.349, 1.438, 1.463],
                    [0.003356, 0.005846, 0.008054, 0.01265, 0.02207, 0.04013, 0.07506]),
        # ESBO's predictor: Segment-GP (thesis), from n = 2 on
        "ESBO": ([-15.353, -2.047, -0.142, 0.372, 0.242, 0.552],
                 [0.0001155, 0.1082, 0.1067, 0.2072, 0.7717, 1.315]),
    }
    ll_vs_time = {m: [{"n": n, "time_s": t, "ll": v}
                      for n, v, t in zip(ns[len(ns) - len(vals):], vals, ts)]
                  for m, (vals, ts) in ll.items()}
    # -- Figure 3 (b-d): end points at false-stop rate 0.1 from fig2_sheet.md, (N=0, N=64)
    ends = {"pt2_deadtime": {"FT-PFN": (60.1, 41.1), "CAT-PFN": (82.8, 70.5)},
            "cartpole": {"FT-PFN": (226.6, 314.8), "CAT-PFN": (274.7, 396.3)},
            "furuta": {"FT-PFN": (19.3, 120.7), "CAT-PFN": (76.8, 204.2)}}
    fsr = np.linspace(0, 0.1, 60)
    stop = {}
    for p, per in ends.items():
        stop[p] = {}
        for m, (e0, e64) in per.items():
            stop[p][m] = {}
            for n, e in (("0", e0), ("64", e64)):
                y = e * (0.35 + 0.65 * (1 - np.exp(-fsr / 0.02)) / (1 - np.exp(-5)))
                stop[p][m][n] = {"false_stop_rate": fsr.tolist(), "steps_saved": y.tolist()}
    f3 = {"_placeholder": True, "ll_vs_time": ll_vs_time, "stop_curves": stop}

    # -- Figure 4: crash end points at 100 % from optplay_crashes.md; regret invented
    pct = np.linspace(0, 100, 201)
    crash_end = {
        "pt2_deadtime": {"ESRS": 11.90, "BO": 8.25, "ESBO": 4.25, "CAT-PFN": 1.80,
                         "FT-PFN": 2.14, "ESBO-Oracle": 6.50},
        "cartpole": {"ESRS": 53.80, "BO": 15.45, "ESBO": 14.60, "CAT-PFN": 3.82,
                     "FT-PFN": 8.94, "ESBO-Oracle": 16.45},
        "furuta": {"ESRS": 15.70, "BO": 14.00, "ESBO": 7.60, "CAT-PFN": 2.33,
                   "FT-PFN": 10.73, "ESBO-Oracle": 5.90},
    }
    crashes = {}
    for p, per in crash_end.items():
        methods = {}
        for m, e in per.items():
            shape = 1 - np.exp(-pct / rng.uniform(15, 80))
            y = 1 + (e - 1) * shape / shape[-1]
            methods[m] = np.maximum.accumulate(y + rng.normal(0, 0.03 * e, pct.size)).tolist()
        crashes[p] = {"pct": pct.tolist(), "methods": methods}
    reg_end = {"ESRS": 0.0, "BO": -0.35, "ESBO": -0.55, "FT-PFN": -0.8, "CAT-PFN": -1.15,
               "ESBO-Oracle": -1.3}
    regret = {m: (0.6 + (e - 0.6) * (1 - np.exp(-pct / 30)) / (1 - np.exp(-100 / 30)))
              .tolist() for m, e in reg_end.items()}
    f4 = {"_placeholder": True, "regret_pooled": {"pct": pct.tolist(), "methods": regret},
          "crashes": crashes}

    # -- Figure 5: end points from hwplay_optimization__{without,with}_weight.md
    hw = {"without_weight": {"ESBO": (0.737, 10.6, 2140), "BO": (0.692, 21.6, 1340),
                             "ESRS": (0.730, 12.8, 2510), "CAT-PFN": (0.008, 3.4, 1800)},
          "with_weight": {"ESBO": (1.044, 9.2, 2300), "BO": (1.102, 10.6, 1170),
                          "ESRS": (1.254, 7.0, 2510), "CAT-PFN": (0.887, 3.6, 2350)}}
    f5: dict = {"_placeholder": True}
    for rig, per in hw.items():
        f5[rig] = {"regret": {}, "crashes": {}}
        for m, (r_end, c_end, t_end) in per.items():
            t = np.sort(rng.uniform(0, t_end, 40))
            t[0] = 0.0
            drop = np.maximum.accumulate(rng.uniform(0, 1, t.size))
            med = 1.45 + (r_end - 1.45) * drop
            f5[rig]["regret"][m] = {"t": t.tolist(), "median": med.tolist(),
                                    "q25": (med - 0.15).tolist(), "q75": (med + 0.15).tolist()}
            cr = c_end * (1 - np.exp(-t / (0.3 * t_end))) / (1 - np.exp(-1 / 0.3))
            cr = np.floor(cr * 5) / 5
            f5[rig]["crashes"][m] = {"t": t.tolist(), "mean": cr.tolist(),
                                     "q25": (0.8 * cr).tolist(), "q75": (1.2 * cr).tolist()}
    return {"fig3": f3, "fig4": f4, "fig5": f5}


# ==================================================================================== MAIN
def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = OUT / f"{name}.pdf"
    fig.savefig(pdf)                 # no bbox_inches="tight": keep exactly TEXT_WIDTH wide
    plt.close(fig)
    if shutil.which("gs"):
        subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m",
                        "-r300", "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
                        f"-sOutputFile={OUT / (name + '.png')}", str(pdf)], check=True)
    print(f"wrote {pdf}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--placeholder", action="store_true",
                    help="write synthetic data/*.json before plotting")
    args = ap.parse_args()
    if args.placeholder:
        DATA.mkdir(parents=True, exist_ok=True)
        for name, d in placeholder_data().items():
            (DATA / f"{name}.json").write_text(json.dumps(d))
    with plt.rc_context(rc()):
        for name, draw in (("fig3", fig3), ("fig4", fig4), ("fig5", fig5)):
            save(draw(json.loads((DATA / f"{name}.json").read_text())), name)
        save(legend_only(), "legend")


if __name__ == "__main__":
    main()
