"""Reuse the loaded ROOT interpreter for a single-input haddnano finalization."""
import os
from pathlib import Path
import runpy
import shlex
import shutil
import sys


class _SingleFileOS:
    def __init__(self, original, destination):
        self.original = original
        self.destination = destination

    def __getattr__(self, name):
        return getattr(self.original, name)

    def system(self, command):
        arguments = shlex.split(command)
        if not arguments or Path(arguments[0]).name != 'haddnano.py':
            return self.original.system(command)
        if len(arguments) != 3 or arguments[1] != self.destination:
            raise RuntimeError('Unexpected single-input haddnano command: ' + command)
        script = arguments[0] if os.path.isfile(arguments[0]) else shutil.which(arguments[0])
        if not script:
            raise FileNotFoundError('Cannot find the configured haddnano.py')
        original_argv = sys.argv
        try:
            sys.argv = [script] + arguments[1:]
            namespace = runpy.run_path(script, run_name='__main__')
            # The pinned CLI script relies on process exit to close its files.
            # In-process use must flush/close explicitly before the job report
            # or subsequent readers open the final ROOT file.
            namespace['of'].Close()
            for handle in namespace['fileHandles']:
                handle.Close()
        finally:
            sys.argv = original_argv
        return 0


def run_postprocessor(processor, framework):
    # The pinned NanoAODTools version has no merge callback. Scope the adapter
    # to this framework's os reference; never replace process-wide os.system.
    # Keep the original script's compaction/compression and job-report ordering.
    if len(processor.inputFiles) != 1 or not processor.haddFileName or processor.noOut:
        return processor.run()
    original_os = framework.os
    framework.os = _SingleFileOS(original_os, processor.haddFileName)
    try:
        result = processor.run()
    finally:
        framework.os = original_os
    if not Path(processor.haddFileName).is_file():
        raise RuntimeError('Single-file finalization failed: ' + processor.haddFileName)
    return result
