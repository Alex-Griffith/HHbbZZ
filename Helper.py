import ROOT
import yaml

PI=3.14159
def PassTrig(event,cfgFile):
    
    
    PassTrig = False
    with open(cfgFile, 'r') as ymlfile:
        cfg = yaml.full_load(ymlfile)
        TriggerList = []
        for TriggerName in cfg['Triggers']:
            TriggerList.append(eval(TriggerName))
         
    for i in range(len(TriggerList)):
        PassTrig = PassTrig | TriggerList[i]

    return PassTrig

def goodLooseElectrons2012(electrons, elePtcut):
    goodElectrons = []
    for x in electrons:
        if ((x.pt>elePtcut) & (abs(x.eta)<2.5)):
            goodElectrons.append(x)

    return goodElectrons

def goodLooseMuons2012(muons, muPtcut):
    goodMuons = []
    for x in muons:
        if ((x.pt>muPtcut) & (abs(x.eta)<2.4) & (x.isPFcand | x.isGlobal | x.isTracker)):
            goodMuons.append(x)

    return goodMuons

def goodLooseTaus2012(Taus, TauPtcut):
    goodTaus = []
    for x in Taus:
        if ((x.pt>TauPtcut) & (abs(x.eta)<2.3)):
            goodTaus.append(x)

    return goodTaus

def goodTaus2015(Taus, TauPtcut):
    goodTaus = []
    for x in Taus:
        if ((x.pt>TauPtcut)):
            goodTaus.append(x)

    return goodTaus

def goodLoosePhotons2015(Photons):
    goodPhotons = []
    for x in Photons:
        goodPhotons.append(x)

    return goodPhotons

def goodPhotons2015(Photons,phoPtCut):
    goodPhotons = []
    for x in Photons:
        if x.pt>phoPtCut:
            goodPhotons.append(x)

    return goodPhotons

def goodMuons2015_noIso_noPf(muons, muPtcut, sip3dcut):
    bestMuons = []
    for x in muons:
        if ((x.pt>muPtcut) & (abs(x.eta)<2.4) & (x.isGlobal | x.isTracker)):
            if(x.sip3d < sip3dcut):
                if((abs(x.dxy)<0.5)&(abs(x.dz)<1)):
                    bestMuons.append(x)

    return bestMuons

def goodElectrons2015_noIso_noBdt(electrons, elePtcut, sip3dcut):
    bestElectrons = []
    for x in electrons:
        if ((x.pt>elePtcut)):
            if(x.sip3d < sip3dcut):
                if((abs(x.dxy)<0.5)&(abs(x.dz)<1)):
                    bestElectrons.append(x)

    return  bestElectrons

def passTight_BDT_Id(electrons,year = '2018'):
    Tight_Id = []
    cutVal = 1000
    mvaVal = -1
    
    for x in electrons:
        if (year == '2018'):
            if (x.pt<=10):
                if (abs(x.eta) < 0.8): cutVal = 0.9044286167
                if ((abs(x.eta) >= 0.8)&(abs(x.eta) <1.479)): cutVal = 0.9094166886
                if (abs(x.eta) >= 1.479): cutVal = 0.9443653660
            else:
                if (abs(x.eta) < 0.8): cutVal = 0.1968600840
                if ((abs(x.eta) >= 0.8)&(abs(x.eta) <1.479)): cutVal = 0.0759172100
                if (abs(x.eta) >= 1.479): cutVal = -0.5169136775

            mvaVal = x.mvaFall17V2Iso_WP90
            
        if (year == '2017'):
            if (x.pt<=10):
                if (abs(x.eta) < 0.8): cutVal = 0.9128577458
                if ((abs(x.eta) >= 0.8)&(abs(x.eta) <1.479)): cutVal = 0.9056792368
                if (abs(x.eta) >= 1.479): cutVal = 0.9439440575
            else:
                if (abs(x.eta) < 0.8): cutVal = 0.1559788054
                if ((abs(x.eta) >= 0.8)&(abs(x.eta) <1.479)): cutVal = 0.0273863727
                if (abs(x.eta) >= 1.479): cutVal = -0.5532483665
            
            mvaVal = x.mvaFall17V2Iso_WP90
        if (year == '2016'):
            if (x.pt<=10):
                if (abs(x.eta) < 0.8): cutVal = 0.9557993256
                if ((abs(x.eta) >= 0.8)&(abs(x.eta) <1.479)): cutVal = 0.9475406570
                if (abs(x.eta) >= 1.479): cutVal = 0.9285158721
            else:
                if (abs(x.eta) < 0.8): cutVal = 0.3272075608
                if ((abs(x.eta) >= 0.8)&(abs(x.eta) <1.479)): cutVal = 0.2468345995
                if (abs(x.eta) >= 1.479): cutVal = -0.5955762814
            
            mvaVal = x.mvaFall17V2Iso_WP90

        if mvaVal > cutVal:
            Tight_Id.append(True)
        else:
            Tight_Id.append(False)
    
    return Tight_Id

def passTight_Id(muons):
    Tight_Id = []
    for x in muons:
        if (x.pt<200):
            Tight_Id.append(x.isPFcand)
        else:
            Tight_Id.append(((x.ptErr/x.pt)<0.3)&(abs(x.dxy)<0.2)&(abs(x.dz)<0.5)&(x.nTrackerLayers>5)|x.isPFcand)

    return Tight_Id
