# Single-pass 4l storage for Z+X

The output event union is the existing nominal/shifted SR and ZXCR union **or**
`passedZPlusLStorage`. The latter is a nominal-only storage flag, not a measured
fake-rate region, a fourth SR/CR category, or a replacement for existing flags.
`post_proc.py --mode 4l` enables the recommended FR envelope by default, on both
data and MC. No extra production switch is required. Use `--no-zx-storage`
only for a legacy-acceptance comparison. Masks, metadata and trigger inputs
are still written in that comparison. Other analysis modes retain their old
defaults; `4l2j --zx-storage` explicitly enables the same extra FR envelope,
while 2l2j rejects the storage option.

## Default FR storage envelope

- Apply the existing configured trigger OR and data golden JSON as before.
- Require exactly three current nominal CR-loose leptons, with a tight
  opposite-sign same-flavour tag pair. Loose/tight membership comes directly
  from `ZXLooseLeptons`, including the existing electron cross-cleaning.
- Use the selected FSR-dressed tag p4 when FSR is enabled, the configured broad
  tag mass bounds, |m(tag)-configured Zmass|<7 GeV, and tag pT>20/10 GeV.
- Apply the current bare-lepton pair cuts: DeltaR>0.02 for every pair and
  mass>=4 GeV for every opposite-sign pair. Require finite 0<=MET<25 GeV.
- Keep both a tight and a failing loose probe. Do not require jets or a dijet;
  this includes 0/1-jet FR inputs and allows downstream jet/b-tag comparisons.
- Evaluate storage once from nominal objects; existing nominal and shifted
  SR/CR events are retained regardless of this envelope. In particular, these
  MET/three-loose cuts are never applied globally to the existing SR/CR union.

The default fixes the current loose, tag, multiplicity and low-MET envelope.
It supports FR binning, trigger matching and jet/b-tag studies within that
envelope. It cannot recover probes outside the current loose definition or
new MET>=25 regions. These would need a deliberately broader production.

## Explicit wide storage envelope

Use `post_proc.py --mode 4l --zx-storage-profile wide` only when broad probe
or sideband studies justify the increased size. This profile instead uses:

- Require at least three basic-acceptance leptons after nominal corrections:
  electron pT/eta acceptance, or muon pT/eta/type acceptance from the existing
  `goodLoose*2012()` functions. Extra probes need not pass SIP/dxy/dz/ID/isolation.
- Require an opposite-sign same-flavour pair of current CR-tight leptons with
  the existing broad configured MZcut mass window (currently 12 < mass < 120 GeV).
  Tag p4 is FSR dressed when FSR is enabled. Electron/muon cross-cleaning follows
  the existing `ZXLooseLeptons` tight decisions.
- Do not impose a narrow Z window, MET, jet count, dijet, exact-three-lepton,
  probe-tight requirement, or four-tight-lepton veto on this storage branch.
- Evaluate this once from the nominal worker. Do not add twelve FR reselections.

With storage enabled, data/nominal 4l preselection uses object counts, not raw-pT thresholds, so that
nominal corrections can move a probe across its basic acceptance threshold.
SR/CR selectors and their thresholds are unchanged; the larger preselection may
recover threshold-migrating data events absent from the old output.

## Branches

New derived branches:

| Branch | Meaning |
| --- | --- |
| passedZPlusLStorage | Event satisfies the nominal storage envelope above |
| Electron_ZXLoose, Muon_ZXLoose | Exact membership in the current nominal CR loose list, indexed by the original Electron/Muon collection |
| Electron_ZXTight, Muon_ZXTight | Tight status within that loose list, including CR electron cross-cleaning |

No best Z/probe is forced by the storage layer. Rebuild and rank pairs/probes
from the full saved collections, the masks and FSR associations in downstream
code. Retain all candidate/probe choices until the measurement prescription is
fixed. In particular, a saved event is not one fake-rate denominator entry by
default. For the existing prescription, select exactly three current CR-loose
leptons, tight OS-SF Z tags and one loose probe; form pass as a subset of this
same denominator using its ZXTight mask, after the remaining measurement cuts.

Newly kept input branches in both data and MC: `HLT*`, `nTrigObj`, `TrigObj_*`,
and `Flag_*`. Their absence in a particular NanoAOD schema must be recorded;
missing HLT paths are not equivalent to false decisions. Trigger matching and
the tag-trigger prescription still belong to the downstream FR measurement.

Existing branches are reused: all Electron/Muon and Jet collections, compact
FsrPhoton inputs, selected photon indices, FSR-dressed lepton p4,
Muon_pfRelIso03FsrCorr, PuppiMET, PV/rho, run/luminosityBlock/event, candidate
indices, CR flags, selection views, MC generator information and weights.
No duplicate FR pT/eta, photon collection, jet-pair or weight branch is added.

