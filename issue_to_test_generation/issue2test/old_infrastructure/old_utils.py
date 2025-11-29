import os
import json
import logging

#import config
from feedback_guided_test_gen import config

from old_docker_test_runner import DockerTestRunner
import re

swebench_path = config.SWE_BENCH_DOCKER_PATH


def create_trajectory_folder(github_issue, workspace_path):
    """
    Create a folder for storing test generation results inside the issue's workspace.
    The folder is named using the issue ID and placed inside the workspace.
    """
    issue_id = github_issue['instance_id']  # Use the issue_id as part of the folder name
    reports_folder = os.path.join(workspace_path, "reports")
    os.makedirs(reports_folder, exist_ok=True)  # Create the reports folder inside the workspace if it doesn't exist
    return reports_folder


def save_iteration_data(iteration_folder, iteration, prompt_input, prompt_output):
    """
    Save the LLM inputs and outputs for each iteration.

    Args:
        iteration_folder (str): The folder to save the iteration data.
        iteration (int): The current iteration number.
        prompt_input (str): The input prompt passed to the LLM.
        prompt_output (tuple): A tuple containing the LLM response and additional metadata.

    Returns:
        str: Path to the iteration folder where the data is saved.
    """
    # Unpack the tuple
    llm_response = prompt_output[0]
    input_tokens = prompt_output[1]
    response_tokens = prompt_output[2]

    # Create a folder for this iteration
    #iteration_folder = os.path.join(trajectory_folder, f"step_{iteration}")
    #os.makedirs(iteration_folder, exist_ok=True)

    # Save the input prompt
    input_file = os.path.join(iteration_folder, "prompt_input.txt")
    with open(input_file, 'w') as f:
        f.write(prompt_input)

    # Save the output response (test case)
    output_file = os.path.join(iteration_folder, "prompt_output.txt")
    with open(output_file, 'w') as f:
        f.write(llm_response)

    # Save the metadata (token usage)
    metadata_file = os.path.join(iteration_folder, "metadata.txt")
    with open(metadata_file, 'w') as f:
        f.write(f"Input Tokens: {input_tokens}\n")
        f.write(f"Response Tokens: {response_tokens}\n")

    logging.info(f"Iteration {iteration} data saved in {iteration_folder}")

    return iteration_folder


def save_iteration_data_for_step(trajectory_folder, step, prompt_input, prompt_output):
    """
    Save the LLM inputs and outputs for each iteration.

    Args:
        trajectory_folder (str): The folder to save the iteration data.
        iteration (int): The current iteration number.
        prompt_input (str): The input prompt passed to the LLM.
        prompt_output (tuple): A tuple containing the LLM response and additional metadata.

    Returns:
        str: Path to the iteration folder where the data is saved.
    """
    # Unpack the tuple
    llm_response = prompt_output[0]
    input_tokens = prompt_output[1]
    response_tokens = prompt_output[2]

    # Create a folder for this iteration
    iteration_folder = os.path.join(trajectory_folder, step)
    os.makedirs(iteration_folder, exist_ok=True)

    # Save the input prompt
    input_file = os.path.join(iteration_folder, "prompt_input.txt")
    with open(input_file, 'w') as f:
        f.write(prompt_input)

    # Save the output response (test case)
    output_file = os.path.join(iteration_folder, "prompt_output.txt")
    with open(output_file, 'w') as f:
        f.write(llm_response)

    # Save the metadata (token usage)
    metadata_file = os.path.join(iteration_folder, "metadata.txt")
    with open(metadata_file, 'w') as f:
        f.write(f"Input Tokens: {input_tokens}\n")
        f.write(f"Response Tokens: {response_tokens}\n")

    logging.info(f"Iteration {step} data saved in {iteration_folder}")

    return iteration_folder


def save_iteration_data_for_step_tool(trajectory_folder, step, tool):
    """
    Save the LLM inputs and outputs for each iteration.

    Args:
        trajectory_folder (str): The folder to save the iteration data.
        iteration (int): The current iteration number.
        prompt_input (str): The input prompt passed to the LLM.
        prompt_output (tuple): A tuple containing the LLM response and additional metadata.

    Returns:
        str: Path to the iteration folder where the data is saved.
    """
    # Create a folder for this iteration
    iteration_folder = os.path.join(trajectory_folder, step)
    os.makedirs(iteration_folder, exist_ok=True)

    logging.info(f"Iteration {step} data saved in {iteration_folder}")

    return iteration_folder


def create_final_status_file(trajectory_folder, status_data):
    """Create a final status JSON file summarizing the execution."""
    status_file = os.path.join(trajectory_folder, "status.json")
    full_status_file_path = os.path.abspath(status_file)  # Get the fully qualified file path

    with open(full_status_file_path, 'w') as f:
        json.dump(status_data, f, indent=4)

    logging.info(f"Final status saved in {full_status_file_path}")


def extract_code_block(text: str) -> str:
    """
    Extracts only the code content from a code block enclosed by ```python or ``` markers.

    Args:
        text (str): The input text containing code blocks and explanations.

    Returns:
        str: The content of the first code block found, without markers or additional text.
    """
    # Regex pattern to capture code between ```python and ```
    pattern = r"```(?:python)?\n(.*?)\n```"

    # Find the first code block match
    match = re.search(pattern, text, re.DOTALL)

    # If a match is found, return the stripped code content; otherwise, return an empty string
    return match.group(1).strip() if match else ""


def strip_code_block(code: str) -> str:
    """Strip the ```python and ``` markers from a code block."""
    lines = code.splitlines()
    stripped_lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(stripped_lines)


def parse_json_with_markers(json_string: str) -> dict:
    """
    Parse a JSON string that may be wrapped with ```json or ``` markers.

    Args:
        json_string (str): The JSON string, possibly wrapped in code block markers.

    Returns:
        dict: Parsed JSON data.
    """
    # Strip the code block markers
    cleaned_json_string = strip_code_block(json_string)

    # Parse the cleaned JSON string
    try:
        parsed_data = json.loads(cleaned_json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")

    return parsed_data


def run_test_in_docker(test_case_generator, generated_tests_folder, new_test_file_path):
    """
    Run the test case in a Docker container and check the results.

    Args:
        test_case_generator (TestCaseGenerator): The generator responsible for generating test cases.
        generated_tests_folder (str): The path where generated tests are stored.
        new_test_file_path (str): The path to the newly generated test file.

    Returns:
        tuple: (test_failures, result_content), indicating whether there are test failures and the test results.
    """
    # Step 1: Create paths.lst in the generated_tests folder
    original_test_file_path = test_case_generator.test_code_file
    relative_test_folder = os.path.dirname(original_test_file_path)
    relative_new_test_file_path = os.path.join(relative_test_folder, 'test_new.py')

    paths_lst_content = f"test_new.py {relative_new_test_file_path}\n"

    paths_lst_path = os.path.join(generated_tests_folder, "paths.lst")
    with open(paths_lst_path, 'w') as f:
        f.write(paths_lst_content)
        logging.info(f"Created paths.lst file with content: {paths_lst_content}")

    # Step 2: Run the tests in Docker
    issue_id = test_case_generator.github_issue_id
    docker_runner = DockerTestRunner(swebench_path, new_test_file_path, issue_id)
    docker_runner.run_tests_in_docker(generated_tests_folder)

    # Step 3: Check test results from the Docker output
    test_failures, result_content = docker_runner.check_test_results(generated_tests_folder)

    return test_failures, result_content
