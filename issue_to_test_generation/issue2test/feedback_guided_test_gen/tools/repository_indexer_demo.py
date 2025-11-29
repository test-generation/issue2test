# repository_indexer_demo.py

from repository_indexer import SearchManager


def demo_search_class(search_manager, class_name):
    class_snippets, summary, found = search_manager.search_class(class_name)
    if found:
        print(f"\n[Class Search] Found class '{class_name}':")
        print(class_snippets)
    else:
        print(f"\n[Class Search] Class '{class_name}' not found.")


def demo_search_function(search_manager, function_name):
    function_snippets, summary, found = search_manager.search_method(function_name)
    if found:
        print(f"\n[Function Search] Found function '{function_name}':")
        print(function_snippets)
    else:
        print(f"\n[Function Search] Function '{function_name}' not found.")


def demo_search_function_in_file(search_manager, file_name, function_name):
    function_snippets, summary, found = search_manager.search_method_in_file(function_name, file_name)
    if found:
        print(f"\n[Function in File Search] Found function '{function_name}' in file '{file_name}':")
        print(function_snippets)
    else:
        print(f"\n[Function in File Search] Function '{function_name}' not found in file '{file_name}'.")


def demo_fuzzy_module_search(search_manager, target_module):
    similar_modules = search_manager.fuzzy_module_search(target_module)
    print("\n[Fuzzy Module Search] Similar modules found:")
    for module in similar_modules:
        print(module)


def demo_search_function_in_module(search_manager, module_path, func_name):
    matches = search_manager.search_function_in_module(module_path, func_name)
    print("\n[Function in Module Search] Matches found for the function in the specified module:")
    for file, alias_info, line_range in matches:
        print(f"File: {file}, Usage: {alias_info}, Lines: {line_range}")


def demo_search_code_in_file(search_manager, file_name, code_str):
    code_snippets, summary, found = search_manager.search_code_in_file(code_str, file_name)
    if found:
        print(f"\n[Code Snippet Search] Code snippets containing '{code_str}' in file '{file_name}':")
        print(code_snippets)
    else:
        print(f"\n[Code Snippet Search] No snippets containing '{code_str}' found in file '{file_name}'.")


def demo_search_code_across_project(search_manager, code_str):
    code_snippets, summary, found = search_manager.search_code(code_str)
    if found:
        print(f"\n[Code Snippet Across Project] Code snippets containing '{code_str}' in the project:")
        print(code_snippets)
    else:
        print(f"\n[Code Snippet Across Project] No snippets containing '{code_str}' found in the project.")


def demo_search_import_and_alias_usages(search_manager, symbol_name):
    output, summary, found = search_manager.search_import_and_alias_usages(symbol_name)
    if found:
        print(output)
    else:
        print(f"No imports or aliases found for symbol '{symbol_name}'.")


def main():
    # Path to the root of the project you want to analyze
    # project_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/feedback_guided_test_gen/workspace/scikit-learn__scikit-learn-13142/c61e595c-b807-4be9-a499-5193233f2dd8/scikit-learn"
    # project_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/feedback_guided_test_gen/workspace//scikit-learn__scikit-learn-13142_previous_run_20241111-115746/c61e595c-b807-4be9-a499-5193233f2dd8"
    # project_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/lance/lance/feedback_guided_test_gen/workspace//sympy__sympy-12419"
    project_path = "/Users/nashid/repos/issue-to-test/issue_to_test_generation/workspace/sympy__sympy-12419_previous_run_20250228-165314/7927b9d1-5e5c-4a10-a2d5-3ed2af6167d4/sympy"

    # Instantiate SearchManager with the project path
    search_manager = SearchManager(project_path)

    # Example values; change these for each function call as needed
    # demo_search_class(search_manager, "Symbols")

    # demo_search_function(search_manager, "assert_array_equal")
    # demo_search_function(search_manager, "predict")

    # demo_search_function_in_file(search_manager, "sklearn.mixture", "your_function_name")

    # demo_fuzzy_module_search(search_manager, "sklearn.utils.testing")
    # demo_fuzzy_module_search(search_manager, "sklearn.utils")
    demo_fuzzy_module_search(search_manager, "pytest")

    # Use the new function to search for import and alias usages
    # symbol_name = "assert_array_equal"
    # symbol_name = "symbols"
    # symbol_name = "pytest"
    # demo_search_import_and_alias_usages(search_manager, symbol_name)

    # module_name = "sklearn.utils._testing"
    # output, summary, found = search_manager.search_for_imported_symbol(module_name, symbol_name)
    # if found:
    #     print(output)
    # else:
    #     print("Import not found.")

    # demo_search_function_in_module(search_manager, "sklearn.utils", "assert_array_equal")
    # demo_search_code_in_file(search_manager, "your_module.py", "assert_array_equal")
    # demo_search_code_across_project(search_manager, "assert_array_equal")
    # demo_search_code_across_project(search_manager, "pytest")


if __name__ == "__main__":
    main()
