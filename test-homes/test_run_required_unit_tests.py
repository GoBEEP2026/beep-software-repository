import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from run_required_unit_tests import (
    run_required_unit_tests,
)


class TestRequiredUnitTestRunner(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

        self.root = Path(self.temp.name).resolve()

        self.filename = "test_fictional_suite.py"

        self.runner_path = (
            Path(__file__).resolve().parent
            / "run_required_unit_tests.py"
        )

    def write_suite(self, content):
        path = self.root / self.filename

        path.write_text(
            content,
            encoding="utf-8",
        )

        return path

    def passing_suite(self):
        return (
            "import unittest\n"
            "\n"
            "class FictionalTests(unittest.TestCase):\n"
            "    def test_first(self):\n"
            "        self.assertTrue(True)\n"
            "\n"
            "    def test_second(self):\n"
            "        self.assertEqual(1, 1)\n"
        )

    def execute_runner(self, expected_count):
        command = (
            "import sys\n"
            f"sys.path.insert(0, "
            f"{str(self.runner_path.parent)!r})\n"
            "from run_required_unit_tests import "
            "run_required_unit_tests\n"
            "sys.exit(run_required_unit_tests("
            f"{self.filename!r}, "
            f"{expected_count!r}, "
            f"{str(self.root)!r}))\n"
        )

        return subprocess.run(
            [sys.executable, "-c", command],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_rejected(self, result, message):
        self.assertEqual(
            result.returncode,
            1,
            result.stdout + result.stderr,
        )

        self.assertIn(
            message,
            result.stdout + result.stderr,
        )

    # Input validation: 6 tests

    def test_invalid_filename(self):
        result = run_required_unit_tests(
            "invalid.py", 1, self.root
        )

        self.assertEqual(result, 1)

    def test_path_traversal_filename(self):
        result = run_required_unit_tests(
            "../test_outside.py", 1, self.root
        )

        self.assertEqual(result, 1)

    def test_zero_expected_count(self):
        result = run_required_unit_tests(
            self.filename, 0, self.root
        )

        self.assertEqual(result, 1)

    def test_negative_expected_count(self):
        result = run_required_unit_tests(
            self.filename, -1, self.root
        )

        self.assertEqual(result, 1)

    def test_non_integer_expected_count(self):
        result = run_required_unit_tests(
            self.filename, "2", self.root
        )

        self.assertEqual(result, 1)

    def test_boolean_expected_count(self):
        result = run_required_unit_tests(
            self.filename, True, self.root
        )

        self.assertEqual(result, 1)

    # File and discovery safeguards: 6 tests

    def test_missing_test_file(self):
        result = self.execute_runner(2)

        self.assert_rejected(
            result,
            "does not exist",
        )

    def test_symbolic_link_test_file(self):
        target = self.root / "target.py"

        target.write_text(
            self.passing_suite(),
            encoding="utf-8",
        )

        path = self.root / self.filename
        path.symlink_to(target)

        result = self.execute_runner(2)

        self.assert_rejected(
            result,
            "cannot be a symbolic link",
        )

    def test_zero_discovered_tests(self):
        self.write_suite(
            "import unittest\n"
            "class EmptyTests(unittest.TestCase):\n"
            "    pass\n"
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "No unit tests were discovered",
        )

    def test_fewer_tests_than_expected(self):
        self.write_suite(
            self.passing_suite()
        )

        result = self.execute_runner(3)

        self.assert_rejected(
            result,
            "Unexpected unit test count",
        )

    def test_more_tests_than_expected(self):
        self.write_suite(
            self.passing_suite()
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "Unexpected unit test count",
        )

    def test_discovery_import_error(self):
        self.write_suite(
            "import nonexistent_fictional_module\n"
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "discovery reported errors",
        )

    # Test execution safeguards: 6 tests

    def test_all_expected_tests_pass(self):
        self.write_suite(
            self.passing_suite()
        )

        result = self.execute_runner(2)

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )

        self.assertIn(
            "REQUIRED UNIT TEST VALIDATION PASSED",
            result.stdout,
        )

        self.assertIn(
            "Verified tests: 2/2",
            result.stdout,
        )

    def test_failed_assertion(self):
        self.write_suite(
            "import unittest\n"
            "class FictionalTests(unittest.TestCase):\n"
            "    def test_failure(self):\n"
            "        self.assertTrue(False)\n"
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "Required unit tests failed",
        )

    def test_execution_error(self):
        self.write_suite(
            "import unittest\n"
            "class FictionalTests(unittest.TestCase):\n"
            "    def test_error(self):\n"
            "        raise RuntimeError('Test error')\n"
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "Required unit tests failed",
        )

    def test_skipped_test_rejected(self):
        self.write_suite(
            "import unittest\n"
            "class FictionalTests(unittest.TestCase):\n"
            "    @unittest.skip('Fictional skip')\n"
            "    def test_skipped(self):\n"
            "        pass\n"
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "cannot be skipped",
        )

    def test_expected_failure_rejected(self):
        self.write_suite(
            "import unittest\n"
            "class FictionalTests(unittest.TestCase):\n"
            "    @unittest.expectedFailure\n"
            "    def test_failure(self):\n"
            "        self.assertTrue(False)\n"
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "cannot contain expected failures",
        )

    def test_unexpected_success_rejected(self):
        self.write_suite(
            "import unittest\n"
            "class FictionalTests(unittest.TestCase):\n"
            "    @unittest.expectedFailure\n"
            "    def test_success(self):\n"
            "        self.assertTrue(True)\n"
        )

        result = self.execute_runner(1)

        self.assert_rejected(
            result,
            "Required unit tests failed",
        )

    # Reporting and command-line safeguards: 2 tests

    def test_expected_and_discovered_counts_reported(self):
        self.write_suite(
            self.passing_suite()
        )

        result = self.execute_runner(2)

        self.assertEqual(result.returncode, 0)

        self.assertIn(
            "Expected tests: 2",
            result.stdout,
        )

        self.assertIn(
            "Discovered tests: 2",
            result.stdout,
        )

    def test_missing_command_line_arguments(self):
        result = subprocess.run(
            [
                sys.executable,
                str(self.runner_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            2,
        )


if __name__ == "__main__":
    unittest.main()
