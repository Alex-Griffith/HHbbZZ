<<<<<<< HEAD
#!/usr/bin/env python
import os,sys

from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from wvAnalysisModule import *
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 import *
from PhysicsTools.NanoAODTools.postprocessing.modules.btv.btagSFProducer import *
from JetSFMaker import *

testfile = "root://cms-xrd-global.cern.ch//store/data/Run2018A/SingleMuon/NANOAOD/Nano25Oct2019-v1/20000/D03C6AE0-73AD-A940-B8CA-779A621D4853.root"


entriesToRun = 0  # 0 if need to run over all entries else put number of entries to run
isMCTrueFalse = True
Year = 2016
# Keep DownloadFileToLocalThenRun=True this should reduce the file read error from eos.
DownloadFileToLocalThenRun=True

if testfile.find("SingleMuon") != -1 or testfile.find("EGamma") != -1 or testfile.find("SingleElectron") != -1 or testfile.find("DoubleMuon") != -1 or testfile.find("MuonEG") != -1 or testfile.find("DoubleEG") != -1:
  isMCTrueFalse=False
  if testfile.find("Run2016") != -1:
    Year=2016
    jsonFileName="Cert_271036-284044_13TeV_ReReco_07Aug2017_Collisions16_JSON.txt"
  if testfile.find("Run2017") != -1:
    Year=2017
    jsonFileName="Cert_294927-306462_13TeV_EOY2017ReReco_Collisions17_JSON.txt"
  if testfile.find("Run2018") != -1:
    Year=2018
    jsonFileName="Cert_314472-325175_13TeV_17SeptEarlyReReco2018ABC_PromptEraD_Collisions18_JSON.txt"
  print "\n===> Running over ",Year," data...\n"
  print "===> JSON File: ",jsonFileName
  jetmetCorrector = createJMECorrector(isMC=isMCTrueFalse, dataYear=Year, jesUncert="Merged", jetType = "AK4PFchs")
  fatJetCorrector = createJMECorrector(isMC=isMCTrueFalse, dataYear=Year, jesUncert="Merged", jetType = "AK8PFPuppi")
  p=PostProcessor(".",[testfile],None,None,[wvAnalysisModule(),jetmetCorrector(),fatJetCorrector()],provenance=False,fwkJobReport=False,jsonInput=jsonFileName,maxEntries=entriesToRun,haddFileName="nano.root",prefetch=DownloadFileToLocalThenRun)
else:
  print "==> Processing a MC file..."
  isMCTrueFalse=True
  if testfile.find("RunIIAutumn18NanoAODv") != -1: year = 2018
  if testfile.find("VVjj_2018v") != -1: year = 2018
  if testfile.find("RunIIFall17NanoAODv") != -1: year = 2017
  if testfile.find("VVjj_2017v") != -1: year = 2017
  if testfile.find("RunIISummer16NanoAODv") != -1: year = 2016
  if testfile.find("VVjj_2016v") != -1: year = 2016
  jetmetCorrector = createJMECorrector(isMC=isMCTrueFalse, dataYear=year, jesUncert="Merged", jetType = "AK4PFchs")
  fatJetCorrector = createJMECorrector(isMC=isMCTrueFalse, dataYear=year, jesUncert="Merged", jetType = "AK8PFPuppi")
  if year == 2016:
    era="Legacy2016"
    sfFileName="DeepCSV_2016LegacySF_V1.csv"
  if year == 2017:
    era="2017"
    sfFileName="DeepCSV_94XSF_V5_B_F.csv"
  if year == 2018:
    era="2018"
    sfFileName="DeepCSV_102XSF_V2.csv"
  btagSF = lambda: btagSFProducer(era,algo="deepcsv",selectedWPs=['L','M','T','shape_corr'],sfFileName=sfFileName)
  puidSF = lambda: JetSFMaker("%s" % year)
  p=PostProcessor(".",[testfile],"",None,[wvAnalysisModule(),jetmetCorrector(),fatJetCorrector(),btagSF(),puidSF()],provenance=True,fwkJobReport=False,maxEntries=entriesToRun,haddFileName="nano.root",prefetch=DownloadFileToLocalThenRun)

p.run()
print "DONE"
#os.system("ls -lR")
=======
#!/usr/bin/env python3
import os
import sys
import argparse

from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor
from PhysicsTools.NanoAODTools.postprocessing.modules.common.muonScaleResProducer import *
from PhysicsTools.NanoAODTools.postprocessing.modules.jme.jetmetHelperRun2 import createJMECorrector
from PhysicsTools.NanoAODTools.postprocessing.modules.btv.btagSFProducer import btagSFProducer
from PhysicsTools.NanoAODTools.postprocessing.modules.common.puWeightProducer import *

