"""Run-3 ZZ k-factors for the HHbbZZ NanoAODTools skim.

Reference: CJLST/ZZAnalysis, Run3, NanoAnalysis/python/weightFiller.py.

IMPORTANT: The input event must provide GenZZ_mass for ggZZ, and both
GenZZ_mass and LHEMela_costhetastar for qqZZ. These may be produced by an
earlier module or already exist in the input tree. Output branches produced
by a *later* module are not automatically readable as event attributes.

This module deliberately does not calculate overallEventWeight.
"""

import os
import math
import h5py
import numpy as np
from scipy.interpolate import make_interp_spline
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class kFactorProducer_Run3(Module):
    GG_VARS = ("nominal", "PDF", "PDF_aS", "QCD_mu")
    QQ_VARS = ("nominal", "QCD_up", "QCD_dn", "EW_factor",
               "smoothing_factor", "alpha_S_factor")

    def __init__(self, year, sample_path="", kfactor_dir=None,
                 gg_order=1, strict=True):
        """Initialize Run-3 k-factors.
        Args:
            year: e.g. 2022, 2023, 2024 (also accepts strings such as 2022EE).
            sample_path: sample dataset name/path used to identify qqZZ/ggZZ.
            kfactor_dir: directory containing Run3/gluonFusion and
                Run3/qqBarToZZ; or the Run3 directory itself.
            gg_order: 1 = NNLO/LO, 2 = NNLO/NLO (match sample generator order).
            strict: raise on invalid generator inputs. False fills unity
                for invalid events; debugging only, not physics.
        """
        self.year = year
        self.sample_path = str(sample_path)
        self.strict = bool(strict)
        self.gg_order = int(gg_order)
        if self.gg_order not in (1, 2):
            raise ValueError("gg_order must be 1 (NNLO/LO) or 2 (NNLO/NLO)")
        year_digits = str(year)[:4]
        if not year_digits.isdigit() or int(year_digits) < 2022:
            raise ValueError("kFactorProducer_Run3 is for 2022+ only")

        lower = self.sample_path.lower()
        self.is_ggzz = "gluglutocontinto2z" in lower
        self.is_qqzz = ("zzto4l" in lower and not self.is_ggzz
                        and "glugluhtozzto4l" not in lower)
        self.apply_kfactor = self.is_ggzz or self.is_qqzz

        if kfactor_dir is None:
            base = os.environ.get("CMSSW_BASE")
            if not base:
                raise EnvironmentError("CMSSW_BASE is not set; supply kfactor_dir")
            kfactor_dir = os.path.join(
                base, "src/PhysicsTools/NanoAODTools/python/postprocessing/"
                      "analysis/nanoAOD_skim/data/kFactor")
        root = os.path.abspath(os.path.expanduser(str(kfactor_dir)))
        self.data_dir = os.path.join(root, "Run3") if os.path.isdir(
            os.path.join(root, "Run3")) else root

        self.gg_splines = {}
        self.qq_splines = {}
        self.out = None
        self._mela = None
        self._MelaModule = None
        self._branch_names = []
        self._missing_count = 0

        if self.is_ggzz:
            filename = ("Run3_K-NNLO.h5" if self.gg_order == 1
                        else "Run3_K-NLO-NNLO.h5")
            path = os.path.join(self.data_dir, "gluonFusion", filename)
            self.gg_splines = self._read_splines(path, "hmass", self.GG_VARS)
        elif self.is_qqzz:
            for i in range(4):
                # Matches CJLST's cos{3-i} ordering for |cos(theta*)| bins.
                path = os.path.join(self.data_dir, "qqBarToZZ",
                                    "kfac_m4l__cos%d.h5" % (3 - i))
                splines = self._read_splines(path, "zzmass", self.QQ_VARS)
                for name, spline in splines.items():
                    self.qq_splines[(i, name)] = spline

        print("[kFactorProducer_Run3] year=%s ggZZ=%s qqZZ=%s gg_order=%d"
              % (year, self.is_ggzz, self.is_qqzz, self.gg_order))
        if self.apply_kfactor:
            print("[kFactorProducer_Run3] tables: %s" % self.data_dir)

    @staticmethod
    def _read_splines(path, x_name, names):
        if not os.path.isfile(path):
            raise FileNotFoundError("Run3 k-factor table missing: %s" % path)
        with h5py.File(path, "r") as h5:
            x = np.asarray(h5[x_name], dtype=float).reshape(-1)
            if len(x) < 2 or not np.all(np.isfinite(x)) or not np.all(np.diff(x) > 0):
                raise ValueError("Invalid mass grid in %s" % path)
            result = {}
            for name in names:
                y = np.asarray(h5[name], dtype=float).reshape(-1)
                if len(y) != len(x) or not np.all(np.isfinite(y)):
                    raise ValueError("Invalid '%s' array in %s" % (name, path))
                # k=1 is the linear interpolation used by CJLST.
                result[name] = make_interp_spline(x, y, k=1)
            return result

    def _declare(self, name):
        self.out.branch(name, "F")
        self._branch_names.append(name)

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree
        self._branch_names = []
        if self.apply_kfactor:
            self._declare("GenZZ_mass")
        if self.is_qqzz:
            self._initialize_mela()
            self._declare("LHEMela_costhetastar")
        if self.is_ggzz:
            self._declare("KFactor_QCD_ggZZ_Nominal")
            for variation in ("PDF", "QCD", "aS"):
                for direction in ("up", "dn"):
                    self._declare("KFactor_QCD_ggZZ_%s_%s" % (variation, direction))

        elif self.is_qqzz:
            self._declare("KFactor_ZZQQB_Nominal")
            for variation in ("QCD", "EW", "aS", "smoothing"):
                for direction in ("up", "dn"):
                    self._declare("KFactor_ZZQQB_%s_%s" % (variation, direction))

    @staticmethod
    def _mother(part, genparts):
        idx = part.genPartIdxMother
        n = 0
        while idx >= 0 and genparts[idx].pdgId == part.pdgId:
            idx = genparts[idx].genPartIdxMother
            n += 1
            if n > len(genparts):
                raise ValueError("Cyclic GenPart ancestry")
        return idx, genparts[idx].pdgId if idx >= 0 else 0

    @classmethod
    def _parent_id(cls, part, genparts):
        idx, pid = cls._mother(part, genparts)
        if idx < 0:
            return 0
        ppidx = genparts[idx].genPartIdxMother
        if pid == 23 and ppidx >= 0 and genparts[ppidx].pdgId == 25:
            return 25
        return pid

    @classmethod
    def _genzz_mass(cls, event):
        """Same GenPart selection as CJLST Run3 mcTruthAnalyzer.py."""
        from ROOT import TLorentzVector
        parts = Collection(event, "GenPart")
        zz, associated = [], []
        for i, p in enumerate(parts):
            if abs(p.pdgId) not in (11, 13, 15) or p.genPartIdxMother < 0:
                continue
            mid = parts[p.genPartIdxMother].pdgId
            pid = cls._parent_id(p, parts)
            if mid == 25 or (mid == 23 and pid == 25):
                zz.append(i)
            elif (mid == 23 and pid == 23) or mid == 24:
                associated.append(i)
        if len(associated) == 4 and not zz:
            zz = associated
        if len(zz) != 4:
            return 0.0
        p4 = TLorentzVector()
        for i in zz:
            p4 += parts[i].p4()
        return float(p4.M())

    def _initialize_mela(self):
        if not self.is_qqzz or self._mela is not None:
            return
        try:
            import Mela
        except ImportError as exc:
            raise RuntimeError("qqZZ requires official CJLST Mela Python binding") from exc
        self._MelaModule = Mela
        self._mela = Mela.Mela(13.6, 125, Mela.VerbosityLevel.ERROR)
        self._mela.setCandidateDecayMode(Mela.CandidateDecayMode.CandidateDecay_ZZ)

    def _lhe_costhetastar(self, event):
        """CJLST LHEAngProbFiller.py NanoAOD v12-v14 selection + MELA."""
        self._initialize_mela()
        parts = Collection(event, "LHEPart")
        leptons = [p for p in parts if p.status == 1 and abs(p.pdgId) in (11, 13, 15)]
        if len(leptons) < 4:
            raise ValueError("Fewer than 4 LHE status=1 leptons")
        daughters = self._MelaModule.SimpleParticleCollection_t()
        for p in leptons[-4:]:
            daughters.add_particle(self._MelaModule.SimpleParticle_t(
                p.pdgId, p.pt, p.eta, p.phi, p.mass, True))
        try:
            self._mela.setInputEvent(daughters, None, None, 0)
            _, _, _, _, _, _, costhetastar, _ = self._mela.computeDecayAngles()
            return float(costhetastar)
        finally:
            self._mela.resetInputEvent()

    def _fill_unity(self):
        for name in self._branch_names:
            self.out.fillBranch(name, 1.0)

    @staticmethod
    def _cos_bin(costheta):
        c = abs(costheta)
        if c < 0.25:
            return 0
        if c < 0.5:
            return 1
        if c < 0.75:
            return 2
        return 3


    def analyze(self, event):
        if not self.apply_kfactor:
            return True
        try:
            mass = self._genzz_mass(event)
            if mass <= 0:
                raise ValueError("GenZZ_mass must be positive, got %s" % mass)
            if self.is_ggzz:
                values = {
                    "KFactor_QCD_ggZZ_Nominal": float(self.gg_splines["nominal"](mass))
                }
                for label, source in (("PDF", "PDF"), ("QCD", "QCD_mu"),
                                      ("aS", "PDF_aS")):
                    delta = float(self.gg_splines[source](mass))
                    values["KFactor_QCD_ggZZ_%s_up" % label] = 1.0 + delta
                    values["KFactor_QCD_ggZZ_%s_dn" % label] = 1.0 - delta

            else:
                costheta = self._lhe_costhetastar(event)
                if abs(costheta) > 1.0 + 1e-5:
                    raise ValueError("Invalid LHEMela_costhetastar=%s" % costheta)
                i = self._cos_bin(costheta)
                def ev(name):
                    return float(self.qq_splines[(i, name)](mass))
                nominal = ev("nominal")
                values = {
                    "KFactor_ZZQQB_Nominal": nominal,
                    "KFactor_ZZQQB_QCD_up": ev("QCD_up"),
                    "KFactor_ZZQQB_QCD_dn": ev("QCD_dn"),
                }
                for label, source in (("EW", "EW_factor"),
                                      ("smoothing", "smoothing_factor"),
                                      ("aS", "alpha_S_factor")):
                    delta = ev(source)
                    values["KFactor_ZZQQB_%s_up" % label] = 1.0 + delta
                    values["KFactor_ZZQQB_%s_dn" % label] = 1.0 - delta
            for name, value in values.items():
                if not math.isfinite(value):
                    raise ValueError("Nonfinite output %s=%s" % (name, value))
            values["GenZZ_mass"] = mass
            if self.is_qqzz:
                values["LHEMela_costhetastar"] = costheta
            for name in self._branch_names:
                self.out.fillBranch(name, values[name])
        except (RuntimeError, ValueError, AttributeError) as exc:
            if self.strict:
                raise
            self._missing_count += 1
            if self._missing_count <= 5:
                print("[kFactorProducer_Run3] WARNING: %s; filling unity" % exc)
            self._fill_unity()
        return True

    def endJob(self):
        if self._missing_count:
            print("[kFactorProducer_Run3] WARNING: unity fallback in %d events"
                  % self._missing_count)


def create_kfactor_producer(year, sample_path, kfactor_dir=None,
                            gg_order=1, strict=True):
    """Drop-in factory for corrections_config.py."""
    return kFactorProducer_Run3(year, sample_path, kfactor_dir,
                               gg_order=gg_order, strict=strict)
