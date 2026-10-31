"""Native boundary checks for the real worker's separate no-SIP collection.

Run in CMSSW with managed Python: python tests/check_zx_layers_root.py REPO
"""
from pathlib import Path
import sys

import ROOT

source = Path(sys.argv[1]).resolve()
ROOT.gROOT.ProcessLine('.L %s/src/H4LTools.cc+O' % source)


def make_worker():
    worker = ROOT.H4LTools(False)
    worker.Initialize()
    worker.SetAnalysisMode('4l')
    worker.SetNanoVersion(15)
    worker.isFSR = False
    worker.InitializeElecut(5., 2.5, 4., .5, 1., 0., 0., 0., 0., 0., 0.)
    worker.InitializeMucut(3., 2.4, 8., .5, 1.)
    worker.InitializeFsrPhotonCut(2., 2.4, 1.8, .5, .012)
    worker.InitializeJetcut(20., 2.4, 2)
    worker.InitializeEvtCut(70., 105., 160., 91.1876, 40., 12., 120.)
    return worker


def identities(leptons):
    return {(abs(int(l.pdgId)), int(l.sourceIndex)): bool(l.tight) for l in leptons}


# SIP threshold, ID and displacement failures must remain separate decisions.
worker = make_worker()
for i, sip in enumerate((3.9, 4., 10.)):
    worker.SetElectrons(25., .2, float(i), .000511, .01, .02, sip, 0., 0., True, 11)
for i, (sip, dxy, loose_id) in enumerate(((7.9, .01, True), (8., .01, True),
                                         (20., .01, True), (1., .5, True),
                                         (1., .01, False))):
    worker.SetMuons(25., -.5, float(i), .105, True, True, dxy, .02,
                    sip, loose_id, 0., True, 13, .1)
worker.BatchFsrRecovery_Run3()
worker.LeptonSelection()
before = identities(worker.ZXLooseLeptons)
worker.BuildZXLooseNoSIP()
after = identities(worker.ZXLooseLeptonsNoSIP)
assert before == {(11, 0): True, (13, 0): True, (13, 4): False}, before
assert after == {(11, 0): True, (11, 1): False, (11, 2): False,
                 (13, 0): True, (13, 1): False, (13, 2): False, (13, 4): False}, after
assert identities(worker.ZXLooseLeptons) == before
worker.BuildZXLooseNoSIP()
assert identities(worker.ZXLooseLeptonsNoSIP) == after  # no accumulation
worker.Initialize()
assert not worker.ZXLooseLeptonsNoSIP

# A four-lepton application candidate gains SIP-failing probes without touching
# the original CR flags or candidate fields. Jets are cleaned against all legs.
worker = make_worker()
for pdg, pt, eta, phi, sip in ((11, 45.5, 0., 0., 1.),
                               (-11, 45.5, 0., 3.141592653589793, 1.),
                               (13, 25., .4, 1., 20.),
                               (-13, 20., -.4, -1., 20.)):
    if abs(pdg) == 11:
        worker.SetElectrons(pt, eta, phi, .000511, .01, .02, sip, 0., 0., True, pdg)
    else:
        worker.SetMuons(pt, eta, phi, .105, True, True, .01, .02,
                        sip, True, 0., True, pdg, .1)
worker.BatchFsrRecovery_Run3()
worker.LeptonSelection()
worker.BuildZXLooseNoSIP()
assert len(worker.ZXLooseLeptons) == 2
assert not worker.ZXNoSIPCRStorage()  # no jets
for phi in (1.8, -1.8):
    worker.SetJets(35., 1.8, phi, 5., 2, .1, .1, .1, .1)
assert worker.ZXNoSIPCRStorage()
assert not worker.passedZXCR2P2FSelection
assert not worker.passedZXCR3P1FSelection
assert len(worker.jetidx) == 0
print('ZX_LAYER_NATIVE_BOUNDARIES_PASS')
