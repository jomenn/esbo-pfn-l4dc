# Task: fill the L4DC paper figures (Figures 3, 4, 5) with the real data

You can paste this file as-is into Claude Code (or work through it by hand) from the root of
the `esbo-pfn` repository, on a machine that has the benchmark database.

## 1. Context

The figures for our L4DC paper (PMLR template) are already designed. Their **format is
fixed** and lives in `paper/l4dc/make_figures.py`. Right now they are drawn from
**placeholder data** (`paper/l4dc/data/fig{3,4,5}.json`, written with `"_placeholder": true`,
which puts a faint "placeholder" mark in every panel). The placeholder PDFs/PNGs are in
`paper/l4dc/figures/`. Look at them first: they show exactly what each panel must contain.

Your job is to **replace the placeholder JSON files with JSON files computed from the real
results**, in exactly the same format, and re-render. You do not design anything.

## 2. Hard rules

1. **Do not change the `FORMAT` block, the layout or the drawing functions in
   `make_figures.py`.** Sizes, fonts (8 pt), colors, line styles, legend and panel geometry
   are decided. If the real data does not fit a panel (e.g. the y range clips a curve, or a
   tick label collides), do not tweak it yourself: report it in your summary (section 8)
   with a screenshot and a proposal.
2. Write **one new script**, `paper/l4dc/export_data.py`, that reads the benchmark database
   and writes `paper/l4dc/data/fig3.json`, `fig4.json`, `fig5.json`. It must be rerunnable
   end to end with one command. Reuse the existing loaders and metrics in
   `src/esbopfn/plots/` and `src/esbopfn/benchmarks/` (listed per figure below) instead of
   re-implementing them, so the paper numbers are the thesis numbers.
3. **Never invent or interpolate data.** If a series is missing in the database, leave it
   out of the JSON (the plot simply omits it) and list it in your summary. Do not copy
   placeholder values.
4. The real JSON files must **not** contain `"_placeholder"` (or set it to `false`).
5. Do not commit or push; I'll review the diff.

## 3. Setup

```bash
export PFN_HOME=/path/to/pfn_home          # contains benchmarks/db.sqlite
uv sync                                    # project env
uv run pfn --help                          # sanity check
```

The database must contain the thesis import (`pfn import thesis-results --from <thesis
project> --raw <optplay trees>`, see `docs/BENCHMARKS.md` and `docs/REPRODUCE.md`) and the
hardware units (`pfn hw import-logs`). **Figure 4 (a) needs the raw optplay trees**
(`--raw`): the aggregated thesis import keeps only final incumbents, and
`optimization.fig_cross` raises `MissingData` without per-run incumbent traces.

For LaTeX-rendered text (usetex) install `cm-super` (`sudo apt install cm-super`); without
it the script falls back to matplotlib's bundled Computer Modern, which is fine too.

Render after exporting:

```bash
uv run python paper/l4dc/export_data.py
uv run python paper/l4dc/make_figures.py          # no --placeholder!
cd paper/l4dc && pdflatex preview.tex             # all three figures in the PMLR template
```

## 4. Method names (rename!)

The paper uses six method names. **XDecPFN is renamed CAT-PFN** everywhere. Map the ids in
the database to the paper names exactly like this, and drop every other method/model
(DecPFN, DecPFN-H, DecPFN-no-St, LC-PFN, Trajectory-TabPFN, Segment-TabPFN, Segment-GP,
ESBO-T-TabPFN, all threshold/τ variants). Legends are set per figure in `LEGEND_METHODS`
(Figure 3: FT-PFN, CAT-PFN, ESBO; Figures 4 and 5: all six); don't change them:

| paper name    | prediction (Fig. 3) model template | optimization (Fig. 4) / hardware (Fig. 5) strategy id |
|---------------|------------------------------------|--------------------------------------------------------|
| `FT-PFN`      | `ftpfn/{p}/default/default`        | `ftpfn-ei` (default params, thesis label `FT-PFN-EI`)  |
| `CAT-PFN`     | `xdecpfn/{p}/default/default`      | `xdecpfn-pi` (default params, thesis label `XDecPFN-PI`) |
| `ESBO`        | `segment-gp` (ESBO's GP predictor; Fig. 3a only) | `esbo-gp` (thesis label `ESBO-GP`)                     |
| `ESRS`        | –                                  | `esrs`                                                 |
| `ESBO-Oracle` | –                                  | `esbo-oracle`                                          |
| `BO`          | –                                  | `bo`                                                   |

Use the default-parameter cells from `src/esbopfn/configs/benchmarks/optimization.yaml`
(`main` list), never the `tau`/`crash_threshold` variants. The JSON keys must be exactly
the paper names above (the plot script raises `KeyError` on any other name); use `CAT-PFN`,
not `CAT-PFN (ours)` — the "(ours)" is added only in the legend.

Problems: `pt2_deadtime`, `cartpole`, `furuta` (the three crashing systems). Rigs:
`without_weight`, `with_weight`.

## 5. Data contract (JSON format)

All arrays are plain JSON lists of floats, equal length within one series. Anything not
listed here is ignored.

### `fig3.json` – prediction

```jsonc
{
  "ll_vs_time": {                       // panel (a), pooled over all problems
    "FT-PFN":  [ {"n": 0, "time_s": 0.00334, "ll": 0.173}, {"n": 2, ...}, ... ],
    "CAT-PFN": [ ... ],                 // n in {0, 2, 4, 8, 16, 32, 64}
    "ESBO":    [ ... ]                  // Segment-GP, n in {2, 4, 8, 16, 32, 64}
  },
  "stop_curves": {                      // panels (b)–(d)
    "pt2_deadtime": {
      "FT-PFN":  { "0":  {"false_stop_rate": [...], "steps_saved": [...]},
                   "64": {"false_stop_rate": [...], "steps_saved": [...]} },
      "CAT-PFN": { "0": {...}, "64": {...} }
    },
    "cartpole": { ... },
    "furuta":   { ... }
  },
  "ll_xlim": [0.002, 2.5],              // optional; only if the real points fall outside
  "ll_ylim": [-1.0, 2.0]                // optional; same (points below are not drawn)
}
```

- **(a) `ll`**: median over non-crashed queries of the per-trial conditioned LL (mean over the
  five cutoffs 10…90 % of T) minus the per-problem median `med_D` of the participants,
  pooled across problems; **`time_s`**: median inference seconds per prediction, median
  across problems. This is exactly the pooled panel of the thesis `fig3_cross`
  (`prediction_summary.fig3_board` / `draw_fig3_cross`, sidecar
  `assets/figures/prediction_summary/fig3_cross.md`). Give **all** context sizes; the plot
  computes the Pareto front (steps-post) itself. ESBO appears only in (a), not in (b–d).
  **Note:** keep `med_D` as in the thesis (median over the full thesis participant set), so
  that the numbers match the thesis. Report which set you used.
- **(b–d)**: the thesis `fig2_sheet` curves (`prediction_summary.fig2_curves` /
  `draw_fig2_sheet`, sidecar `fig2_sheet.md`): x = share of non-crashed queries the rule
  "stop at the first step with p_crash ≥ τ" stops, τ swept over every emitted probability;
  y = mean steps saved on crashed queries (crash step − stop step, 0 if never stopped).
  Only context sizes N = 0 and N = 64. Include points up to at least false-stop rate 0.1
  (the axis is clipped to [0, 0.1]), sorted by false-stop rate.

### `fig4.json` – simulation

```jsonc
{
  "regret_pooled": {                    // panel (a)
    "pct": [0.0, ..., 100.0],           // % of the simulated time budget
    "methods": { "FT-PFN": [...], "CAT-PFN": [...], "ESBO": [...], "ESRS": [...],
                 "ESBO-Oracle": [...], "BO": [...] }   // same length as pct
  },
  "crashes": {                          // panels (b)–(d)
    "pt2_deadtime": { "pct": [...], "methods": { "<paper name>": [...], ... } },
    "cartpole":     { ... },
    "furuta":       { ... }
  }
}
```

- **(a)** = panel (b) of the thesis figure `optplay_cross` (`optimization.fig_cross`, x axis
  `"time"`): per-instance scaled regret `(J − J_best) / (J_ESRS − J_best)`, median over the
  instances of a problem, mean over the problems, **log10 last (floor 1e-4)**, over % of
  the simulated time budget `15 T min(d, 4)`. Use `optimization.regret_curves(runs, cells,
  esrs, "time", n_points)` and the `"pooled"` entry. (The axis label says only
  "log10 regret"; the data is still the scaled regret defined here.) Where a curve is undefined (median not
  yet finite on every problem) write `null`; matplotlib leaves a gap (allowed, but tell me).
- **(b–d)** = the thesis `optplay_crashes` curves (`optimization.fig_crashes`): mean number
  of crashed trials among the trials finished so far, averaged over the runs on all
  instances, over % of the simulated time budget. Native runs if present, the thesis crash
  aggregates otherwise (that function already does this fallback; report which source each
  problem used).

### `fig5.json` – hardware

```jsonc
{
  "without_weight": {
    "regret":  { "<paper name>": {"t": [...], "median": [...], "q25": [...], "q75": [...]} },
    "crashes": { "<paper name>": {"t": [...], "mean":   [...], "q25": [...], "q75": [...]} }
  },
  "with_weight": { ... same ... }
}
```

- Same quantities as the thesis `hwplay_optimization__{rig}` panels (a) and (c)
  (`plots/hardware.py::fig_optimization`, metrics in `hardware.metrics`):
  - regret = `log10(J⁻ − J_best)`, J⁻ the best successful cost so far, J_best the best
    successful cost on the rig over the **thesis method set of that figure** (so numbers
    match the thesis), median over seeds with the 25/75 % seed band; a seed without a
    success yet is left out of the median at that x.
  - crashes = cumulative crashed-trial count, mean over seeds, 25/75 % band.
  - `t` = reset-normalized wall-clock in s (`hardware.metrics.wall_axis`, every reset
    replaced by the mean reset of the reference method).
- Only the methods that ran on the rig appear (expected: CAT-PFN, ESBO, ESRS, BO; no FT-PFN
  and no ESBO-Oracle on hardware). The legend still shows all six on purpose; the caption
  will say which ran on hardware. Panel order is fixed by the script: (a, b) regret
  without/with weight, (c, d) crashes without/with weight; you only fill the JSON.
- Curves are drawn as steps (`where="post"`), so give the values at the event times; the
  band keys `q25`/`q75` are optional.

## 6. Verification (must pass before you report back)

Compare your exported end points with the thesis numbers in the sidecar `.md` files. They
must agree to the printed precision; any deviation goes into the summary with an
explanation.

| check | expected (thesis) | source |
|---|---|---|
| Fig 3a FT-PFN, n = 64 | LL 1.590 @ 0.004515 s | `fig3_cross.md` |
| Fig 3a CAT-PFN (XDecPFN), n = 0 / 64 | 0.611 @ 0.003356 s / 1.463 @ 0.07506 s | `fig3_cross.md` |
| Fig 3a ESBO (Segment-GP), n = 8 / 16 / 64 | −0.142 @ 0.1067 s / 0.372 @ 0.2072 s / 0.552 @ 1.315 s | `fig3_cross.md` |
| Fig 3b–d steps saved at false-stop ≤ 0.1, CAT-PFN N=64 | PT2 70.5, cartpole 396.3, furuta 204.2 | `fig2_sheet.md` |
| … FT-PFN N=64 | PT2 41.1, cartpole 314.8, furuta 120.7 | `fig2_sheet.md` |
| … CAT-PFN N=0 / FT-PFN N=0 | PT2 82.8/60.1, cartpole 274.7/226.6, furuta 76.8/19.3 | `fig2_sheet.md` |
| Fig 4b–d crashes at 100 %, PT2 | ESRS 11.90, BO 8.25, ESBO 4.25, CAT-PFN 1.80, FT-PFN 2.14, Oracle 6.50 | `optplay_crashes.md` |
| … cartpole | ESRS 53.80, BO 15.45, ESBO 14.60, CAT-PFN 3.82, FT-PFN 8.94, Oracle 16.45 | `optplay_crashes.md` |
| … furuta | ESRS 15.70, BO 14.00, ESBO 7.60, CAT-PFN 2.33, FT-PFN 10.73, Oracle 5.90 | `optplay_crashes.md` |
| Fig 5 w/o weight, final median log10 regret | ESBO 0.737, BO 0.692, ESRS 0.730, CAT-PFN 0.008 | `hwplay_optimization__without_weight.md` |
| Fig 5 w/o weight, mean crashes | ESBO 10.6, BO 21.6, ESRS 12.8, CAT-PFN 3.4 | same |
| Fig 5 with weight, final median log10 regret | ESBO 1.044, BO 1.102, ESRS 1.254, CAT-PFN 0.887 | `hwplay_optimization__with_weight.md` |
| Fig 5 with weight, mean crashes | ESBO 9.2, BO 10.6, ESRS 7.0, CAT-PFN 3.6 | same |
| Fig 4a | no thesis number in the repo; check against `optplay_cross` in the thesis PDF | thesis |

Put these checks in `export_data.py` as assertions (or a `--check` flag that prints a
table of exported vs. expected), so they rerun with the data.

Then look at every rendered panel (`paper/l4dc/figures/*.png` and the compiled
`preview.pdf`) for: clipped curves, curves hidden behind the legend/titles, tick labels
overlapping, empty panels, a remaining "placeholder" mark.

## 7. Where things are

- Figure script (do not change its format): `paper/l4dc/make_figures.py`
- Placeholder renders to compare against: `paper/l4dc/figures/fig{3,4,5}.{pdf,png}`
- PMLR preview: `paper/l4dc/preview.tex`
- Thesis figure code to reuse: `src/esbopfn/plots/prediction_summary.py` (Fig. 3),
  `src/esbopfn/plots/optimization.py` (`regret_curves`, `fig_cross`, `fig_crashes`; Fig. 4),
  `src/esbopfn/plots/hardware.py` + `src/esbopfn/plots/_hw_common.py` (Fig. 5),
  shared helpers `src/esbopfn/plots/common.py`, configs in
  `src/esbopfn/configs/benchmarks/{prediction_summary,optimization,hardware}.yaml`
- Thesis numbers: `assets/figures/**/<figure>.md`
- Database docs: `docs/BENCHMARKS.md`, `docs/FIGURES.md`, `docs/REPRODUCE.md`

## 8. What to send back

1. `paper/l4dc/export_data.py` and the three real `paper/l4dc/data/fig*.json`.
2. The rendered `paper/l4dc/figures/fig{3,4,5}.pdf` (+ PNGs) and `preview.pdf`.
3. A short summary:
   - the verification table (exported vs. expected) with every deviation explained,
   - missing series/problems and why,
   - which data source each panel used (native runs vs. thesis import),
   - layout problems you saw with the real data (with a proposal, without changing the
     format yourself),
   - open questions (e.g. if `ftpfn-ei`/`xdecpfn-pi` are not the right variants).
