# Z+X retention validation and storage budget

The tables below record the **2026-10-29 schemaVersion 2** SIP-limited default.
The 2026-10-31 schemaVersion 3 adds no-SIP loose masks, the union of both
three-loose FR envelopes and separate no-SIP application inputs. The old full
campaign storage estimate does not include this extension. See the dated
three-layer comparison below for the new bounded measurements.

2026-10-29. Base: Run3 commit `85fd0cfe94ac43817d7db75022548e3f4beb5afd`.
The bounded native runtime is CMSSW_15_0_2, ROOT 6.32.11 and uv-managed
Python 3.9.23. Tests use fixed raw 2024 NanoAOD prefixes, seed 12345, the same
correction-module order, all 13 MC selection views and LZMA:9 compression.
They are technical checks, not fake-rate measurements or full production.

## Retention contract

Plain `--mode 4l` enables `fr` storage. The output is the old nominal/shifted
SR/CR union plus nominal three-loose, tight-Z-tag, current pair/tag-pT,
MET<25 GeV pass/fail events without a jet-count cut. Default SR and four-lepton
application-CR definitions are unchanged. See [the full contract](zx_storage.md).

The native regression checks include:

- Default output identities against an independent, previously computed
  projection of the wide output, using original-index masks, saved nominal
  momenta and selected FSR photons. The independent reconstruction also
  reproduces every current 2P1F fail decision after its candidate jet cuts.
- All other persisted values on surviving events against the wide output;
  only the deliberately narrowed `passedZPlusLStorage` flag changes meaning
  with the recorded profile. No input Electron/Muon/Jet/PuppiMET branch is
  allowed to disappear; available HLT/TrigObj/Flag branches are checked too.
- Original data/WZ/ggZZ event union and original branch values against the
  unmodified base, including MC variation-only events. The data GEN index
  repair is an explicit exception requiring four -1 values, not an ignored
  branch. Runs, LuminosityBlocks and SelectionViews remain equal.
- ROOT files must not be zombie/recovered, and framework job reports must
  contain no FrameworkError. Identical NaNs require the same representation;
  finite values use no numerical tolerance.

Local checks: 24 unit tests cover FR and wide decisions, original indices,
trigger errors, the existing jet helper and single-input finalization/restoration.
Syntax and whitespace checks pass. No correction or selection systematic was
removed for speed.

The plain `--mode 4l` native checks pass for all seven inputs (165,038 raw
events in total). They retain 2,272 events and match 7,231,120 scalar values
from the previous wide outputs, excluding only the intended profile flag
change described above. All original data/WZ/ggZZ events survive; the ggZZ
sample includes 1,210 SR, 40 CR and five variation-only old events.

| Input | Raw prefix | Old union | Previous wide | Default FR union | Wide file / MB | Default file / MB |
|---|---:|---:|---:|---:|---:|---:|
| Data | 100,000 | 3 | 362 | 23 | 0.827 | 0.285 |
| WZ | 5,000 | 4 | 546 | 42 | 1.648 | 0.409 |
| ggZZ→4e | 5,000 | 1,255 | 3,001 | 1,576 | 7.800 | 4.485 |
| DY→mu mu | 30,000 | 61 | 3,216 | 348 | 8.852 | 3.321 |
| DY→ee | 10,038 | 12 | 713 | 78 | 4.151 | 2.742 |
| TT | 10,000 | 4 | 790 | 7 | 4.789 | 2.472 |
| qqZZ | 5,000 | 143 | 847 | 198 | 4.542 | 3.112 |

The same stored branch set survives in every row. These are within-input
comparisons: data/WZ/ggZZ prefixes omit raw MetaData/ParameterSets, while the
other probes retain full input file metadata. Do not compare their absolute
bytes/event as interchangeable production rates. The default data FR envelope
has two pass and 19 fail events, and WZ has 34 pass and five fail events;
additional old SR/CR/views need not themselves satisfy the FR envelope.

## Matched performance with the delivered default

A final sequential WZ rerun uses the exact same default FR envelope in the
unoptimized reference and optimized code. Both save the same 42 events and
1,380 branches; all 127,864 scalar values and Runs/LuminosityBlocks/SelectionViews
agree exactly. It uses the same input prefix, corrections, 13 views, seed and
LZMA:9. The explicit wide option also matches the previous 546-event wide
output, and `--no-zx-storage` matches the original four-event acceptance and
original values.

