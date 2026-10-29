import os
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest

from skim_io import run_postprocessor


class SkimIOTest(unittest.TestCase):
    def test_single_file_reuses_backend_and_restores_framework(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'skim.root', Path(directory) / 'final.root'
            source.write_bytes(b'completed skim bytes')
            backend = Path(directory) / 'haddnano.py'
            backend.write_text(
                "import sys\nfrom pathlib import Path\n"
                "Path(sys.argv[1]).write_bytes(Path(sys.argv[2]).read_bytes())\n"
                "class File:\n"
                "    def Close(self):\n"
                "        Path(sys.argv[1] + '.closed').write_text('closed')\n"
                "of = File()\nfileHandles = []\n")
            framework = SimpleNamespace(os=os)
            original_argv = sys.argv
            def run():
                self.assertIsNot(framework.os, os)
                self.assertEqual(framework.os.system(' '.join(shlex.quote(str(p)) for p in (backend, output, source))), 0)
            processor = SimpleNamespace(inputFiles=['raw.root'], noOut=False,
                                        haddFileName=str(output), run=run)
            run_postprocessor(processor, framework)
            self.assertEqual(output.read_bytes(), b'completed skim bytes')
            self.assertTrue(source.exists())
            self.assertTrue(Path(str(output) + '.closed').exists())
            self.assertIs(framework.os, os)
            self.assertIs(sys.argv, original_argv)

    def test_multi_input_uses_existing_processor(self):
        framework = SimpleNamespace(os=os)
        processor = SimpleNamespace(inputFiles=['a.root', 'b.root'], noOut=False,
                                    haddFileName='final.root', run=lambda: framework.os)
        self.assertIs(run_postprocessor(processor, framework), os)

    def test_processing_failure_is_exposed_and_framework_restored(self):
        framework = SimpleNamespace(os=os)
        def run():
            raise RuntimeError('processing failed')
        processor = SimpleNamespace(inputFiles=['raw.root'], noOut=False,
                                    haddFileName='final.root', run=run)
        with self.assertRaisesRegex(RuntimeError, 'processing failed'):
            run_postprocessor(processor, framework)
        self.assertIs(framework.os, os)


if __name__ == '__main__':
    unittest.main()
