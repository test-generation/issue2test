import os
import ast

def search_test_files(directory, keywords):
    matches = []

    # Walk through the directory and subdirectories
    for root, _, files in os.walk(directory):
        for file in files:
            # Check if the file name itself contains any of the keywords
            if any(keyword in file for keyword in keywords) and file.endswith('.py') and (file.startswith('test_') or file.endswith('_test.py')):
                file_path = os.path.join(root, file)
                matches.append((file_path, 0, [f"File name contains keyword(s)"], 'file name'))

            # Only consider files that appear to be test files
            if file.endswith('.py') and (file.startswith('test_') or file.endswith('_test.py')):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                    # Check for matches in the AST
                    try:
                        tree = ast.parse(''.join(lines))
                    except SyntaxError as e:
                        print(f"Syntax error in the file {file_path}: {e}")
                        continue

                    for keyword in keywords:
                        for node in ast.iter_child_nodes(tree):
                            # Check for test functions
                            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_") and keyword in node.name:
                                line_num = node.lineno
                                matches.append((file_path, line_num, lines[line_num-2:line_num+1], 'test function'))
                            # Check for test classes
                            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test") and keyword in node.name:
                                line_num = node.lineno
                                matches.append((file_path, line_num, lines[line_num-2:line_num+1], 'test class'))
                            # Check for variable assignments within test functions and classes
                            elif isinstance(node, ast.Assign):
                                for target in node.targets:
                                    if isinstance(target, ast.Name) and keyword in target.id:
                                        line_num = target.lineno
                                        matches.append((file_path, line_num, lines[line_num-2:line_num+1], 'variable'))
                            # Check for imports that contain the keyword
                            elif isinstance(node, ast.Import):
                                for alias in node.names:
                                    if keyword in alias.name:
                                        line_num = node.lineno
                                        matches.append((file_path, line_num, lines[line_num-2:line_num+1], 'import'))
                            elif isinstance(node, ast.ImportFrom):
                                if node.module and keyword in node.module:
                                    line_num = node.lineno
                                    matches.append((file_path, line_num, lines[line_num-2:line_num+1], 'from import'))

    return matches

def print_matches(matches, max_matches=5):
    count = 0  # Counter to limit matches
    for file_path, line_num, context, match_type in matches:
        if count >= max_matches:  # Stop after max_matches
            break
        print(f"\nMatch found in {file_path} (Line {line_num} - {match_type}):")
        start = line_num - 1
        for c in context:
            if c == "File name contains keyword(s)":
                print(c)
            else:
                print("Line", start, ":", c.strip())  # Strip extra newlines
                start += 1
        print("-" * 40)
        count += 1  # Increment the counter


def format_matches(matches):
    output = []

    for file_path, line_num, context, match_type in matches:
        output.append(f"\nMatch found in {file_path} (Line {line_num} - {match_type}):")
        start = line_num - 1
        for c in context:
            if c ==  "File name contains keyword(s)":
                output.append(c)
            else:
                output.append(f"Line {start} : {c.strip()}")
                start += 1
        output.append("-" * 40)

    return "\n".join(output)


if __name__ == "__main__":
    # Define the directory to search and the keywords
    # directory_to_search = '/Volumes/nashid-g40/ubc-works/repos/issue-to-test/issue_to_test_generation/issue2test/workspace/django__django-12125/ed9ea2de-12bf-4e36-aef5-dfd8561f45ff/django'
    # keywords = ['AutocompleteJsonView', 'CustomAutocompleteJsonView', 'serialize_result', 'django admin', 'autocomplete', 'results', 'notes', 'MyModelAdmin', 'get_urls', 'test_autocomplete_view', 'admin:myapp_mymodel_autocomplete', 'json response', 'context', 'queryset']

    directory_to_search = '/Users/nashid/repos/issue-to-test/issue_to_test_generation/workspace/sympy__sympy-12419_previous_run_20250228-165314/7927b9d1-5e5c-4a10-a2d5-3ed2af6167d4/sympy'
    keywords = ['pytest']

    # Search for matches and print them
    matches = search_test_files(directory_to_search, keywords)
    print_matches(matches)