import itertools
import unittest
from types import SimpleNamespace

from trigger_selection import TriggerSelection


class TriggerSelectionTest(unittest.TestCase):
    def test_same_or_for_all_decisions(self):
        selector = TriggerSelection(['event.HLT_A', 'event.HLT_B', 'event.HLT_C'])
        for values in itertools.product((False, True), repeat=3):
            event = SimpleNamespace(**dict(zip(selector.names, values)))
            self.assertEqual(selector(event), any(values))

    def test_missing_path_is_an_error_even_after_true(self):
        selector = TriggerSelection(['event.HLT_A', 'event.HLT_B'])
        with self.assertRaises(AttributeError):
            selector(SimpleNamespace(HLT_A=True))

    def test_configuration_is_restricted_to_hlt_branches(self):
        with self.assertRaises(ValueError):
            TriggerSelection(['event.HLT_A or event.HLT_B'])


if __name__ == '__main__':
    unittest.main()
