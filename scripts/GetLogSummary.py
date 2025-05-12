import argparse
import os
import re

# Set up the parser
parser = argparse.ArgumentParser(description="Process some logs.")
parser.add_argument("-d", "--directory", type=str, help="Path to the directory containing the *.stdout files", required=True)
parser.add_argument("--debug", action="store_true", help="Enable debug mode")

# Parse the arguments
args = parser.parse_args()

# Use the parsed arguments
DEBUG = args.debug
log_files_dir = args.directory

# Regular expression patterns to match the desired lines
patterns = {
    "Total": re.compile(r'Total:\s+:(\d+)\s+Events'),
    "PassTrig": re.compile(r'PassTrig:\s+:(\d+)\s+Events'),
    "Pass2eCut": re.compile(r'Pass2eCut:\s+:(\d+)\s+Events'),
    "Pass2muCut": re.compile(r'Pass2muCut:\s+:(\d+)\s+Events'),
    "Pass2lCut": re.compile(r'Pass2lCut:\s+:(\d+)\s+Events'),
    "40 < m_ee < 180": re.compile(r'Pass2eCut \(40 < mll < 180\):\s+:(\d+)\s+Events'),
    "40 < m_mumu < 180": re.compile(r'Pass2muCut \(40 < mll < 180\):\s+:(\d+)\s+Events'),
    "40 < mll < 180": re.compile(r'Pass2lCut \(40 < mll < 180\):\s+:(\d+)\s+Events'),
    "Pass2l1JCut": re.compile(r'Pass2l1JCut:\s+:(\d+)\s+Events'),
    "Pass2l2jCut": re.compile(r'Pass2l2jCut:\s+:(\d+)\s+Events'),
    "Pass2l1Jor2jCut": re.compile(r'Pass2l1Jor2jCut:\s+:(\d+)\s+Events'),
    "PassZZSelection": re.compile(r'PassZZSelection:\s+:(\d+)\s+Events')
}

# Dictionary to store the sum of events for each category
category_sums = {}

# Loop through each *.stdout file in the directory
for filename in os.listdir(log_files_dir):
    if filename.endswith('.stdout'):
        file_path = os.path.join(log_files_dir, filename)
        if DEBUG: print(("\n\nFilename: "+log_files_dir+'/'+filename))

        with open(file_path, 'r') as f:
            content = f.read()

            # Find events for each category based on the specified patterns
            for category, pattern in list(patterns.items()):
                match = pattern.search(content)
                if DEBUG: print(("{} {}".format(category, pattern)))
                if DEBUG: print(("Match: {}".format(match)))
                if match:
                    events = int(match.group(1))
                    if DEBUG: print(("{:25} {}".format(category, events)))
                    if category in category_sums:
                        category_sums[category] += events
                    else:
                        category_sums[category] = events

# Print the sum of events for each category
if DEBUG: print("\n\n")
for category, events in list(category_sums.items()):
    print(("{category:17}: {events:>7} Events".format(category=category, events=events)))