| WZ default FR, 5,000 raw events | Reference | Optimized warm rerun | Reduction |
|---|---:|---:|---:|
| Event-loop CPU / s | 15.094 | 6.766 | 55.2% |
| post_proc main-flow wall / s | 32.909 | 18.157 | 44.8% |
| Final ROOT bytes | 408,902 | 408,910 | Same event content |

The final validator passes on all 11 native outputs, explicitly requiring
FSR inputs/corrected muon isolation and, for MC, GenPart ancestry/status flags,
electron/muon truth indices and genWeight for downstream prompt subtraction.

The small byte difference is ROOT file metadata. These timings isolate the
flow optimization with identical retention; they do not mix in the reduction
from wide storage to the default. As below, the driver preloads ROOT/framework
and wall times are host/cache/I/O dependent, not campaign-level predictions.

## Previously measured optimization with identical wide retention

These isolate performance changes by comparing the same wide envelope and
output schema before/after optimization. They are not before/after timings
from narrowing the storage envelope.

| Input | Raw prefix | Saved | Reference event-loop CPU / s | Optimized CPU / s | Reduction | Reference main-flow wall / s | Optimized wall / s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Data | 100,000 | 362 | 49.07 | 13.16 | 73.2% | 62.22 | 27.66 |
| WZ | 5,000 | 546 | 12.48 | 7.83 | 37.3% | 25.30 | 23.61 |
| ggZZ→4e | 5,000 | 3,001 | 36.74 | 22.34 | 39.2% | 56.85 | 44.80 |

CPU includes the eventLoop call and its per-file setup. Main-flow wall is
post_proc invocation through return, including its loading, preselection,
loop and merge; the test driver preloads ROOT/framework. Input downloads,
driver launch/preload and validation are excluded. Host/cache/I/O variability
prevents extrapolating these percentages to an entire campaign wall time.
The WZ reference is a warm rerun; the data reference includes the same isolated
GEN index repair. Saved values, schemas and normalization/selection metadata
agree; final optimized file sizes differ from references only by tens of bytes.

The delivered single-input finalization runs the original haddnano in the
loaded ROOT process, with explicit file closure. Direct renaming was rejected:
it grew the ggZZ fixture from about 7.8 to 13.8 MB despite equal event values.
GEN diagnostic logs now explicitly count retained events; Runs normalization
and stored truth/weights retain their original meanings.

## Storage estimate, including validation MC

Scope: frozen 2024 data C–I, both existing 2024 WZ generators, qqZZ and six
ggZZ modes, and all 11 missing 2023preBPix/2023postBPix/2024 DY/WZ/qqZZ/TT
datasets (8,250 inputs). Other existing 2024 backgrounds/signals, 26.50 GB,
are reused without widening. Both WZ variants count toward disk space;
their physical yields must not be added. This is not a complete five-era
Run3 estimate: 2022 and 2023 data inventories are absent.

Sizes use decimal GB and describe one output set, including reused outputs;
raw NanoAOD, caches and an additional merged copy are excluded.

| Additional retention; old SR/CR/views always survive | Central estimate / GB | Engineering range / GB |
|---|---:|---:|
| Old acceptance with the missing MC completed | 154.5 | 138.9–174.1 |
| Current complete FR cuts including >=2 jets, add pass | 157.7 | 140.8–178.9 |
| **Delivered default: current FR envelope, no jet-count cut** | **213.7** | **174.4–262.8** |
| Same no-jet envelope with MET<50 instead (sizing alternative only) | 272.4 | 209.6–350.8 |
| Wide basic-probe envelope | 771.0 | 508.8–1,098.7 |

Existing related directories measure 95.449 GB. Existing groups are estimated
as their measured size plus the raw-event-scaled change in compressed Events
content, with 0.1 MB/input reserved for new schema metadata. Missing MC uses
raw-event-scaled compressed Events content plus measured file-level overhead
(about 2.25–2.28 MB/input for MC). File overhead alone for the 8,250 missing
inputs is about 18.82 GB. Early prefix caches lacked raw MetaData/ParameterSets;
their total bytes/event must not be scaled directly to full production.

2023 processes use their corresponding 2024 proxies, inclusive DY uses the
ee/muon average, and ggZZ increments use the 4e proxy, especially uncertain
for tau modes. Each family has one limited input. Engineering ranges vary
the extrapolated event-content component by 0.6–1.5 while fixing existing
sizes and file overhead. They are not confidence intervals or guaranteed
bounds. In particular, zero strict pass events in the small data/TT probes
does not predict zero over a full year.

