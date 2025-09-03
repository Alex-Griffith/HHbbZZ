from __future__ import print_function
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
import os
import numpy as np
import correctionlib

class jetJERC(Module):
    def __init__(self, json_JERC, json_JERsmear, L1Key=None, L2Key=None, L3Key=None, L2L3Key=None, scaleTotalKey=None,smearKey=None, JERKey=None, JERsfKey=None, overwritePt=False, usePhiDependentJEC=False, useRunDependentJEC=False):
        self.overwritePt = overwritePt
        self.usePhiDependentJEC = usePhiDependentJEC
        self.useRunDependentJEC = useRunDependentJEC
        self.evaluator_JERC = correctionlib.CorrectionSet.from_file(json_JERC)
        self.evaluator_jer = self.evaluator_JERC
        self.evaluator_L1 = self.evaluator_JERC[L1Key]
        self.evaluator_L2 = self.evaluator_JERC[L2Key]
        self.evaluator_L3 = self.evaluator_JERC[L3Key]
        self.evaluator_L2L3 = self.evaluator_JERC[L2L3Key]
        self.is_mc = JERKey is not None
        self.evaluator_JER, self.evaluator_JERsf, self.evaluator_JES = None, None, None
        if self.is_mc:
            self.evaluator_JER = self.evaluator_JERC[JERKey]
            self.evaluator_JERsf = self.evaluator_JERC[JERsfKey]
            self.evaluator_JES = self.evaluator_JERC[scaleTotalKey]

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree
        if self.overwritePt :
            self.out.branch("Jet_pt", "F", lenVar="nJet")
            self.out.branch("Jet_mass", "F", lenVar="nJet")
            self.out.branch("Jet_uncorrected_pt", "F", lenVar="nJet")
            self.out.branch("Jet_uncorrected_mass", "F", lenVar="nJet")
        else:
            self.out.branch("Jet_corrected_pt", "F", lenVar="nJet")
            self.out.branch("Jet_corrected_mass", "F", lenVar="nJet")
        if self.is_mc:
            self.out.branch("Jet_scaleUp_pt", "F", lenVar="nJet")
            self.out.branch("Jet_scaleDn_pt", "F", lenVar="nJet")
            self.out.branch("Jet_scaleUp_mass", "F", lenVar="nJet")
            self.out.branch("Jet_scaleDn_mass", "F", lenVar="nJet")
            self.out.branch("Jet_smearUp_pt", "F", lenVar="nJet")
            self.out.branch("Jet_smearDn_pt", "F", lenVar="nJet")
            self.out.branch("Jet_smearUp_mass", "F", lenVar="nJet")
            self.out.branch("Jet_smearDn_mass", "F", lenVar="nJet")

    def fixPhi(self, phi):
        if phi > np.pi: phi -= 2*np.pi
        elif phi < -np.pi: phi += 2*np.pi
        return phi

    def analyze(self, event):
        jets = Collection(event, "Jet")
        if self.is_mc:
            gen_jets = Collection(event, "GenJet")
            gen_jets_pt = np.array([gen_jet.pt for gen_jet in gen_jets])
            gen_jets_eta = np.array([gen_jet.eta for gen_jet in gen_jets])
            gen_jets_phi = np.array([gen_jet.phi for gen_jet in gen_jets])

        pt_corr, mass_corr, pt_uncorr, mass_uncorr = [], [], [], []
        pt_smear_up, pt_smear_dn, mass_smear_up, mass_smear_dn = [], [], [], []
        pt_scale_up, pt_scale_dn, mass_scale_up, mass_scale_dn = [], [], [], []

        for i, jet in enumerate(jets):
            # ======================= "BEFORE" BLOCK =======================
            # print(f"\n\n--- Processing Jet {i} (Event {getattr(event, 'event', 'N/A')}) ---")
            # print(f"  [INPUT]  pt: {jet.pt:<10.8f} eta: {jet.eta:<10.8f} phi: {jet.phi:<10.8f} mass: {jet.mass:<10.8f}")
            
            pt_raw = jet.pt * (1 - jet.rawFactor)
            mass_raw = jet.mass * (1 - jet.rawFactor)
            
            # L1 correction is always the same
            pt_L1 = pt_raw * self.evaluator_L1.evaluate(jet.area, jet.eta, pt_raw, event.Rho_fixedGridRhoFastjetAll)
            
            # ======================= DYNAMIC JEC APPLICATION (FINAL) =======================
            # This block dynamically determines if phi is needed for each correction level.
            
            # --- L2 Correction ---
            try:
                # First, try the call WITH phi, as this is the newer convention
                l2_corr = self.evaluator_L2.evaluate(jet.eta, jet.phi, pt_L1)
            except RuntimeError as e:
                if "Too many inputs" in str(e):
                    # If that fails, it means this correction doesn't need phi. Retry without it.
                    l2_corr = self.evaluator_L2.evaluate(jet.eta, pt_L1)
                else:
                    # If it's a different error (e.g., "Insufficient inputs"), re-raise it.
                    raise e
            pt_L2 = pt_L1 * l2_corr

            # --- L3 Correction ---
            try:
                l3_corr = self.evaluator_L3.evaluate(jet.eta, jet.phi, pt_L2)
            except RuntimeError as e:
                if "Too many inputs" in str(e):
                    l3_corr = self.evaluator_L3.evaluate(jet.eta, pt_L2)
                else:
                    raise e
            pt_L3 = pt_L2 * l3_corr
            
            # --- L2L3 Residual Correction (for Data) ---
            if not self.is_mc:
                try:
                    l2l3_corr = self.evaluator_L2L3.evaluate(jet.eta, jet.phi, pt_L3)
                except RuntimeError as e:
                    if "Too many inputs" in str(e):
                        l2l3_corr = self.evaluator_L2L3.evaluate(jet.eta, pt_L3)
                    else:
                        raise e
                pt_JEC = pt_L3 * l2l3_corr
            else:
                pt_JEC = pt_L3
            # =============================================================================

            mass_JEC = mass_raw * (pt_JEC / pt_raw if pt_raw > 0 else 1.0)

            final_pt = pt_JEC
            final_mass = mass_JEC

            # vvv CHANGE THE FORMATTING HERE vvv
            # print(f"  [INTERMEDIATE] pt_JEC: {pt_JEC:<10.8f}")

            if self.is_mc:
                JER = self.evaluator_JER.evaluate(jet.eta, pt_JEC, event.Rho_fixedGridRhoFastjetAll)
                delta_eta = jet.eta - gen_jets_eta
                fixPhi = np.vectorize(self.fixPhi, otypes=[float])
                delta_phi = fixPhi(jet.phi - gen_jets_phi)
                pt_gen_candidates = np.where((np.abs(pt_JEC - gen_jets_pt) < 3 * pt_JEC * JER) & (np.sqrt(delta_eta**2 + delta_phi**2)<0.2), gen_jets_pt, -1.0)
                pt_gen_filtered = pt_gen_candidates[pt_gen_candidates > 0]
                pt_gen = pt_gen_filtered[0] if len(pt_gen_filtered) > 0 else -1.

                # vvv ADD THIS LINE vvv
                # print(f"  [SMEARING] Matched GenJet pt: {pt_gen:<10.8f}")

                JERsf = self.evaluator_JERsf.evaluate(jet.eta, pt_JEC, "nom")
                JERsf_up = self.evaluator_JERsf.evaluate(jet.eta, pt_JEC, "up")
                JERsf_dn = self.evaluator_JERsf.evaluate(jet.eta, pt_JEC, "down")
                
                # vvv MODIFY THIS LINE TO INCLUDE RHO vvv
                # print(f"  [FACTORS] Rho: {event.Rho_fixedGridRhoFastjetAll:<10.8f} ScaleFactor: {JERsf:<10.4f} PtResolution: {JER:<10.8f}")

                smear_factor, smear_factor_up, smear_factor_dn = 1.0, 1.0, 1.0
                if pt_gen > 0:
                    # vvv ADD THIS LINE vvv
                    # print(f"  [SMEARING] Method: Stochastic (using GenJet match)")
                    smear_factor = 1.0 + (JERsf - 1.0) * (pt_JEC - pt_gen) / pt_JEC
                    smear_factor_up = 1.0 + (JERsf_up - 1.0) * (pt_JEC - pt_gen) / pt_JEC
                    smear_factor_dn = 1.0 + (JERsf_dn - 1.0) * (pt_JEC - pt_gen) / pt_JEC
                elif JERsf > 1:
                    sigma = JER * np.sqrt(JERsf**2 - 1)
                    # vvv ADD THESE LINES vvv
                    seed_id = int(event.event + (jet.eta + 2.5) * 10000)
                    # print(f"  [SMEARING] Method: Smearing (no GenJet match)")
                    # print(f"  [SMEARING] Seed ID: {seed_id}, Sigma: {sigma:<10.8f}")
                    np.random.seed(seed_id)
                    smear_factor = np.random.normal(1.0, sigma)
                    np.random.seed(seed_id) # Reset seed for consistency if needed elsewhere
                    smear_factor_up = np.random.normal(1.0, JER * np.sqrt(JERsf_up**2 - 1))
                    smear_factor_dn = np.random.normal(1.0, JER * np.sqrt(JERsf_dn**2 - 1))
                
                smear_factor = max(0.0, smear_factor)
                smear_factor_up = max(0.0, smear_factor_up)
                smear_factor_dn = max(0.0, smear_factor_dn)

                pt_JEC_JER = pt_JEC * smear_factor
                mass_JEC_JER = mass_JEC * smear_factor
                final_pt = pt_JEC_JER
                final_mass = mass_JEC_JER
                
                pt_JEC_JER_up = pt_JEC * smear_factor_up
                pt_JEC_JER_dn = pt_JEC * smear_factor_dn
                JESuncert = self.evaluator_JES.evaluate(jet.eta, pt_JEC)
                pt_JES_up = pt_JEC_JER * (1 + JESuncert)
                pt_JES_dn = pt_JEC_JER * (1 - JESuncert)

                # ======================= "AFTER" BLOCK =======================
                # print(f"  [OUTPUT] pt: {final_pt:<10.8f} eta: {jet.eta:<10.8f} mass: {final_mass:<10.8f}")
                
                pt_smear_up.append(pt_JEC_JER_up)
                pt_smear_dn.append(pt_JEC_JER_dn)
                mass_smear_up.append(mass_JEC * smear_factor_up)
                mass_smear_dn.append(mass_JEC * smear_factor_dn)
                pt_scale_up.append(pt_JES_up)
                pt_scale_dn.append(pt_JES_dn)
                mass_scale_up.append(mass_JEC_JER * (1 + JESuncert))
                mass_scale_dn.append(mass_JEC_JER * (1 - JESuncert))
            else:
                # ======================= "AFTER" BLOCK (Data) =======================
                # print(f"  [OUTPUT] pt: {final_pt:<10.8f} eta: {jet.eta:<10.8f} mass: {final_mass:<10.8f}")

            pt_corr.append(final_pt)
            mass_corr.append(final_mass)
            pt_uncorr.append(jet.pt)
            mass_uncorr.append(jet.mass)

        if self.overwritePt :
            self.out.fillBranch("Jet_uncorrected_pt", pt_uncorr)
            self.out.fillBranch("Jet_pt", pt_corr)
            self.out.fillBranch("Jet_uncorrected_mass", mass_uncorr)
            self.out.fillBranch("Jet_mass", mass_corr)
        else :
            self.out.fillBranch("Jet_corrected_pt", pt_corr)
            self.out.fillBranch("Jet_corrected_mass", mass_corr)

        if self.is_mc:
            self.out.fillBranch("Jet_smearUp_pt", pt_smear_up)
            self.out.fillBranch("Jet_smearDn_pt", pt_smear_dn)
            self.out.fillBranch("Jet_smearUp_mass", mass_smear_up)
            self.out.fillBranch("Jet_smearDn_mass", mass_smear_dn)
            self.out.fillBranch("Jet_scaleUp_pt", pt_scale_up)
            self.out.fillBranch("Jet_scaleDn_pt", pt_scale_dn)
            self.out.fillBranch("Jet_scaleUp_mass", mass_scale_up)
            self.out.fillBranch("Jet_scaleDn_mass", mass_scale_dn)

        return True