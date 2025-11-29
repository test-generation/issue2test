import os
import toml
import logging
from jinja2 import Template
import runtime_state_tracking
from feedback_guided_test_gen.utils import save_iteration_data, strip_code_block
# from llm_invocation import LLMInvocation
from feedback_guided_test_gen.llm_invocation import LLMInvocation
from tools.extract_code_block import extract_code_block
import json

class TestCaseGenerator:
    def __init__(self, project,
                 github_issue,
                 source_code_file,
                 test_code_file_full_path,
                 github_issue_description,
                 model,
                 workspace_path,
                 test_code_file,
                 trajectory_folder,
                 configuration,
                 hints_text=""):
        self.project_name = project
        self.github_issue = github_issue
        self.source_code_file = source_code_file
        self.test_code_file_full_path = test_code_file_full_path
        self.github_issue_id = github_issue["instance_id"]
        self.github_issue_description = github_issue_description
        self.test_code_file = test_code_file
        self.configuration = configuration
        self.hints_text = hints_text

        self.meta_prompt_text = ""

        self.model = model
        self.llm_invoker = LLMInvocation(model=model)

        self.logger = logging.getLogger(__name__)

        self.workspace_path = workspace_path
        self.trajectory_folder = trajectory_folder

        # Path to the prompt template
        base_dir = os.path.dirname(__file__)
        self.prompt_template_path = os.path.join(base_dir, 'prompts/test_generation.toml')

        # Load meta-prompting configuration
        self.meta_prompting_enabled = self.configuration["USE_META_PROMPTING"]
        self.meta_prompt_text = ""

        if self.meta_prompting_enabled:
            path_to_issue_to_test = self.configuration["ISSUE_TO_TEST_DIR"]
            path_to_meta_prompt = os.path.join(path_to_issue_to_test,
                                               "..", "unit_test_guidelines",
                                               self.github_issue_id + ".md")
            with open(path_to_meta_prompt, "r", encoding="utf-8") as f:
                self.meta_prompt_text = f.read()

        # Load hypothesis configuration
        self.use_hypothesis = self.configuration.get("USE_HYPOTHESIS", False)
        self.hypothesis_index = self.configuration.get("HYPOTHESIS_INDEX")
        self.hypothesis_text = ""

        if self.use_hypothesis:
            path_to_issue_to_test = self.configuration["ISSUE_TO_TEST_DIR"]
            path_to_hypothesis = os.path.join(path_to_issue_to_test, "..", "hypothesis",
                                              self.github_issue_id + ".json")

            if os.path.exists(path_to_hypothesis):
                with open(path_to_hypothesis, "r", encoding="utf-8") as f:
                    hypotheses = json.load(f)

                if 0 <= self.hypothesis_index < len(hypotheses):
                    selected_hypothesis = hypotheses[self.hypothesis_index]
                    self.hypothesis_text += f"### {selected_hypothesis['title']}\n"
                    for reason in selected_hypothesis["reasons"]:
                        self.hypothesis_text += f"- {reason}\n"
                    self.logger.info(f"Loaded Hypothesis {self.hypothesis_index + 1}: {selected_hypothesis['title']}")
                else:
                    self.logger.warning(f"Invalid hypothesis index: {self.hypothesis_index}. Skipping hypothesis.")
            else:
                self.logger.warning(f"Hypothesis file not found: {path_to_hypothesis}")


    def load_prompt_template(self):
        """Load the test generation prompt template from TOML."""
        with open(self.prompt_template_path, 'r') as f:
            return toml.load(f)

    def build_prompt(self):
        """Builds the LLM prompt using the loaded TOML template and renders it with Jinja2."""
        template_data = self.load_prompt_template()
        user_template = Template(template_data['test_generation_prompt']['user'])

        hints_text = self.github_issue.get("hints_text", "")

        rendered_user_prompt = user_template.render(
            github_issue=self.github_issue_description,
            hints_text=hints_text,
            source_file_numbered=self.get_source_code(),
            test_file_numbered=self.get_test_code(),
            meta_prompting_enabled=self.meta_prompting_enabled,
            meta_prompt_text=self.meta_prompt_text,
            use_hypothesis=self.use_hypothesis,
            hypothesis_text=self.hypothesis_text
        )

        system_prompt = template_data['test_generation_prompt']['system']
        return {"system": system_prompt, "user": rendered_user_prompt}

    def get_numbered_source_code(self):
        """Fetch the source code and add line numbers."""
        with open(self.source_code_file, 'r') as f:
            lines = f.readlines()
        return "\n".join(f"{i + 1}: {line}" for i, line in enumerate(lines))

    def get_source_code(self):
        """
        Fetch the source code from the file and add line numbers.

        Returns:
            str: Source code with line numbers added for easier debugging.
        """
        try:
            with open(self.source_code_file, 'r') as f:  # Open the source code file
                lines = f.readlines()  # Read all lines
        except FileNotFoundError:
            raise FileNotFoundError(f"Source code file {self.source_code_file} not found.")

        # Add line numbers to each line
        numbered_lines = [f"{idx + 1}: {line}" for idx, line in enumerate(lines)]

        # Join the lines into a single string and return
        return ''.join(numbered_lines)

    def get_test_file_content(self):
        """Fetch the content of the test file (if available)."""
        if os.path.exists(self.test_code_file_full_path):
            with open(self.test_code_file_full_path, 'r') as f:
                return f.read()
        return "No existing test file found."

    def get_test_code(self):
        """Fetch the content of the test file (if available) and add line numbers."""
        if os.path.exists(self.test_code_file_full_path):
            with open(self.test_code_file_full_path, 'r') as f:
                lines = f.readlines()
            numbered_lines = [f"{idx + 1}: {line}" for idx, line in enumerate(lines)]
            return ''.join(numbered_lines)
        return "No existing test file found."

    def generate_test(self, generate_test_folder_workspace):
        """Generate a test case using the LLM and save the inputs/outputs."""
        prompt = self.build_prompt()
        self.logger.info(f"Generating test case for iteration {runtime_state_tracking.step_count}...")

        # Call LLM with system and user prompts
        response = self.llm_invoker.call_model(prompt)

        system_prompt, user_prompt = prompt['system'], prompt['user']

        # Save input/output for this iteration
        save_iteration_data(generate_test_folder_workspace, runtime_state_tracking.step_count, user_prompt, response)

        generated_test_code = response[0]
        # return strip_code_block(generated_test_code)
        return extract_code_block(generated_test_code)

    def save_test_case(self, test_code, destination_dir):
        """Save the generated test case."""
        test_file_path = os.path.join(destination_dir, 'test_new.py')
        with open(test_file_path, 'w') as f:
            f.write(test_code)
        self.logger.info(f"Test case saved at {test_file_path}")
        return test_file_path
