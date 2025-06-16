#!/bin/bash 
#
# Instructions:
# cmsenv
# wget -O ${TMPDIR}/checkout.csh https://raw.githubusercontent.com/lwang046/HHbbZZ/HZZ_Analysis_Run3/checkout.csh
# cd $CMSSW_BASE/src
# chmod u+x ${TMPDIR}/checkout.csh
# ${TMPDIR}/checkout.csh


set -e

git cms-init

git clone git@github.com:cms-nanoAOD/nanoAOD-tools.git PhysicsTools/NanoAODTools
git clone git@github.com:cms-cat/nanoAOD-tools-modules.git PhysicsTools/NATModules
cd PhysicsTools/NanoAODTools


cd $CMSSW_BASE/src
git clone --branch HHbbZZ_Analysis_Run3 https://github.com/lwang046/HHbbZZ.git PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim
cd PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim
cd -
cmsenv

#cp PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/data/btag/*.csv PhysicsTools/NanoAODTools/data/btagSF/.
scram b -j12

cd $CMSSW_BASE/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim
#MELA
git clone https://github.com/JHUGen/JHUGenMELA.git JHUGenMELA
(cd JHUGenMELA; git checkout -b from-v242 v2.4.2; ./setup.sh)

'''
#MELA Analytics
git clone https://github.com/MELALabs/MelaAnalytics.git
(cd MelaAnalytics; git checkout -b from-v23 v2.3; ./setup.sh)

#Move MELA libraries to the proper place, so that we can avoid its silly
#env settings 
mkdir -p ${CMSSW_BASE}/lib/${SCRAM_ARCH}
ln -s ${CMSSW_BASE}/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/JHUGenMELA/MELA/data/*/*.so \
      ${CMSSW_BASE}/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/MelaAnalytics/CandidateLOCaster/lib/*.so \
      ${CMSSW_BASE}/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/MelaAnalytics/GenericMEComputer/lib/*.so \
      ${CMSSW_BASE}/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/MelaAnalytics/EventContainer/lib/*.so \
      ${CMSSW_BASE}/lib/${SCRAM_ARCH}
'''