Only the default and explicit wide envelopes are implemented. The MET50 row
is a budget comparison, not an available CLI profile. Default storage keeps
full objects within the retained events; future loosening beyond the current
loose/multiplicity/MET envelope requires broader inputs.

Current quota planning must include old outputs and merge overlap separately.
With old files retained, the default would write about 187.2 GB of new files
in addition to the reused 26.5 GB already counted. Keeping both all per-file
outputs and an equally sized merged copy can nearly double that new volume.
No full production, merge or deletion was performed for these measurements.

## 2026-10-31: three-layer retention, schemaVersion 3

The comparison baseline is the already optimized `94c4ad5` default, not the
unoptimized teacher producer. The new default retains no-SIP loose, current
with-SIP loose and unchanged CR-tight masks, both three-loose FR envelopes,
and separate no-SIP four-lepton application inputs. SR and existing CR selectors
are unchanged. No-SIP construction and storage run only once on nominal inputs;
the original 13 MC selection views are retained.

Four fixed raw prefixes (140,000 events total), seed 12345, the same corrections
and LZMA:9 were rerun sequentially in CMSSW_15_0_2 / ROOT 6.32.11 /
uv-managed Python 3.9.23. Each process explicitly loads the C++ files from its
source snapshot before timing, rather than the runtime's historical checkout.

| Input | Raw prefix | Saved before → after | ROOT MB before → after | Size change | Event-loop CPU s before → after |
|---|---:|---:|---:|---:|---:|
| WZ | 5,000 | 42 → 43 | 0.408914 → 0.415147 | +1.52% | 6.075 → 6.289 |
| Data Run2024H EGamma0 | 100,000 | 23 → 48 | 0.284448 → 0.350289 | +23.15% | 11.421 → 11.084 |
| ggZZ→4e | 5,000 | 1,576 → 1,603 | 4.485035 → 4.561842 | +1.71% | 16.202 → 15.620 |
| DY→mu mu | 30,000 | 348 → 486 | 3.320708 → 3.586888 | +8.02% | 18.497 → 18.773 |

MB are decimal. These are within-input comparisons; DY includes full input
file metadata, while the other fixtures omit raw MetaData/ParameterSets.
Do not extrapolate a size multiplier across processes or use the earlier
schemaVersion 2 campaign budget for this new default.

A separate WZ storage-disabled control keeps exactly 4 events in both versions:
CPU 5.639 → 5.832 s (+3.4%), bytes 235026 → 235743. The three-layer bookkeeping
cost is small in this fixture. CPU differences for the default runs range from
about -3.6% to +3.5%; the negative differences are not evidence of a new speed
optimization. Main-flow wall times (before → after) were WZ 19.515 → 9.417 s,
data 47.475 → 18.043 s, ggZZ 28.467 → 21.737 s; cache/I/O variation makes them
unsuitable for claiming an acceleration. Full timings are retained in the
measurement JSON. Startup/C++ loading and post-run validation are outside the
reported main-flow timer.

All old events survive, and no added event passes nominal or shifted SR/CR.
Existing physical branches and ZXLoose/ZXTight masks match exactly on common
events; only the deliberately broadened passedZPlusLStorage decision is excluded
from scalar equality, with old true decisions explicitly required to remain true.
The five comparisons check 6,370,381 scalars, including identical representations
for five input NaNs. Runs, LuminosityBlocks and SelectionViews also agree.
In ggZZ the original 1,210 SR, 40 CR and five variation-only events are unchanged.

All ten completed outputs pass job-report checks. The new outputs pass ROOT
integrity/schema/mask validation, including independent reconstruction of both
loose masks from the saved object inputs. Local unit tests: 27 pass.
`tests/check_zx_layers_root.py` passes native worker tests for electron SIP=4 and
muon SIP=8 boundaries, ID versus SIP failures, dxy boundaries, repeated calls,
event reset and read-only no-SIP application retention with candidate jet cuts.

Two attempts were interrupted with an SSH/session loss before a complete
result (initial compilation smoke test and first DY-after attempt). Their
partial logs/outputs were retained and excluded from all counts and timings.
Only the unfinished DY-after and WZ-off tests were resumed, using a foreground
connection with periodic progress. No full production or PR was started.
