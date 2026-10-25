#!/usr/bin/env python3
"""Overlay histograms of key distributions in the base-branch and PR skims.

Usage: plot_skims.py REF_DIR NEW_DIR [--tree Events] [--outdir plots] [--summary summary.md]
Writes one PNG per sample and variable, one multi-page PDF per sample, and a markdown
table of entries and means. Variables missing from both files get a table row but no plot.
By default only nominal SR or CR events contribute; --selection all reproduces the
inclusive saved-event plots. Each side uses its own nominal selection.
Besides the general distributions, it covers the MLP input variables; angles and mT that
are not stored in the skim are computed from the stored kinematics (see DERIVED).
"""
import argparse
from pathlib import Path

import awkward as ak
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import uproot
from matplotlib.backends.backend_pdf import PdfPages

# Analysis code fills missing objects with -99 (leptons, Z) or -999 (jets, b tags).
# Events kept only by a momentum variation carry these in the nominal branches.
SENTINEL = -99.0

PT = lambda hi, n: np.linspace(0, hi, n + 1)
ETA = lambda lim, n: np.linspace(-lim, lim, n + 1)
DPHI = np.linspace(0, np.pi, 17)
SCORE = np.linspace(0, 1, 26)
COUNT = np.arange(-0.5, 10.5)

# (name, x-axis label, bin edges); a tuple name is summed per event.
VARIABLES = [
    # MLP inputs: four-lepton and Z kinematics
    ("pT4l", "4l pT [GeV]", PT(400, 40)),
    ("eta4l", "4l eta", ETA(8, 32)),
    ("pTZ1", "Z1 pT [GeV]", PT(300, 30)),
    ("etaZ1", "Z1 eta", ETA(6, 24)),
    ("pTZ2", "Z2 pT [GeV]", PT(200, 20)),
    ("etaZ2", "Z2 eta", ETA(6, 24)),
    # MLP inputs: jet kinematics
    ("pTj1", "jet 1 pT [GeV]", PT(300, 30)),
    ("etaj1", "jet 1 eta", ETA(5, 20)),
    ("pTj2", "jet 2 pT [GeV]", PT(200, 20)),
    ("etaj2", "jet 2 eta", ETA(5, 20)),
    ("invjj", "mjj [GeV]", PT(400, 40)),
    # MLP inputs: masses and jet counts
    ("mass4l", "m4l [GeV]", np.linspace(70, 870, 41)),
    ("massZ1", "mZ1 [GeV]", np.linspace(40, 120, 41)),
    ("massZ2", "mZ2 [GeV]", PT(120, 30)),
    ("mj1", "jet 1 mass [GeV]", PT(60, 30)),
    ("njets_pt30_eta4p7", "number of jets (pT>30, |eta|<4.7)", COUNT),
    ("dphi_jj", "|dphi(j1, j2)|", DPHI),
    ("deta_jj", "|deta(j1, j2)|", PT(8, 32)),
    # MLP inputs: b tagging (RobustParT for these samples; j1/j2 are the two highest scores)
    ("btagger1_RPT", "highest b-tag score (RobustParT)", SCORE),
    ("btagger2_RPT", "second-highest b-tag score (RobustParT)", SCORE),
    # MLP inputs: Z-Z and 4l-jet angles
    ("dR_ZZ", "dR(Z1, Z2)", PT(6, 30)),
    ("dphi_ZZ", "|dphi(Z1, Z2)|", DPHI),
    ("deta_ZZ", "|deta(Z1, Z2)|", PT(8, 32)),
    ("dR_4l_j1", "dR(4l, j1)", PT(8, 32)),
    ("dphi_4l_j1", "|dphi(4l, j1)|", DPHI),
    ("deta_4l_j1", "|deta(4l, j1)|", PT(10, 40)),
    # MLP inputs: missing momentum
    ("mT_4l_MET", "mT(4l, PuppiMET) [GeV], massless 4l", PT(400, 40)),
    ("PuppiMET_pt", "PuppiMET pT [GeV]", PT(200, 40)),
    ("PuppiMET_sumEt", "PuppiMET sumEt [GeV]", PT(3000, 30)),
    # MLP inputs: matrix-element discriminants (not stored in the skim)
    ("D_int", "D_int", SCORE),
    ("D_0m", "D_0m", SCORE),
    ("D_L1", "D_L1", SCORE),
    # MLP inputs: stored masses of the selected jets
    ("goodJet_mass_j1", "goodJet_mass of j1 [GeV]", PT(60, 30)),
    ("goodJet_mass_j2", "goodJet_mass of j2 [GeV]", PT(60, 30)),
    # General distributions
    ("ngoodJets", "number of good jets", COUNT),
    (("nTightEle", "nTightMu"), "number of tight leptons", np.arange(-0.5, 8.5)),
    ("nTightEle", "number of tight electrons", np.arange(-0.5, 8.5)),
    ("nTightMu", "number of tight muons", np.arange(-0.5, 8.5)),
    ("goodJet_pt", "good jet pT, all jets [GeV]", PT(300, 30)),
    ("pTL1", "lepton 1 pT [GeV]", PT(200, 40)),
    ("pTL2", "lepton 2 pT [GeV]", PT(150, 30)),
    ("pTL3", "lepton 3 pT [GeV]", PT(120, 24)),
    ("pTL4", "lepton 4 pT [GeV]", PT(100, 20)),
    ("btagger1_PN", "jet 1 PNet b score", SCORE),
    ("btagger2_PN", "jet 2 PNet b score", SCORE),
    ("btagger1_UPT", "jet 1 UParT b score", SCORE),
    ("btagger2_UPT", "jet 2 UParT b score", SCORE),
    ("btagger1_DJ", "jet 1 DeepJet b score", SCORE),
    ("btagger2_DJ", "jet 2 DeepJet b score", SCORE),
    ("goodJet_btagRPT", "good jet RobustParT b score, all jets", SCORE),
    ("goodJet_btagUPT", "good jet UParT b score, all jets", SCORE),
]


