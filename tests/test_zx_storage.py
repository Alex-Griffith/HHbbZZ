"""Decision-level tests; these do not replace a native ROOT production check."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zx_storage import zx_storage


def wide_storage(*args):
    return zx_storage(*args, profile="wide")


class RestVector:
    # Only addition and invariant mass are used by the storage decision.
    def __init__(self, energy):
        self.energy = energy

    def __add__(self, other):
        return RestVector(self.energy + other.energy)

    def M(self):
        return self.energy

    def Pt(self):
        return self.energy

    def DeltaR(self, other):
        return 1.


def lepton(pdg, index, tight=True, energy=45.5):
    return SimpleNamespace(pdgId=pdg, sourceIndex=index, tight=tight,
                           p4=RestVector(energy), bareP4=RestVector(energy))


def worker(leptons, electrons=2, muons=1):
    return SimpleNamespace(ZXLooseLeptons=leptons, Zmass=91.1876, MZcutdown=12., MZcutup=120.,
                           goodLooseElectrons2012=lambda: list(range(electrons)),
                           goodLooseMuons2012=lambda: list(range(muons)))


class WideStorageTest(unittest.TestCase):
    def test_pass_and_fail_probes_are_both_retained(self):
        for passed in (True, False):
            with self.subTest(passed=passed):
                w = worker([lepton(11, 0), lepton(-11, 1), lepton(13, 0, passed)])
                keep, masks = wide_storage(w, 2, 1, "4l")
                self.assertTrue(keep)
                self.assertEqual(masks["Muon_ZXLoose"], [True])
                self.assertEqual(masks["Muon_ZXTight"], [passed])

    def test_probe_outside_current_sip_loose_list_is_still_stored(self):
        # The third basic-acceptance object fails current SIP/dxy/dz and is
        # therefore absent from ZXLooseLeptons; raw collection is still saved.
        keep, masks = wide_storage(worker([lepton(11, 0), lepton(-11, 1)]), 2, 1, "4l")
        self.assertTrue(keep)
        self.assertEqual(masks["Muon_ZXLoose"], [False])

    def test_four_or_more_leptons_not_vetoed(self):
        w = worker([lepton(11, 0), lepton(-11, 1)], electrons=3, muons=2)
        self.assertTrue(wide_storage(w, 3, 2, "4l")[0])

    def test_tags_must_be_tight_same_flavour_opposite_sign(self):
        for tags in ([lepton(11, 0), lepton(11, 1)],
                     [lepton(11, 0), lepton(-13, 0)],
                     [lepton(11, 0), lepton(-11, 1, False)]):
            self.assertFalse(wide_storage(worker(tags), 2, 1, "4l")[0])

    def test_only_two_basic_leptons_not_kept(self):
        w = worker([lepton(11, 0), lepton(-11, 1)], muons=0)
        self.assertFalse(wide_storage(w, 2, 0, "4l")[0])

    def test_storage_mass_window_is_broad_and_strict_at_boundaries(self):
        for mass, expected in ((12., False), (60., True), (119., True), (120., False)):
            w = worker([lepton(11, 0, energy=mass / 2), lepton(-11, 1, energy=mass / 2)])
            self.assertEqual(wide_storage(w, 2, 1, "4l")[0], expected)

    def test_masks_use_original_collection_indices_and_reset(self):
        w = worker([lepton(11, 2), lepton(-11, 0)], electrons=3)
        _, masks = wide_storage(w, 3, 1, "4l")
        self.assertEqual(masks["Electron_ZXTight"], [True, False, True])
        _, empty = wide_storage(worker([], 0, 0), 0, 0, "4l")
        self.assertEqual(empty["Electron_ZXTight"], [])

    def test_2l2j_has_no_additional_retention(self):
        keep, masks = wide_storage(worker([lepton(11, 0), lepton(-11, 1)]), 2, 1, "2l2j")
        self.assertFalse(keep)
        self.assertFalse(any(masks["Electron_ZXTight"]))


class FRStorageTest(unittest.TestCase):
    def setUp(self):
        self.leptons = [lepton(11, 0), lepton(-11, 1), lepton(13, 0, False)]

    def decide(self, met=10.):
        return zx_storage(worker(self.leptons), 2, 1, "4l", met=met)

    def test_default_keeps_pass_and_fail_without_requiring_jets(self):
        # The worker intentionally has no Jet state or jet-count accessor.
        for tight in (False, True):
            self.leptons[2].tight = tight
            self.assertTrue(self.decide()[0])

    def test_met_boundaries_and_invalid_values(self):
        for met, expected in ((0., True), (24.999, True), (25., False),
                              (-1., False), (float('nan'), False), (float('inf'), False)):
            with self.subTest(met=met):
                self.assertEqual(self.decide(met)[0], expected)

    def test_loose_definition_is_enforced_and_masks_remain_complete(self):
        self.leptons.pop()
        keep, masks = self.decide()
        self.assertFalse(keep)
        self.assertEqual(masks['Electron_ZXTight'], [True, True])
        self.assertEqual(masks['Muon_ZXLoose'], [False])
        self.leptons.extend([lepton(13, 0), lepton(-13, 1)])
        self.assertFalse(zx_storage(worker(self.leptons), 2, 2, '4l', met=10.)[0])

    def test_narrow_z_and_tag_pt(self):
        for first, second, expected in ((45.5, 45.5, True), (40., 40., False),
                                         (10., 81., False), (10.01, 80.99, True)):
            self.leptons[0].p4 = RestVector(first)
            self.leptons[1].p4 = RestVector(second)
            self.assertEqual(self.decide()[0], expected)

    def test_pair_cuts_use_bare_vectors_while_z_uses_dressed_vectors(self):
        self.leptons[0].bareP4 = RestVector(1.)
        self.leptons[1].bareP4 = RestVector(1.)
        self.assertFalse(self.decide()[0])
        self.leptons[1].bareP4 = RestVector(3.)
        self.assertTrue(self.decide()[0])
        self.leptons[2].bareP4.DeltaR = lambda other: .02
        self.leptons[0].bareP4.DeltaR = lambda other: .02
        self.assertFalse(self.decide()[0])

    def test_unknown_profile_is_an_error(self):
        with self.assertRaisesRegex(ValueError, 'Unknown ZX storage profile'):
            zx_storage(worker(self.leptons), 2, 1, '4l', profile='typo', met=10.)


if __name__ == "__main__":
    unittest.main()
