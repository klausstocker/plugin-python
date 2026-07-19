import unittest
from pathlib import Path


class TestJobeDockerfile(unittest.TestCase):
    def test_builds_catch2_v3_libraries_for_linked_test_runner(self):
        dockerfile = (Path(__file__).resolve().parents[1] / "jobe" / "Dockerfile").read_text()

        self.assertIn("ARG CATCH2_VERSION=v3.4.0", dockerfile)
        self.assertIn("cmake --install /tmp/catch2-build", dockerfile)
        self.assertIn("test -f /usr/local/include/catch2/catch_test_macros.hpp", dockerfile)
        self.assertIn("test -f /usr/local/lib/libCatch2Main.a", dockerfile)
        self.assertIn("test -f /usr/local/lib/libCatch2.a", dockerfile)
        self.assertNotIn("single_include/catch2/catch.hpp", dockerfile)