def abs_dphi(a, b):
    return np.abs((a - b + np.pi) % (2 * np.pi) - np.pi)


def jet_mass_at(arr, which):
    """goodJet_mass of the selected jet, found by matching its pT among the good jets."""
    pt, gpt, gmass = arr[f"pT{which}"], arr["goodJet_pt"], arr["goodJet_mass"]
    best = ak.argmin(abs(gpt - pt), axis=1, keepdims=True)
    mass = ak.to_numpy(ak.fill_none(ak.firsts(gmass[best]), np.nan)).astype(np.float64)
    match = ak.to_numpy(ak.fill_none(ak.firsts(abs(gpt - pt)[best]), np.inf)) < 1e-3 * np.maximum(pt, 1.0)
    return np.where(match, mass, np.nan)


# Variables computed per event from stored branches: (input branches, function).
# Events with a placeholder in any scalar input get NaN, which values() drops.
DERIVED = {
    "dphi_jj": (("phij1", "phij2"), lambda a: abs_dphi(a["phij1"], a["phij2"])),
    "deta_jj": (("etaj1", "etaj2"), lambda a: np.abs(a["etaj1"] - a["etaj2"])),
    "dR_ZZ": (("etaZ1", "phiZ1", "etaZ2", "phiZ2"),
              lambda a: np.hypot(a["etaZ1"] - a["etaZ2"], abs_dphi(a["phiZ1"], a["phiZ2"]))),
    "dphi_ZZ": (("phiZ1", "phiZ2"), lambda a: abs_dphi(a["phiZ1"], a["phiZ2"])),
    "deta_ZZ": (("etaZ1", "etaZ2"), lambda a: np.abs(a["etaZ1"] - a["etaZ2"])),
    "dR_4l_j1": (("eta4l", "phi4l", "etaj1", "phij1"),
                 lambda a: np.hypot(a["eta4l"] - a["etaj1"], abs_dphi(a["phi4l"], a["phij1"]))),
    "dphi_4l_j1": (("phi4l", "phij1"), lambda a: abs_dphi(a["phi4l"], a["phij1"])),
    "deta_4l_j1": (("eta4l", "etaj1"), lambda a: np.abs(a["eta4l"] - a["etaj1"])),
    "mT_4l_MET": (("pT4l", "phi4l", "PuppiMET_pt", "PuppiMET_phi"),
                  lambda a: np.sqrt(2 * a["pT4l"] * a["PuppiMET_pt"]
                                    * (1 - np.cos(a["phi4l"] - a["PuppiMET_phi"])))),
    "goodJet_mass_j1": (("pTj1", "goodJet_pt", "goodJet_mass"), lambda a: jet_mass_at(a, "j1")),
    "goodJet_mass_j2": (("pTj2", "goodJet_pt", "goodJet_mass"), lambda a: jet_mass_at(a, "j2")),
}


def var_key(name):
    return "+".join(name) if isinstance(name, tuple) else name


def selection_mask(tree, selection):
    if selection == "all":
        return np.ones(tree.num_entries, dtype=bool)
    branches = {"nominal": ("passedFullSelection", "isZXCR"),
                "sr": ("passedFullSelection",), "cr": ("isZXCR",)}[selection]
    # Missing flags must fail rather than silently include variation-only events.
    return np.logical_or.reduce([tree[n].array(library="np") != 0 for n in branches])


def derived(tree, name, event_mask):
    inputs, func = DERIVED[name]
    if any(n not in tree for n in inputs):
        return None
    arr = {n: tree[n].array(library="ak")[event_mask] for n in inputs}
    scalars = {n: ak.to_numpy(a).astype(np.float64) for n, a in arr.items() if a.ndim == 1}
    valid = np.logical_and.reduce([v > SENTINEL + 0.5 for v in scalars.values()])
    with np.errstate(invalid="ignore"):
        out = np.asarray(func({**arr, **scalars}), dtype=np.float64)
    return np.where(valid, out, np.nan)


