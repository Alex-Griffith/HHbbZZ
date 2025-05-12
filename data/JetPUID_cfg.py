#from https://github.com/latinos/LatinoAnalysis/blob/master/NanoGardener/python/data/JetPUID_cfg.py

# PUID scale factors and uncertainties (PRELIMINARY based on 2016 training only) are downloaded from
# https://lathomas.web.cern.ch/lathomas/JetMETStuff/PUIDStudies/Oct2019/
# and from
# /afs/cern.ch/work/l/lathomas/public/PileUpIDScaleFactor_PreliminaryRun2/
# see twiki https://twiki.cern.ch/twiki/bin/viewauth/CMS/PileupJetID
# following Laurent's updated talk in
# https://indico.cern.ch/event/860457/

_jet_puid_sf = {
    '2016': {'source': 'PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/data/PUID_80XTraining_EffSFandUncties.root'},
    '2017': {'source': 'PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/data/PUID_80XTraining_EffSFandUncties.root'},
    '2018': {'source': 'PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/data/PUID_80XTraining_EffSFandUncties.root'}
}

for jet, jetTag in [('real','eff'), ('pu','mistag')]:
    for wp, iwp in [('loose', 'L'), ('medium', 'M'), ('tight', 'T')]:
        for year, jcfg in _jet_puid_sf.items():
            jcfg['%s_%s' % (jet, wp)] = 'h2_%s_sf%s_%s' % (jetTag, year, iwp)
            jcfg['%s_mc_%s' % (jet, wp)] = 'h2_%s_mc%s_%s' % (jetTag, year, iwp)
            jcfg['%s_%s_uncty' % (jet, wp)] = 'h2_%s_sf%s_%s_Systuncty' % (jetTag, year, iwp)

jet_puid_sf = {}

jet_puid_sf['2016'] = _jet_puid_sf['2016']
jet_puid_sf['2017'] = _jet_puid_sf['2017']
jet_puid_sf['2018'] = _jet_puid_sf['2018']

del _jet_puid_sf
