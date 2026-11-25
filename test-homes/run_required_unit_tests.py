import argparse
import re
import sys
import unittest
from pathlib import Path


TEST_FILENAME_PATTERN = re.compile(
    r"test_[A-Za-z0-9_]+\.py"
)


def run_required_unit_tests(
    test_filename,
    expected_count,
    test_directory=None,
):
    """
    Discover and execute a required unit test suite.

    Reject missing test files, zero-test discovery,
    unexpected test counts, and failed tests.
    """

    if test_directory is None:
        test_directory = (
            Path(__file__).resolve().parent
        )

    test_directory = Path(
        test_directory
    ).resolve()

    if (
        not isinstance(test_filename, str)
        or not TEST_FILENAME_PATTERN.fullmatch(
            test_filename
        )
    ):
        print(
            "ERROR: Invalid unit test filename"
        )
        return 1

    if (
        type(expected_count) is not int
        or expected_count <= 0
    ):
        print(
            "ERROR: Expected test count must "
            "be a positive integer"
        )
        return 1

    test_path = (
        test_directory / test_filename
    )

    if not test_path.is_file():
        print(
            f"ERROR: Required unit test file "
            f"does not exist: {test_filename}"
        )
        return 1

    if test_path.is_symlink():
        print(
            "ERROR: Required unit test file "
            "cannot be a symbolic link"
        )
        return 1

    print(
        f"Required test suite: {test_filename}",
        flush=True,
    )

    print(
        f"Expected tests: {expected_count}",
        flush=True,
    )

    loader = unittest.TestLoader()

    try:
        suite = loader.discover(
            start_dir=str(test_directory),
            pattern=test_filename,
        )

    except Exception as exc:
        print(
            f"ERROR: Unit test discovery failed: {exc}"
        )
        return 1

    if loader.errors:
        print(
            "ERROR: Unit test discovery "
            "reported errors"
        )

        for error in loader.errors:
            print(error)

        return 1

    discovered_count = suite.countTestCases()

    print(
        f"Discovered tests: {discovered_count}",
        flush=True,
    )

    if discovered_count == 0:
        print(
            "ERROR: No unit tests were discovered"
        )
        return 1

    if discovered_count != expected_count:
        print(
            f"ERROR: Unexpected unit test count. "
            f"Expected {expected_count}, "
            f"discovered {discovered_count}"
        )
        return 1

    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
    )

    result = runner.run(suite)

    if result.testsRun != expected_count:
        print(
            f"ERROR: Unexpected executed test count. "
            f"Expected {expected_count}, "
            f"executed {result.testsRun}"
        )
        return 1

    if not result.wasSuccessful():
        print(
            "ERROR: Required unit tests failed"
        )
        return 1

    if result.skipped:
        print(
            "ERROR: Required unit tests "
            "cannot be skipped"
        )
        return 1

    if result.expectedFailures:
        print(
            "ERROR: Required unit tests "
            "cannot contain expected failures"
        )
        return 1

    print(
        "REQUIRED UNIT TEST VALIDATION PASSED"
    )

    print(
        f"Verified tests: "
        f"{result.testsRun}/{expected_count}"
    )

    return 0


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Execute required unit tests "
            "and verify the expected test count."
        )
    )

    parser.add_argument(
        "test_filename",
        help="Required unit test filename",
    )

    parser.add_argument(
        "expected_count",
        type=int,
        help="Expected number of unit tests",
    )

    arguments = parser.parse_args()

    sys.exit(
        run_required_unit_tests(
            arguments.test_filename,
            arguments.expected_count,
        )
    )
