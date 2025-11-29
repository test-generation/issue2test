import os
import ast
import importlib
from difflib import get_close_matches


def get_project_structure(root_dir):
    project_structure = {}

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                module_name = os.path.relpath(filepath, root_dir).replace(os.sep, '.').replace('.py', '')
                project_structure[module_name] = extract_definitions(filepath)

    return project_structure


def extract_definitions(filepath):
    try:
        with open(filepath, 'r', encoding='unicode_escape') as file:
            node = ast.parse(file.read(), filename=filepath)
    except Exception as e:
        # print(str(e))
        return {'classes': [], 'functions': []}

    definitions = {'classes': [], 'functions': []}

    for n in node.body:
        if isinstance(n, ast.ClassDef):
            definitions['classes'].append(n.name)
        elif isinstance(n, ast.FunctionDef):
            definitions['functions'].append(n.name)

    return definitions


def check_import(import_path):
    """Try to import a module and return if it is valid or not."""
    try:
        importlib.import_module(import_path)
        return True
    except ImportError:
        return False


def find_closest_matches(import_name, project_structure):
    possible_modules = list(project_structure.keys())
    suggestions = get_close_matches(import_name, possible_modules, n=3, cutoff=0.6)
    return suggestions


def suggest_fixes_for_import(import_statement, project_structure):
    """Suggest possible fixes for the provided import statement."""
    if check_import(import_statement):
        print(f"'{import_statement}' is a valid import.")
    else:
        print(f"'{import_statement}' is not a valid import.")
        suggestions = find_closest_matches(import_statement, project_structure)
        if suggestions:
            print("Did you mean one of these?")
            for suggestion in suggestions:
                print(f"  - {suggestion}")
        else:
            print("No close matches found in the project structure.")


def analyze_project_for_import(root_dir, import_statement):
    project_structure = get_project_structure(root_dir)

    print("\n[INFO] Project structure scanned.\n")

    for module, definitions in project_structure.items():
        print(f"Module: {module}")
        if definitions['classes']:
            print(f"  Classes: {', '.join(definitions['classes'])}")
        if definitions['functions']:
            print(f"  Functions: {', '.join(definitions['functions'])}")
        print()

    print(f"\n[INFO] Checking the provided import statement: '{import_statement}'")
    suggest_fixes_for_import(import_statement, project_structure)


# --- Usage ---
if __name__ == "__main__":
    # project_root = input("Enter the path to your project root: ").strip()
    # import_statement = input("Enter the import statement to check (e.g., 'django.models.db.Query'): ").strip()

    project_root = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/feedback_guided_test_gen/workspace/pylint-dev__pylint-7080/a62b3ea9-e8a7-4013-a2c5-2951cd30e505/pylint/pylint/"
    # import_statement = "pylint.reporters.text"
    # import_statement = "pylint.lint.pylinter"
    import_statement = "sklearn.utils._testing"
    analyze_project_for_import(project_root, import_statement)

    print("\n[INFO] Analysis completed.")
