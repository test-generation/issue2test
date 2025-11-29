import os
import re
import subprocess
import shutil
import logging

from feedback_guided_test_gen import config


class DockerTestRunner:
    def __init__(self, swebench_folder, new_test_file_path, issue_id, project_name):
        self.swebench_folder = swebench_folder
        self.new_test_file_path = new_test_file_path
        self.issue_id = issue_id
        self.project_name = project_name
        self.logger = logging.getLogger(__name__)

    def clean_django_test_path(self, path):
        """
        Cleans up Django test file paths by removing the 'tests/' prefix if it exists at the start.

        This ensures that test file paths do not include the 'tests/' directory at the beginning,
        making them compatible with required formats for execute_in_docker.py script.

        Example:
            clean_django_test_path("tests/messages_tests/test_new.py")  -> "messages_tests/test_new.py"
            clean_django_test_path("tests/test_models.py")              -> "test_models.py"
            clean_django_test_path("src/tests/api/test_views.py")       -> "src/tests/api/test_views.py" (unchanged)

        :param path: The original test file path.
        :return: A cleaned-up path without the 'tests/' prefix.
        """
        prefix = "tests/"

        if path.startswith(prefix):
            cleaned_path = path[len(prefix):]  # Dynamically remove only the prefix
        else:
            cleaned_path = path  # Keep the original path unchanged

        return cleaned_path

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

    def generate_swebench_files(self, test_folder, relative_path_to_docker):  # changed (new method)
        """
        Generate required files for execute_in_docker.py:
        - `test_paths`: Maps host test file path to its expected path inside the container.
        - `test_folders`: Maps the project name to the default test directory in Docker.
        """  # changed
        test_paths_file = os.path.join(test_folder, "test_paths")  # changed

        # **1. Get the absolute path of the generated test file on the host machine**
        generated_test_host_path = os.path.abspath(os.path.join(test_folder, "test_new.py"))  # changed

        # **2. Determine the correct test path inside Docker**
        docker_test_path = f"tests/test_new.py"  # FOLLOWING OLD SCRIPT LOGIC  # changed

        # **3. Create test_paths (host file -> Docker path mapping)**
        with open(test_paths_file, "w") as f:  # changed
            f.write(f"{generated_test_host_path}#{relative_path_to_docker}\n")  # changed

        # Logging to confirm generated files
        self.logger.info(
            f"Generated test_paths file: {test_paths_file} -> {generated_test_host_path} -> {docker_test_path}")  # changed

        return test_paths_file  # changed

    def generate_swebench_files_django(self, test_folder, relative_path_to_docker):  # changed (new method)
        """
        Generate required files for execute_in_docker.py:
        - `test_paths`: Maps host test file path to its expected path inside the container.
        - `test_folders`: Maps the project name to the default test directory in Docker.
        """  # changed
        # test_paths_file = os.path.join(test_folder, "test_paths")
        test_paths_file = os.path.join(test_folder, "paths.lst")# changed

        # **1. Get the absolute path of the generated test file on the host machine**
        generated_test_host_path = os.path.abspath(os.path.join(test_folder, "test_new.py"))  # changed

        # **2. Determine the correct test path inside Docker**
        docker_test_path = f"tests/test_new.py"  # FOLLOWING OLD SCRIPT LOGIC  # changed

        # ✅ Remove "tests/" prefix if it exists
        # if relative_path_to_docker.startswith("tests/"):
        #     relative_path_to_docker = relative_path_to_docker.replace("tests/", "", 1)
        relative_path_to_docker = self.clean_django_test_path(relative_path_to_docker)

        # **3. Create test_paths (host file -> Docker path mapping)**
        with open(test_paths_file, "w") as f:  # changed
            f.write(f"{generated_test_host_path}#{relative_path_to_docker}\n")  # changed

        # Logging to confirm generated files
        self.logger.info(
            f"Generated test_paths file: {test_paths_file} -> {generated_test_host_path} -> {docker_test_path}")  # changed

        return test_paths_file  # changed

    def run_tests_in_docker(self, test_folder, relative_path_to_docker):
        """
        Run the tests inside a Docker container using Django's `runtests.py`.
        """
        issue_id = self.issue_id  # e.g., django__django-11583

        # generated_tests_folder, test_folders_mapping, relative_path_to_docker
        files_to_copy = self.generate_swebench_files(test_folder, relative_path_to_docker)  # changed

        test_folder_mapping = os.path.join(config.SWE_BENCH_DOCKER_DIR, "test_folders")

        if self.project_name == "django":
            test_paths_django = self.generate_swebench_files_django(test_folder,
                                                                    relative_path_to_docker)
            docker_command = [
                "python",
                "execute_in_docker.py",
                issue_id,
                test_paths_django,
                files_to_copy,
                test_folder_mapping
            ]
        else:
            docker_command = [
                "python",
                "execute_in_docker.py",
                issue_id,
                files_to_copy,
                files_to_copy,
                test_folder_mapping
            ]

        # Change directory to the SWE-bench path
        swebench_dir = self.swebench_folder
        self.logger.info(f"Changing directory to {swebench_dir}")
        os.chdir(swebench_dir)  # Change to the directory containing `run_tests_in_docker.py`

        self.logger.info(f"Running tests in Docker with command: {' '.join(docker_command)}")

        try:
            subprocess.run(docker_command,
                           check=True,
                           timeout=config.DOCKER_EXECUTION_TIME_OUT_IN_SECONDS)
        except subprocess.TimeoutExpired:
            self.logger.error("Test execution timed out.")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Test execution failed: {e}")
            raise

    def check_test_results(self, test_folder):
        """
        Parse the test results file to check for errors, failures, or warnings.
        Returns a detailed status including pass, fail, and warning counts.
        """
        results_file = os.path.join(self.swebench_folder, f"{self.issue_id}_test_results_buggy")

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
    error_pattern = re.compile(r"^\s*E\s|Error|Exception|FAILED")

    # Check each line for a match with the error pattern
    for line in lines:
        if error_pattern.search(line):
            return True  # Return True as soon as an error is detected

    return False  # Return False if no errors are found
