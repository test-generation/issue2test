import json
import logging
from feedback_guided_test_gen.llm_invocation import LLMInvocation
import common_helpers
import os
import sys
from tools.test_output_analyzer import parse_test_results_with_llm

#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Sample test log (Modify this to test different cases)
TEST_LOG = """
+ pytest -rA -vv -o console_output_style=classic --tb=no astropy/io/fits/tests/test_new.py
============================= test session starts ==============================
platform linux -- Python 3.6.13, pytest-3.3.1, py-1.11.0, pluggy-0.6.0
collecting ... collected 3 items

astropy/io/fits/tests/test_new.py::TestFITSRecordExponentReplacement::test_replace_exponent_d_to_e FAILED
astropy/io/fits/tests/test_new.py::TestFITSRecordExponentReplacement::test_ascii_table_data_exponent_replacement FAILED
astropy/io/fits/tests/test_new.py::TestFITSRecordExponentReplacement::test_field_data_exponent_replacement PASSED

==================== 2 failed, 1 passed in 0.20 seconds =====================
"""


def test_parse_test_results_with_llm():
    """
    Test the LLM-based test result parsing function with a sample log.
    """
    try:
        # Save test log to a temporary file
        test_log_file = "temp_test_log.txt"
        with open(test_log_file, "w") as f:
            f.write(TEST_LOG)

        # Call the function
        parsed_results = parse_test_results_with_llm(test_log_file)

        # Print results for verification
        print(json.dumps(parsed_results, indent=2))

        # Validate JSON structure
        assert "test_file" in parsed_results, "Missing 'test_file' key"
        assert "tests" in parsed_results, "Missing 'tests' key"
        assert isinstance(parsed_results["tests"], list), "'tests' should be a list"
        assert "summary" in parsed_results, "Missing 'summary' key"

        # Extract test cases
        passing_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] == "PASSED"]
        failing_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] == "FAILED"]

        # Print extracted results
        print("\n✅ Passing Tests:", passing_tests)
        print("❌ Failing Tests:", failing_tests)
        print("📜 Summary:", parsed_results["summary"])

    except AssertionError as e:
        logging.error(f"Test failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


# Run the test
test_parse_test_results_with_llm()
