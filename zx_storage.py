"""Nominal Z+lepton storage envelope, separate from SR/ZXCR selections."""
import math


def zx_storage(worker, n_electrons, n_muons, mode, profile="fr", met=float("nan")):
    """Return a storage decision and nominal three-layer object masks.

    The default FR envelope keeps pass/fail with the current three-loose,
    narrow-Z, tag-pT, pair and MET cuts, without a jet cut, for either the
    with-SIP or no-SIP loose count. The explicit wide
    profile also stores basic probes outside the current loose definition.
    Neither profile changes worker state or SR/CR candidate choices.
    """
    if profile not in ("fr", "wide"):
        raise ValueError("Unknown ZX storage profile: " + profile)
    masks = {"%s_ZX%s" % (collection, decision): [False] * count
             for collection, count in (("Electron", n_electrons), ("Muon", n_muons))
             for decision in ("LooseNoSIP", "Loose", "Tight")}
    if mode not in ("4l", "4l2j"):
        return False, masks

    loose = list(worker.ZXLooseLeptons)
    no_sip = list(worker.ZXLooseLeptonsNoSIP)
    for lepton in no_sip:
        collection = "Electron" if abs(lepton.pdgId) == 11 else "Muon"
        masks[collection + "_ZXLooseNoSIP"][int(lepton.sourceIndex)] = True
    tight = []
    for lepton in loose:
        collection = "Electron" if abs(lepton.pdgId) == 11 else "Muon"
        index = int(lepton.sourceIndex)
        masks[collection + "_ZXLoose"][index] = True
        masks[collection + "_ZXTight"][index] = bool(lepton.tight)
        if lepton.tight:
            tight.append(lepton)

    if profile == "fr":
        return (fr_envelope(worker, loose, met) or
                fr_envelope(worker, no_sip, met)), masks
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
                return True, masks
    return False, masks


def fr_envelope(worker, leptons, met):
    """Same bounded Z+l kinematics for either loose definition."""
    if len(leptons) != 3 or not math.isfinite(met) or not 0. <= met < 25.:
        return False
    for i, first in enumerate(leptons):
        for second in leptons[i + 1:]:
            if first.bareP4.DeltaR(second.bareP4) <= .02:
                return False
            if first.pdgId * second.pdgId < 0 and (first.bareP4 + second.bareP4).M() < 4.:
                return False
    tight = [lepton for lepton in leptons if lepton.tight]
    for i, first in enumerate(tight):
        for second in tight[i + 1:]:
            if first.pdgId + second.pdgId != 0:
                continue
            mass = (first.p4 + second.p4).M()
            if (worker.MZcutdown < mass < worker.MZcutup and
                    abs(mass - worker.Zmass) < 7. and
                    max(first.p4.Pt(), second.p4.Pt()) > 20. and
                    min(first.p4.Pt(), second.p4.Pt()) > 10.):
                return True
    return False
