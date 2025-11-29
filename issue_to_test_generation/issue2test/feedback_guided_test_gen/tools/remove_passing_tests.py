import ast
import argparse
import logging
from issue2test.feedback_guided_test_gen.tools.test_output_analyzer import parse_pytest_summary


def remove_passing_tests_ast(test_file_path, pytest_output_path, output_file_path):
    """
    Generate a new test file containing only failing tests based on pytest output, using AST for parsing.

    :param test_file_path: Path to the original test file.
    :param pytest_output_path: Path to the pytest output file containing test results.
    :param output_file_path: Path where the modified test file with only failing tests will be saved.
    """
    # Parse pytest output to get passing test names
    parsed_results = parse_pytest_summary(pytest_output_path)
    passing_tests = {test["name"].split("::")[-1] for test in parsed_results["tests"] if test["outcome"] == "PASSED"}

    # Parse the original test file into an AST
    with open(test_file_path, 'r') as file:
        tree = ast.parse(file.read())

    # Filter out nodes for passing test functions
    new_body = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in passing_tests:
            print(f"Excluding passing test function: {node.name}")
            continue
        new_body.append(node)

    # Update the AST to contain only the desired nodes
    tree.body = new_body

    # Write the modified AST to a new file
    with open(output_file_path, 'w') as file:
        file.write(ast.unparse(tree))

    print(f"New test file with only failing tests saved as: {output_file_path}")


def get_passing_tests_ast(test_file_path, pytest_output_path, output_file_path=None, return_code=False):
    """
    Extract passing tests from a test file based on pytest output, using AST for parsing.
    Optionally returns the test code as a string instead of writing to a file.

    :param test_file_path: Path to the original test file.
    :param pytest_output_path: Path to the pytest output file containing test results.
    :param output_file_path: (Optional) Path where the modified test file with only passing tests will be saved.
    :param return_code: (bool) If True, returns the passing test code as a string instead of writing to a file.
    :return: If return_code=True, returns the passing test code as a string. Otherwise, returns None.
    """
    try:
        # Parse pytest output to get passing test names
        parsed_results = parse_pytest_summary(pytest_output_path)
        passing_tests = {test["name"].split("::")[-1] for test in parsed_results["tests"] if test["outcome"] == "PASSED"}
        logging.info(f"Passing tests extracted: {passing_tests}")

        # Parse the original test file into an AST
        with open(test_file_path, 'r') as file:
            test_code = file.read()
        tree = ast.parse(test_code)

        # Build a new AST containing only passing test functions
        new_body = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # If this is a top-level test function, include it if its name is in passing_tests
                if node.name in passing_tests:
                    logging.info(f"Including passing test function: {node.name}")
                    new_body.append(node)
                else:
                    logging.debug(f"Excluding non-passing test function: {node.name}")
            elif isinstance(node, ast.ClassDef):
                # For classes, include only the methods that are passing tests.
                new_class_body = [
                    subnode for subnode in node.body
                    if isinstance(subnode, ast.FunctionDef) and subnode.name in passing_tests
                ]
                if new_class_body:
                    node.body = new_class_body
                    new_body.append(node)
                    logging.info(f"Including test class {node.name} with {len(new_class_body)} passing methods.")
                else:
                    logging.debug(f"Excluding test class {node.name} as it contains no passing tests.")
            else:
                # Include any other nodes (imports, etc.) as is.
                new_body.append(node)

        # Update the AST with the filtered body
        tree.body = new_body

        # Convert the modified AST back to source code
        new_test_code = ast.unparse(tree)

        # If output_file_path is given, write the modified test cases to a file
        if output_file_path:
            with open(output_file_path, 'w') as file:
                file.write(new_test_code)
            logging.info(f"New test file with only passing tests saved as: {output_file_path}")

        # Return the test code if requested
        if return_code:
            return new_test_code

    except Exception as e:
        logging.error(f"Error in get_passing_tests_ast: {e}")
        raise

    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove passing tests from a test file.")

    parser.add_argument("--test_file_path",
                        help="Path to the original test file.",
                        default="./resources/generated_tests/test_new.py")

    parser.add_argument("--pytest_output_path",
                        help="Path to the pytest output file with test results.",
                        default="./resources/pydata__xarray-4094_test_results.txt")

    parser.add_argument("--output_file_path",
                        help="Path for the new test file with only failing tests.",
                        default="./resources/generated_tests/test_new_failing.py")

    args = parser.parse_args()

    # Run the removal process
    remove_passing_tests_ast(args.test_file_path, args.pytest_output_path, args.output_file_path)


    parser.add_argument("--test_file_path",
                        help="Path to the original test file.",
                        default="./resources/generated_tests/test_new.py")

    parser.add_argument("--pytest_output_path",
                        help="Path to the pytest output file with test results.",
                        default="./resources/pydata__xarray-4094_test_results.txt")

    parser.add_argument("--output_file_path",
                        help="Path for the new test file with only failing tests.",
                        default="./resources/generated_tests/test_new_passing.py")

    args = parser.parse_args()

    # get only the passing tests
    get_passing_tests_ast(args.test_file_path, args.pytest_output_path, args.output_file_path)
