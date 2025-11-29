import logging
# from issue2test_logger import LanceLogger
from lance_logger import LanceLogger
from config_loader import get_settings
from templates import ADDITIONAL_INCLUDES_TEXT, ADDITIONAL_INSTRUCTIONS_TEXT, FAILED_TESTS_TEXT
from jinja2 import Environment, StrictUndefined

from common_helpers import read_file

MAX_TESTS_PER_RUN = 4


class PromptBuilder:

    def __init__(self,
                 source_code_file: str,
                 test_code_file: str,
                 code_coverage_report: str,
                 included_files: str = "",
                 additional_instructions: str = "",
                 failed_test_runs: str = "",
                 language: str = "python",
                 github_issue:str = "",
                 hints_text:str = ""):
        self.source_file_name = source_code_file.split("/")[-1]
        self.test_file_name = test_code_file.split("/")[-1]
        self.source_file = read_file(source_code_file)
        self.test_file = read_file(test_code_file)
        self.code_coverage_report = code_coverage_report
        self.language = language
        self.github_issue = github_issue
        self.hints_text = hints_text

        self.logger = LanceLogger.initialize_logger(__name__)

        # add line numbers to each line in 'source_file'. start from 1
        self.source_file_numbered = "\n".join(
            [f"{i + 1} {line}" for i, line in enumerate(self.source_file.split("\n"))]
        )
        self.test_file_numbered = "\n".join(
            [f"{i + 1} {line}" for i, line in enumerate(self.test_file.split("\n"))]
        )

        # Conditionally fill in optional sections
        self.included_files = (
            ADDITIONAL_INCLUDES_TEXT.format(included_files=included_files)
            if included_files
            else ""
        )
        self.additional_instructions = (
            ADDITIONAL_INSTRUCTIONS_TEXT.format(
                additional_instructions=additional_instructions
            )
            if additional_instructions
            else ""
        )
        self.failed_test_runs = (
            FAILED_TESTS_TEXT.format(failed_test_runs=failed_test_runs)
            if failed_test_runs
            else ""
        )

    def build_prompt(self) -> dict:
        """
        Replaces placeholders with the actual content of files read during initialization, and returns the formatted prompt.

        Parameters:
            None

        Returns:
            str: The formatted prompt string.
        """
        variables = {
            "source_file_name": self.source_file_name,
            "test_file_name": self.test_file_name,
            "source_file_numbered": self.source_file_numbered,
            "test_file_numbered": self.test_file_numbered,
            "source_file": self.source_file,
            "test_file": self.test_file,
            "code_coverage_report": self.code_coverage_report,
            "additional_includes_section": self.included_files,
            "failed_tests_section": self.failed_test_runs,
            "additional_instructions_text": self.additional_instructions,
            "language": self.language,
            "max_tests": MAX_TESTS_PER_RUN,
            "github_issue": self.github_issue,
            "hints_text": self.hints_text,
        }
        environment = Environment(undefined=StrictUndefined)
        try:
            system_prompt = environment.from_string(
                get_settings().test_generation_prompt_github_issue.system
            ).render(variables)
            user_prompt = environment.from_string(
                get_settings().test_generation_prompt_github_issue.user
            ).render(variables)

            self.logger.info(f"system_prompt: {system_prompt}")
            self.logger.info(f"user_prompt: {user_prompt}")
        except Exception as e:
            logging.error(f"Error rendering prompt: {e}")
            return {"system": "", "user": ""}

        # print(f"#### user_prompt:\n\n{user_prompt}")
        return {"system": system_prompt, "user": user_prompt}

    def build_prompt_custom(self, file) -> dict:
        variables = {
            "source_file_name": self.source_file_name,
            "test_file_name": self.test_file_name,
            "source_file_numbered": self.source_file_numbered,
            "test_file_numbered": self.test_file_numbered,
            "source_file": self.source_file,
            "test_file": self.test_file,
            "code_coverage_report": self.code_coverage_report,
            "additional_includes_section": self.included_files,
            "failed_tests_section": self.failed_test_runs,
            "additional_instructions_text": self.additional_instructions,
            "language": self.language,
            "max_tests": MAX_TESTS_PER_RUN,
        }
        environment = Environment(undefined=StrictUndefined)
        try:
            system_prompt = environment.from_string(
                get_settings().get(file).system
            ).render(variables)
            user_prompt = environment.from_string(get_settings().get(file).user).render(
                variables
            )
        except Exception as e:
            logging.error(f"Error rendering prompt: {e}")
            return {"system": "", "user": ""}

        return {"system": system_prompt, "user": user_prompt}


    def feedback_loop_for_compilation_error(self):
        """
        Handle the feedback loop when a compilation error is detected.
        """
        self.logger.info("Applying feedback loop to fix compilation error.")
        # You could re-generate tests, modify the imports, or log additional information.
        # Here, we'll just log the issue and perhaps modify the test generation prompt.
        new_prompt = f"Fix the compilation error related to imports in the test: {self.test_code_file}"
        self.logger.info(f"New prompt for LLM: {new_prompt}")
        response, _, _ = self.llm_invoker.call_model(prompt=new_prompt)
        self.logger.info(f"LLM Response: {response}")
        # Optionally, you can try to apply the suggested fix from LLM to the test file.

