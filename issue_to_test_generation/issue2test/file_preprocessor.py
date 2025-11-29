import ast
import textwrap

from common_helpers import _is_python_file


class FilePreprocessor:
    def __init__(self, path_to_file):
        self.path_to_file = path_to_file
        self.rules = [(_is_python_file, self._process_if_python)]

    def process_file(self, text: str) -> str:
        for condition, action in self.rules:
            if condition():
                return action(text)
        return text

    def _process_if_python(self, text: str) -> str:
        if self.contains_class_definition():
            return textwrap.indent(text, "    ")
        return text

    def contains_class_definition(self) -> bool:
        try:
            with open(self.path_to_file, "r") as file:
                content = file.read()
            parsed_ast = ast.parse(content)
            for node in ast.walk(parsed_ast):
                if isinstance(node, ast.ClassDef):
                    return True
        except SyntaxError as e:
            print(f"Syntax error when parsing the file: {e}")
        return False

