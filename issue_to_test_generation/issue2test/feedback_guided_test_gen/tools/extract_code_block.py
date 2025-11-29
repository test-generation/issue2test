import re


def extract_code_block(text: str) -> str:
    """
    Extracts the first fenced code block from markdown text, preserving all internal whitespace
    and special characters, while removing any trailing blank lines or spaces.
    """
    # Regex to match a code block with or without a language identifier
    pattern = r"```(?:\w+)?\n(.*?)\n?```"

    # Search for the first code block match
    match = re.search(pattern, text, re.DOTALL)

    # Return the matched content exactly as-is with trailing whitespace removed
    return match.group(1).rstrip() if match else ""
