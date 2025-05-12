import os
import sys

sys.path.append("Utils/.")
from color_style import style

output = os.popen('condor_q -submitter rasharma').read()

error_check_string = [ 'Server responded with an error',
                       'The remote file is not open',
                       'Error in <TNetXNGFile::ReadBuffer>']

#Oprint output.split("\t")
lpcschedd = ""
print(type(output))
for outputs in output.split('\n'):
  #print outputs
  if outputs.find('Submitter') != -1:
    lpcschedd = outputs.split()[2].split('.')[0]
  if outputs.find('rasharma') != -1 and outputs.split()[5] == 'R':
    """This if condition checks the username and if the job is in
    Running (R) condition.
    """
    condor_tail = "condor_tail "+outputs.split()[0]+" -name "+lpcschedd

    print("\n","-"*51,"\n\n")
    print((style.GREEN + outputs+style.RESET+"\n\n"))
    print("COMMAND: ",condor_tail)
    print("\n")
    # os.system(condor_tail)
    output = os.popen(condor_tail).read()

    foundOrNot = any(match in output for match in error_check_string)

    if foundOrNot:
        print(output)
        print((style.RED + "ERROR: Going to kill this job" + style.RESET))
        killCommand = "condor_rm "+outputs.split()[0]+" -name "+lpcschedd
        print((style.RED + "Running Command: " + killCommand + style.RESET))
        os.system(killCommand)
        print((style.RED + "Successfully killed." + style.RESET))
    else:
        print(output)
print("\n\n")