# Custom module imports
from H4Lmodule import *
from H4LCppModule import *
from JetSFMaker import *

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputFile", default="", type=str, help="Input file name")
    parser.add_argument("-n", "--entriesToRun", default=100, type=int, help="Set  to 0 if need to run over all entries else put number of entries to run")
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
    print(("DEBUG: Input file list: {}".format(testfilelist)))
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
        cfgFile = "Input_2022.yml"
        jsonFileName = "golden_Json/Cert_Collisions2022_355100_362760_Golden.json"
        sfFileName = "DeepCSV_102XSF_V2.csv" # FIXME: Update for year 2022
        #modulesToRun.extend([lambda: muonScaleResProducer('','', 2022)]) # FIXME: Update for year 2022
    if "UL18" in first_file or "UL2018" in first_file:
        """UL2018 for identification of 2018 UL data and UL18 for identification of 2018 UL MC
        """
        year = 2018
        cfgFile = "Input_2018.yml"
        jsonFileName = "golden_Json/Cert_314472-325175_13TeV_Legacy2018_Collisions18_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        modulesToRun.extend([muonScaleRes2018()])
    if "UL17" in first_file or "UL2017" in first_file:
        year = 2017
        cfgFile = "Input_2017.yml"
        jsonFileName="golden_Json/Cert_294927-306462_13TeV_UL2017_Collisions17_GoldenJSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        modulesToRun.extend([muonScaleRes2017()])
    if "UL16" in first_file or "UL2016" in first_file:
        year = 2016
        jsonFileName = "golden_Json/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
        sfFileName = "DeepCSV_102XSF_V2.csv"
        modulesToRun.extend([muonScaleRes2016()])

    H4LCppModule = lambda: HZZAnalysisCppProducer(year,cfgFile, isMC, isFSR)
    modulesToRun.extend([H4LCppModule()])

    print(("Input json file: {}".format(jsonFileName)))
    print(("Input cfg file: {}".format(cfgFile)))
    print(("isMC: {}".format(isMC)))
    print(("isFSR: {}".format(isFSR)))

    if isMC:
        if (not args.NOsyst):
            # FIXME: JES not used properly
            #jetmetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK4PFchs")
            #fatJetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK8PFPuppi")
            # btagSF = lambda: btagSFProducer("UL"+str(year), algo="deepjet",selectedWPs=['L','M','T','shape_corr'], sfFileName=sfFileName)
            btagSF = lambda: btagSFProducer(era = "UL"+str(year), algo = "deepcsv")
            puidSF = lambda: JetSFMaker("%s" % year)
            #modulesToRun.extend([jetmetCorrector(), fatJetCorrector()])#, puidSF()
            # # modulesToRun.extend([jetmetCorrector(), fatJetCorrector(), btagSF(), puidSF()])

        # FIXME: No PU weight for 2022
        if year == 2018: modulesToRun.extend([puAutoWeight_2018()])
        if year == 2017: modulesToRun.extend([puAutoWeight_2017()])
        if year == 2016: modulesToRun.extend([puAutoWeight_2016()])

        # INFO: Keep the `fwkJobReport=False` to trigger `haddnano.py`
        #            otherwise the output file will have larger size then expected. Reference: https://github.com/cms-nanoAOD/nanoAOD-tools/issues/249
        p=PostProcessor(".",testfilelist, None, None,modules = modulesToRun, provenance=True,fwkJobReport=True,haddFileName="skimmed_nano.root", maxEntries=entriesToRun, prefetch=DownloadFileToLocalThenRun, outputbranchsel="keep_and_drop.txt")
    else:
        #if (not args.NOsyst):
            # FIXME: JES not used properly
            #jetmetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK4PFchs")
            #fatJetCorrector = createJMECorrector(isMC=isMC, dataYear=year, jesUncert="All", jetType = "AK8PFPuppi")
            #modulesToRun.extend([jetmetCorrector(), fatJetCorrector()])

        p=PostProcessor(".",testfilelist, None, None, modules = modulesToRun, provenance=True, fwkJobReport=True,haddFileName="skimmed_nano.root", jsonInput=jsonFileName, maxEntries=entriesToRun, prefetch=DownloadFileToLocalThenRun, outputbranchsel="keep_and_drop_data.txt")

    p.run()


if __name__ == "__main__":
    main()
>>>>>>> parent of ab45a38 (JERJEC and 2023)
