# lance/feedback_guided_test_gen.tools/test_output_analyzer.py
import logging
import re
import json
from jinja2 import Template

from common_helpers import load_prompt_template
from feedback_guided_test_gen.utils import extract_code_block
from llm_invocation import LLMInvocation


def detect_pytest_output(file_path):
    """
    Detect if the output file is from pytest by checking for pytest command patterns.

    :param file_path: Path to the output file.
    :return: True if pytest output is detected, False otherwise.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            if line.strip().startswith("+ pytest"):
                return True
    return False


def parse_pytest_summary(file_path):
    """
    Parse the pytest output to extract the short test summary, listing test names and outcomes.
    Falls back to GPT-4o-mini if regex parsing fails or does not find any failed tests.

    :param file_path: Path to the file containing pytest output.
    :return: A dictionary containing parsed test information, including the test file name.
    """
    try:
        # Read and clean the file content
        with open(file_path, 'r') as file:
            output = file.read().strip()

        # Initialize parsed results
        parsed_results = {
            "test_file": file_path,
            "tests": [],
            "summary": None,
        }

        # Locate the short test summary section
        summary_section_match = re.search(r"=+\s*short test summary info\s*=+(.*?)(=+)", output, re.S)
        if summary_section_match:
            summary_section = summary_section_match.group(1).strip()
            parsed_results["summary"] = summary_section

            # Extract test names and outcomes
            test_result_pattern = re.compile(r"(PASSED|FAILED|SKIPPED|ERROR) (\S+)")
            for match in test_result_pattern.finditer(summary_section):
                outcome = match.group(1)
                test_name = match.group(2)
                parsed_results["tests"].append({"name": test_name, "outcome": outcome})

        # Check if any test has a 'FAILED' outcome
        found_failure = False
        for test in parsed_results.get("tests", []):
            if test.get("outcome") == "FAILED":
                found_failure = True
                break

        # If no failures are found, fall back to LLM
        if not found_failure:
            logging.warning("Regex parsing did not find any failures. Using GPT-4o-mini for better extraction...")
            return parse_test_results_with_llm(file_path)

        return parsed_results

    except Exception as e:
        logging.error(f"Regex parsing failed: {e}. Falling back to GPT-4o-mini...")
        return parse_test_results_with_llm(file_path)


def parse_test_results_with_llm(file_path):
    """
    Extract test results from a test log file using GPT-4o-mini (fallback method).

    :param file_path: Path to the test output file.
    :return: Parsed test information as a dictionary.
    """
    with open(file_path, "r") as f:
        test_output = f.read()

    # Load the TOML prompt
    toml_name = "extract_test_results"
    template_data = load_prompt_template(toml_name)

    system_prompt = template_data['extract_test_results']['system']
    user_template = Template(template_data['extract_test_results']['user'])

    # Render the user template with actual values using Jinja2
    rendered_user_prompt = user_template.render(test_output=test_output)

    llm_invocation = LLMInvocation(model="gpt-4o-mini")

    # Call GPT-4o-mini for structured test result extraction
    prompt = {
        "system": system_prompt,
        "user": rendered_user_prompt
    }
    response = llm_invocation.call_model(prompt=prompt)

    if not response or len(response) == 0:
        logging.error(f"❌ LLM returned an empty response for {file_path}")
        return {"tests": [], "has_failures": True}  # Assume failure

    generated_json = response[0]
    response_json = extract_code_block(generated_json).strip()  # Ensure clean JSON

    # Validate JSON before parsing
    if not response_json or response_json == "":
        logging.error(f"❌ LLM returned an empty extracted JSON block for {file_path}")
        logging.error(f"🚨 LLM Raw Output:\n{generated_json}")  # Show full response for debugging
        return {"tests": [], "has_failures": True}  # Assume failure

    try:
        parsed_data = json.loads(response_json)
    except json.JSONDecodeError as e:
        logging.error(f"❌ LLM Response JSON Error for {file_path}: {e}")
        logging.error(f"🚨 LLM Extracted JSON:\n{response_json}")  # Show extracted JSON
        return {"tests": [], "has_failures": True}  # Assume failure

    return parsed_data


def display_parsed_results(parsed_results):
    """
    Display parsed results in pretty JSON format, including the test file path.

    :param parsed_results: Dictionary containing parsed output sections.
    """
    print("\n--- Parsed Test Results ---")
    print(json.dumps(parsed_results, indent=4))


if __name__ == "__main__":
    test_output_path = "./resources/pydata__xarray-4094_test_results.txt"

    # Check if the output is from pytest
    if detect_pytest_output(test_output_path):
        print("Detected pytest output. Parsing short test summary...")
        parsed_results = parse_pytest_summary(test_output_path)

        # Display results in pretty JSON format
        display_parsed_results(parsed_results)
    else:
        print("No pytest output detected in the file.")
