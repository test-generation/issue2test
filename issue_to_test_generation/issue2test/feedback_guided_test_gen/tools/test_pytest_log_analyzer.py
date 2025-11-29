# test_pytest_log_analyzer.py

import unittest
from pytest_log_analyzer import parse_pytest_log

class TestPytestLogAnalyzer(unittest.TestCase):

    def setUp(self):
        # Exact log content provided for testing
        self.log_content = """
+ pytest -rA sklearn/mixture/tests/test_bayesian_mixture.py sklearn/mixture/tests/test_new.py
============================= test session starts ==============================
platform linux -- Python 3.6.13, pytest-6.2.4, py-1.11.0, pluggy-0.13.1
rootdir: /testbed, configfile: setup.cfg
collected 18 items / 2 errors / 16 selected

==================================== ERRORS ====================================
______________ ERROR collecting sklearn/mixture/tests/test_new.py ______________
sklearn/mixture/tests/test_new.py:4: in <module>
    from sklearn.utils._testing import assert_array_equal
E   ModuleNotFoundError: No module named 'sklearn.utils._testing'
______________ ERROR collecting sklearn/mixture/tests/test_new.py ______________
ImportError while importing test module '/testbed/sklearn/mixture/tests/test_new.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/miniconda3/envs/testbed/lib/python3.6/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
sklearn/mixture/tests/test_new.py:4: in <module>
    from sklearn.utils._testing import assert_array_equal
E   ModuleNotFoundError: No module named 'sklearn.utils._testing'
=========================== short test summary info ============================
ERROR sklearn/mixture/tests/test_new.py - ModuleNotFoundError: No module name...
ERROR sklearn/mixture/tests/test_new.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
============================== 2 errors in 0.50s ===============================
+ git checkout 1c8668b0a021832386470ddf740d834e02c66f69 sklearn/mixture/tests/test_bayesian_mixture.py sklearn/mixture/tests/test_gaussian_mixture.py
Updated 0 paths from 96511ff23%
        """

    def test_parse_pytest_log(self):
        # Run the parsing function
        parsed_results = parse_pytest_log(self.log_content)

        # Expected results based on the log content
        expected_results = {
            "tests": [
                {
                    "name": "sklearn/mixture/tests/test_new.py",
                    "outcome": "ERROR"
                },
                {
                    "name": "sklearn/mixture/tests/test_new.py",
                    "outcome": "ERROR"
                }
            ],
            "errors": [
                {
                    "error_type": "ModuleNotFoundError",
                    "module": "sklearn.utils._testing",
                    "symbol": "assert_array_equal",
                    "full_error_text": "E   ModuleNotFoundError: No module named 'sklearn.utils._testing'",
                    "import_statement": "from sklearn.utils._testing import assert_array_equal"
                },
                {
                    "error_type": "ModuleNotFoundError",
                    "module": "sklearn.utils._testing",
                    "symbol": "assert_array_equal",
                    "full_error_text": "E   ModuleNotFoundError: No module named 'sklearn.utils._testing'",
                    "import_statement": "from sklearn.utils._testing import assert_array_equal"
                }
            ]
        }

        # Assertions for tests section
        self.assertIn("tests", parsed_results)
        self.assertEqual(len(parsed_results["tests"]), len(expected_results["tests"]))
        for i, test in enumerate(expected_results["tests"]):
            self.assertEqual(parsed_results["tests"][i]["name"], test["name"])
            self.assertEqual(parsed_results["tests"][i]["outcome"], test["outcome"])

        # Assertions for errors section
        self.assertIn("errors", parsed_results)
        self.assertEqual(len(parsed_results["errors"]), len(expected_results["errors"]))
        for i, error in enumerate(expected_results["errors"]):
            self.assertEqual(parsed_results["errors"][i]["error_type"], error["error_type"])
            self.assertEqual(parsed_results["errors"][i]["module"], error["module"])
            self.assertEqual(parsed_results["errors"][i]["symbol"], error["symbol"])
            self.assertEqual(parsed_results["errors"][i]["full_error_text"], error["full_error_text"])
            self.assertEqual(parsed_results["errors"][i]["import_statement"], error["import_statement"])

if __name__ == "__main__":
    unittest.main()
