import unittest
from pathlib import Path


class TestJobeDockerfile(unittest.TestCase):
    def test_installs_header_only_catch2_v2_for_generated_test_runner(self):
        dockerfile = (Path(__file__).resolve().parents[1] / "jobe" / "Dockerfile").read_text()

        self.assertIn("ARG CATCH2_VERSION=v2.13.10", dockerfile)
        self.assertIn("catchorg/Catch2.git /tmp/catch2", dockerfile)
        self.assertIn("/tmp/catch2/single_include/catch2/catch.hpp", dockerfile)
        self.assertIn("/usr/local/include/catch2/catch.hpp", dockerfile)
