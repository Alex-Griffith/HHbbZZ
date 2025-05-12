"""From the root file having cut-flow histogram, print the cut-flow table."""

import ROOT

# Set ROOT to run in batch mode
ROOT.gROOT.SetBatch(True)

def print_bins_noSort(hist):
    xaxis = hist.GetXaxis()
    for i in range(1, hist.GetNbinsX() + 1):
        bin_content = hist.GetBinContent(i)
        bin_label = xaxis.GetBinLabel(i)
        print(("Bin {:33}: {:.2f}".format(bin_label, bin_content)))

def print_bins(hist):
    xaxis = hist.GetXaxis()
    bins_info = []

    for i in range(1, hist.GetNbinsX() + 1):
        bin_content = hist.GetBinContent(i)
        bin_label = xaxis.GetBinLabel(i)
        bins_info.append((bin_label, bin_content))

    # Sort the bins_info list based on bin content
    sorted_bins = sorted(bins_info, key=lambda x: x[1], reverse=True)

    prev_bin_content = None
    print(("Bin {:33}: {:15}  {}%".format("Cut string name", "nEvents left", "change")))
    for bin_label, bin_content in sorted_bins:
        if prev_bin_content is not None:
            percentage_change = ((bin_content - prev_bin_content) / prev_bin_content) * 100
            print(("Bin {:33}: {:>15.2f}  {:>10.2f}%".format(bin_label, bin_content, percentage_change)))
        else:
            print(("Bin {:33}: {:>15.2f}".format(bin_label, bin_content)))
        prev_bin_content = bin_content

    print("\n\n")
    print(("| {:<33} | {:>10} | {:>6} |".format("Cut string name", "left nEvents", "Change (%)")))
    print(("|{}|{}|{}|".format("-" * 35, "-" * 12, "-" * 9)))
    for bin_label, bin_content in sorted_bins:
        if prev_bin_content is not None:
            percentage_change = ((bin_content - prev_bin_content) / prev_bin_content) * 100
            print(("| {:<33} | {:>10.2f} | {:>6.2f} |".format(bin_label, bin_content, percentage_change)))
        else:
            print(("| {:<33} | {:>10.2f} | {:>6} |".format(bin_label, bin_content, "-")))
        prev_bin_content = bin_content


def print_histogram(hist):
    print(("Histogram Name: {}".format(hist.GetName())))
    print(("Entries: {}, Total Sum: {:.6e}".format(hist.GetEntries(), hist.GetSumOfWeights())))

    print("Bin Contents:")
    print_bins(hist)

def print_cutflow_histogram():
    file = ROOT.TFile("/eos/user/g/guoj/Sample/2L2Q/UL_Legacy/2018/GluGluHToZZTo2L2Q_M1000_TuneCP5_13TeV_powheg2_JHUGenV7011_pythia8__v16_L1v1-v1_0.root")
    cutflow = file.Get("cutflow")

    if cutflow:
        print_histogram(cutflow)
    else:
        print("Histogram not found.")

    file.Close()

print_cutflow_histogram()

