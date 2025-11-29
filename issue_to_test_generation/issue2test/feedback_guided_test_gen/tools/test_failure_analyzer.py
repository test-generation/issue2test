def has_test_failures_naive(log: str) -> bool:
    """
    Check if there are any test failures in the log output.

    Args:
        log (str): The log output from a test run.

    Returns:
        bool: True if there are any test failures or errors, False otherwise.
    """
    failure_indicators = ["Failed", "DID NOT RAISE", "Traceback", "NameError", "ERROR", "RecursionError"]

    for line in log.splitlines():
        if any(indicator in line for indicator in failure_indicators):
            return True
    return False


def has_test_failures(test_status_map: dict) -> bool:
    """
    Check if there are any test failures or errors in the test status map.

    Args:
        test_status_map (dict): A dictionary where keys are test identifiers and values are status strings.

    Returns:
        bool: True if there are any 'FAILED' or 'ERROR' statuses, False otherwise.
    """
    for status in test_status_map.values():
        if status in {"FAILED", "ERROR"}:
            return True
    return False


def main():
    # Example test status map
    test_status_map = {
        'sympy/matrices/expressions/tests/test_new.py:test_identity_matrix_sum': 'FAILED',
        'sympy/matrices/expressions/tests/test_new.py:test_kronecker_delta_sum': 'FAILED',
        'test_identity_matrix_sum': 'ERROR'
    }

    # Check for failures
    has_failures = has_test_failures(test_status_map)
    if has_failures:
        print("There are test failures or errors.")
    else:
        print("All tests passed successfully.")


# Run main if this script is executed
if __name__ == "__main__":
    main()
