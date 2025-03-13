#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import tempfile

from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.modules.common.muonScaleResProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 import createJMECorrector
from PhysicsTools.NanoAODTools.postprocessing.modules.btv.btagSFProducer import btagSFProducer
from PhysicsTools.NanoAODTools.postprocessing.modules.common.puWeightProducer import *

# Custom module imports
from modules.H4LCppModule import *
from modules.JetSFMaker import *
from modules.GenVarsProducer import *
from modules.keep_and_drop_list import keep_drop_rules_Data_MC, keep_drop_rules_GEN

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputFile", default="", type=str, help="Input file name")
    parser.add_argument('-o', '--outputFile', default="skimmed_nano.root", type=str, help="Output file name")
    parser.add_argument('-outDir', '--outputDir', default=".", type=str, help="Output directory")
    parser.add_argument('-c', '--cutFlowFile', default="cutFlow.json", type=str, help="Cut flow file name")
    parser.add_argument("-n", "--entriesToRun", default=100, type=int, help="Set  to 0 if need to run over all entries else put number of entries to run")
    parser.add_argument("-d", "--DownloadFileToLocalThenRun", default=True, type=bool, help="Download file to local then run")
    parser.add_argument("--WithSyst", default=False, action="store_true", help="Do not run systematics")
    parser.add_argument("--DEBUG", default=False, action="store_true", help="Print debug information")
    parser.add_argument("--channels",  choices=["all", "4l", "2l2q", "2l2v"],  default="2l2v",
                        help="Channels to run: all, 4l, 2l2q, or 2l2v")
    return parser.parse_args()

def getListFromFile(filename):
    """Read file list from a text file."""
    with open(filename, "r") as file:
        return ["root://cms-xrd-global.cern.ch/" + line.strip() for line in file]

def create_temp_keep_drop_file(rules):
    """Create a temporary keep and drop file from a list of rules."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
    temp_file.write("\n".join(rules))
    temp_file.close()
    return temp_file.name

def main():
    args = parse_arguments()

    # Initial setup
    testfilelist = []
    modulesToRun = []
    isMC = True
    isFSR = True
    isFiducialAna = True
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
    print("DEBUG: Input file list: {}".format(testfilelist))
    if len(testfilelist) == 0:
        print("ERROR: No input files found. Exiting.")
        exit(1)

    """Determine the year and type (MC or Data) of input ROOT file:
    For data the string "/data/" is always there. So, we take this
    as handle to decide if the root file is MC or data.
    """
    first_file = testfilelist[0]
    isMC = "/data/" not in first_file

    if "Summer22" in first_file or "Run2022" in first_file:
        """Summer22 and Run2022 for identification of 2022 MC and data respectiverly
        """
        year = 2022
        cfgFile = "config/Input_2022.yml"
        jsonFileName = "data/golden_json/Cert_Collisions2022_355100_362760_Golden.json"
        sfFileName = "DeepCSV_102XSF_V2.csv" # FIXME: Update for year 2022
        modulesToRun.extend([muonScaleRes2022()]) # FIXME: Update for year 2022
    if "UL18" in first_file or "UL2018" in first_file:
        """UL2018 for identification of 2018 UL data and UL18 for identification of 2018 UL MC
        """
        year = 2018
        cfgFile = "config/Input_2018.yml"
        jsonFileName = "data/golden_json/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        modulesToRun.extend([muonScaleRes2018()])
    if "UL17" in first_file or "UL2017" in first_file:
        year = 2017
        cfgFile = "config/Input_2017.yml"
        jsonFileName="data/golden_json/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        modulesToRun.extend([muonScaleRes2017()])
    if "UL16" in first_file or "UL2016" in first_file:
        year = 2016
        cfgFile = "config/Input_2016.yml"
        jsonFileName = "data/golden_json/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        modulesToRun.extend([muonScaleRes2016()])

    H4LCppModule = lambda: HZZAnalysisCppProducer(year=year, cfgFile=cfgFile,
                                                  isMC=isMC, isFSR=isFSR,
                                                  cutFlowJSONFile=args.cutFlowFile,
                                                  channels=args.channels,
                                                  DEBUG=args.DEBUG
                                                  )
    print("systematic info: {}".format(args.WithSyst))
    print("Input json file: {}".format(jsonFileName))
    print("Input cfg file: {}".format(cfgFile))
    print("isMC: {}".format(isMC))
    print("isFSR: {}".format(isFSR))

    if isMC:
        GenVarModule = lambda : GenVarsProducer() # FIXME: Gen variable producer module is not working
        modulesToRun.extend([H4LCppModule(), GenVarModule()])
        if (args.WithSyst):
            jetmetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK4PFchs")
            fatJetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK8PFPuppi")
            # btagSF = lambda: btagSFProducer("UL"+str(year), algo="deepjet",selectedWPs=['L','M','T','shape_corr'], sfFileName=sfFileName)
            # btagSF = lambda: btagSFProducer(era = "UL"+str(year), algo = "deepcsv")
            puidSF = lambda: JetSFMaker("%s" % year)
            modulesToRun.extend([jetmetCorrector(), fatJetCorrector(), puidSF()])
            # modulesToRun.extend([jetmetCorrector(), fatJetCorrector(), btagSF(), puidSF()])

        # FIXME: No PU weight for 2022
        if year == 2018: modulesToRun.extend([puAutoWeight_2018()])
        if year == 2017: modulesToRun.extend([puAutoWeight_2017()])
        if year == 2016: modulesToRun.extend([puAutoWeight_2016()])

        # INFO: Keep the `fwkJobReport=False` to trigger `haddnano.py`
        #            otherwise the output file will have larger size then expected. Reference: https://github.com/cms-nanoAOD/nanoAOD-tools/issues/249
        temp_keep_drop_file = create_temp_keep_drop_file(keep_drop_rules_GEN + keep_drop_rules_Data_MC)
        print("DEBUG: Keep and drop file: {}".format(temp_keep_drop_file))
        p=PostProcessor(args.outputDir,testfilelist, None, None,modules = modulesToRun,
                        provenance=True,fwkJobReport=True,
                        haddFileName=args.outputFile,
                        maxEntries=entriesToRun,
                        prefetch=DownloadFileToLocalThenRun, longTermCache= True,   # prefetch: download file to local then run, longTermCache: keep the file in local after running so that if it is present use local instead of downloading again
                        outputbranchsel=temp_keep_drop_file)
    else:
        modulesToRun.extend([H4LCppModule()])
        if (args.WithSyst):
            jetmetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK4PFchs")
            fatJetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK8PFPuppi")
            modulesToRun.extend([jetmetCorrector(), fatJetCorrector()])

        temp_keep_drop_file = create_temp_keep_drop_file(keep_drop_rules_Data_MC)
        print("DEBUG: Keep and drop file: {}".format(temp_keep_drop_file))
        p=PostProcessor(args.outputDir,testfilelist, None, None, modules = modulesToRun,
                        provenance=True, fwkJobReport=True,
                        haddFileName=args.outputFile,
                        jsonInput=jsonFileName,
                        maxEntries=entriesToRun,
                        prefetch=DownloadFileToLocalThenRun,  longTermCache= True,   # prefetch: download file to local then run, longTermCache: keep the file in local after running so that if it is present use local instead of downloading again
                        outputbranchsel=temp_keep_drop_file)

    p.run()

if __name__ == "__main__":
    main()
