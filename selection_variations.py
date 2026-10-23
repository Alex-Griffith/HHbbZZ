"""Selection views shared by nominal and the existing Run-3 momentum shifts.

The order is an output contract (also written as SelectionViews in the ROOT file).
Each view changes ONE source at a time; this is not a Cartesian product.
"""
VIEWS = ("nominal",) + tuple(
    "%s_%s" % (collection, shift)
    for collection in ("Electron", "Muon", "Jet")
    for shift in ("scaleUp", "scaleDn", "smearUp", "smearDn")
)

FIELDS = {
    "isSR": "O", "isZXCR": "O", "CRtype": "I", "nJet": "I",
    "jetOffset": "I", "jet1Idx": "I", "jet2Idx": "I",
    "mass4l": "F", "pt4l": "F", "massZ1": "F", "massZ2": "F",
    "mjj": "F", "m4ljj": "F",
}
for _leg in range(1, 5):
    FIELDS["lep%dIdx" % _leg] = "I"
    FIELDS["lep%dPdgId" % _leg] = "I"
    FIELDS["lep%dTight" % _leg] = "O"


def shifted_value(obj, collection, field, view):
    """Read the correction module's absolute shifted value, never a ratio."""
    if view != "nominal":
        source, shift = view.split("_", 1)
        if source == collection and (field == "pt" or collection == "Jet"):
            return getattr(obj, "%s_%s" % (shift, field))
    return getattr(obj, field)


def validate_inputs(event, views):
    # Correction outputs live in InputTree extra branches, so checking only
    # GetListOfBranches() would incorrectly reject them before the file is saved.
    for view in views[1:]:
        source, shift = view.split("_", 1)
        count = int(getattr(event, "n" + source))
        # NATModules return before filling per-event extra branches when this
        # collection is empty. There are then no momenta to vary or validate.
        if count == 0:
            continue
        for field in (("pt", "mass") if source == "Jet" else ("pt",)):
            name = "%s_%s_%s" % (source, shift, field)
            try:
                values = getattr(event, name)
            except (AttributeError, RuntimeError) as exc:
                raise RuntimeError("Selection view %s needs correction output %s" % (view, name)) from exc
            if len(values) != count:
                raise RuntimeError("%s has %d entries, expected %d" % (name, len(values), count))


def snapshot(worker, is_sr, is_cr, mode):
    """Copy values before the independent variation worker is reset."""
    result = {name: (-999. if kind == "F" else False if kind == "O" else -1)
              for name, kind in FIELDS.items()}
    result.update(isSR=bool(is_sr), isZXCR=bool(is_cr), CRtype=0,
                  nJet=len(worker.jetidx), jetOffset=0)
    for leg in range(1, 5):
        result["lep%dPdgId" % leg] = 0
    result["goodJetIdx"] = [int(index) for index in worker.jetidx]
    if not (is_sr or is_cr):
        return result
    result["CRtype"] = (1 if worker.passedZXCR2P1FSelection else
                        2 if worker.passedZXCR2P2FSelection else
                        3 if worker.passedZXCR3P1FSelection else 0)
    result["massZ1"] = worker.Z1.M()
    if mode != "2l2j" and result["CRtype"] != 1:
        p4 = worker.ZZsystem if worker.isFSR else worker.ZZsystemnofsr
        result.update(mass4l=p4.M(), pt4l=p4.Pt(), massZ2=worker.Z2.M())
    for leg in range(4):
        result["lep%dIdx" % (leg + 1)] = int(worker.candidateLepIdx[leg])
        result["lep%dPdgId" % (leg + 1)] = int(worker.candidateLepPdgId[leg])
        result["lep%dTight" % (leg + 1)] = (bool(worker.ZXCRTight[leg]) if is_cr
                                                     else worker.candidateLepIdx[leg] >= 0)
    # Inclusive 4l SR has no dijet requirement. Build this optional observable
    # only AFTER accepting the event, without changing its SR decision.
    if mode == "4l" and is_sr:
        worker.BuildBestDijet()
    if worker.dijetIdx[0] >= 0:
        result.update(jet1Idx=int(worker.dijetIdx[0]), jet2Idx=int(worker.dijetIdx[1]),
                      mjj=float(worker.invjj))
        if mode != "2l2j" and result["CRtype"] != 1:
            import ROOT
            dijet = ROOT.TLorentzVector()
            second = ROOT.TLorentzVector()
            dijet.SetPtEtaPhiM(worker.pTj1, worker.etaj1, worker.phij1, worker.mj1)
            second.SetPtEtaPhiM(worker.pTj2, worker.etaj2, worker.phij2, worker.mj2)
            result["m4ljj"] = (p4 + dijet + second).M()
    return result


def fill_results(out, results):
    jets = []
    for result in results:
        result["jetOffset"] = len(jets)
        jets.extend(result["goodJetIdx"])
    for field in FIELDS:
        out.fillBranch("Sel_" + field, [result[field] for result in results])
    out.fillBranch("Sel_goodJetIdx", jets)
    return any(result["isSR"] or result["isZXCR"] for result in results)
