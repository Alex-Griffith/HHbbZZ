"""Run in CMSSW/NanoAODTools: controlled boundary cases use the real C++ selector.

These fixtures test mechanics, not measured physics migration rates.
"""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from H4LCppModule import HZZAnalysisCppProducer
from selection_variations import VIEWS, validate_inputs, snapshot, fill_results


def event_fixture(muons, jets, photons=(), electrons=()):
    event = SimpleNamespace(nElectron=len(electrons), nMuon=len(muons), nJet=len(jets),
                            nFsrPhoton=len(photons), PuppiMET_pt=10.)
    for collection, objects in (("Electron", electrons), ("Muon", muons),
                                ("Jet", jets), ("FsrPhoton", photons)):
        for field in {key for obj in objects for key in vars(obj)}:
            setattr(event, collection + "_" + field, [getattr(obj, field) for obj in objects])
        for shift in ("scaleUp", "scaleDn", "smearUp", "smearDn"):
            for field in (("pt", "mass") if collection == "Jet" else ("pt",)):
                if collection == "FsrPhoton":
                    continue
                setattr(event, "%s_%s_%s" % (collection, shift, field),
                        [getattr(obj, field) for obj in objects])
    event._tree = SimpleNamespace(GetListOfBranches=lambda: [
        SimpleNamespace(GetName=lambda name=name: name) for name in vars(event)])
    return event


def muon(pt, phi, pdgId, tight=True):
    return SimpleNamespace(pt=pt, eta=0., phi=phi, mass=.10566, dxy=0., dz=0.,
                           sip3d=1., looseId=tight, mediumId=tight, tightId=tight,
                           mvaLowPt=1., isGlobal=True,
                           isTracker=True, isPFcand=True, pdgId=pdgId,
                           pfRelIso03_all=.1, genPartIdx=-1)


def jet(pt, phi, score):
    return SimpleNamespace(pt=pt, eta=1.5, phi=phi, mass=5., jetId=6,
                           btagDeepFlavB=score, btagPNetB=score, btagUParTAK4B=score)


def photon(pt, eta, score, phi=0., muonIdx=0, electronIdx=-1, iso=.1):
    return SimpleNamespace(pt=pt, eta=eta, phi=phi, dROverEt2=score,
                           relIso03=iso, muonIdx=muonIdx, electronIdx=electronIdx)


def electron(pt=30., phi=0.):
    return SimpleNamespace(pt=pt, eta=0., phi=phi, mass=.000511,
                           dxy=0., dz=0., sip3d=1., deltaEtaSC=0.,
                           mvaIso_WPHZZ=True, pdgId=11, genPartIdx=-1)


class Output:
    def __init__(self):
        self.values = {}

    def fillBranch(self, name, value):
        self.values[name] = value


class SelectionMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.producer = HZZAnalysisCppProducer(2024, str(Path(__file__).resolve().parents[1] / "Input_2024.yml"),
                                            True, True, "4l", 15)

    def select(self, event, view="nominal", mode="4l"):
        worker = self.producer.variationWorker
        worker.Initialize()
        worker.SetAnalysisMode(mode)
        original = self.producer.analysisMode
        self.producer.analysisMode = mode
        try:
            sr, cr = self.producer._select(event, worker, view)
            return snapshot(worker, sr, cr, mode)
        finally:
            self.producer.analysisMode = original

    def test_lepton_threshold_migration_and_union(self):
        event = event_fixture([muon(45., 0., 13), muon(45., math.pi, -13),
                               muon(10., .8, 13), muon(2.99, -2., -13)],
                              [jet(40., 0., .8), jet(35., 2., .8)])
        event.Muon_scaleUp_pt = [45., 45., 10., 5.]
        validate_inputs(event, VIEWS)
        nominal = self.select(event)
        shifted = self.select(event, "Muon_scaleUp")
        self.assertFalse(nominal["isSR"] or nominal["isZXCR"])
        self.assertTrue(shifted["isSR"])
        self.assertEqual(sorted(shifted["lep%dIdx" % i] for i in range(1, 5)), [0, 1, 2, 3])
        out = Output()
        self.assertTrue(fill_results(out, [nominal, shifted]))
        self.assertEqual(out.values["Sel_isSR"], [False, True])

    def test_cr_jet_migration_inclusive4l_and_mass_shift(self):
        event = event_fixture([muon(45., 0., 13), muon(45., math.pi, -13),
                               muon(10., .8, 13, tight=False)],
                              [jet(19.9, 0., .7), jet(35., 2., .8)])
        event.Jet_scaleUp_pt = [20.1, 35.]
        event.Jet_scaleUp_mass = [8., 10.]
        nominal = self.select(event)
        shifted = self.select(event, "Jet_scaleUp")
        self.assertFalse(nominal["isZXCR"])
        self.assertTrue(shifted["isZXCR"])
        self.assertEqual(shifted["CRtype"], 1)
        self.assertEqual((shifted["jet1Idx"], shifted["jet2Idx"]), (1, 0))
        self.assertEqual(shifted["lep3Idx"], 2)
        self.assertFalse(shifted["lep3Tight"])
        self.assertGreater(shifted["mjj"], 0.)
        self.assertEqual(shifted["mass4l"], -999.)

    def test_missing_shift_is_an_error_for_nonempty_collection(self):
        event = event_fixture([], [jet(30., 0., .5)])
        del event.Jet_smearDn_mass
        with self.assertRaisesRegex(RuntimeError, "Jet_smearDn_mass"):
            validate_inputs(event, VIEWS)

    def test_empty_collection_needs_no_per_event_extra_branch(self):
        event = event_fixture([], [])
        del event.Muon_scaleUp_pt
        del event.Jet_smearDn_mass
        validate_inputs(event, VIEWS)

    def test_sr_jet_migration_only_in_4l2j(self):
        event = event_fixture([muon(45., 0., 13), muon(45., math.pi, -13),
                               muon(10., .8, 13), muon(8., -2., -13)],
                              [jet(19.9, 0., .7), jet(35., 2., .8)])
        event.Jet_scaleUp_pt = [20.1, 35.]
        self.assertTrue(self.select(event)["isSR"])
        nominal = self.select(event, mode="4l2j")
        self.assertFalse(nominal["isSR"] or nominal["isZXCR"])
        self.assertTrue(self.select(event, "Jet_scaleUp", mode="4l2j")["isSR"])

    def test_four_lepton_cr_types_and_jet_migration(self):
        for failed, region in ((1, 3), (2, 2)):
            with self.subTest(failed=failed):
                event = event_fixture([muon(45., 0., 13), muon(45., math.pi, -13),
                                       muon(10., .8, 13, tight=failed != 2),
                                       muon(8., -2., -13, tight=False)],
                                      [jet(19.9, 0., .7), jet(35., 2., .8)])
                event.Jet_scaleUp_pt = [20.1, 35.]
                self.assertFalse(self.select(event)["isZXCR"])
                shifted = self.select(event, "Jet_scaleUp")
                self.assertTrue(shifted["isZXCR"])
                self.assertFalse(shifted["isSR"])
                self.assertEqual(shifted["CRtype"], region)
                self.assertGreater(shifted["mass4l"], 70.)
                self.assertEqual(sum(not shifted["lep%dTight" % i] for i in range(1, 5)), failed)

    def test_best_z_candidate_is_rebuilt(self):
        event = event_fixture([muon(45., 0., 13), muon(45., math.pi, -13),
                               muon(10., .8, 13), muon(8., -2., -13),
                               muon(46., 1.4, 13), muon(46., 1.4-math.pi, -13)], [])
        nominal = self.select(event)
        event.Muon_scaleUp_pt = [45.6, 45.6, 10., 8., 46., 46.]
        shifted = self.select(event, "Muon_scaleUp")
        self.assertTrue(nominal["isSR"] and shifted["isSR"])
        self.assertEqual({nominal["lep1Idx"], nominal["lep2Idx"]}, {4, 5})
        self.assertEqual({shifted["lep1Idx"], shifted["lep2Idx"]}, {0, 1})

    def test_fsr_isolation_is_recomputed_with_varied_muon_pt(self):
        muons = [muon(45., 0., 13), muon(45., math.pi, -13),
                 muon(10., .8, 13), muon(8., -2., -13)]
        muons[3].pfRelIso03_all = .6
        photon = SimpleNamespace(pt=3., eta=.03, phi=-2., relIso03=.1,
                                 electronIdx=-1, muonIdx=3, dROverEt2=.03/9.)
        event = event_fixture(muons, [], [photon])
        self.assertTrue(self.select(event)["isSR"])
        event.Muon_scaleUp_pt = [45., 45., 10., 16.]
        self.assertFalse(self.select(event, "Muon_scaleUp")["isSR"])

    def test_tied_btags_two_distinct_jets_and_nominal_reset(self):
        event = event_fixture([muon(45., 0., 13), muon(45., math.pi, -13),
                               muon(10., .8, 13), muon(8., -2., -13)],
                              [jet(40., 0., .8), jet(35., 2., .8), jet(30., -2., .7)])
        first = self.select(event)
        self.assertTrue(first["isSR"])
        self.assertEqual((first["jet1Idx"], first["jet2Idx"]), (0, 1))
        event.Muon_smearDn_pt = [1., 1., 1., 1.]
        failed = self.select(event, "Muon_smearDn")
        self.assertFalse(failed["isSR"])
        self.assertEqual(failed["lep1Idx"], -1)
        self.assertEqual(first, self.select(event))

    def fsr_state(self, event, enabled=True):
        worker = self.producer.variationWorker
        worker.Initialize()
        worker.SetAnalysisMode("4l")
        worker.isFSR = enabled
        try:
            self.producer._select(event, worker)
            return (list(worker.ElectronFsrPhotonIdx), list(worker.MuonFsrPhotonIdx),
                    list(worker.MuonFsrRelIso03),
                    [p4.Pt() for p4 in worker.Electrondressed_Run3],
                    [p4.Pt() for p4 in worker.Muondressed_Run3])
        finally:
            worker.isFSR = True

    def test_fsr_chooses_minimum_score_after_quality_cuts(self):
        photons = [photon(3., .09, .01), photon(5., .02, .0008)]
        first = self.fsr_state(event_fixture([muon(30., 0., 13)], [], photons))
        reversed_order = self.fsr_state(event_fixture([muon(30., 0., 13)], [], photons[::-1]))
        self.assertEqual(first[1], [1])
        self.assertEqual(reversed_order[1], [0])
        self.assertEqual(first[4], reversed_order[4])
        # The NanoAOD-best photon may fail the stricter analysis isolation.
        photons[1].relIso03 = .9
        self.assertEqual(self.fsr_state(event_fixture([muon(30., 0., 13)], [], photons))[1], [0])

    def test_fsr_ratio_and_recovery_cone_cuts(self):
        for fsr in [photon(3., .108, .012), photon(3., .12, .013333),
                    photon(10., .51, .0051)]:
            with self.subTest(score=fsr.dROverEt2, eta=fsr.eta):
                self.assertEqual(self.fsr_state(event_fixture([muon(30., 0., 13)], [], [fsr]))[1], [-1])
        self.assertEqual(self.fsr_state(event_fixture([muon(30., 0., 13)], [],
                         [photon(3., .107, .0119)]))[1], [0])

    def test_fsr_isolation_cone_and_recovery_cone_are_distinct(self):
        mu = muon(30., 0., 13)
        for distance in [.009, .01, .3, .31]:
            with self.subTest(distance=distance):
                state = self.fsr_state(event_fixture([mu], [], [photon(10., distance, distance/100.)]))
                self.assertEqual(state[1], [0])  # still recovered, including outside iso cone
                self.assertAlmostEqual(state[2][0], .1, places=6)
                self.assertGreater(state[4][0], mu.pt)
        state = self.fsr_state(event_fixture([mu], [], [photon(10., .02, .0002)]))
        self.assertEqual(state[2], [0.])  # nonnegative isolation

    def test_fsr_ownership_electron_matching_and_disabled_switch(self):
        event = event_fixture([muon(30., 0., 13)], [],
                              [photon(5., .03, .0012, muonIdx=-1, electronIdx=0)], [electron()])
        state = self.fsr_state(event)
        self.assertEqual((state[0], state[1]), ([0], [-1]))
        self.assertGreater(state[3][0], 30.)
        disabled = self.fsr_state(event, enabled=False)
        self.assertEqual((disabled[0], disabled[1]), ([-1], [-1]))
        self.assertAlmostEqual(disabled[3][0], 30., places=6)

    def test_fsr_exact_score_ties_keep_first_index(self):
        event = event_fixture([muon(30., 0., 13)], [],
                              [photon(5., .03, .0012), photon(10., .12, .0012)])
        self.assertEqual(self.fsr_state(event)[1], [0])


if __name__ == "__main__":
    unittest.main()
