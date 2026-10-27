#!/bin/bash

export MELA_LIB_DIR="$CMSSW_BASE/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/JHUGenMELA/MELA/data/$SCRAM_ARCH"

export PYTHONPATH="$MELA_LIB_DIR:$PYTHONPATH"
export LD_LIBRARY_PATH="$MELA_LIB_DIR:$LD_LIBRARY_PATH"

echo "MELA environment configured: $MELA_LIB_DIR"
