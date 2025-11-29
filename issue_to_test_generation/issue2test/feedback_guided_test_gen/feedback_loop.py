import logging
import os
import shutil
from pathlib import Path
import traceback

import runtime_state_tracking
import config
from docker_test_runner import DockerTestRunner, naive_contains_error
from feedback_guided_test_gen import utils
from feedback_guided_test_gen.eval_helper import parse_log_sympy
from tools.remove_passing_tests import remove_passing_tests_ast, get_passing_tests_ast
from tools.test_failure_analyzer import has_test_failures, has_test_failures_naive
from tools.test_output_analyzer import parse_pytest_summary
from feedback_guided_test_gen.config import SWE_BENCH_DOCKER_DIR

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
                      max_iterations=20,
                      configuration=None):
    """
    Runs the feedback-guided loop for generating, running, and refining tests.

    Args:
        test_case_generator (TestCaseGenerator): Responsible for generating test cases.
        error_handler (ErrorHandler): Handles errors (e.g., compilation, assertion) during test execution.
        status_data (dict): A dictionary to track iteration statuses and errors.
        max_iterations (int): Maximum number of iterations for refining tests.

    Returns:
        dict: Updated status_data with the final status of the feedback loop execution.
        :param configuration:
    """
    generated_tests_folder = utils.get_generated_tests_folder(github_issue['instance_id'])
    project_name = test_case_generator.project_name

    previous_error_message = None
    error_category, reason, root_cause, repair_steps = "", "", "", ""

    for step_count in range(1, max_iterations + 1):
        try:
            logging.info(f"Starting step {runtime_state_tracking.step_count}")
            runtime_state_tracking.step_count += 1

            # Create the workspace for generated test code for each step
            iteration_test_workspace = os.path.join(trajectory_folder,
                                                    f"step_{runtime_state_tracking.step_count}-test-gen")
            if not os.path.exists(iteration_test_workspace):
                os.makedirs(iteration_test_workspace, exist_ok=True)

            # Step 1: Generate the test case using LLM
            generated_test_case = test_case_generator.generate_test(iteration_test_workspace)

            iteration_test_file_path = os.path.join(iteration_test_workspace,
                                                    f"step_{runtime_state_tracking.step_count}.py")
            with open(iteration_test_file_path, 'w') as f:
                f.write(generated_test_case)
                logging.info(f"Saved generated test case for step {runtime_state_tracking.step_count} "
                             f"to {iteration_test_file_path}")

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

            # Step 3: Create files_to_copy in the generated_tests folder
            original_test_file_path = test_case_generator.test_code_file
            relative_test_folder = os.path.dirname(original_test_file_path)
            relative_new_test_file_path = os.path.join(relative_test_folder, 'test_new.py')
            relative_path_to_docker = relative_new_test_file_path
            # if project_name == "django":
            #     relative_path_to_docker = remove_tests_prefix(relative_new_test_file_path)
            paths_lst_content = f"test_new.py#{relative_new_test_file_path}"

            paths_lst_path = os.path.join(generated_tests_folder, "paths.lst")
            with open(paths_lst_path, 'w') as f:
                if project_name == "django":
                    paths_lst_content = f"test_new.py#{remove_tests_prefix(relative_new_test_file_path)}"
                f.write(paths_lst_content)
                logging.info(f"Created files_to_copy file with content: {paths_lst_content}")

            # Step 4: Run the tests in Docker
            issue_id = test_case_generator.github_issue_id
            SWE_BENCH_DOCKER_PATH = SWE_BENCH_DOCKER_DIR
            docker_runner = DockerTestRunner(SWE_BENCH_DOCKER_PATH,
                                             new_test_file_path,
                                             issue_id,
                                             project_name=test_case_generator.project_name)
            docker_runner.run_tests_in_docker(generated_tests_folder, relative_path_to_docker)

            # Step 5: Check test results from the {issue_id}_test_results_buggy file
            test_results = f"{issue_id}_test_results_buggy"

            test_results_file = os.path.join(SWE_BENCH_DOCKER_PATH, test_results)

            parsed_results = parse_pytest_summary(test_results_file)

            # Identify passing and failing tests
            successful_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] == "PASSED"]
            failed_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] == "FAILED"]

            # Analyze test execution logs
            log_detected_failures, test_summary, test_log_output = docker_runner.check_test_results(
                generated_tests_folder)

            # Final failure determination: Either log-detected or explicitly listed failures
            is_test_failure = log_detected_failures or naive_contains_error(test_log_output) or len(failed_tests) > 0

            # If some tests passed but others failed, remove only passing tests
            # Also attempt to convert passing tests to fail for FAIL to PASS transition
            if len(successful_tests) > 0 and len(failed_tests) > 0:
                # Remove only the passing tests, keeping failing tests intact
                runtime_state_tracking.step_count += 1

                logging.info(f"Some tests passed unexpectedly. Removing passing tests: {successful_tests}")
                step = f"step_{runtime_state_tracking.step_count}-test-removal"
                refinement_workspace = os.path.join(trajectory_folder, step)
                if not os.path.exists(refinement_workspace):
                    os.makedirs(refinement_workspace)

                refinement_test_file_path = os.path.join(refinement_workspace,
                                                                         f"step_{runtime_state_tracking.step_count}.py")

                # Extract passing tests FIRST before modifying `new_test_file_path`
                # synthesized_passing_tests = get_passing_tests_ast(
                #     new_test_file_path,  # Use original before modification
                #     test_results_file,
                #     output_file_path=None,
                #     return_code=True
                # )

                # Extract only failing tests using AST-based transformation
                remove_passing_tests_ast(new_test_file_path,
                                         test_results_file,
                                         refinement_test_file_path)

                # Now Save the generated test case in test_new.py for docker execution
                new_test_file_path = os.path.join(generated_tests_folder, "test_new.py")
                shutil.copyfile(refinement_test_file_path, new_test_file_path)
                logging.info(f"Saved generated test case for step {step_count} to {new_test_file_path}")

                # Store the test case after removing passing tests for later use
                with open(new_test_file_path, 'r') as f:
                    test_case_after_passing_removal = f.read()

                # synthesized_passing_tests = get_passing_tests_ast(new_test_file_path,
                #                                                   test_results_file,
                #                                                   output_file_path=None,
                #                                                   return_code=True)

                # is_assertion_addresses_the_issue = error_handler.refine_test_case_until_related_assertion_generated(
                #     test_case_generator,
                #     synthesized_passing_tests,
                #     runtime_state_tracking.step_count,
                #     trajectory_folder,
                #     status_data,
                #     github_issue,
                #     test_case_generator.get_source_code())
                # if is_assertion_addresses_the_issue:
                #     break
            else:
                # No passing tests to remove; keep the original generated test case
                test_case_after_passing_removal = generated_test_case

            # once we reach here, we only have test cases which are failing
            is_assertion_addresses_the_issue = False
            if is_test_failure:
                logging.info("Test failures detected.")

                # Check if we're stuck on the same error
                if test_summary == previous_error_message:
                    logging.warning("Same error encountered as in the previous iteration.")
                previous_error_message = test_summary

                # Step 6: Categorize the error (via LLM)
                error_category, reason, root_cause, repair_steps = error_handler.categorize_error(test_log_output,
                                                                                                  generated_test_case)

                # Step 6a: Handle Compilation Failure
                if error_category == 'compilation' or error_category == 'runtime':
                    logging.info("Handling compilation or runtime error...")

                    is_compilation_fixed, is_assertion_directly_related, fixed_compilation_error_in_test_code = error_handler.handle_compilation_and_runtime_error(
                        test_execution_logs=test_log_output,
                        source_code=test_case_generator.get_source_code(),
                        test_code=generated_test_case,
                        iteration=step_count,
                        test_case_generator=test_case_generator,
                        generated_tests_folder=generated_tests_folder,
                        new_test_file_path=new_test_file_path,
                        github_issue=test_case_generator.github_issue,
                        search_manager=search_manager,
                        error_category=error_category,
                        reason=reason,
                        root_cause=root_cause,
                        repair_steps=repair_steps
                    )
                    status_data["steps"][-1]["compilation_error"] = is_compilation_fixed
                    status_data["steps"][-1]["compilation_fix"] = fixed_compilation_error_in_test_code

                    generated_test_case = fixed_compilation_error_in_test_code
                    is_assertion_addresses_the_issue = is_assertion_directly_related

                    # if compilation error is not fixed,
                    # continue to the next iteration and try to generate a new test case
                    if not is_compilation_fixed:
                        continue

                    if is_compilation_fixed:
                        is_assertion_addresses_the_issue = is_assertion_directly_related
                        if is_assertion_addresses_the_issue:
                            break  # Exit the loop since the assertion is related to the issue

                # Step 6c: Handle Assertion Failure
                elif error_category == 'assertion':
                    logging.info("Handling assertion error...")
                    synthesized_test_case = test_case_after_passing_removal
                    is_related_to_issue = error_handler.is_assertion_error(test_log_output,
                                                                           test_case_generator.github_issue_id,
                                                                           test_case_generator.github_issue,
                                                                           synthesized_test_case)
                    is_assertion_addresses_the_issue = is_related_to_issue.get("is_direct_match", "").lower() == "yes"
            else:
                logging.info("Generated tests passed unexpectedly given a Github issue."
                             "Refining test case until it fails.")
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

            if is_assertion_addresses_the_issue:
                break
            else:
                logging.info("Assertion failure is not directly related to the GitHub issue. Refining test case...")
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
        except Exception as e:
            error_trace = traceback.format_exc()
            logging.error(f"Error in iteration {step_count}: {e}\n"
                          f"Error Traceback:\n{error_trace}")
            status_data["steps"].append({
                "step": runtime_state_tracking.step_count,
                "error": str(e)
            })

    # Step 7: Set the final status (Success/Failed) based on whether any errors remain unresolved
    status_data["final_status"] = "Success" if all(
        not iteration.get("test_failures") and not iteration.get("compilation_error") for iteration in
        status_data["steps"]
    ) else "Failed"

    status_data["calculated_cost"] = runtime_state_tracking.calculated_cost
    status_data["litellm_reported_cost"] = runtime_state_tracking.litellm_reported_cost
    return status_data
