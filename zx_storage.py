"""Nominal Z+lepton storage envelope, separate from SR/ZXCR selections."""
import math


def zx_storage(worker, n_electrons, n_muons, mode, profile="fr", met=float("nan")):
    """Return a storage decision and exact current CR loose/tight object masks.

    The default FR envelope keeps pass/fail with the current three-loose,
    narrow-Z, tag-pT, pair and MET cuts, without a jet cut. The explicit wide
    profile also stores basic probes outside the current loose definition.
    Neither profile changes worker state or SR/CR candidate choices.
    """
    if profile not in ("fr", "wide"):
        raise ValueError("Unknown ZX storage profile: " + profile)
    masks = {"%s_ZX%s" % (collection, decision): [False] * count
             for collection, count in (("Electron", n_electrons), ("Muon", n_muons))
             for decision in ("Loose", "Tight")}
    if mode not in ("4l", "4l2j"):
        return False, masks

    loose = list(worker.ZXLooseLeptons)
    tight = []
    for lepton in loose:
        collection = "Electron" if abs(lepton.pdgId) == 11 else "Muon"
        index = int(lepton.sourceIndex)
        masks[collection + "_ZXLoose"][index] = True
        masks[collection + "_ZXTight"][index] = bool(lepton.tight)
        if lepton.tight:
            tight.append(lepton)

    if profile == "fr":
        if len(loose) != 3 or not math.isfinite(met) or not 0. <= met < 25.:
            return False, masks
        for i, first in enumerate(loose):
            for second in loose[i + 1:]:
                if first.bareP4.DeltaR(second.bareP4) <= .02:
                    return False, masks
                if first.pdgId * second.pdgId < 0 and (first.bareP4 + second.bareP4).M() < 4.:
                    return False, masks
    else:
        # Wide probes precede SIP/dxy/dz/ID/isolation; opt in deliberately.
        basic_count = (len(worker.goodLooseElectrons2012()) +
                       len(worker.goodLooseMuons2012()))
        if basic_count < 3:
            return False, masks
    for i, first in enumerate(tight):
        for second in tight[i + 1:]:
            if first.pdgId + second.pdgId != 0:
                continue
            mass = (first.p4 + second.p4).M()
            if worker.MZcutdown < mass < worker.MZcutup:
                if profile == "fr" and (abs(mass - worker.Zmass) >= 7. or
                                        max(first.p4.Pt(), second.p4.Pt()) <= 20. or
                                        min(first.p4.Pt(), second.p4.Pt()) <= 10.):
                    continue
                return True, masks
    return False, masks
