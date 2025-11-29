import os
import shutil

from dataset_processing.load_dataset import load_and_filter_issues
from issue2test_logger import LanceLogger
from linter.lint_code import lint_python_content
from unit_test_generator import UnitTestGenerator
from common_helpers import strip_code_block


class Lance:
    def __init__(self, args):
        self.args = args
        self.logger = LanceLogger.initialize_logger(__name__)

        self.issue_id = args.target_id
        self.issue = load_and_filter_issues(args.target_id)
        self.logger.info(f"================ github issue {self.issue['problem_statement']} ================")
        github_issue = self.issue['problem_statement']
        hints_text = self.issue['hints_text']

        self.validate_paths()
        self.duplicate_test_file()

        self.test_gen = UnitTestGenerator(
            source_code_file=args.source_code_file,
            test_code_file=args.test_file_output_path,
            # code_coverage_report_path=args.code_coverage_report_path,
            test_execution_command=args.test_execution_command,
            test_code_command_dir=args.test_code_command_dir,
            included_files=args.included_files,
            # coverage_type=args.coverage_type,
            # target_coverage=args.target_coverage,
            additional_instructions=args.additional_instructions,
            llm_model=args.model,
            github_issue=github_issue,
            hints_text=hints_text,
        )

    def validate_paths(self):
        if not os.path.isfile(self.args.source_code_file):
            raise FileNotFoundError(f"Source file not found at {self.args.source_code_file}")
        if not os.path.isfile(self.args.test_code_file_full_path):
            raise FileNotFoundError(f"Test file not found at {self.args.test_code_file_full_path}")

    def duplicate_test_file(self):
        if self.args.test_file_output_path != "":
            shutil.copy(self.args.test_code_file_full_path, self.args.test_file_output_path)
        else:
            self.args.test_file_output_path = self.args.test_code_file_full_path

    def save_diff_to_file(self, diff_content):
        """Save the Git diff output to a patch file with the GitHub issue name."""
        issue_id = self.issue_id.replace(' ', '_')
        file_name = f"{issue_id}.patch.diff"
        try:
            with open(file_name, 'w') as patch_file:
                patch_file.write(diff_content)
            self.logger.info(f"Patch saved successfully as {file_name}")
        except IOError as e:
            self.logger.error(f"Failed to save patch file: {e}")

    def save_test_code_to_new_file(self, generated_code):
        """Save the Git diff output to a patch file with the GitHub issue name."""
        issue_id = self.issue_id.replace(' ', '_')
        file_name = f"{issue_id}.py"
        try:
            with open(file_name, 'w') as patch_file:
                generated_code = strip_code_block(generated_code)
                patch_file.write(generated_code)
            self.logger.info(f"new test code saved successfully in {file_name}")
        except IOError as e:
            self.logger.error(f"Failed to save new test code file: {e}")

        return file_name


    def run(self):
        iteration_count = 0
        max_iterations = self.args.maximum_iterations or 3

        while iteration_count < max_iterations:
            # Step 1: Generate the tests
            generated_tests_dict = self.test_gen.generate_tests(max_tokens=4096)
            generated_code = generated_tests_dict[0]
            generated_code = strip_code_block(generated_code)

            lint_attempt_count = 0
            max_lint_attempts = 3  # Limit to avoid infinite loops during lint fixing

            while lint_attempt_count < max_lint_attempts:
                # Step 2: Lint the generated code
                lint_passed, lint_output = lint_python_content(generated_code)

                if lint_passed:
                    break  # Exit the linter loop if code passes linting

                # Step 3: If linting fails, attempt to fix the linter errors
                self.logger.warning(f"Linting failed on attempt {lint_attempt_count + 1}. Attempting to fix linter errors...")
                self.logger.debug(f"Linting output:\n{lint_output}")
                generated_code = self.test_gen.fix_linter_errors(generated_code, lint_output)

                lint_attempt_count += 1

            if not lint_passed:
                self.logger.error(f"Maximum linter fixing attempts reached after {lint_attempt_count} tries.")
                iteration_count += 1
                continue  # Skip to the next iteration, regenerating the code

            # Step 4: Save generated code to file for testing
            self.save_test_code_to_new_file(generated_code)

            # Compilation Feedback Loop
            compilation_attempt_count = 0
            max_compilation_attempts = 3

            while compilation_attempt_count < max_compilation_attempts:
                # Step 5: Run the tests and check for compilation errors
                self.logger.info("Running generated tests to check for compilation errors.")
                self.test_gen.run_test_and_handle_compilation_error()

                # Step 6: Verify if the generated tests compiled and executed correctly
                if self.test_gen.check_compilation_error('.report.json'):
                    self.logger.warning(f"Iteration {iteration_count + 1}: Compilation error detected. Regenerating test cases...")
                    iteration_count += 1
                    continue

                # No compilation error found
                self.logger.info("No compilation errors found. Exiting compilation feedback loop.")
                break

            if compilation_attempt_count == max_compilation_attempts:
                self.logger.error("Maximum compilation fixing attempts reached. Failed to resolve compilation errors.")
                iteration_count += 1
                continue

            # Step 7: Double-check relevance using another LLM
            relevance_passed, relevance_feedback = self.check_relevance_with_llm(generated_code)

            if relevance_passed:
                self.save_test_code_to_new_file(generated_code)
                break
            else:
                self.logger.warning(f"Iteration {iteration_count + 1}: Relevance check failed. Regenerating test cases...")
                self.logger.debug(f"Relevance feedback:\n{relevance_feedback}")
                iteration_count += 1

        if iteration_count == max_iterations:
            self.logger.error("Maximum iterations reached. Failed to generate valid and relevant test code.")


    def check_relevance_with_llm(self, code: str) -> tuple[bool, str]:
        """Double-check the generated code for relevance to the GitHub issue using another LLM.

        Args:
            code: The generated Python code to be checked.

        Returns:
            - A tuple containing:
                - A boolean indicating if the code is relevant.
                - A string with detailed feedback on relevance.
        """
        # Placeholder for calling another LLM or API to check relevance
        relevance_passed = True  # Assume it passes for the placeholder
        relevance_feedback = "Relevant to the GitHub issue"  # Placeholder feedback

        # Insert logic here to call the other LLM and determine relevance
        # Example (pseudo-code):
        # response = another_llm.check_relevance(code, github_issue=self.issue['problem_statement'])
        # relevance_passed = response.is_relevant
        # relevance_feedback = response.feedback

        return relevance_passed, relevance_feedback

    def run_old(self):
        iteration_count = 0
        test_results_list = []

        generated_tests_dict = self.test_gen.generate_tests(max_tokens=4096)
        print(generated_tests_dict)

        # self.save_diff_to_file(generated_tests_dict[0])
        self.save_test_code_to_new_file(generated_tests_dict[0])

        # self.test_gen.initial_test_suite_analysis()
        # for generated_test in generated_tests_dict.get("new_tests", []):
        #     test_result = self.test_gen.validate_test(
        #         generated_test, generated_tests_dict
        #     )
        #     test_results_list.append(test_result)

        # while (
        #         self.test_gen.current_coverage < (self.test_gen.target_coverage / 100)
        #         and iteration_count < self.args.maximum_iterations
        # ):
        #     self.logger.info(f"Current Coverage: {round(self.test_gen.current_coverage * 100, 2)}%")
        #     self.logger.info(f"Target Coverage: {self.test_gen.target_coverage}%")
        #
        #     generated_tests_dict = self.test_gen.generate_tests(max_tokens=4096)
        #
        #     for generated_test in generated_tests_dict.get("new_tests", []):
        #         test_result = self.test_gen.validate_test(
        #             generated_test, generated_tests_dict
        #         )
        #         test_results_list.append(test_result)
        #
        #     iteration_count += 1
        #
        #     if self.test_gen.current_coverage < (self.test_gen.target_coverage / 100):
        #         self.test_gen.run_coverage()
        #
        # if self.test_gen.current_coverage >= (self.test_gen.target_coverage / 100):
        #     self.logger.info(
        #         f"Reached above target coverage of {self.test_gen.target_coverage}% "
        #         f"(Current Coverage: {round(self.test_gen.current_coverage * 100, 2)}%) "
        #         f"in {iteration_count} iterations."
        #     )
        # elif iteration_count == self.args.maximum_iterations:
        #     failure_message = (f"Reached maximum iteration limit without achieving desired coverage. "
        #                        f"Current Coverage: {round(self.test_gen.current_coverage * 100, 2)}%")
        #     self.logger.error(failure_message)

        # ReportGenerator.generate_report(test_results_list, self.args.report_filepath)
        # self.logger.info("Report generated successfully at: " + self.args.report_filepath)
