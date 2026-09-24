"""Helpers for teacher unit tests, available locally and on Jobe."""

import sys
from io import StringIO


class RedirectedStdout:
    """Capture stdout so examples can test printed output with unittest."""

    def __init__(self):
        self._stdout = None
        self._string_io = None

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._string_io = StringIO()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._stdout

    def __str__(self):
        return self._string_io.getvalue()
