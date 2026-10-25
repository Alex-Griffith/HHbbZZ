#!/bin/bash
# Runs inside the cmssw/el9 container. Follows README steps 1-4 twice, once for the
# base-branch code and once for the PR code, each in its own CMSSW area.
# Mounts: /src/{base,pr} = code, /inputs = test files, /out = skim outputs.
set -eo pipefail

: "${CMSSW_RELEASE:?}" "${SCRAM_ARCH:?}"
export SCRAM_ARCH
source /cvmfs/cms.cern.ch/cmsset_default.sh

PKG=PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim
WORK=/tmp/work
mkdir -p "$WORK"

# Step 2 dependencies, cloned once so both areas use identical versions.
git clone -q https://github.com/cms-nanoAOD/nanoAOD-tools.git "$WORK/deps/NanoAODTools"
git clone -q https://github.com/cms-cat/nanoAOD-tools-modules.git "$WORK/deps/NATModules"

# NATModules includes Boost headers without declaring boost in its BuildFile, and
# MuonScaRe.cc uses cout without <iostream>; lxplus hides both with system headers,
# the container does not.
grep -q '<use name="boost"/>' "$WORK/deps/NATModules/BuildFile.xml" ||
  sed -i '1i <use name="boost"/>' "$WORK/deps/NATModules/BuildFile.xml"
grep -q '^#include <iostream>' "$WORK/deps/NATModules/src/MuonScaRe.cc" ||
  sed -i '0,/^#include/s//#include <iostream>\n#include/' "$WORK/deps/NATModules/src/MuonScaRe.cc"
# haddnano.py calls "python", which EL9 lacks; post_proc.py needs it for skimmed_nano.root.
sed -i '1s|.*|#!/usr/bin/env python3|' "$WORK/deps/NanoAODTools/scripts/haddnano.py"

mapfile -t inputs < <(find /inputs -name '*.root' | sort)
[ "${#inputs[@]}" -gt 0 ] || { echo "no .root files under /inputs"; exit 1; }

for side in base pr; do
  # Step 1: CMSSW release
  cd "$WORK"
  scram project -n "$side" CMSSW "$CMSSW_RELEASE"
  cd "$WORK/$side/src"
  eval "$(scram runtime -sh)"

  # Step 2: nanoAOD-tools and NAT modules
  mkdir -p PhysicsTools
  cp -r "$WORK/deps/NanoAODTools" PhysicsTools/NanoAODTools
  cp -r "$WORK/deps/NATModules" PhysicsTools/NATModules

  # Step 3: this repository (base or PR version), then build
  mkdir -p "$PKG"
  cp -r "/src/$side/." "$PKG/"
  scram b -j "$(nproc)"
  eval "$(scram runtime -sh)"

  # Step 4: run the skim on each test input
  mkdir -p "/out/$side"
  cd "$CMSSW_BASE/src/$PKG"
  for f in "${inputs[@]}"; do
    python3 post_proc.py -i "$f" $SKIM_ARGS
    mv skimmed_nano.root "/out/$side/$(basename "$f")"
    rm -f ./*_Skim.root
  done
done
