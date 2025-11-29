# pytest_log_analyzer.py

import re
import unicodedata
import json
from enum import Enum


class TestStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


def parse_pytest_log(log):
    """
    Parses the raw pytest log, detecting test outcomes and errors.

    Args:
        log (str): Raw log output from pytest.

    Returns:
        dict: Structured dictionary of parsed test outcomes and errors.
    """
    results = {
        "tests": [],
        "errors": []
    }

    lines = log.split("\n")
    previous_line = ""

    for line in lines:
        line = remove_ansi_escape_codes(line)
        line = ''.join(c for c in line if unicodedata.category(c)[0] != 'C')

        # Check for known error patterns
        error_details = extract_error_details(line, previous_line)
        if error_details:
            results["errors"].append(error_details)
            continue

        # Detect test outcomes like PASSED, FAILED, ERROR, etc.
        test_outcome = detect_test_outcome(line)
        if test_outcome:
            results["tests"].append(test_outcome)

        # Update previous line for reference in multi-line errors
        previous_line = line

    return results


def detect_test_outcome(line):
    """
    Detects the outcome of a test (e.g., PASSED, FAILED) in a log line.

    Args:
        line (str): A single line from the pytest log.

    Returns:
        dict: A dictionary with test name and outcome status, or None if no outcome is detected.
    """
    for status in TestStatus:
        if line.startswith(status.value):
            # Assume the format "STATUS test_name" or "STATUS - test_name"
            parts = line.replace(" - ", " ").split()
            if len(parts) >= 2:
                return {"name": parts[1], "outcome": status.value}
    return None


def extract_error_details(line, previous_line):
    """
    Extracts details of errors from a given log line, handling multi-line errors.

    Args:
        line (str): A single line from the pytest log.
        previous_line (str): The previous line, used to capture import statements.

    Returns:
        dict: Parsed error details including type, message, and other relevant data, or None if no error is found.
    """
    # Define regex patterns for known errors
    error_patterns = {
        "ModuleNotFoundError": re.compile(r"ModuleNotFoundError: No module named '(.*?)'"),
        "ImportError": re.compile(r"ImportError: cannot import name '(.*?)' from '(.*?)'"),
        "AssertionError": re.compile(r"AssertionError: (.*)"),
        "SyntaxError": re.compile(r"SyntaxError: (.*?) at line (\d+)"),
        "TypeError": re.compile(r"TypeError: (.*)"),
        "AttributeError": re.compile(r"AttributeError: (.*)"),
        "ValueError": re.compile(r"ValueError: (.*)"),
        "NameError": re.compile(r"NameError: name '(.*?)' is not defined"),
        "IndexError": re.compile(r"IndexError: (.*)"),
        "KeyError": re.compile(r"KeyError: '(.*?)'")
    }

    for error_type, pattern in error_patterns.items():
        match = pattern.search(line)
        if match:
            details = match.groups()
            if error_type == "ModuleNotFoundError":
                module_name = details[0]
                # Capture import statement from the previous line
                import_statement_match = re.search(r"from (.*?) import (.*)", previous_line)
                import_statement = import_statement_match.group(0) if import_statement_match else None
                symbol = import_statement_match.group(2) if import_statement_match else None
                return {
                    "error_type": error_type,
                    "module": module_name,
                    "symbol": symbol,
                    "full_error_text": line.strip(),
                    "import_statement": import_statement
                }
            return {
                "error_type": error_type,
                "details": details,
                "full_error_text": line.strip()
            }
    return None


def remove_ansi_escape_codes(text):
    """
    Removes ANSI escape codes from log text for cleaner parsing.

    Args:
        text (str): Text string possibly containing ANSI escape codes.

    Returns:
        str: Cleaned text with ANSI escape codes removed.
    """
    ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape_pattern.sub('', text)


def structure_parsed_results(results):
    """
    Structures parsed results into a summary format (JSON).

    Args:
        results (dict): Parsed results dictionary.

    Returns:
        str: Structured summary in JSON format for easy consumption.
    """
    return json.dumps(results, indent=4)


def find_module_not_found_errors(parsed_results):
    """
    Finds all unique ModuleNotFoundError entries in the parsed results and extracts the missing symbols.

    Args:
        parsed_results (dict): The parsed JSON results from parse_pytest_log.

    Returns:
        set: A set of tuples containing unique (module, symbol) pairs for each ModuleNotFoundError found.
    """
    module_not_found_errors = set()

    # Loop through each error in parsed_results
    for error in parsed_results.get("errors", []):
        # Check if the error type is ModuleNotFoundError
        if error.get("error_type") == "ModuleNotFoundError":
            # Extract the module and symbol if they exist
            module = error.get("module")
            symbol = error.get("symbol")
            module_not_found_errors.add((module, symbol))  # Add tuple to set for uniqueness

    return module_not_found_errors

def get_first_module_not_found_error(parsed_results):
    module_not_found_errors = find_module_not_found_errors(parsed_results)
    return next(iter(module_not_found_errors), None)

# Example usage
if __name__ == "__main__":
    log_content = """
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

    parsed_results = parse_pytest_log(log_content)
    print(structure_parsed_results(parsed_results))


    parsed_results_json = """
{
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
"""
    # Parse JSON to dictionary
    parsed_results = json.loads(parsed_results_json)

    # Get unique ModuleNotFoundError symbols
    module_not_found_errors = find_module_not_found_errors(parsed_results)
    print("Unique ModuleNotFoundError Symbols:", module_not_found_errors)

