# issue2test/locate/locate_test_files_with_llm.py

import logging
from issue2test.locate.locate import Locate
from issue2test.util.preprocess_data import show_project_structure
from issue2test.util.llm_invocations import create_chatgpt_config, num_tokens_from_messages, request_chatgpt_engine

class LLMLocateTestFiles(Locate):
    obtain_relevant_test_files_prompt = """
Please look through the following GitHub problem description and Repository structure and provide a list of test files where one would need to add new tests to validate the fix for the problem.

### GitHub Problem Description ###
{problem_statement}

###

### Repository Structure ###
{structure}

###

Please only provide the full path and return at most 5 test files.
The returned files should be separated by new lines ordered by most to least important and wrapped with ```
For example:
```
test_file1.py
test_file2.py
```
"""

    def __init__(self, instance_id, structure, problem_statement, **kwargs):
        super().__init__(instance_id, structure, problem_statement)
        self.max_tokens = 300

    def _parse_model_return_lines(self, content: str) -> list[str]:
        return content.strip().split("\n")

    def localize(self, top_n=1, mock=False) -> tuple[list, list, list, any]:
        return self.localize_test_files(self, top_n, mock)

    def localize_test_files(self, top_n=1, mock=False) -> tuple[list, list, list, any]:
        """Identify the test files in the repository where new tests should be added to validate the fix"""
        found_test_files = []

        message = self.obtain_relevant_test_files_prompt.format(
            problem_statement=self.problem_statement,
            structure=show_project_structure(self.structure).strip(),
        ).strip()

        print(f"prompting with message:\n{message}")
        print("=" * 80)

        if mock:
            traj = {
                "prompt": message,
                "usage": {
                    "prompt_tokens": num_tokens_from_messages(message, "gpt-4o-2024-08-06"),
                },
            }
            return [], {"raw_output_loc": ""}, traj

        config = create_chatgpt_config(
            message=message,
            max_tokens=self.max_tokens,
            temperature=0,
            batch_size=1,
            model="gpt-4o-2024-08-06",
        )
        ret = request_chatgpt_engine(config)
        raw_output = ret.choices[0].message.content
        traj = {
            "prompt": message,
            "response": raw_output,
            "usage": {
                "prompt_tokens": ret.usage.prompt_tokens,
                "completion_tokens": ret.usage.completion_tokens,
            },
        }
        model_found_test_files = self._parse_model_return_lines(raw_output)

        # Assuming we have a way to get all the test files in the project structure
        test_files = [file for file in show_project_structure(self.structure) if 'test' in file.lower()]

        for test_file in test_files:
            if test_file in model_found_test_files:
                found_test_files.append(test_file)

        # sort based on order of appearance in model_found_test_files
        found_test_files = sorted(found_test_files, key=lambda x: model_found_test_files.index(x))

        print(raw_output)

        return found_test_files, {"raw_output_test_files": raw_output}, traj

