"""Resolve the configured HLT names once, then read their decisions per event."""
import re


class TriggerSelection:
    def __init__(self, expressions):
        self.names = []
        for expression in expressions:
            if not re.fullmatch(r"event\.HLT_[A-Za-z0-9_]+", expression):
                raise ValueError("Expected an event.HLT_* branch: " + expression)
            self.names.append(expression[6:])
        self.names = tuple(self.names)

    def __call__(self, event):
        # Read every configured branch, even after a true bit. Like the old
        # eager evaluation, a missing path must raise rather than become false.
        passed = False
        for name in self.names:
            passed |= bool(getattr(event, name))
        return passed
