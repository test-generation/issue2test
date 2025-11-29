import os
import re
import subprocess
import shutil
import logging


class DockerTestRunner:
    def __init__(self, swebench_folder, new_test_file_path, issue_id):
        self.swebench_folder = swebench_folder
        self.new_test_file_path = new_test_file_path
        self.issue_id = issue_id
        self.logger = logging.getLogger(__name__)

    def prepare_environment(self):
        """Prepare the environment by creating the necessary directories."""
        os.chdir(self.swebench_folder)
        self.logger.info(f"Changed directory to {self.swebench_folder}")

        test_folder = os.path.join(self.swebench_folder, 'generated-tests')
        os.makedirs(test_folder, exist_ok=True)
        self.logger.info(f"Created or verified existence of folder: {test_folder}")
        return test_folder

    def copy_test_file(self, test_folder):
        """Copy the generated test file to the 'generated-tests' folder."""
        destination_file = os.path.join(test_folder, 'test_new.py')
        try:
            shutil.copy(self.new_test_file_path, destination_file)
            self.logger.info(f"Copied '{self.new_test_file_path}' to '{destination_file}'")
            return destination_file
        except IOError as e:
            self.logger.error(f"Failed to copy '{self.new_test_file_path}' to '{destination_file}': {e}")
            raise

    def run_tests_in_docker(self, test_folder):
        """
        Run the tests inside a Docker container using Django's `runtests.py`.
        """
        issue_id = self.issue_id  # e.g., django__django-11583
        docker_command = [
            "python", "run_tests_in_docker.py", issue_id,
            "--files_folder", test_folder
        ]

        # Change directory to the SWE-bench path
        swebench_dir = self.swebench_folder
        self.logger.info(f"Changing directory to {swebench_dir}")
        os.chdir(swebench_dir)  # Change to the directory containing `run_tests_in_docker.py`

        self.logger.info(f"Running tests in Docker with command: {' '.join(docker_command)}")

        try:
            subprocess.run(docker_command, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Test execution failed: {e}")
            raise

    def check_test_results(self, test_folder):
        """
        Parse the test results file to check for errors, failures, or warnings.
        Returns a detailed status including pass, fail, and warning counts.
        """
        results_file = os.path.join(self.swebench_folder, f"{self.issue_id}_test_results.txt")
        if not os.path.exists(results_file):
            self.logger.error(f"Results file not found at {results_file}")
            return True, "No results file found."

        with open(results_file, "r") as f:
            result_content = f.read()

        # Initialize counters for different types of results
        test_failures = False
        pass_count = len(re.findall(r"(?<=\n)PASSED ", result_content))
        fail_count = len(re.findall(r"(?<=\n)FAILED ", result_content))
        error_count = len(re.findall(r"(?<=\n)ERROR ", result_content))
        warning_count = len(re.findall(r"(?<=\n)WARNING ", result_content))

        # Determine if there are any test failures
        if fail_count > 0 or error_count > 0:
            test_failures = True

        # Compile results in a dictionary for better readability
        results_summary = {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "test_failures": test_failures
        }

        return test_failures, results_summary, result_content


def naive_contains_error(log_content):
    lines = log_content.splitlines()

    # Generic pattern to detect error lines (lines starting with "E " or containing "Error" or "Exception")
    error_pattern = re.compile(r"^\s*E\s|Error|Exception")

    # Check each line for a match with the error pattern
    for line in lines:
        if error_pattern.search(line):
            return True  # Return True as soon as an error is detected

    return False  # Return False if no errors are found
