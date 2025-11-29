ADDITIONAL_INCLUDES_TEXT = """
## Additional Includes
The following files are included as context for the above source code. These files typically contain libraries or other necessary dependencies to help write more comprehensive tests:
======
{included_files}
======
"""

ADDITIONAL_INSTRUCTIONS_TEXT = """
## Additional Instructions
Please consider the following instructions while generating the unit tests:
======
{additional_instructions}
======
"""

FAILED_TESTS_TEXT = """
## Failed Tests from Previous Iterations
Below is a list of tests that you generated in previous iterations, which failed. Please avoid regenerating these tests and consider their failure reasons when creating new tests to ensure improved outcomes.
======
{failed_test_runs}
======
"""
