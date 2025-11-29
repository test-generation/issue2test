import json
import logging
import os
import shutil
import subprocess

from file_preprocessor import FilePreprocessor
from lance_logger import LanceLogger
#from issue2test_logger import LanceLogger
from llm_invocation import LLMInvocation
from common_helpers import get_code_language, strip_code_block
from test_utils import detect_compilation_error

class UnitTestGeneratorCompilationFailure:
    def __init__(self, source_code_file: str,
                 test_code_file: str,
                 new_test_file_path: str,
                 test_execution_command: str,
                 llm_model: str,
                 swebench_folder:str,
                 test_code_command_dir: str = os.getcwd(),
                 additional_instructions: str = "",
                 github_issue: str = ""):
        self.source_code_file = source_code_file
        with open(self.source_code_file, 'r') as source_file:
            source_code = source_file.read()
        self.source_code = source_code

        self.test_code_file = test_code_file
        with open(self.test_code_file, 'r') as test_file:
            test_code = test_file.read()
        self.test_code = test_code

        self.new_test_file_path = new_test_file_path

        self.test_execution_command = test_execution_command
        self.test_code_command_dir = test_code_command_dir
        self.additional_instructions = additional_instructions
        self.github_issue = github_issue

        self.language = get_code_language(source_code_file)

        self.llm_invoker = LLMInvocation(model=llm_model)
        self.swebench_folder = swebench_folder

        self.logger = LanceLogger.initialize_logger(__name__)

        self.preprocessor = FilePreprocessor(self.test_code_file)
        self.failed_test_runs = []

        # self.run_coverage()
        #self.prompt = self.build_prompt()

    # def build_prompt(self):
    #     """
    #     Returns:
    #         str: prompt that will be used for generating new tests
    #     """
    #     failed_test_runs_value = ""
    #     self.code_coverage_report = ""
    #     self.prompt_builder = PromptBuilder(
    #         source_code_file=self.source_code_file,
    #         test_code_file=self.test_code_file,
    #         code_coverage_report=self.code_coverage_report,
    #         included_files="",
    #         additional_instructions=self.additional_instructions,
    #         failed_test_runs=failed_test_runs_value,
    #         language=self.language,
    #         github_issue=self.github_issue,
    #     )
    #
    #     return self.prompt_builder.build_prompt()

    def build_prompt(self, compilation_error_message: str = ""):
        """
        Returns:
            str: A prompt that will be used for fixing the compilation error in the generated tests.
        """
        # Read the source code, existing test code, and newly generated test code
        # with open(self.source_code_file, 'r') as source_file:
        #     source_code = source_file.read()
        source_code = self.source_code

        # with open(self.test_code_file, 'r') as test_file:
        #     test_code = test_file.read()
        test_code = self.test_code

        with open(self.new_test_file_path, 'r') as new_test_file:
            new_test_code = new_test_file.read()

        system_message = (
            "You are an AI coding assistant. "
            "Your task is to fix compilation errors in Python test code."
        )

        # Generic prompt construction
        user_message = (
            f"Based on the provided source code, existing tests, and newly generated tests, "
            f"a compilation error has occurred.\n\n"
            f"--- Source Code ---\n"
            f"{source_code}\n\n"
            f"--- Existing Test Code ---\n"
            f"{test_code}\n\n"
            f"--- Newly Generated Test Code ---\n"
            f"{new_test_code}\n\n"
            f"--- Compilation Error ---\n"
            f"{compilation_error_message}\n\n"
            f"Please identify and fix the issue in the newly generated test code. "
            f"The error might be related to incorrect imports, syntax, or other factors. "
            f"Update the test code to ensure it compiles and runs correctly. "
            f"Provide the corrected test code only, without additional explanations."
        )

        return {
            "system": system_message,
            "user": user_message
        }

    def generate_tests(self, max_tokens=4096):
        self.prompt = self.build_prompt()
        response, prompt_token_count, response_token_count = (
            self.llm_invoker.call_model(prompt=self.prompt,
                                        max_tokens=max_tokens))

        self.logger.info(f"generated test: {response}")
        self.logger.info(f"Total token count for LLM {self.llm_invoker.model}: "
                         f"{prompt_token_count + response_token_count}")
        try:
            tests_dict = [response,
                          "",
                          ""]
        except Exception as e:
            self.logger.error(f"Error during test generation: {e}")
            fail_details = {
                "status": "FAIL",
                "reason": f"Parsing error: {e}",
                "exit_code": None,  # No exit code as it's a parsing issue
                "stderr": str(e),
                "stdout": "",  # No output expected from a parsing error
                "test": response,  # Use the response that led to the error
            }
            # self.failed_test_runs.append(fail_details)
            tests_dict = []

        return tests_dict

    def check_compilation_error(self, report_file: str) -> bool:
        """
        Check the .report.json file for any compilation errors.
        """
        try:
            with open(report_file, 'r') as file:
                report_data = json.load(file)

            for collector in report_data.get('collectors', []):
                if collector['outcome'] == 'failed':
                    if 'ImportError' in collector.get('longrepr', ''):
                        self.logger.error("Compilation error detected.")
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Error parsing report file: {e}")
            return True  # Fail-safe: consider any error in parsing as a potential compilation error

    def create_test_folder(self, folder_path):
        os.makedirs(folder_path, exist_ok=True)
        self.logger.info(f"Created or verified existence of folder: {folder_path}")

    def run_test_and_handle_compilation_error(self, new_test_file_path):
        # Step 0: Navigate to the correct directory
        os.chdir("/Users/nashid/repos/issue-to-test/test_execution/SWE-bench")
        self.logger.info("Changed directory to /Users/nashid/repos/issue-to-test/test_execution/SWE-bench")

        # Step 1: Create the 'generated-tests' folder
        test_folder = "/Users/nashid/repos/issue-to-test/test_execution/SWE-bench/generated-tests"
        os.makedirs(test_folder, exist_ok=True)
        self.logger.info(f"Created or verified existence of folder: {test_folder}")

        # Step 2: Copy the newly generated test file into the 'generated-tests' folder
        destination_file = os.path.join(self.swebench_folder, 'generated-tests', 'new_tests.py')
        try:
            shutil.copy(self.new_test_file_path, destination_file)
            self.logger.info(f"Copied '{self.new_test_file_path}' to '{destination_file}'")
        except IOError as e:
            self.logger.error(f"Failed to copy '{self.new_test_file_path}' to '{destination_file}': {e}")
            return

        # Step 3: Run the tests in Docker using pytest
        docker_command = [
            "python", "run_tests_in_docker.py",
            #"pytest-dev__pytest-5227",
            #"django__django-15996",
            "sphinx-doc__sphinx-8721",
            "--files_folder", test_folder,
            "--pytest_params", "collect-only --disable-warnings --json-report" # collect-only --disable-warnings --json-report
        ]
        self.logger.info(f"Running tests with command: {' '.join(docker_command)}")
        try:
            subprocess.run(docker_command, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Test execution failed with error: {e}")
            return

        # Step 4: Check the .report.json for any compilation errors
        test_folder = "/Users/nashid/repos/issue-to-test/test_execution/SWE-bench/"
        report_file_path = os.path.join(test_folder, ".report.json")
        if not os.path.exists(report_file_path):
            self.logger.error(f"Report file not found at {report_file_path}")
            return

        with open(report_file_path, "r") as report_file:
            report_data = json.load(report_file)

        # Step 5: Analyze the outcome for compilation errors
        json_output = report_data
        compilation_error_found, compilation_error_message = detect_compilation_error(json_output)

        #compilation_error_found = False
        #compilation_error_message = None
        #for collector in report_data.get("collectors", []):
        #    if collector["outcome"] == "failed" and not collector["result"]:
        #        compilation_error_message = collector.get('longrepr', 'No additional information provided.')
        #        self.logger.error(
        #            f"Compilation error detected during collection phase in {collector.get('nodeid', 'unknown file')}")
        #        self.logger.debug(f"Detailed error: {collector.get('longrepr', 'No additional information provided.')}")
        #        compilation_error_found = True
        #        break

        if compilation_error_found:
            self.logger.error("Compilation error detected and logged. Compilation error message:",
                              compilation_error_message)
            return compilation_error_found, compilation_error_message
        else:
            self.logger.info("No compilation errors found. Test execution proceeded as expected.")
            return compilation_error_found, compilation_error_message

    def save_test_code_to_new_file(self, generated_code, output_file_name):
        """Save the generated test code to a specified file."""
        try:
            with open(output_file_name, 'w') as patch_file:
                patch_file.write(strip_code_block(generated_code))
            self.logger.info(f"New test code saved successfully in {output_file_name}")
        except IOError as e:
            self.logger.error(f"Failed to save new test code file: {e}")


def handle_compilation_failure_feedback_loop(test_generator, max_attempts=3):
    """
    Handles compilation failure by attempting to fix the issues iteratively.

    Args:
        test_generator: The instance of UnitTestGeneratorCompilationFailure.
        max_attempts: Maximum number of attempts to fix the compilation error.

    Returns:
        bool: True if the compilation error was resolved, False otherwise.
    """
    #new_test_file_path = test_generator.new_test_file_path  # Start with the initial test file path
    new_test_file_path = "new_tests.py"
    previous_error_message = None

    for attempt in range(1, max_attempts + 1):
        new_test_file_path = test_generator.new_test_file_path
        test_generator.logger.info(f"Compilation attempt {attempt}/{max_attempts}.")

        # Run the test and capture any compilation error message
        compilation_error_found, compilation_error_message = test_generator.run_test_and_handle_compilation_error(new_test_file_path)

        if compilation_error_found:
            # Log the error message
            test_generator.logger.error(
                f"Compilation error encountered on attempt {attempt}:\n{compilation_error_message}")

            # Compare with the previous error message to see if we're stuck on the same issue
            if compilation_error_message == previous_error_message:
                test_generator.logger.warning(
                    f"Same compilation error encountered on attempt {attempt}. The issue may not be solvable with automatic retries."
                )
                continue  # Proceed to the next attempt

            # Modify the prompt to fix the error based on the error message
            test_generator.prompt = test_generator.build_prompt(compilation_error_message=compilation_error_message)

            # Generate a new test based on the updated prompt
            generated_tests_dict = test_generator.generate_tests(max_tokens=4096)
            generated_code = strip_code_block(generated_tests_dict[0])

            # Save the regenerated code to a new test file with a generic name
            output_file_name = f"{test_generator.swebench_folder}/new_tests_attempt_{attempt}.py"
            test_generator.save_test_code_to_new_file(generated_code, output_file_name)

            # Update the new test file path for the next attempt
            test_generator.new_test_file_path = output_file_name

            # Update the previous error message
            previous_error_message = compilation_error_message
        else:
            test_generator.logger.info("Compilation errors resolved.")
            return True

    test_generator.logger.error("Maximum attempts to resolve compilation errors were reached without success.")
    return False


def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Parameters (these would be set according to your specific use case)

    # pytest-dev__pytest-6116
    source_code_file = "../../workspace/pytest-dev__pytest-6116/pytest/src/_pytest/main.py"
    test_code_file = "../../workspace/pytest-dev__pytest-6116/pytest/testing/test_collection.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/pytest-dev__pytest-6116.py"


    # pytest-dev__pytest-5692
    source_code_file = "../../workspace/pytest-dev__pytest-5692/pytest/src/_pytest/junitxml.py"
    test_code_file = "../../workspace/pytest-dev__pytest-5692/pytest/testing/test_junitxml.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/pytest-dev__pytest-5692.py"


    # pytest-dev__pytest-5227.py
    source_code_file = "../../workspace/pytest-dev__pytest-5227/pytest/src/_pytest/logging.py"
    test_code_file = "../../workspace/pytest-dev__pytest-5227/pytest/testing/logging/test_reporting.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/pytest-dev__pytest-5692.py"

    # django__django-15996
    source_code_file = "../../workspace/django__django-15996/django/django/db/migrations/serializer.py"
    test_code_file = "../../workspace/django__django-15996/django/tests/migrations/test_writer.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/django__django-15996.py"

    # django__django-15996
    source_code_file = "../../workspace/django__django-11583/django/django/utils/autoreload.py"
    test_code_file = "../../workspace/django__django-11583/django/tests/utils_tests/test_autoreload.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/django__django-11583.py"

    # pydata__xarray-3364
    source_code_file = "../../workspace/django__django-11583/django/django/utils/autoreload.py"
    test_code_file = "../../workspace/django__django-11583/django/tests/utils_tests/test_autoreload.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/django__django-11583.py"


    # sphinx-doc__sphinx-8721
    source_code_file = "../../workspace/sphinx-doc__sphinx-8721/sphinx/sphinx/ext/viewcode.py"
    test_code_file = "../../workspace/sphinx-doc__sphinx-8721/sphinx/tests/test_ext_viewcode.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/sphinx-doc__sphinx-8721.py"


    # scikit-learn__scikit-learn-13439
    source_code_file = "../../workspace/scikit-learn__scikit-learn-13439/scikit-learn/sklearn/pipeline.py"
    test_code_file = "../../workspace/scikit-learn__scikit-learn-13439/scikit-learn/sklearn/tests/test_pipeline.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/scikit-learn__scikit-learn-13439.py"



    # sympy__sympy-18189
    source_code_file = "../../workspace/sympy__sympy-18189/sympy/sympy/solvers/diophantine.py"
    test_code_file = "../../workspace/sympy__sympy-18189/sympy/sympy/solvers/tests/test_diophantine.py"
    new_test_file_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/sympy__sympy-18189.py"




    test_execution_command = "pytest --json-report"
    llm_model = "gpt-4o"
    test_code_command_dir = "/Users/nashid/repos/issue-to-test/test_execution/SWE-bench"



    # Instantiate and run the test generator with error handling
    test_generator = UnitTestGeneratorCompilationFailure(
        source_code_file=source_code_file,
        test_code_file=test_code_file,
        new_test_file_path=new_test_file_path,
        test_execution_command=test_execution_command,
        llm_model=llm_model,
        test_code_command_dir=test_code_command_dir,
        swebench_folder="/Users/nashid/repos/issue-to-test/test_execution/SWE-bench"
    )

    # test_generator.run_test_and_handle_compilation_error()
    success = handle_compilation_failure_feedback_loop(test_generator, max_attempts=3)
    if success:
        print("Compilation errors resolved successfully.")
    else:
        print("Failed to resolve compilation errors.")


if __name__ == "__main__":
    main()
