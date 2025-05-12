import os
import sys

class condorJobHelper(object):
    """docstring for condorJobHelper"""
    def __init__(self, fileName="test",
                 listOfFilesToTransfer="",
                 request_memory=0,
                 request_cpus=0,
                 logFilePath = 'test',
                 logFileName = 'test',
                 Arguments="",
                 JobFlavour="longlunch",
                 Queue=1):
        self.fileName = fileName
        self.listOfFilesToTransfer = listOfFilesToTransfer
        self.request_memory = request_memory
        self.request_cpus = request_cpus
        self.logFilePath = logFilePath
        self.logFileName = logFileName
        self.Arguments = Arguments
        self.JobFlavour = JobFlavour
        self.Queue = Queue

    def jdlFileHeaderCreater(self):
        outJdl = open(self.fileName+'.jdl','w')
        outJdl.write('Executable = '+self.fileName+'.sh')
        outJdl.write('\n'+'Universe = vanilla')
        outJdl.write('\n'+'Notification = ERROR')
        outJdl.write('\n'+'Should_Transfer_Files = YES')
        outJdl.write('\n'+'WhenToTransferOutput = ON_EXIT')
        outJdl.write('\n'+'Transfer_Input_Files = '+self.fileName+'.sh, ' + self.listOfFilesToTransfer)
        outJdl.write('\n'+'x509userproxy = $ENV(X509_USER_PROXY)')
        outJdl.write('\n'+'+JobFlavour = "'+self.JobFlavour+'"')
        if self.request_memory != 0: outJdl.write('\n'+'request_memory = '+str(self.request_memory))
        if self.request_cpus != 0: outJdl.write('\n'+'request_cpus = '+ str(self.request_cpus))
        return self.fileName+'.jdl'

    def jdlFileAppendLogInfo(self):
        outJdl = open(self.fileName+'.jdl','a')
        outJdl.write('\n'+'Output = '+self.logFilePath+os.sep+self.logFileName+'_$(Cluster)_$(Process).stdout')
        outJdl.write('\n'+'Error  = '+self.logFilePath+os.sep+self.logFileName+'_$(Cluster)_$(Process).stdout')
        outJdl.write('\n'+'Log  = '+self.logFilePath+os.sep+self.logFileName+'_$(Cluster)_$(Process).log')
        outJdl.write('\n'+'Arguments = $(Cluster) $(Process) '+self.Arguments)
        outJdl.write('\n'+'Queue '+str(self.Queue))
        outJdl.close()

    def shFileHeaderCreater(self):
        outScript = open(self.fileName+".sh","w");
        outScript.write('#!/bin/bash')
        outScript.write('\n'+'echo "Starting job on " `date`')
        outScript.write('\n'+'echo "Running on: `uname -a`"')
        outScript.write('\n'+'echo "System software: `cat /etc/redhat-release`"')
        outScript.write('\n'+'source /cvmfs/cms.cern.ch/cmsset_default.sh')
        outScript.write('\n'+'echo "'+'#'*51+'"')
        outScript.write('\n'+'echo "#    List of Input Arguments: "')
        outScript.write('\n'+'echo "'+'#'*51+'"')
        outScript.write('\n'+'echo "Input Arguments (CluserID): $1" ')
        outScript.write('\n'+'echo "Input Arguments (ProcessID): $2" ')
        for x in range(3,len(self.Arguments)+3):
            outScript.write('\n'+'echo "Input Arguments: $'+x+'" ')
        outScript.write('\n'+'echo "'+'#'*51+'"')
        outScript.write('\n'+'')
        outScript.close()
        return self.fileName+'.sh'

    def jdlAndShFileCreater(self):
        jdlFile = self.jdlFileHeaderCreater()
        jdlFile = self.jdlFileAppendLogInfo()
        shFile = self.shFileCreater()
        return jdlFile, shFile
