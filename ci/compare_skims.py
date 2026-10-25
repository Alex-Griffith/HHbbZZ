#!/usr/bin/env python3
"""Compare skim outputs of the reference (base branch) code and the new (PR) code.

Usage: compare_skims.py REF_DIR NEW_DIR [--tree Events] [--report report.md]
Exit codes: 0 = identical, 3 = differences found, anything else = the job crashed.
"""
import argparse
import sys
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

KEY_BRANCHES = ("run", "luminosityBlock", "event")
RTOL = 1e-6
DIFF_EXIT = 3


def load(path, tree):
    return uproot.open(path)[tree].arrays(library="ak")


def event_index(arr):
    keys = zip(*(ak.to_numpy(arr[b]).tolist() for b in KEY_BRANCHES))
    index = {}
    for i, k in enumerate(keys):
        if k in index:
            raise RuntimeError(f"duplicate event key {k}")
        index[k] = i
    return index


def differs(x, y):
    if x.dtype.kind in "fc":
        return ~np.isclose(x, y, rtol=RTOL, equal_nan=True)
    return x != y


def mismatch_per_event(a, b):
    """Boolean mask over events: True where the branch value differs."""
    if a.ndim == 1:
        return differs(ak.to_numpy(a), ak.to_numpy(b))
    if a.ndim != 2:
        raise NotImplementedError(f"branch with ndim={a.ndim}")
    na, nb = ak.to_numpy(ak.num(a)), ak.to_numpy(ak.num(b))
    mask = na != nb
    same = ~mask
    elem = differs(ak.to_numpy(ak.flatten(a[same])), ak.to_numpy(ak.flatten(b[same])))
    mask[same] = ak.to_numpy(ak.any(ak.unflatten(elem, na[same]), axis=1))
    return mask


def compare_file(ref_path, new_path, tree, out):
    ref, new = load(ref_path, tree), load(new_path, tree)
    ok = True
    out += [f"## {ref_path.name}", "", f"- entries: ref {len(ref)}, new {len(new)}"]

    rb, nb = set(ref.fields), set(new.fields)
    for label, s in (("removed branches", rb - nb), ("added branches", nb - rb)):
        if s:
            ok = False
            out.append(f"- {label}: {', '.join(sorted(s))}")

    ri, ni = event_index(ref), event_index(new)
    for label, s in (("events lost", ri.keys() - ni.keys()), ("events gained", ni.keys() - ri.keys())):
        if s:
            ok = False
            out.append(f"- {label}: {len(s)} (e.g. run,lumi,event = {sorted(s)[:5]})")

    common = sorted(ri.keys() & ni.keys())
    r_idx = np.array([ri[k] for k in common], dtype=np.int64)
    n_idx = np.array([ni[k] for k in common], dtype=np.int64)
    # A branch that switched between scalar and array cannot be compared value by value.
    rank_changed = sorted(b for b in rb & nb if ref[b].ndim != new[b].ndim)
    if rank_changed:
        ok = False
        out.append("- branches changed between scalar and array: " + ", ".join(
            f"{b} (ndim {ref[b].ndim} -> {new[b].ndim})" for b in rank_changed))

    rows = []
    for b in sorted((rb & nb) - set(rank_changed)):
        m = mismatch_per_event(ref[b][r_idx], new[b][n_idx])
        if m.any():
            ok = False
            rows.append(f"| {b} | {int(m.sum())} / {len(m)} |")
    if rows:
        out += ["", "| branch | common events differing |", "|---|---|", *rows]
    out += ["", "**identical**" if ok else "**differences found**", ""]
    return ok


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ref_dir", type=Path)
    p.add_argument("new_dir", type=Path)
    p.add_argument("--tree", default="Events")
    p.add_argument("--report", type=Path, default=Path("report.md"))
    args = p.parse_args()

    ref_files = sorted(args.ref_dir.glob("*.root"))
    if not ref_files:
        raise FileNotFoundError(f"no .root files in {args.ref_dir}")

    out = ["# Skim comparison: base vs PR", ""]
    all_ok = True
    for ref_path in ref_files:
        new_path = args.new_dir / ref_path.name
        if not new_path.exists():
            raise FileNotFoundError(f"missing new output {new_path}")
        all_ok &= compare_file(ref_path, new_path, args.tree, out)

    text = "\n".join(out)
    args.report.write_text(text)
    print(text)
    sys.exit(0 if all_ok else DIFF_EXIT)


if __name__ == "__main__":
    main()
