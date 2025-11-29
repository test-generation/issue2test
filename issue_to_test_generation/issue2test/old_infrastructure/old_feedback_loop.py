import logging
import os
import shutil
from pathlib import Path

#import config
from feedback_guided_test_gen import config

#import globals
from feedback_guided_test_gen import globals

from old_docker_test_runner import DockerTestRunner, naive_contains_error
from feedback_guided_test_gen.eval_helper import parse_log_sympy
from tools.remove_passing_tests import remove_passing_tests_ast
from tools.test_failure_analyzer import has_test_failures, has_test_failures_naive
from tools.test_output_analyzer import parse_pytest_summary

SWEBENCH_PATH = config.SWE_BENCH_DOCKER_PATH

def remove_tests_prefix(relative_new_test_file_path):
    """
    Removes the 'tests' prefix from a relative file path using pathlib.

    Args:
        relative_new_test_file_path (str): The relative file path, e.g., "tests/module/test_file.py".

    Returns:
        str: The updated file path without the 'tests/' prefix, e.g., "module/test_file.py".
    """
    path = Path(relative_new_test_file_path)
    # Check if the first part of the path is 'tests'
    if path.parts[0] == "tests":
        return str(Path(*path.parts[1:]))
    return str(path)


def run_feedback_loop(test_case_generator,
                      error_handler,
                      status_data,
                      trajectory_folder,
                      github_issue,
                      search_manager,
                      max_iterations=20,):
    """
    Runs the feedback-guided loop for generating, running, and refining tests.

    Args:
        test_case_generator (TestCaseGenerator): Responsible for generating test cases.
        error_handler (ErrorHandler): Handles errors (e.g., compilation, assertion) during test execution.
        status_data (dict): A dictionary to track iteration statuses and errors.
        max_iterations (int): Maximum number of iterations for refining tests.

    Returns:
        dict: Updated status_data with the final status of the feedback loop execution.
    """
    generated_tests_folder = os.path.join(SWEBENCH_PATH, "generated_tests")

    previous_error_message = None
    error_category, reason, root_cause, repair_steps = "", "", "", ""

    for step_count in range(1, max_iterations + 1):
        try:
            logging.info(f"Starting step {globals.global_step}")
            globals.global_step += 1

            # Create the workspace for generated test code for each step
            iteration_test_workspace = os.path.join(trajectory_folder, f"step_{globals.global_step}-test-gen")
            if not os.path.exists(iteration_test_workspace):
                os.makedirs(iteration_test_workspace, exist_ok=True)

            # Step 1: Generate the test case using LLM
            generated_test_case = test_case_generator.generate_test(iteration_test_workspace)

            iteration_test_file_path = os.path.join(iteration_test_workspace, f"step_{globals.global_step}.py")
            with open(iteration_test_file_path, 'w') as f:
                f.write(generated_test_case)
                logging.info(f"Saved generated test case for step {globals.global_step} to {iteration_test_file_path}")

            # Track this iteration in status_data
            status_data["steps"].append({
                "step": step_count + 1,
                "test_case_generated": True
            })

            # Step 2: Prepare the folder for the generated tests
            if not os.path.exists(generated_tests_folder):
                os.makedirs(generated_tests_folder, exist_ok=True)
                logging.info(f"Created folder {generated_tests_folder}")

            # Save the generated test case in test_new.py for docker execution
            new_test_file_path = os.path.join(generated_tests_folder, "test_new.py")
            with open(new_test_file_path, 'w') as f:
                f.write(generated_test_case)
                logging.info(f"Saved generated test case to {new_test_file_path}")

            # Step 3: Create paths.lst in the generated_tests folder
            original_test_file_path = test_case_generator.test_code_file
            relative_test_folder = os.path.dirname(original_test_file_path)
            relative_new_test_file_path = os.path.join(relative_test_folder, 'test_new.py')
            # relative_new_test_file_path = remove_tests_prefix(relative_new_test_file_path)
            paths_lst_content = f"test_new.py {relative_new_test_file_path}"

            paths_lst_path = os.path.join(generated_tests_folder, "paths.lst")
            with open(paths_lst_path, 'w') as f:
                f.write(paths_lst_content)
                logging.info(f"Created paths.lst file with content: {paths_lst_content}")

            # Step 4: Run the tests in Docker
            issue_id = test_case_generator.github_issue_id
            docker_runner = DockerTestRunner(SWEBENCH_PATH, new_test_file_path, issue_id)
            docker_runner.run_tests_in_docker(generated_tests_folder)

            # Step 5: Check test results from the {issue_id}_test_results.txt file
            test_results_file = os.path.join(SWEBENCH_PATH, f"{issue_id}_test_results.txt")
            parsed_results = parse_pytest_summary(test_results_file)

            # Identify passing and failing tests
            passing_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] == "PASSED"]
            failing_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] == "FAILED"]
            test_failures, results_summary, result_content = docker_runner.check_test_results(generated_tests_folder)
            test_failures = test_failures or naive_contains_error(result_content)

            if test_case_generator.project_name == "sympy":
                test_failures = has_test_failures_naive(result_content)
                # test_status_map = parse_log_sympy(result_content)
                # test_failures = has_test_failures(test_status_map)

            if passing_tests and failing_tests:
                # Remove only the passing tests, keeping failing tests intact
                globals.global_step += 1

                logging.info(f"Some tests passed unexpectedly. Removing passing tests: {passing_tests}")
                step = f"step_{globals.global_step}-test-removal"
                refinement_workspace = os.path.join(trajectory_folder, step)
                if not os.path.exists(refinement_workspace):
                    os.makedirs(refinement_workspace)

                refinement_test_file_path = os.path.join(refinement_workspace, f"step_{globals.global_step}.py")
                remove_passing_tests_ast(new_test_file_path,
                                         test_results_file,
                                         refinement_test_file_path)

                # Now Save the generated test case in test_new.py for docker execution
                new_test_file_path = os.path.join(generated_tests_folder, "test_new.py")
                shutil.copyfile(refinement_test_file_path, new_test_file_path)
                logging.info(f"Saved generated test case for step {step_count} to {new_test_file_path}")

            # once we reach here, we only have test cases which are failing
            is_direct_match = False
            if test_failures:
                logging.info("Test failures detected.")

                # Check if we're stuck on the same error
                if results_summary == previous_error_message:
                    logging.warning("Same error encountered as in the previous iteration.")
                previous_error_message = results_summary

                # Step 6: Categorize the error (via LLM)
                error_category, reason, root_cause, repair_steps = error_handler.categorize_error(result_content, step_count, generated_test_case)

                # Step 6a: Handle Compilation Failure
                if error_category == 'compilation' or error_category == 'runtime':
                    logging.info("Handling compilation error...")

                    is_compilation_fixed, is_assertion_directly_related, fixed_compilation_error_in_test_code = error_handler.handle_compilation_error(
                        test_execution_logs=result_content,
                        source_code=test_case_generator.get_source_code(),
                        test_code=generated_test_case,
                        iteration=step_count,
                        test_case_generator=test_case_generator,
                        generated_tests_folder=generated_tests_folder,
                        new_test_file_path=new_test_file_path,
                        github_issue=test_case_generator.github_issue,
                        search_manager=search_manager,
                        error_category = error_category,
                        reason = reason,
                        root_cause = root_cause,
                        repair_steps = repair_steps
                    )
                    status_data["steps"][-1]["compilation_error"] = is_compilation_fixed
                    status_data["steps"][-1]["compilation_fix"] = fixed_compilation_error_in_test_code

                    generated_test_case = fixed_compilation_error_in_test_code
                    is_direct_match = is_assertion_directly_related
                    if is_compilation_fixed and not is_assertion_directly_related:
                        is_direct_match = False

                    if is_direct_match:
                        break
                    # if compilation error is not fixed, continue to the next iteration
                    if not is_compilation_fixed:
                        continue
                    # else it means compilation is fixed and the test case only has assertion error

                # # Step 6b: Handle Runtime Failure (NEW)
                # elif error_category == 'runtime':
                #     logging.info("Handling runtime error...")
                #     fix = error_handler.handle_runtime_error(result_content,
                #                                              test_case_generator.github_issue_id,
                #                                              test_case_generator.github_issue,
                #                                              step_count)
                #     status_data["iterations"][-1]["runtime_error"] = True
                #     status_data["iterations"][-1]["runtime_fix"] = fix

                # Step 6c: Handle Assertion Failure
                elif error_category == 'assertion':
                    logging.info("Handling assertion error...")
                    is_related_to_issue = error_handler.handle_assertion_error(result_content,
                                                                               test_case_generator.github_issue_id,
                                                                               test_case_generator.github_issue,
                                                                               step_count)
                    is_direct_match = is_related_to_issue.get("is_direct_match", False)
            else:
                logging.info("Generated tests passed unexpectedly given a Github issue. Refining test case until it fails.")
                status = error_handler.refine_test_until_failure(
                    test_case_generator=test_case_generator,
                    test_code=generated_test_case,
                    iteration=step_count,
                    trajectory_folder=trajectory_folder,
                    status_data=status_data,
                    github_issue=test_case_generator.github_issue,
                    source_code=test_case_generator.get_source_code(),
                    search_manager=search_manager
                )
                if status:
                    break


            if is_direct_match:
                break

            if not is_direct_match:
                logging.info("Assertion failure is not directly related to the GitHub issue. Refining test case...")
                # error_handler.refine_test_case_until_related_assertion_generated(test_case_generator,
                #                                                                  generated_test_case,
                #                                                                  step_count,
                #                                                                  trajectory_folder,
                #                                                                  status_data,
                #                                                                  github_issue=test_case_generator.github_issue,
                #                                                                  source_code=test_case_generator.get_source_code())
                status = error_handler.refine_test_until_failure(
                    test_case_generator=test_case_generator,
                    test_code=generated_test_case,
                    iteration=step_count,
                    trajectory_folder=trajectory_folder,
                    status_data=status_data,
                    github_issue=test_case_generator.github_issue,
                    source_code=test_case_generator.get_source_code(),
                    search_manager=search_manager
                )
                if status:
                    break
            # else:
            #     logging.info("Assertion failure is related to the GitHub issue.")
            #     break
            #
        except Exception as e:
            logging.error(f"Error in iteration {step_count}: {e}")
            status_data["steps"].append({
                "step": globals.global_step,
                "error": str(e)
            })

    # Step 7: Set the final status (Success/Failed) based on whether any errors remain unresolved
    status_data["final_status"] = "Success" if all(
        not iteration.get("test_failures") and not iteration.get("compilation_error") for iteration in
        status_data["steps"]
    ) else "Failed"

    return status_data
