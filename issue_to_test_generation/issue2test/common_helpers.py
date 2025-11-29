import os

from config_loader import get_settings

import toml

from feedback_guided_test_gen.utils import extract_code_block


def _is_python_file(path_to_file) -> bool:
    return path_to_file.endswith(".py")


def _is_java_file(path_to_file) -> bool:
    return path_to_file.endswith(".py")


def read_file(file_path):
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading {file_path}: {e}"


def get_code_language(source_code_file):
    language_extensions_map = get_settings().language_extension

    extension_to_language = {}

    for language, extensions in language_extensions_map.items():
        for ext in extensions:
            extension_to_language[ext] = language

    extension_s = "." + source_code_file.rsplit(".")[-1]

    language_name = "unknown"

    # Check if the extracted file extension is in the dictionary
    if extension_s and (extension_s in extension_to_language):
        # Set the language name based on the file extension
        language_name = extension_to_language[extension_s]

    return language_name.lower()


def strip_code_block(code: str) -> str:
    """Strip the ```python and ``` markers from a code block."""
    #lines = code.splitlines()
    #stripped_lines = [line for line in lines if not line.strip().startswith("```")]
    #return "\n".join(stripped_lines)
    return extract_code_block(code)

def load_prompt_template(toml_name):
    """Load the test generation prompt template from TOML."""
    base_dir = os.path.dirname(__file__)
    toml_name = f"feedback_guided_test_gen/prompts/{toml_name}.toml"
    prompt_template_path = os.path.join(base_dir, toml_name)

    with open(prompt_template_path, 'r') as f:
        return toml.load(f)


def load_prompt_template_add_toml_extension(toml_name):
    """Load the test generation prompt template from TOML."""
    base_dir = os.path.dirname(__file__)
    toml_name = f"feedback_guided_test_gen/prompts/{toml_name}.toml"
    prompt_template_path = os.path.join(base_dir, toml_name)

    with open(prompt_template_path, 'r') as f:
        return toml.load(f)
