#!/bin/bash 
#
# Instructions:
# cmsenv
# wget -O ${TMPDIR}/checkout.csh https://raw.githubusercontent.com/lwang046/HHbbZZ/HHbbZZ_Analysis_Run3/checkout.csh
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
scram b -j12
