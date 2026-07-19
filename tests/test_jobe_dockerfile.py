import unittest
from pathlib import Path


class TestJobeDockerfile(unittest.TestCase):
    def test_installs_packaged_catch2_v3_for_linked_test_runner(self):
        dockerfile = (Path(__file__).resolve().parents[1] / "jobe" / "Dockerfile").read_text()

        self.assertIn("catch2", dockerfile)
        self.assertIn("test -f /usr/include/catch2/catch_test_macros.hpp", dockerfile)
        self.assertIn("test -f /usr/lib/*/libCatch2Main.a", dockerfile)
        self.assertIn("test -f /usr/lib/*/libCatch2.a", dockerfile)
        self.assertNotIn("CATCH2_VERSION", dockerfile)
        self.assertNotIn("single_include/catch2/catch.hpp", dockerfile)