Data explicitly stores `GENlep_Hindex=[-1,-1,-1,-1]`. Its length counter is
shared with the four reconstructed `lep_Hindex` entries; filling an empty GEN
array used to expose uninitialized buffer contents when the shared count was
subsequently set to four. MC retains its original truth-index definition.

The legacy goodJet/cleaning flags are not a cleaned-jet list for every possible
FR candidate. Recompute candidate-specific cleaning from full Jet and lepton
collections, including the probe, using the production prescription. Existing
application CR candidates can use their saved Sel_goodJetIdx and leg indices.

Production records must retain dataset/era and source-file mappings, input and
processed-lumisection coverage, golden JSON, configs, source and correction
versions. Selected event lumisections alone do not determine luminosity. Dedup
data streams with run/luminosityBlock/event and an explicit stream policy.

## Use and limits

Continue selecting nominal application regions with passedZXCR3P1FSelection or
passedZXCR2P2FSelection, and nominal SR with passedFullSelection. Newly retained
FR-only events have these flags false and must not enter SR histograms merely
because they are present in Events. Existing application CRs still require >=2
cleaned jets; this patch does not make the 0/1-jet four-lepton CR inclusive.

This stores the inputs to measure FR and subtract matching prompt MC; it does
not calculate fake rates, prompt-subtraction weights or final Z+X templates.
In particular, tight muons in production still use SIP<8, not SIP<4; all
measurement/application definitions must match the intended selection.

Both profiles fix the existing trigger coverage, input NanoAOD schema and tag
tight definition. Only the explicit wide profile permits changing the current
probe-loose, multiplicity and MET/narrow-Z cuts downstream. Neither guarantees
arbitrary tag, trigger, acceptance or detector-reconstruction changes without
rereading inputs.

## Output acceptance and provenance

`ZXStorageConfig` schemaVersion 2 is a one-row-per-input TTree containing JSON
with the enabled mode, `fr`/`wide` profile and storage thresholds, selection YAML,
input file, available HLT/TrigObj/Flag and Electron/Muon/Jet/PuppiMET schemas,
and actual CMSSW/ROOT versions. Merge preserves individual input rows, including schema
differences; absent branches are not silently recorded as false decisions.
Existing production file mappings, input/processed ranges, certified lumisections
and normalization records remain required; the selected event list is not a
luminosity ledger. For partial tests record the input entry limit explicitly.

`ci/check_zx_storage.py` validates the persisted event union, nominal flags,
original-index mask lengths/tight-subset membership and all available retained
lepton, jet, MET, trigger and quality inputs. It rejects mixed profiles and
checks the default envelope's loose count and MET. StorageOnly is a separate acceptance category: no SR/CR
flag is set to make it pass an older acceptance program. Frozen campaign runners
are not modified or reused to publish these tests.

## Performance changes

Configured trigger branch names are resolved once per producer from the already
loaded YAML. Per-event evaluation still reads every configured path and raises
on a missing one, including when an earlier path is true. No trigger OR changes.

Nominal and all enabled shifted region decisions run before output-only work.
Rejected events skip GenAnalysis input transfers, truth derivation and legacy
output arrays. Shifted-only and storage-only events still receive the complete
output schema. Correction modules and their random-number sequence are unchanged.
Data no longer loads/constructs the unused GenAnalysis library/worker.
GEN end-job diagnostics now count retained events and are explicitly labelled
`RetainedGEN*`, with the scope recorded in metadata; they are not a generated
event efficiency denominator. Runs/genEventSumw and stored truth/weight branches
are unchanged. Full generated-event cutflows require a separate all-event
diagnostic pass; do not compare these log counters to the older all-trigger
counters.
The nominal snapshot stays after legacy fields are read because BuildBestDijet
has side effects. Exact output comparisons test this order explicitly.

For a single input, `skim_io.run_postprocessor` executes the configured original
haddnano.py in the already loaded ROOT process. It preserves the original merge
and compaction behavior and normal job-report ordering while avoiding a second
Python/ROOT startup. The adapter is scoped to the pinned framework's os reference;
process-wide os.system and PATH are unchanged, and sys.argv/framework references
are restored on failure. The pinned CLI relies on process exit for file closure;
the adapter explicitly closes its output and input handles before the job report.
Multiple inputs keep the existing subprocess behavior.
A tested direct-rename alternative increased the ggZZ fixture size substantially
and is not the delivered default.

## Local validation

From the repository root, run
`uv run --no-project --managed-python --python 3.11 python -m unittest discover -s tests -p 'test_*.py'`.
The tests cover default FR pass/fail symmetry, MET/tag/pair boundaries, wide-probe
retention, original indices, eager trigger errors and finalization restoration,
together with the existing jet helper tests. See [validation and sizing](zx_storage_validation.md)
for bounded native comparisons and the storage estimate; these do not constitute
full production acceptance or 2022/2023 validation.
