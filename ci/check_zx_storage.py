"""Validate persisted storage inputs and the union independently of SR/CR.

Usage: uv run --managed-python --python 3.9 python ci/check_zx_storage.py skim.root
Run inside the pinned CMSSW runtime. No event is accepted merely by Events membership.
"""
import argparse
import collections
import json


def validate(path):
    import ROOT
    file = ROOT.TFile.Open(path)
    if not file or file.IsZombie() or file.TestBit(ROOT.TFile.kRecovered):
        raise RuntimeError("Invalid ROOT file: " + path)
    tree = file.Get("Events")
    metadata = file.Get("ZXStorageConfig")
    if not tree or not metadata:
        raise RuntimeError("Missing Events/ZXStorageConfig")
    configs = [json.loads(str(row.configJSON)) for row in metadata]
    enabled = {row['enabled'] for row in configs}
    profiles = {row.get('profile', 'wide') for row in configs}
    if len(enabled) != 1 or len(profiles) != 1:
        raise RuntimeError("Mixed storage modes in one output")
    names = {branch.GetName() for branch in tree.GetListOfBranches()}
    expected = {'passedZPlusLStorage', 'nElectron', 'nMuon', 'nJet',
                'Sel_isSR', 'Sel_isZXCR', 'Sel_goodJetIdx', 'nFsrPhoton',
                'FsrPhoton_pt', 'FsrPhoton_eta', 'FsrPhoton_phi',
                'FsrPhoton_relIso03', 'FsrPhoton_dROverEt2',
                'Muon_pfRelIso03FsrCorr'}
    for collection in ('Electron', 'Muon'):
        expected.update(collection + suffix for suffix in
                        ('_ZXLoose', '_ZXTight', '_pt', '_eta', '_phi',
                         '_sip3d', '_dxy', '_dz', '_fsrPhotonIdxAnalysis'))
    for config in configs:
        expected.update(config['inputBranches'])
        expected.update(config.get('objectBranches', []))
        if config['isMC']:
            expected.update(('nGenPart', 'GenPart_pdgId', 'GenPart_statusFlags',
                             'GenPart_genPartIdxMother', 'Electron_genPartIdx',
                             'Muon_genPartIdx', 'genWeight'))
    if expected - names:
        raise RuntimeError("Dropped storage inputs: " + str(sorted(expected - names)))
    counts = collections.Counter()
    for event in tree:
        sr, cr = bool(event.passedFullSelection), bool(event.isZXCR)
        stored = bool(event.passedZPlusLStorage)
        shifted = any(event.Sel_isSR) or any(event.Sel_isZXCR)
        if sr and cr or not (shifted or stored):
            raise RuntimeError("Invalid SR/CR/storage union")
        if bool(event.Sel_isSR[0]) != sr or bool(event.Sel_isZXCR[0]) != cr:
            raise RuntimeError("Nominal view disagrees with legacy flags")
        if stored and not next(iter(enabled)):
            raise RuntimeError("Storage event with feature disabled")
        for collection in ('Electron', 'Muon'):
            size = int(getattr(event, 'n' + collection))
            loose = list(getattr(event, collection + '_ZXLoose'))
            tight = list(getattr(event, collection + '_ZXTight'))
            if len(loose) != size or len(tight) != size or any(t and not l for l, t in zip(loose, tight)):
                raise RuntimeError("Invalid original-collection ZX masks")
        if len(event.Jet_pt) != event.nJet:
            raise RuntimeError("Incomplete Jet collection")
        if not configs[0]['isMC'] and list(event.GENlep_Hindex) != [-1] * 4:
            raise RuntimeError("Data GENlep_Hindex must contain four explicit unavailable indices")
        counts['events'] += 1
        counts['SR' if sr else 'CR' if cr else 'VariationOnly' if shifted else 'StorageOnly'] += 1
        counts['storage'] += int(stored)
        if stored:
            loose_count = sum(event.Electron_ZXLoose) + sum(event.Muon_ZXLoose)
            tight_count = sum(event.Electron_ZXTight) + sum(event.Muon_ZXTight)
            if next(iter(profiles)) == 'fr' and (loose_count != 3 or
                                                not 0 <= event.PuppiMET_pt < 25):
                raise RuntimeError("Event outside the configured FR storage envelope")
            if loose_count == 3:
                counts['stored_3loose_pass' if tight_count == 3 else 'stored_3loose_fail'] += 1
            counts['stored_raw_jets_0or1'] += int(event.nJet < 2)
    result = dict(counts=counts, storage_enabled=next(iter(enabled)),
                  storage_profile=next(iter(profiles)),
                  branch_count=len(names), input_metadata_rows=len(configs))
    file.Close()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()
    print(json.dumps(validate(args.path), sort_keys=True))
