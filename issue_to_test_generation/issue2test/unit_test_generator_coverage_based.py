import json
import logging
import os

from command_executor import CommandExecutor
from coverage.jacoco_coverage import JacocoCoverage
from coverage.pycov_coverage import PycovCoverage
from error_message_parser import extract_error_message_python
from file_preprocessor import FilePreprocessor
from lance_logger import LanceLogger
#from issue2test_logger import LanceLogger
from llm_invocation import LLMInvocation
from prompt_builder import PromptBuilder
from common_helpers import get_code_language
from yaml_parser_utils import load_yaml


class UnitTestGenerator:
    def __init__(self, source_code_file: str,
                 test_code_file: str,
                 code_coverage_report_path: str,
                 test_execution_command: str,
                 llm_model: str,
                 test_code_command_dir: str = os.getcwd(),
                 included_files: list = None,
                 coverage_type="jacoco",
                 target_coverage: int = 100,
                 additional_instructions: str = ""):
        self.source_code_file = source_code_file
        self.test_code_file = test_code_file
        self.code_coverage_report_path = code_coverage_report_path
        self.test_execution_command = test_execution_command
        self.test_code_command_dir = test_code_command_dir
        self.included_files = self.get_included_files(included_files)
        self.coverage_type = coverage_type
        self.target_coverage = target_coverage
        self.additional_instructions = additional_instructions
        self.language = get_code_language(source_code_file)

        self.llm_invoker = LLMInvocation(model=llm_model)

        self.logger = LanceLogger.initialize_logger(__name__)

        self.preprocessor = FilePreprocessor(self.test_code_file)
        self.failed_test_runs = []

        self.run_coverage()
        self.prompt = self.build_prompt()

    def run_coverage(self):
        """
        run the build/test command and get the baseline coverage
        """
        self.logger.info(f'generate baseline coverage report: "{self.test_execution_command}"')

        stdout, stderr, exit_code, time_of_test_execution_command = CommandExecutor.run_command(
            command=self.test_execution_command, cwd=self.test_code_command_dir
        )

        if exit_code != 0:
            raise RuntimeError(
                f'Fatal: Error running test command. '
                f'make sure this build command is correct: "{self.test_execution_command}"\n'
                f'Exit code: {exit_code}'
                f'\nStdout: {stdout}'
                f'\nStderr: {stderr}'
            )

        # Instantiate Coverage and process the coverage report
        if self.coverage_type == "jacoco":
            coverage_processor = JacocoCoverage(
                file_path=self.code_coverage_report_path,
                src_file_path=self.source_code_file)
        elif self.coverage_type == "pycov":
            coverage_processor = PycovCoverage(
                file_path=self.code_coverage_report_path,
                src_file_path=self.source_code_file)
        else:
            raise ValueError(f"Unsupported coverage type: {self.coverage_type}")

        # Use the process_coverage_report method of Coverage, passing in the time the test command was executed
        try:
            lines_covered, lines_missed, percentage_covered = (
                coverage_processor.process_coverage_report(
                    time_of_test_execution_command=time_of_test_execution_command
                )
            )

            # Process the extracted coverage metrics
            self.current_coverage = percentage_covered
            self.code_coverage_report = f"Lines covered: {lines_covered}\nLines missed: {lines_missed}\nPercentage covered: {round(percentage_covered * 100, 2)}%"
        except AssertionError as error:
            self.logger.error(f"Error in coverage processing: {error}")
            raise
        except (ValueError, NotImplementedError) as e:
            self.logger.warning(f"Error parsing coverage report: {e}")
            with open(self.code_coverage_report_path, "r") as f:
                self.code_coverage_report = f.read()

    @staticmethod
    def get_included_files(included_files):
        if included_files:
            included_files_content = []
            file_names = []
            for file_path in included_files:
                try:
                    with open(file_path, "r") as file:
                        included_files_content.append(file.read())
                        file_names.append(file_path)
                except IOError as e:
                    print(f"Error reading file {file_path}: {str(e)}")
                    logging.error(f"Error reading file {file_path}: {str(e)}")

            out_str = ""
            if included_files_content:
                for i, content in enumerate(included_files_content):
                    out_str += f"file_path: `{file_names[i]}`\ncontent:\n```\n{content}\n```\n"

            return out_str.strip()
        return ""

    def build_prompt(self):
        """
        Returns:
            str: prompt that will be used for generating new tests
        """
        # Check for existence of failed tests:
        if not self.failed_test_runs:
            failed_test_runs_value = ""
        else:
            failed_test_runs_value = ""
            try:
                for failed_test in self.failed_test_runs:
                    failed_test_dict = failed_test.get("code", {})
                    if not failed_test_dict:
                        continue
                    # dump dict to str
                    code = json.dumps(failed_test_dict)
                    if "error_message" in failed_test:
                        error_message = failed_test["error_message"]
                    else:
                        error_message = None
                    failed_test_runs_value += f"Failed Test:\n```\n{code}\n```\n"
                    if error_message:
                        failed_test_runs_value += (f"Error message for test above:\n{error_message}\n\n\n")
                    else:
                        failed_test_runs_value += "\n\n"
            except Exception as e:
                self.logger.error(f"Error processing failed test runs: {e}")
                failed_test_runs_value = ""
        self.failed_test_runs = ([])

        self.prompt_builder = PromptBuilder(
            source_code_file=self.source_code_file,
            test_code_file=self.test_code_file,
            code_coverage_report=self.code_coverage_report,
            included_files=self.included_files,
            additional_instructions=self.additional_instructions,
            failed_test_runs=failed_test_runs_value,
            language=self.language,
        )

        return self.prompt_builder.build_prompt()

    def initial_test_suite_analysis(self):
        """
        Simple implementation for initial test suite analysis.
        We can move to an approach using AST or string parsing, instead of just using LLM for everything.
        Specifically, when we can use AST to extract the test headers indentation and the relevant line number to insert new tests.
        :return:
        """
        try:
            test_headers_indentation = None
            allowed_attempts = 3
            counter_attempts = 0
            while test_headers_indentation is None and counter_attempts < allowed_attempts:
                prompt_headers_indentation = (
                    self.prompt_builder.build_prompt_custom(
                        file="test_headers_indentation_prompt"
                    )
                )
                response, prompt_token_count, response_token_count = (
                    self.llm_invoker.call_model(prompt=prompt_headers_indentation)
                )
                tests_dict = load_yaml(response)
                test_headers_indentation = tests_dict.get(
                    "test_headers_indentation", None
                )
                counter_attempts += 1

            if test_headers_indentation is None:
                raise Exception("Failed to analyze the test headers indentation")

            relevant_line_number_to_insert_tests_after = None
            relevant_line_number_to_insert_imports_after = None
            allowed_attempts = 3
            counter_attempts = 0
            while not relevant_line_number_to_insert_tests_after and counter_attempts < allowed_attempts:
                prompt_test_insert_line = (
                    self.prompt_builder.build_prompt_custom(
                        file="analyze_suite_test_insert_line"
                    )
                )
                response, prompt_token_count, response_token_count = (
                    self.llm_invoker.call_model(prompt=prompt_test_insert_line)
                )
                tests_dict = load_yaml(response)
                relevant_line_number_to_insert_tests_after = tests_dict.get(
                    "relevant_line_number_to_insert_tests_after", None
                )
                relevant_line_number_to_insert_imports_after = tests_dict.get(
                    "relevant_line_number_to_insert_imports_after", None
                )
                counter_attempts += 1

            if not relevant_line_number_to_insert_tests_after:
                raise Exception(
                    "Failed to analyze the relevant line number to insert new tests"
                )

            self.test_headers_indentation = test_headers_indentation
            self.relevant_line_number_to_insert_tests_after = relevant_line_number_to_insert_tests_after
            self.relevant_line_number_to_insert_imports_after = relevant_line_number_to_insert_imports_after
        except Exception as e:
            self.logger.error(f"Error during initial test suite analysis: {e}")
            raise Exception("Error during initial test suite analysis")

    def generate_tests(self, max_tokens=4096):
        self.prompt = self.build_prompt()
        response, prompt_token_count, response_token_count = (
            self.llm_invoker.call_model(prompt=self.prompt,
                                        max_tokens=max_tokens))
        self.logger.info(f"Total token count for LLM {self.llm_invoker.model}: "
                         f"{prompt_token_count + response_token_count}")
        try:
            tests_dict = load_yaml(response, keys_fix_yaml=["test_code",
                                                            "test_name",
                                                            "test_behavior"], )
            if tests_dict is None:
                return {}
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

    def validate_test(self, generated_test: dict, generated_tests_dict: dict):
        try:
            test_code = generated_test.get("test_code", "").rstrip()
            additional_imports = generated_test.get("new_imports_code", "").strip()
            if additional_imports and additional_imports[0] == '"' and additional_imports[-1] == '"':
                additional_imports = additional_imports.strip('"')

            # check if additional_imports only contains '"':
            if additional_imports and additional_imports == '""':
                additional_imports = ""

            relevant_line_number_to_insert_tests_after = self.relevant_line_number_to_insert_tests_after
            relevant_line_number_to_insert_imports_after = self.relevant_line_number_to_insert_imports_after

            needed_indent = self.test_headers_indentation

            # now we will remove the initial indent of test code, and insert the needed indent
            test_code_indented = test_code
            if needed_indent:
                initial_indent = len(test_code) - len(test_code.lstrip())
                delta_indent = int(needed_indent) - initial_indent
                if delta_indent > 0:
                    test_code_indented = "\n".join(
                        [delta_indent * " " + line for line in test_code.split("\n")]
                    )
            test_code_indented = "\n" + test_code_indented.strip("\n") + "\n"

            if test_code_indented and relevant_line_number_to_insert_tests_after:

                # Try to add the generated test to the relevant section in the original test file
                with open(self.test_code_file, "r") as test_file:
                    original_content = test_file.read()  # Store original content
                original_content_lines = original_content.split("\n")
                test_code_lines = test_code_indented.split("\n")
                processed_test_lines = (
                        original_content_lines[:relevant_line_number_to_insert_tests_after]
                        + test_code_lines
                        + original_content_lines[relevant_line_number_to_insert_tests_after:]
                )

                # additional imports for line 'relevant_line_number_to_insert_imports_after
                processed_test = "\n".join(processed_test_lines)
                if relevant_line_number_to_insert_imports_after and additional_imports and additional_imports not in processed_test:
                    additional_imports_lines = additional_imports.split("\n")
                    processed_test_lines = (
                            processed_test_lines[:relevant_line_number_to_insert_imports_after]
                            + additional_imports_lines
                            + processed_test_lines[relevant_line_number_to_insert_imports_after:]
                    )
                    self.relevant_line_number_to_insert_tests_after += len(
                        additional_imports_lines)

                processed_test = "\n".join(processed_test_lines)

                with open(self.test_code_file, "w") as test_file:
                    test_file.write(processed_test)
                self.logger.info(f"Test added to the test file: {self.test_code_file}")

                # Now try to run the test so that we can check if the newly added test is valid
                self.logger.info(f'Run test with the command: "{self.test_execution_command}"')
                stdout, stderr, exit_code, time_of_test_execution_command = CommandExecutor.run_command(
                    command=self.test_execution_command, cwd=self.test_code_command_dir
                )

                # Now we need to check if we were able to run the test successfully or not
                if exit_code != 0:
                    # As the test failed, we go back to the test file with the original content
                    with open(self.test_code_file, "w") as test_file:
                        test_file.write(original_content)

                    self.logger.info(f"Test generated which has failed")
                    failure_details = {
                        "status": "FAIL",
                        "reason": "Test failed",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": stdout,
                        "test": generated_test,
                    }

                    error_message = extract_error_message_python(failure_details["stdout"])
                    if error_message:
                        logging.error(f"Error message:\n{error_message}")

                    self.failed_test_runs.append(
                        {
                            "code": generated_test,
                            "error_message": error_message
                        }
                    )

                    return failure_details

                # We were able to run the test suite
                # So we now check for the coverage increase
                try:
                    if self.coverage_type == "jacoco":
                        new_coverage_processor = JacocoCoverage(
                            file_path=self.code_coverage_report_path,
                            src_file_path=self.source_code_file
                        )
                    elif self.coverage_type == "pycov":
                        new_coverage_processor = PycovCoverage(
                            file_path=self.code_coverage_report_path,
                            src_file_path=self.source_code_file
                        )
                    else:
                        raise ValueError(f"Unsupported coverage type: {self.coverage_type}")

                    _, _, new_percentage_covered = (
                        new_coverage_processor.process_coverage_report(
                            time_of_test_execution_command=time_of_test_execution_command
                        )
                    )

                    if new_percentage_covered <= self.current_coverage:
                        # If coverage does not increase, we go back by removing
                        # the newly generated test from the test file
                        with open(self.test_code_file, "w") as test_file:
                            test_file.write(original_content)
                        self.logger.info(
                            "Generated test did not increase coverage. So reverting the test file to original state."
                        )

                        failure_details = {
                            "status": "FAIL",
                            "reason": "Coverage did not increase",
                            "exit_code": exit_code,
                            "stderr": stderr,
                            "stdout": stdout,
                            "test": generated_test,
                        }
                        self.failed_test_runs.append(
                            {
                                "code": failure_details["test"],
                                "error_message": "did not increase code coverage",
                            }
                        )

                        return failure_details
                except Exception as e:
                    self.logger.error(f"Error during coverage verification: {e}")
                    with open(self.test_code_file, "w") as test_file:
                        test_file.write(original_content)
                    failure_details = {
                        "status": "FAIL",
                        "reason": "Runtime error",
                        "exit_code": exit_code,
                        "stderr": stderr,
                        "stdout": stdout,
                        "test": generated_test,
                    }
                    self.failed_test_runs.append(
                        {
                            "code": failure_details["test"],
                            "error_message": "coverage verification error",
                        }
                    )
                    return failure_details

                # If the test passes and the coverage increases, we return the test as a successful test
                self.current_coverage = new_percentage_covered
                self.logger.info(
                    f"Test generated which has passed and coverage increased. "
                    f"Now current coverage is: {round(new_percentage_covered * 100, 2)}%"
                )
                return {
                    "status": "PASS",
                    "reason": "",
                    "exit_code": exit_code,
                    "stderr": stderr,
                    "stdout": stdout,
                    "test": generated_test,
                }
        except Exception as e:
            self.logger.error(f"Error validating test: {e}")
            return {
                "status": "FAIL",
                "reason": f"Error validating test: {e}",
                "exit_code": None,
                "stderr": str(e),
                "stdout": "",
                "test": generated_test,
            }
