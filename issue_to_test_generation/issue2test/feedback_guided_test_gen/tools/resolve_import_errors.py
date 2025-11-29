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
    # Allow up to 5 suggestions, with a cutoff for reasonably close matches
    suggestions = get_close_matches(import_name, possible_modules, n=5, cutoff=0.6)
    return suggestions


def suggest_fixes_for_import(import_statement, project_structure):
    """
    Suggest possible fixes for the provided import statement and return the suggestions.
    Returns multiple suggestions if close matches are found.
    """
    if check_import(import_statement):
        return {'status': 'valid', 'suggestions': []}
    else:
        suggestions = find_closest_matches(import_statement, project_structure)
        return {'status': 'invalid', 'suggestions': suggestions}


def analyze_project_for_import(root_dir, import_statement):
    """
    Analyze the project structure and suggest fixes for the given import statement.

    Returns:
        dict: A summary containing the project structure and import suggestions.
    """
    project_structure = get_project_structure(root_dir)

    # Generate a structured summary of the project structure
    project_summary = {}
    for module, definitions in project_structure.items():
        project_summary[module] = {
            'classes': definitions['classes'],
            'functions': definitions['functions']
        }

    # Check and suggest fixes for the provided import statement
    import_fix_suggestions = suggest_fixes_for_import(import_statement, project_structure)

    # Return results in a structured format
    return {
        'project_root': root_dir,
        'import_statement': import_statement,
        'project_structure': project_summary,
        'import_analysis': {
            'status': import_fix_suggestions['status'],
            'suggestions': import_fix_suggestions['suggestions']
        }
    }


# --- Usage Example ---
if __name__ == "__main__":
    project_root = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/feedback_guided_test_gen/workspace/pylint-dev__pylint-7080/a62b3ea9-e8a7-4013-a2c5-2951cd30e505/pylint/pylint/"
    # import_statement = "pylint.reporters.text"
    # import_statement = "pylint.lint.linter"
    # import_statement = "Run"
    import_statement = "pylint.lint.pylinter"

    results = analyze_project_for_import(project_root, import_statement)

    # Output results for review
    print("\nProject Structure:\n")
    for module, details in results['project_structure'].items():
        print(f"Module: {module}")
        if details['classes']:
            print(f"  Classes: {', '.join(details['classes'])}")
        if details['functions']:
            print(f"  Functions: {', '.join(details['functions'])}")
        print()

    print("\nImport Analysis:\n")
    print(f"Checked Import: {results['import_statement']}")
    print(f"Status: {results['import_analysis']['status']}")
    if results['import_analysis']['suggestions']:
        print("Suggestions:")
        for suggestion in results['import_analysis']['suggestions']:
            print(f"  - {suggestion}")
    else:
        print("No suggestions available.")
