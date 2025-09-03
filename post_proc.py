#!/usr/bin/env python3
import os
import sys
import argparse

from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.modules.common.muonScaleResProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 import createJMECorrector
from PhysicsTools.NanoAODTools.postprocessing.modules.btv.btagSFProducer import btagSFProducer
from PhysicsTools.NanoAODTools.postprocessing.modules.common.puWeightProducer import *

from jetCorr import jetJERC
from H4Lmodule import *
from H4LCppModule import *
from JetSFMaker import *

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputFile", default="", type=str, help="Input file name")
    parser.add_argument("-n", "--entriesToRun", default=100, type=int, help="Set to 0 to run over all entries")
    parser.add_argument("-d", "--DownloadFileToLocalThenRun", default=True, type=bool, help="Download file to local then run")
    parser.add_argument("--NOsyst", default=False, action="store_true", help="Do not run systematics")
    return parser.parse_args()


def getListFromFile(filename):
    """Read file list from a text file."""
    with open(filename, "r") as file:
        return ["root://cms-xrd-global.cern.ch/" + line.strip() for line in file]


def main():
    args = parse_arguments()

    # Initial setup
    testfilelist = []
    modulesToRun = []
    isMC = True
    isFSR = False
    year = None
    cfgFile = None
    jsonFileName = None
    sfFileName = None

    entriesToRun = int(args.entriesToRun)
    DownloadFileToLocalThenRun = args.DownloadFileToLocalThenRun

    # Determine list of files to process
    if args.inputFile.endswith(".txt"):
        testfilelist = getListFromFile(args.inputFile)
    elif args.inputFile.endswith(".root"):
        testfilelist.append(args.inputFile)
    else:
        print("INFO: No input file specified. Using default file list.")
        testfilelist = getListFromFile("ExampleInputFileList.txt")
    
    if len(testfilelist) == 0:
        print("ERROR: No input files found. Exiting.")
        exit(1)

    # Determine the year and type (MC or Data) of input ROOT file
    first_file = testfilelist[0]
    isMC = "/data/" not in first_file

    jetCorr_module = None

    # --- Year-specific configurations ---
    
    # --- 2022/2022EE UL Data and MC (Corrected Logic) ---
    if "Summer22" in first_file or "Run2022" in first_file:
        year = 2022
        cfgFile = "Input_2022.yml"
        jsonFileName = "golden_Json/Cert_Collisions2022_355100_362760_Golden.json"
        
        if "Summer22EE" in first_file or any(run in first_file for run in ["Run2022E", "Run2022F", "Run2022G"]):
            pu_json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/LUM/2022_Summer22EE/puWeights.json.gz"
            pu_corr_name = "Collisions2022_359022_362760_eraEFG_GoldenJson"
        else: # For pre-EE (Runs B, C, D)
            pu_json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/LUM/2022_Summer22/puWeights.json.gz"
            pu_corr_name = "Collisions2022_355100_357900_eraBCD_GoldenJson"

        # Determine MC campaign (pre- or post-EE)
        if "Summer22EE" in first_file:
            era_tag = "Summer22EE_22Sep2023"
            jer_tag = "Summer22EE_22Sep2023_JR"
            json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2022_Summer22EE/"
        else: # pre-EE (Summer22)
            era_tag = "Summer22_22Sep2023"
            jer_tag = "Summer22_22Sep2023_JR"
            json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2022_Summer22/"

        # Both JEC and JER smearing info are in the same file for Run3
        jec_json = json_path + "jet_jerc.json.gz"
        jer_json = json_path + "jet_jerc.json.gz"
        
        if isMC:
            # FINAL CORRECTION: The key construction for JER was missing an underscore.
            # Using .replace("_JR", "_JRV1") to preserve the underscore.
            # This was the true root cause of the "map::at" error.
            
            # Construct the correct JER tag, e.g., "Summer22EE_22Sep2023_JRV1"
            correct_jer_tag = jer_tag.replace("_JR", "_JRV1")

            jetCorr_module = jetJERC(
                # ======================= BUG FIX START =======================
                # REMOVED the incorrect 'is_mc=isMC,' argument.
                # The jetCorr module correctly infers the MC mode from the presence
                # of a valid 'smearKey'.
                # ======================= BUG FIX END =========================
                json_JERC=jec_json, json_JERsmear=jer_json,
                L1Key=f"{era_tag}_V2_MC_L1FastJet_AK4PFPuppi",
                L2Key=f"{era_tag}_V2_MC_L2Relative_AK4PFPuppi",
                L3Key=f"{era_tag}_V2_MC_L3Absolute_AK4PFPuppi",
                L2L3Key=f"{era_tag}_V2_MC_L2L3Residual_AK4PFPuppi",
                scaleTotalKey=f"{era_tag}_V2_MC_Total_AK4PFPuppi",
                JERKey=f"{correct_jer_tag}_MC_PtResolution_AK4PFPuppi",
                JERsfKey=f"{correct_jer_tag}_MC_ScaleFactor_AK4PFPuppi",
                # ======================= FINAL, CORRECT FIX START =======================
                # The correct key for smearing in Run3 JSONs is the generic name "JERSmear".
                # It does not depend on the era tag. This will resolve the map::at error
                # while correctly enabling smearing.
                smearKey="JERSmear",
                overwritePt=True
            )
        else: # Data
            run_period = ""
            if "Run2022C" in first_file or "Run2022D" in first_file:
                run_period = "RunCD"
                era_tag = "Summer22_22Sep2023" # pre-EE era
            elif "Run2022E" in first_file:
                run_period = "RunE"
                era_tag = "Summer22EE_22Sep2023" # post-EE era
            elif "Run2022F" in first_file:
                run_period = "RunF"
                era_tag = "Summer22EE_22Sep2023" # post-EE era
            elif "Run2022G" in first_file:
                run_period = "RunG"
                era_tag = "Summer22EE_22Sep2023" # post-EE era
            
            if not run_period:
                raise ValueError("Could not determine run period (e.g., RunCD, RunE) for 2022 data.")

            # CORRECTED: Changed V3 to V2 to match JSON summary
            data_era_tag = f"{era_tag}_{run_period}_V2_DATA"
            jetCorr_module = jetJERC(
                json_JERC=jec_json, json_JERsmear=jer_json,
                L1Key=f"{data_era_tag}_L1FastJet_AK4PFPuppi", L2Key=f"{data_era_tag}_L2Relative_AK4PFPuppi",
                L3Key=f"{data_era_tag}_L3Absolute_AK4PFPuppi", L2L3Key=f"{data_era_tag}_L2L3Residual_AK4PFPuppi",
                smearKey=None, overwritePt=True
            )

    # --- 2023 Data and MC (FINAL CORRECTION) ---
    elif "Summer23" in first_file or "Run2023" in first_file:
        year = 2023
        cfgFile = "Input_2023.yml"
        jsonFileName = "golden_Json/Cert_Collisions2023_366442_370790_Golden.json"
        
        # CORRECTED: Determine PU path and name based on era (BPix vs non-BPix)
        if "BPix" in first_file or any(run in first_file for run in ["Run2023C", "Run2023D"]):
            # This block covers all BPix MC and Data (Runs C & D)
            pu_json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/LUM/2023_Summer23BPix/puWeights.json.gz"
            pu_corr_name = "Collisions2023_369803_370790_eraD_GoldenJson" # The one and only key in this file
        else: # For Summer23 non-BPix (RunB)
            pu_json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/LUM/2023_Summer23/puWeights.json.gz"
            pu_corr_name = "Collisions2023_366403_369802_eraBC_GoldenJson" # The one and only key in this file

        # Determine the correct JEC/JER JSON path and base era tag
        if "BPix" in first_file or "Run2023C" in first_file or "Run2023D" in first_file:
            json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2023_Summer23BPix/"
            base_era_name = "Summer23BPixPrompt23"
        else: # For Summer23 non-BPix (RunB)
            json_path = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2023_Summer23/"
            base_era_name = "Summer23Prompt23"

        # Both JEC and JER smearing info are in the same file for Run3
        jec_json = json_path + "jet_jerc.json.gz"
        jer_json = json_path + "jet_jerc.json.gz"

        if isMC:
            # CORRECTED: Define separate tags for JEC and JER as they have different naming schemes in the file.
            # JEC tag, as confirmed by your json_keys file
            jec_mc_tag = f"{base_era_name}_V3_MC"
            # JER tag, as confirmed by your json_keys file
            jer_mc_tag = f"{base_era_name}_RunD_JRV1_MC"
            
            jetCorr_module = jetJERC(
                json_JERC=jec_json, json_JERsmear=jer_json,
                # --- JEC Keys ---
                L1Key=f"{jec_mc_tag}_L1FastJet_AK4PFPuppi",
                L2Key=f"{jec_mc_tag}_L2Relative_AK4PFPuppi",
                L3Key=f"{jec_mc_tag}_L3Absolute_AK4PFPuppi",
                L2L3Key=f"{jec_mc_tag}_L2L3Residual_AK4PFPuppi",
                scaleTotalKey=f"{jec_mc_tag}_Regrouped_Total_AK4PFPuppi",
                
                # --- JER Keys (using the correct, different tag) ---
                JERKey=f"{jer_mc_tag}_PtResolution_AK4PFPuppi",
                JERsfKey=f"{jer_mc_tag}_ScaleFactor_AK4PFPuppi",
                
                # --- Smear Key (generic) ---
                smearKey="JERSmear",
                overwritePt=True
            )
        else: # For Data
            run_period = ""
            if "Run2023D" in first_file: run_period = "RunD"
            elif "Run2023C" in first_file: run_period = "RunCv4" # From previous screenshot
            elif "Run2023B" in first_file: run_period = "RunB"
            
            if not run_period:
                raise ValueError("Could not determine run period (e.g., RunB, RunCv4, RunD) for 2023 data.")

            # NOTE: Data versions might be different (e.g., V2). Confirm with data json keys if needed.
            # Assuming V2 for data based on common practice.
            data_era_tag = f"{base_era_name}_{run_period}_V2_DATA"
            jetCorr_module = jetJERC(
                json_JERC=jec_json, json_JERsmear=jer_json,
                L1Key=f"{data_era_tag}_L1FastJet_AK4PFPuppi",
                L2Key=f"{data_era_tag}_L2Relative_AK4PFPuppi",
                L3Key=f"{data_era_tag}_L3Absolute_AK4PFPuppi",
                L2L3Key=f"{data_era_tag}_L2L3Residual_AK4PFPuppi",
                smearKey=None, # No smearing for data
                overwritePt=True
            )

    # --- 2018 UL Data and MC (Old Logic Restored) ---
    elif "Autumn18" in first_file or "Run2018" in first_file:
        year = 2018
        cfgFile = "Input_2018.yml"
        jsonFileName = "golden_Json/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        if not args.NOsyst:
            jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2018", jesUncert="All", jetType="AK4PFchs")
            modulesToRun.extend([jetmetCorrector()])

    # --- 2017 UL Data and MC (Old Logic Restored) ---
    elif "Fall17" in first_file or "Run2017" in first_file:
        year = 2017
        cfgFile = "Input_2017.yml"
        jsonFileName = "golden_Json/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt"
        sfFileName = "DeepCSV_94XSF_V2.csv"
        if not args.NOsyst:
            jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2017", jesUncert="All", jetType="AK4PFchs")
            modulesToRun.extend([jetmetCorrector()])

    # --- 2016 UL Data and MC (Old Logic Restored) ---
    elif "Summer16" in first_file or "Run2016" in first_file:
        year = 2016
        cfgFile = "Input_2016.yml"
        jsonFileName = "golden_Json/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        sfFileName = "DeepCSV_2016LegacySF_V1.csv"
        if not args.NOsyst:
            jetmetCorrector = createJMECorrector(isMC=isMC, dataYear="UL2016", jesUncert="All", jetType="AK4PFchs")
            modulesToRun.extend([jetmetCorrector()])

    # Add the configured jet corrector module (if it exists) to the front of the list
    if jetCorr_module:
        modulesToRun.insert(0, jetCorr_module)

    # --- Add other modules ---
    # MODIFIED: Pass the PU info to the HZZAnalysisCppProducer constructor
    if year >= 2022:
        modulesToRun.append(HZZAnalysisCppProducer(year, cfgFile, isMC, isFSR, pu_json=pu_json_path, pu_name=pu_corr_name))
    else: # For Run 2, use the old constructor
        modulesToRun.append(HZZAnalysisCppProducer(year, cfgFile, isMC, isFSR))

    print(("Input json file: {}".format(jsonFileName)))
    print(("Input cfg file: {}".format(cfgFile)))
    print(("isMC: {}".format(isMC)))
    print(("isFSR: {}".format(isFSR)))

    if isMC:
        if year == 2018: modulesToRun.extend([puAutoWeight_2018()])
        if year == 2017: modulesToRun.extend([puAutoWeight_2017()])
        if year == 2016: modulesToRun.extend([puAutoWeight_2016()])
        # Note: PU weights for 2022/23 might need a different module
        
        p = PostProcessor(".", testfilelist, None, None, modules=modulesToRun, provenance=True, fwkJobReport=True, haddFileName="skimmed_nano.root", maxEntries=entriesToRun, prefetch=DownloadFileToLocalThenRun, outputbranchsel="keep_and_drop.txt")
    else: # Data
        p = PostProcessor(".", testfilelist, None, None, modules=modulesToRun, provenance=True, fwkJobReport=True, haddFileName="skimmed_nano.root", jsonInput=jsonFileName, maxEntries=entriesToRun, prefetch=DownloadFileToLocalThenRun, outputbranchsel="keep_and_drop_data.txt")

    p.run()


if __name__ == "__main__":
    main()
