import unittest


class TestBranchProtectionFailure(unittest.TestCase):

    def test_intentional_failure(self):
        self.fail(
            "Intentional failure to verify GitHub "
            "branch protection enforcement"
        )


if __name__ == "__main__":
    unittest.main()
