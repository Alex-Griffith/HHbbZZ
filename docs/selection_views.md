# Momentum selection views

This change is based on PR29 (`6a41139972a8b6eb983fab98a572c50a85d01b21`),
with FSR enabled. Lepton ID/SIP thresholds, electron HZZ Iso MVA and jet cleaning
cuts are unchanged. FSR photon selection and the muon isolation correction are
repaired as specified below, so nominal acceptance can change from PR29.

## FSR definition

Keep the native FsrPhoton electronIdx/muonIdx ownership. Among photons with
`pt>2`, `abs(eta)<2.4`, `relIso03<0.8`, require the stored
`dROverEt2<0.012` and lepton-photon `DeltaR<0.5`, then select the smallest stored
`dROverEt2` for each lepton. The last two thresholds now come from YAML
`dRlOverPtcut` and `dRlcut`; their configured values already existed.
Exact score ties keep the first source index. The raw NanoAOD backlinks use
looser photon quality cuts, so they are not substituted for this analysis choice.

Recover the selected photon's four-momentum throughout the recovery cone.
For muon isolation, subtract that muon's selected photon only when
`0.01<DeltaR<0.3`, and floor the corrected isolation at zero. The cut remains
`pfRelIso03FsrCorr<0.35`. The same cached choice is used for dressing and isolation,
and is recomputed by the shared selector for every momentum view. Turning FSR
off leaves both four-momenta and isolation uncorrected.

This uses native photon ownership; it does not perform CJLST's additional
reassignment among a differently selected loose-lepton collection. The stored
score is used without overwriting `FsrPhoton_dROverEt2`.

The nominal output additionally records `Electron_fsrPhotonIdxAnalysis`,
`Muon_fsrPhotonIdxAnalysis` (native photon indices, -1 if absent) and
`Muon_pfRelIso03FsrCorr`. Existing Electron*/Muon* keep rules retain them.
The original NanoAOD `*_fsrPhotonIdx` backlinks remain available for comparison.

## Output and retention

For Run-3 MC, the producer reruns the same C++ reconstruction for these views,
in the following stable order:

| Slot | View |
|---:|---|
| 0 | nominal |
| 1–4 | Electron_scaleUp, Electron_scaleDn, Electron_smearUp, Electron_smearDn |
| 5–8 | Muon_scaleUp, Muon_scaleDn, Muon_smearUp, Muon_smearDn |
| 9–12 | Jet_scaleUp, Jet_scaleDn, Jet_smearUp, Jet_smearDn |

Each view changes one source at a time, using the absolute pT values already
produced by the correction modules. Jet variations also use the corresponding
mass. Lepton rest masses, eta/phi, IDs, trigger decision, event weights and input
PuppiMET stay fixed. This implements the existing momentum variations; it does
not add MET, trigger, ID or weight nuisances. In particular, the 2P1F MET cut is
evaluated with the same input MET in these views.

For enabled Run-3 MC views, the raw preselection counts leptons without a pT
requirement. Data and nominal-only runs keep the original raw preselection. The
calibrated view then applies the original thresholds, reruns FSR recovery and isolation,
finds the best candidate, performs jet cleaning and builds the dijet. The saved
events are the union of nominal and all available views passing SR or ZXCR.
No event is duplicated. The legacy 2l2j mode continues retaining all triggered
events after its collection-count preselection.

**Legacy branches always describe nominal.** For nominal SR yield, require
`passedFullSelection` (or `isSR`), including on newly retained events. A saved
row alone is not a nominal pass. `isZXCR` remains the nominal CR flag.

`Sel_*` arrays have `nSel` entries (13 for enabled Run-3 MC; 1 for data or
`--NOsyst`). The ROOT metadata tree `SelectionViews` records `schemaVersion=1`,
`viewId` and `viewName`. After haddnano, repeated identical mappings from each
input file are expected; deduplicate these three fields to read the mapping.
`--NOsyst` disables the selection reruns; nominal
calibrations and any uncertainty input arrays still produced by those modules
are unaffected. Pre-Run-3 uses only nominal.

- `Sel_isSR`, `Sel_isZXCR`: independent region decisions for each view.
- `Sel_CRtype`: 0=no CR, 1=2P1F, 2=2P2F, 3=3P1F.
- `Sel_mass4l`, `Sel_pt4l`, `Sel_massZ1`, `Sel_massZ2`: selected candidate
  observables; four-lepton quantities are invalid for 2P1F and 2l2j.
- `Sel_lep{1..4}Idx`, `Sel_lep{1..4}PdgId`, `Sel_lep{1..4}Tight`:
  NanoAOD source indices, signed PDG IDs, and tight decisions, in Z1/Z2 order.
  Indices refer to Electron or Muon according to abs(PdgId). They are not the
  legacy concatenated tight-lepton indices. The two leptons within a Z retain
  selector order and are not resorted by pT here.
- `Sel_nJet`: selected jet multiplicity. `Sel_goodJetIdx` is a flat list with
  counter `nSelGoodJet`; the slice for slot i begins at `Sel_jetOffset[i]` and
  has `Sel_nJet[i]` entries. Indices refer to the complete saved Jet collection.
- `Sel_jet1Idx`, `Sel_jet2Idx`, `Sel_mjj`, `Sel_m4ljj`: selected b-tag-ranked
  jet pair and its masses. Inclusive 4l SR still accepts 0/1-jet events; an
  optional pair is built after SR selection when available. Legacy 4l dijet
  branch behavior is unchanged.

Invalid floats are -999, invalid indices are -1 and absent PDG IDs are 0.
Candidate quantities and pair indices are invalid for views failing both
regions. Jet multiplicity/cleaned indices can still be present for failed views.
Missing or incorrectly sized MC momentum-shift arrays for a nonempty collection
raise an error rather than silently substituting nominal values. Empty collections
need no per-event correction array; NATModules omit their extra-branch fill.

The selection results are computed from the correction modules' in-memory
values. NATModules saves jet masses with 12 mantissa bits, so reconstructing mjj
from the saved jet arrays has a small, expected quantization difference. Use the
saved `Sel_*` decisions, indices and masses for these implemented views.

## GenJet and FSR inputs

Derived `GENjet_hadronFlavour` uses its own `nGENJets` counter. Native `nGenJet`
is no longer overwritten, preserving all native `GenJet_*` and source indices.
This fixes output corruption; the original JER correction already ran before
this output fill.

Both keep files retain exactly these raw FSR fields: `nFsrPhoton`,
`FsrPhoton_pt`, `eta`, `phi`, `relIso03`, `dROverEt2`, `electronIdx`, `muonIdx`.
Existing dressed electron/muon branches remain available. The change does not
add unrelated trigger collections or broaden raw photon retention.

## Validation

Validation was performed in the existing CMSSW/NanoAODTools runtime. The fixture
script is retained locally and is not included in this pull request.
Controlled fixtures with the actual C++ selector check FSR
minimum-score choice, photon quality/radius cuts, isolation-cone boundaries,
native ownership, the disabled FSR switch, lepton
threshold migration, CR jet migration in inclusive 4l, tied b tags, source
indices, state reset, missing shift inputs and union flags. Fixture migrations
are not measured physics rates. The initial bounded raw-NanoAOD pilot compares
PR29 nominal output before the FSR repair. A second pilot isolates the FSR repair
with identical view/preselection logic on both sides, checks independent photon
indices and isolation, and verifies native GenJet/FSR round trips and union retention.
