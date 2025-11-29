import logging
import re
import yaml

from typing import List


def load_yaml(response_text: str, keys_fix_yaml: List[str] = []) -> dict:
    response_text = response_text.strip().removeprefix("```yaml").rstrip("`")
    try:
        data = yaml.safe_load(response_text)
    except Exception as e:
        logging.info(
            f"Failed to parse AI prediction: {e}. Attempting to fix YAML formatting."
        )
        data = try_fix_yaml(response_text, keys_fix_yaml=keys_fix_yaml)
        if not data:
            logging.info(f"Failed to parse AI prediction after fixing YAML formatting.")
    return data


def try_fix_yaml(response_text: str, keys_fix_yaml: List[str] = []) -> dict:
    """
    Try to correct any YAML formatting issues in the provided response text.

    Parameters:
    response_text (str): The response text that may contain YAML data with potential formatting issues.
    keys_fix_yaml (List[str]): A list of keys that require YAML formatting adjustments (default is an empty list).

    Returns:
    dict: The parsed YAML data after attempting various strategies to correct formatting issues.

    This function employs multiple fallback strategies to correct YAML formatting issues:
    1. Converts lines with specific keys to a multiline format.
    2. Extracts YAML snippets enclosed within ```yaml``` tags.
    3. Removes leading and trailing curly brackets.
    4. Iteratively removes lines from the end to correct formatting.
    5. Uses the 'language:' key as a starting point to extract the YAML content.

    If all strategies fail, an empty dictionary is returned.

    Example:
        try_fix_yaml(response_text, keys_fix_yaml=['key1', 'key2'])
    """
    response_lines = response_text.split("\n")

    # First attempt: convert 'key: value' to 'key: |-\n        value'
    modified_lines = response_lines.copy()
    for idx in range(len(modified_lines)):
        for key in keys_fix_yaml:
            if key in modified_lines[idx] and "|-" not in modified_lines[idx]:
                modified_lines[idx] = modified_lines[idx].replace(
                    f"{key}", f"{key} |-\n        "
                )
    try:
        data = yaml.safe_load("\n".join(modified_lines))
        logging.info("Successfully parsed YAML after converting lines to multiline format.")
        return data
    except yaml.YAMLError:
        pass

    # Second attempt: extract YAML snippet enclosed between ```yaml``` tags
    yaml_snippet = re.search(r"```(yaml)?[\s\S]*?```", response_text)
    if yaml_snippet:
        snippet_text = yaml_snippet.group()
        try:
            data = yaml.safe_load(snippet_text.lstrip("```yaml").rstrip("`"))
            logging.info("Successfully parsed YAML after extracting snippet.")
            return data
        except yaml.YAMLError:
            pass

    # Third attempt: remove leading and trailing curly brackets
    stripped_text = response_text.strip().removeprefix("{").removesuffix("}")
    try:
        data = yaml.safe_load(stripped_text)
        logging.info("Successfully parsed YAML after removing curly brackets.")
        return data
    except yaml.YAMLError:
        pass

    # Fourth attempt: iteratively remove last lines
    for i in range(1, len(response_lines)):
        temp_text = "\n".join(response_lines[:-i])
        try:
            data = yaml.safe_load(temp_text)
            if "language" in data:
                logging.info(f"Successfully parsed YAML after removing {i} lines.")
                return data
        except yaml.YAMLError:
            pass

    # Fifth attempt: use 'language:' key as a starting point
    try:
        start_idx = response_text.find("\nlanguage:")
        if start_idx == -1:
            start_idx = response_text.find("language:")
        last_code_idx = response_text.rfind("test_code:")
        end_idx = response_text.find("\n\n", last_code_idx)
        if end_idx == -1:
            end_idx = len(response_text)
        yaml_text = response_text[start_idx:end_idx].strip()
        try:
            data = yaml.safe_load(yaml_text)
            logging.info("Successfully parsed YAML using 'language:' as a starting point.")
            return data
        except yaml.YAMLError:
            pass
    except Exception:
        pass

    return {}