def values(tree, name, event_mask):
    """Flat numpy array of the variable, sentinels removed; None if a branch is missing."""
    if name in DERIVED:
        flat = derived(tree, name, event_mask)
        return None if flat is None else flat[np.isfinite(flat)]
    names = name if isinstance(name, tuple) else (name,)
    if any(n not in tree for n in names):
        return None
    arrs = [tree[n].array(library="ak")[event_mask] for n in names]
    arr = arrs[0] if len(arrs) == 1 else sum(arrs[1:], arrs[0])
    flat = ak.to_numpy(ak.flatten(arr, axis=None)).astype(np.float64)
    return flat[np.isfinite(flat) & (flat > SENTINEL + 0.5)]


def plot_one(ref, new, label, edges, title):
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(6, 5.5), sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05}
    )
    counts = {}
    for side, vals, color in (("base", ref, "black"), ("PR", new, "tab:red")):
        if vals is None:
            continue
        h, _ = np.histogram(np.minimum(vals, np.nextafter(edges[-1], edges[0])), bins=edges)
        counts[side] = h
        top.stairs(h, edges, color=color, linewidth=1.5,
                   label=f"{side}: {len(vals)} entries, mean {vals.mean():.3g}" if len(vals) else f"{side}: 0 entries")
    top.set_ylabel("entries (underflow dropped, overflow in last bin)")
    top.set_title(title, fontsize=9)
    top.legend(fontsize=8)

    if "base" in counts and "PR" in counts:
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(counts["base"] > 0, counts["PR"] / counts["base"], np.nan)
            err = np.where(counts["base"] > 0, np.sqrt(counts["PR"]) / counts["base"], np.nan)
        centers = 0.5 * (edges[1:] + edges[:-1])
        bottom.errorbar(centers, ratio, yerr=err, fmt="o", color="tab:red", markersize=3)
    bottom.axhline(1, color="gray", linestyle="--", linewidth=1)
    bottom.set_ylim(0.5, 1.5)
    bottom.set_ylabel("PR / base")
    bottom.set_xlabel(label)
    return fig


def summarize(vals):
    if vals is None:
        return "missing"
    return f"{len(vals)} / {vals.mean():.4g}" if len(vals) else "0 / -"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ref_dir", type=Path)
    p.add_argument("new_dir", type=Path)
    p.add_argument("--tree", default="Events")
    p.add_argument("--outdir", type=Path, default=Path("plots"))
    p.add_argument("--summary", type=Path, default=Path("plots_summary.md"))
    p.add_argument("--selection", choices=("nominal", "sr", "cr", "all"), default="nominal",
                   help="event selection (default: nominal SR or CR; applied separately to each side)")
    args = p.parse_args()

    ref_files = sorted(args.ref_dir.glob("*.root"))
    if not ref_files:
        raise FileNotFoundError(f"no .root files in {args.ref_dir}")
    args.outdir.mkdir(parents=True, exist_ok=True)

    selections = {"nominal": "passedFullSelection || isZXCR", "sr": "passedFullSelection",
                  "cr": "isZXCR", "all": "all saved events"}
    out = ["# Distributions: base vs PR", "",
           f"Event selection: `{selections[args.selection]}` (each side independently).", "",
           "Plots are in the `skim-comparison` artifact under `plots/`. Cells: entries / mean.", ""]
    for ref_path in ref_files:
        new_path = args.new_dir / ref_path.name
        if not new_path.exists():
            raise FileNotFoundError(f"missing new output {new_path}")
        sample = ref_path.stem
        sample_dir = args.outdir / sample
        sample_dir.mkdir(exist_ok=True)
        ref_tree, new_tree = uproot.open(ref_path)[args.tree], uproot.open(new_path)[args.tree]
        ref_mask = selection_mask(ref_tree, args.selection)
        new_mask = selection_mask(new_tree, args.selection)

        out += [f"## {sample}", "",
                f"Selected events: base {int(ref_mask.sum())} / {ref_tree.num_entries} saved; "
                f"PR {int(new_mask.sum())} / {new_tree.num_entries} saved.", "",
                "| variable | base | PR |", "|---|---|---|"]
        with PdfPages(args.outdir / f"{sample}.pdf") as pdf:
            for name, label, edges in VARIABLES:
                # Values below the axis (e.g. mass4l=0, b-tag defaults -1/-3) are dropped
                # from plots and means; values above it go into the last bin.
                ref, new = (None if v is None else v[v >= edges[0]]
                            for v in (values(ref_tree, name, ref_mask), values(new_tree, name, new_mask)))
                key = var_key(name)
                if all(v is None or len(v) == 0 for v in (ref, new)):
                    out.append(f"| {key} | {summarize(ref)} | {summarize(new)} |")
                    continue
                fig = plot_one(ref, new, label, edges, f"{sample}: {key} ({args.selection})")
                fig.savefig(sample_dir / f"{key}.png", dpi=110, bbox_inches="tight")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
                out.append(f"| {key} | {summarize(ref)} | {summarize(new)} |")
        out.append("")

    text = "\n".join(out)
    args.summary.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
