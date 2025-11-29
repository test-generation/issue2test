from tempfile import NamedTemporaryFile
from typing import TextIO
from pylint.lint import Run
from pylint.reporters.text import TextReporter

class Writable(TextIO):
    "Dummy output stream for pylint"

    def __init__(self) -> None:
        self.content: list[str] = []

    def write(self, s: str) -> int:
        self.content.append(s)
        return len(s)

    def read(self, n: int = 0) -> str:
        return "\n".join(self.content)

def is_clean_lint_python_content(content: str) -> bool:
    """Check if python content lints OK.

    Args:
        content: python file content

    Returns: True if the content passes linting, False otherwise.
    """
    pylint_out = Writable()
    reporter = TextReporter(pylint_out)

    with NamedTemporaryFile(buffering=0) as f:
        f.write(content.encode())

        _ = Run(["--errors-only", f.name], reporter=reporter, exit=False)

    return not any(error.endswith("(syntax-error)") for error in pylint_out.content)

def lint_python_content(content: str) -> tuple[bool, str]:
    """Check if python content lints OK and return detailed linting output.

    Args:
        content: python file content

    Returns:
        - A tuple containing:
            - A boolean indicating if the content passes linting.
            - A string with detailed linting output including errors, warnings, and suggestions.
    """
    pylint_out = Writable()
    reporter = TextReporter(pylint_out)

    with NamedTemporaryFile(buffering=0) as f:
        f.write(content.encode())

        _ = Run([f.name], reporter=reporter, exit=False)

    output = "\n".join(pylint_out.content)
    has_errors = any("error" in line.lower() for line in pylint_out.content)

    return not has_errors, output



# Example usage
if __name__ == "__main__":
    # Sample content to lint
    content = """
def foo():
  print("Hello, world!") d
"""

    if lint_python_content(content):
        print("The code is clean.")
    else:
        print("The code has syntax errors.")



    passed, errors = lint_python_content(content)
    if passed:
        print("The code is clean.")
    else:
        print("The code has syntax errors:\n")
        print(errors)
