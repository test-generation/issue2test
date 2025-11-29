import json
import shutil

import toml
import logging
from jinja2 import Template


from old_docker_test_runner import DockerTestRunner, naive_contains_error
from feedback_guided_test_gen.eval_helper import parse_log_sympy
from old_feedback_loop import remove_tests_prefix
from feedback_guided_test_gen.utils import run_test_in_docker, save_iteration_data, parse_json_with_markers, \
    save_iteration_data_for_step
from llm_invocation import LLMInvocation
from tools.extract_code_block import extract_code_block
from tools.pytest_log_analyzer import get_first_module_not_found_error, parse_pytest_log
from tools.test_failure_analyzer import has_test_failures, has_test_failures_naive
from utils import strip_code_block
import os

#import config
from feedback_guided_test_gen import config

#import globals
from feedback_guided_test_gen import globals

SWEBENCH_PATH = config.SWE_BENCH_DOCKER_PATH


class ErrorHandler:
    def __init__(self, model, trajectory_folder, retry_limit):
        self.model = model
        self.llm_invoker = LLMInvocation(model=model)
        self.logger = logging.getLogger(__name__)
        self.trajectory_folder = trajectory_folder
        self.retry_limit = retry_limit

        # Set base directory and template path
        base_dir = os.path.dirname(__file__)
        self.prompts_folder = os.path.join(base_dir, 'prompts')

    def load_prompt_template(self, template_name):
        """Load the TOML prompt template based on the error type."""
        template_path = os.path.join(self.prompts_folder, f'{template_name}.toml')
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Prompt template not found: {template_path}")

        self.logger.info(f"Loading prompt template: {template_path}")
        with open(template_path, 'r') as f:
            return toml.load(f)

    def handle_compilation_error(self,
                                 test_execution_logs,
                                 source_code,
                                 test_code,
                                 iteration,
                                 test_case_generator,
                                 generated_tests_folder,
                                 new_test_file_path,
                                 github_issue,
                                 search_manager,
                                 error_category,
                                 reason,
                                 root_cause,
                                 repair_steps):
        """Handle compilation errors by refining the test or source code using LLM."""
        generated_tests_folder = os.path.join(SWEBENCH_PATH, "generated_tests")

        retries = 0
        # reason = "Unknown"

        while retries < self.retry_limit:
            globals.global_step += 1

            logging.info(f"Handling compilation error attempt {retries + 1} for step {globals.global_step}...")

            # Create a workspace for this refinement attempt
            step = f"step_{globals.global_step}-error_fix"

            retry_workspace = os.path.join(self.trajectory_folder, step)
            os.makedirs(retry_workspace, exist_ok=True)

            # previous_test_backup = os.path.join(retry_workspace, f"backup_test_{retries}.py")
            # if os.path.exists(new_test_file_path):
            #    shutil.copyfile(new_test_file_path, previous_test_backup)
            #    self.logger.info(f"Backed up previous test file to {previous_test_backup}")
            parsed_results_json = parse_pytest_log(test_execution_logs)
            # parsed_results = json.loads(parsed_results_json)
            first_module_error = get_first_module_not_found_error(parsed_results_json)
            if first_module_error and test_case_generator.project_name not in ["sympy"]:
                module, symbol_name = first_module_error
                print(f"First ModuleNotFoundError Entry:")
                print(f"  Module: {module}")
                print(f"  Symbol: {symbol_name}")
                import_analysis_results, summary, found = search_manager.search_import_and_alias_usages(symbol_name)

                # Prepare the prompt for repairing the compilation error - ModuleNotFoundError
                prompt_template = self.load_prompt_template('compilation_failure_import_analysis')
                user_template = Template(prompt_template['compilation_failure_prompt']['user'])

                github_issue_description = github_issue.get("problem_statement", "")
                rendered_user_prompt = user_template.render(
                    github_issue=github_issue_description,
                    test_execution_logs=test_execution_logs,
                    test_file=test_code,
                    import_analysis_results=import_analysis_results,
                    reason=reason,
                    root_cause=root_cause,
                    repair_steps=repair_steps
                )
                system_prompt = prompt_template['compilation_failure_prompt']['system']
                prompt = {
                    "system": system_prompt,
                    "user": rendered_user_prompt
                }
            else:
                # Prepare the prompt for repairing the compilation error
                prompt_template = self.load_prompt_template('compilation_failure')
                user_template = Template(prompt_template['compilation_failure_prompt']['user'])

                github_issue_description = github_issue.get("problem_statement", "")
                rendered_user_prompt = user_template.render(
                    github_issue=github_issue_description,
                    test_execution_logs=test_execution_logs,
                    test_file=test_code,
                    reason=reason,
                    root_cause=root_cause,
                    repair_steps=repair_steps
                )
                system_prompt = prompt_template['compilation_failure_prompt']['system']
                prompt = {
                    "system": system_prompt,
                    "user": rendered_user_prompt
                }
            # Invoke the LLM to generate fix for the compilation error
            response = self.llm_invoker.call_model(prompt)
            generated_fixed_code = extract_code_block(response[0])

            # Save input/output for this iteration
            save_iteration_data_for_step(self.trajectory_folder, step, rendered_user_prompt, response)

            # Save the refined test case for this iteration
            refinement_test_file_path = os.path.join(retry_workspace,
                                                     f"step_{globals.global_step}.py")
            with open(refinement_test_file_path, 'w') as f:
                f.write(generated_fixed_code)
            logging.info(f"Saved fixed test case to {refinement_test_file_path}")

            # Save the generated test case in test_new.py for docker execution
            new_test_file_path = os.path.join(generated_tests_folder, "test_new.py")
            with open(new_test_file_path, 'w') as f:
                f.write(generated_fixed_code)
                logging.info(f"Saved generated test case to {new_test_file_path}")

            # Create paths.lst in the generated_tests folder
            original_test_file_path = test_case_generator.test_code_file
            relative_test_folder = os.path.dirname(original_test_file_path)
            relative_new_test_file_path = os.path.join(relative_test_folder, 'test_new.py')
            # relative_new_test_file_path = remove_tests_prefix(relative_new_test_file_path)
            paths_lst_content = f"test_new.py {relative_new_test_file_path}"

            paths_lst_path = os.path.join(generated_tests_folder, "paths.lst")
            with open(paths_lst_path, 'w') as f:
                f.write(paths_lst_content)
                logging.info(f"Created paths.lst file with content: {paths_lst_content}")

            # Run the refined test in Docker
            issue_id = test_case_generator.github_issue_id
            docker_runner = DockerTestRunner(SWEBENCH_PATH, new_test_file_path, issue_id)
            docker_runner.run_tests_in_docker(generated_tests_folder)

            # test_failures, result_content = run_test_in_docker(test_case_generator, generated_tests_folder,
            #                                                   new_test_file_path)
            # save_iteration_data(self.trajectory_folder, inner_iteration_label, rendered_user_prompt, response)

            # Check the test results
            test_failures, results_summary, result_content = docker_runner.check_test_results(generated_tests_folder)
            test_failures = test_failures or naive_contains_error(result_content)

            if test_case_generator.project_name == "sympy":
                test_failures = has_test_failures_naive(result_content)
                # test_status_map = parse_log_sympy(result_content)
                # test_failures = has_test_failures(test_status_map)

            if test_failures:
                test_code = generated_fixed_code

                # If the test now fails (expected behavior in TDD) but compilation error is fixed, exit the loop
                # error_category, reason, tdd_related = self.categorize_error_tdd(result_content, iteration, github_issue)
                error_category, reason, root_cause, repair_steps, tdd_related = self.categorize_error_tdd(result_content, iteration, github_issue, test_code)
                if error_category == 'runtime' and tdd_related:
                    return True, True, generated_fixed_code

                if error_category == 'assertion':
                    logging.info("compilation error and runtime error is fixed...")

                    logging.info("Handling assertion error...")
                    is_related_to_issue = self.handle_assertion_error(result_content,
                                                                      test_case_generator.github_issue_id,
                                                                      test_case_generator.github_issue,
                                                                      globals.global_step)

                    is_direct_match = is_related_to_issue.get("is_direct_match", False)
                    if is_direct_match:
                        logging.info(
                            "Assertion failure is not directly related to the GitHub issue. Refining test case...")
                        return True, True, generated_fixed_code

                    return True, False, generated_fixed_code

            if not test_failures:
                self.logger.info("Test compiled and passed successfully after fix.")
                return True, False, generated_fixed_code
            retries += 1

        self.logger.error(f"Reached retry limit ({self.retry_limit}) without successfully compiling.")
        return False, None

    def handle_assertion_error(self, assertion_error, github_issue_id, github_issue, iteration):
        """Handle assertion errors by determining if the error is related to the GitHub issue."""
        globals.global_step += 1

        # Load and render the template for assertion failure
        prompt_template = self.load_prompt_template('assertion_failure')
        user_template = Template(prompt_template['assertion_failure_prompt']['user'])

        github_issue_description = github_issue.get("problem_statement", "")
        rendered_user_prompt = user_template.render(
            assertion_error_message=assertion_error,
            github_issue=github_issue_description
        )
        system_prompt = prompt_template['assertion_failure_prompt']['system']
        prompt = {"system": system_prompt, "user": rendered_user_prompt}

        # Invoke the LLM to check if the assertion failure is related to the GitHub issue
        response = self.llm_invoker.call_model(prompt)

        # Save input/output for this iteration
        step = "step_{}_check_assertion".format(globals.global_step)
        save_iteration_data_for_step(self.trajectory_folder, step, rendered_user_prompt, response)

        response = response[0]
        response_json = parse_json_with_markers(response)
        return response_json

    def handle_runtime_error(self, error_message,
                             source_code,
                             test_code,
                             iteration,
                             test_case_generator,
                             trajectory_folder,
                             generated_tests_folder,
                             new_test_file_path):
        """Handle runtime errors (e.g., NullPointerException) by refining the code using LLM."""
        retries = 0  # NEW

        while retries < self.retry_limit:
            inner_iteration_label = f"iteration_{iteration}_inner_{retries + 1}"
            self.logger.info(f"Handling runtime error for retry {retries + 1} in iteration {iteration}...")

            retry_folder = os.path.join(trajectory_folder, f"iteration_{iteration}", f"inner_iteration_{retries + 1}")
            os.makedirs(retry_folder, exist_ok=True)

            previous_test_backup = os.path.join(retry_folder, f"backup_test_{retries}.py")
            if os.path.exists(new_test_file_path):
                shutil.copyfile(new_test_file_path, previous_test_backup)
                self.logger.info(f"Backed up previous test file to {previous_test_backup}")

            # Load and render the template for runtime failure
            prompt_template = self.load_prompt_template('runtime_failure')
            user_template = Template(prompt_template['runtime_failure_prompt']['user'])

            # Render the user prompt with error details and source/test code
            rendered_user_prompt = user_template.render(
                runtime_error_message=error_message,
                source_file_numbered=source_code,
                test_file=test_code
            )
            system_prompt = prompt_template['runtime_failure_prompt']['system']
            prompt = {"system": system_prompt, "user": rendered_user_prompt}

            response = self.llm_invoker.call_model(prompt)
            generated_fixed_code = strip_code_block(response[0])

            with open(new_test_file_path, 'w') as f:
                f.write(generated_fixed_code)
            self.logger.info(f"Saved new test case to {new_test_file_path} for Docker execution.")

            test_failures, result_content = run_test_in_docker(test_case_generator, generated_tests_folder,
                                                               new_test_file_path)  # NEW

            save_iteration_data(retry_folder, retries + 1, rendered_user_prompt, response)

            if not test_failures:
                self.logger.info("Test compiled and passed successfully after fix.")
                return True, generated_fixed_code

            self.logger.info(
                f"Retry {retries + 1} in iteration {iteration} failed. Continuing retries...")  # No changes here
            retries += 1

        self.logger.error(
            f"Reached retry limit ({self.retry_limit}) without successfully fixing runtime error.")  # No changes here
        return False, response.strip()

    def categorize_error(self, result_content, iteration, test_file):
        """
        Categorize the error from the test results as 'compilation' or 'assertion' using LLM.
        Args:
            result_content (str): The content of the test result.
            iteration (int): The current iteration number.
        Returns:
            str: 'compilation' or 'assertion' based on the error category.
        """
        self.logger.info(f"Categorizing error for iteration {globals.global_step}...")
        globals.global_step += 1

        # Load the template for error categorization
        prompt_template = self.load_prompt_template('error_categorization')
        user_template = Template(prompt_template['error_categorization_prompt']['user'])

        # Render the user prompt with the test result content
        rendered_user_prompt = user_template.render(result_content=result_content,
                                                    test_file=test_file)
        system_prompt = prompt_template['error_categorization_prompt']['system']
        prompt = {"system": system_prompt, "user": rendered_user_prompt}

        # Invoke the LLM to classify the error
        response = self.llm_invoker.call_model(prompt)

        step = "step-{}-error_categorization".format(globals.global_step)
        # Save input/output for this iteration
        save_iteration_data_for_step(self.trajectory_folder, step, rendered_user_prompt, response)

        response = response[0]
        response_json = parse_json_with_markers(response)

        error_category = response_json.get("error_type", "unknown")
        reason = response_json.get("reason", "unknown")
        root_cause = response_json.get("root_cause", "unknown")
        repair_steps = response_json.get("repair_steps", "unknown")

        self.logger.info(f"LLM categorized the error as: {error_category}")

        return error_category, reason, root_cause, repair_steps

    def categorize_error_tdd(self, result_content, iteration, github_issue, test_file):
        """
        Categorize the error from the test results as 'compilation' or 'assertion' using LLM.
        Args:
            result_content (str): The content of the test result.
            iteration (int): The current iteration number.
        Returns:
            str: 'compilation' or 'assertion' based on the error category.
        """
        self.logger.info(f"Categorizing error for iteration {globals.global_step}...")
        globals.global_step += 1

        # Load the template for error categorization
        prompt_template = self.load_prompt_template('error_tdd_relevance_categorization')
        user_template = Template(prompt_template['error_tdd_relevance_categorization_prompt']['user'])

        # Render the user prompt with the test result content
        rendered_user_prompt = user_template.render(github_issue=github_issue,
                                                    result_content=result_content,
                                                    test_file=test_file)
        system_prompt = prompt_template['error_tdd_relevance_categorization_prompt']['system']
        prompt = {"system": system_prompt, "user": rendered_user_prompt}

        # Invoke the LLM to classify the error
        response = self.llm_invoker.call_model(prompt)

        step = "step-{}-error_categorization_tdd".format(globals.global_step)
        # Save input/output for this iteration
        save_iteration_data_for_step(self.trajectory_folder, step, rendered_user_prompt, response)

        response = response[0]
        response_json = parse_json_with_markers(response)

        error_category = response_json.get("error_type", "unknown")
        reason = response_json.get("reason", "unknown")
        root_cause = response_json.get("root_cause", "unknown")
        repair_steps = response_json.get("repair_steps", "unknown")
        tdd_related = response_json.get("issue_error_relevance", False)
        self.logger.info(f"LLM categorized the error as: {error_category}, tdd_related: {tdd_related}")

        return error_category, reason, root_cause, repair_steps, tdd_related

    def refine_test_case_until_related_assertion_generated(self, test_case_generator,
                                                           test_code,
                                                           iteration,
                                                           trajectory_folder,
                                                           status_data,
                                                           github_issue,
                                                           source_code):
        """
        Refines the test case until it is related to the GitHub issue, handling both assertion and compilation errors.
        If the test passes or is not yet related to the GitHub issue, refine it further.

        Args:
            test_case_generator (TestCaseGenerator): Generates test cases.
            test_code (str): The initial generated test code that is currently not related to the GitHub issue.
            iteration (int): Current iteration number.
            trajectory_folder (str): Path to store generated tests.
            status_data (dict): Tracks the status of the test generation process.
            github_issue (str): The description of the GitHub issue.
            source_code (str): The source code that the test is checking.
        """
        globals.global_step += 1

        max_refinements = 5  # Limit the number of refinements
        refinement_attempts = 0
        is_related = False  # Track if the refined test is related to the issue

        while refinement_attempts < max_refinements:
            logging.info(
                f"Attempt to generate an assertion that fails: {refinement_attempts + 1}, step {globals.global_step}...")

            # Create a workspace for this refinement attempt
            refinement_workspace = os.path.join(trajectory_folder,
                                                f"step_{globals.global_step}")
            if not os.path.exists(refinement_workspace):
                os.makedirs(refinement_workspace)

            # NEW: Prepare the prompt for generating a failing test case related to the GitHub issue
            prompt_template = self.load_prompt_template('generate_failing_test')
            user_template = Template(prompt_template['failing_test_prompt']['user'])

            # Render the prompt with GitHub issue, source code, and current passing test
            github_issue_description = github_issue.get("problem_statement", "")
            rendered_user_prompt = user_template.render(
                github_issue=github_issue_description,
                source_code=source_code,
                unrelated_assertion_test=test_code
            )

            # NEW: Call the LLM to generate a test that is supposed to fail and relate to the issue
            prompt = {"system": prompt_template['failing_test_prompt']['system'],
                      "user": rendered_user_prompt}
            response = self.llm_invoker.call_model(prompt)
            refined_test_case = strip_code_block(response[0])  # Strip code block from LLM response

            # Save the refined test case
            refinement_test_file_path = os.path.join(refinement_workspace,
                                                     f"step_{globals.global_step}.py")
            with open(refinement_test_file_path, 'w') as f:
                f.write(refined_test_case)
            logging.info(f"Saved refined test case to {refinement_test_file_path}")

            # Run the refined test in Docker
            docker_runner = DockerTestRunner(SWEBENCH_PATH, refinement_test_file_path,
                                             test_case_generator.github_issue_id)
            docker_runner.run_tests_in_docker(refinement_workspace)

            # Check the test results
            test_failures, result_content = docker_runner.check_test_results(refinement_workspace)

            if test_failures:
                logging.info("Refined test failed. Categorizing the error...")

                # Categorize the error (it could be compilation or assertion)
                error_category = self.categorize_error(result_content, iteration, test_code)

                if error_category == 'compilation':
                    # Handle compilation failure in the refinement loop
                    logging.info("Handling compilation error during refinement...")
                    is_compilation_fixed, fix = self.handle_compilation_error(
                        test_execution_logs=result_content,
                        source_code=test_case_generator.get_numbered_source_code(),
                        test_code=refined_test_case,
                        iteration=iteration,
                        test_case_generator=test_case_generator,
                        generated_tests_folder=refinement_workspace,
                        new_test_file_path=refinement_test_file_path,
                        github_issue=github_issue
                    )

                    # If compilation is not fixed, retry the refinement
                    if not is_compilation_fixed:
                        logging.warning(
                            f"Compilation error not fixed during refinement attempt {refinement_attempts + 1}.")
                        refinement_attempts += 1
                        continue

                elif error_category == 'assertion':
                    # Handle assertion failure and check if it’s now related to the GitHub issue
                    is_related_to_issue = self.handle_assertion_error(result_content,
                                                                      test_case_generator.github_issue_id,
                                                                      test_case_generator.github_issue, iteration)
                    is_related = is_related_to_issue.get("is_direct_match", False)

                    if is_related:
                        logging.info("Refined test case is now related to the GitHub issue.")
                        status_data["steps"][-1]["assertion_fix"] = refined_test_case
                        break  # Exit if the test case is related to the issue

            else:
                # If the test passes without errors, exit the loop
                logging.info("Refined test passed successfully.")
                status_data["steps"][-1]["assertion_fix"] = refined_test_case
                break  # Exit since the test passed without any issues

            # Increment refinement attempts
            refinement_attempts += 1

        # If max refinements reached and test still not related
        if refinement_attempts == max_refinements and not is_related:
            logging.warning(
                f"Max refinements ({max_refinements}) reached. Test case still not related to GitHub issue.")
            status_data["steps"][-1]["test_failures"] = False  # Mark as no failures

    def refine_test_until_failure(self,
                                  test_case_generator,
                                  test_code,
                                  iteration,
                                  trajectory_folder,
                                  status_data,
                                  github_issue,
                                  source_code,
                                  search_manager):
        """
        Refines the test case using a prompt that instructs the LLM to create a failing test.
        If the test passes immediately, refine it until it fails, which is necessary for TDD.

        Args:
            test_case_generator (TestCaseGenerator): Generates test cases.
            test_code (str): The initial generated test code that is currently passing.
            iteration (int): Current iteration number.
            trajectory_folder (str): Path to store generated tests.
            status_data (dict): Tracks the status of the test generation process.
            github_issue (str): The description of the GitHub issue.
            source_code (str): The source code that the test is checking.
        """
        generated_tests_folder = os.path.join(SWEBENCH_PATH, "generated_tests")

        max_refinements = 5
        refinement_attempts = 0

        while refinement_attempts < max_refinements:
            globals.global_step += 1

            logging.info(f"Refinement attempt {refinement_attempts + 1} for step {globals.global_step}...")

            # Create a workspace for this refinement attempt
            step = f"step_{globals.global_step}-test_refinement"
            refinement_workspace = os.path.join(trajectory_folder, f"step_{globals.global_step}")
            if not os.path.exists(refinement_workspace):
                os.makedirs(refinement_workspace)

            # Prepare the prompt for generating a failing test case
            prompt_template = self.load_prompt_template('generate_failing_test')
            user_template = Template(prompt_template['failing_test_prompt']['user'])

            github_issue_description = github_issue.get("problem_statement", "")
            # Render the prompt with GitHub issue, source code, and passing test
            rendered_user_prompt = user_template.render(
                github_issue=github_issue_description,
                source_code=source_code,
                passing_test=test_code
            )

            # Call the LLM to generate a test that is supposed to fail
            prompt = {
                "system": prompt_template['failing_test_prompt']['system'],
                "user": rendered_user_prompt
            }
            response = self.llm_invoker.call_model(prompt)
            refined_test_case = strip_code_block(response[0])

            # Save input/output for this iteration
            save_iteration_data_for_step(refinement_workspace, step, rendered_user_prompt, response)

            # Save the refined test case for this iteration
            refinement_test_file_path = os.path.join(refinement_workspace,
                                                     f"step_{globals.global_step}.py")
            with open(refinement_test_file_path, 'w') as f:
                f.write(refined_test_case)
            logging.info(f"Saved refined test case to {refinement_test_file_path}")

            # Save the generated test case in test_new.py for docker execution
            new_test_file_path = os.path.join(generated_tests_folder, "test_new.py")
            with open(new_test_file_path, 'w') as f:
                f.write(refined_test_case)
                logging.info(f"Saved generated test case to {new_test_file_path}")

            # Create paths.lst in the generated_tests folder
            original_test_file_path = test_case_generator.test_code_file
            relative_test_folder = os.path.dirname(original_test_file_path)
            relative_new_test_file_path = os.path.join(relative_test_folder, 'test_new.py')
            # relative_new_test_file_path = remove_tests_prefix(relative_new_test_file_path)
            paths_lst_content = f"test_new.py {relative_new_test_file_path}"

            paths_lst_path = os.path.join(generated_tests_folder, "paths.lst")
            with open(paths_lst_path, 'w') as f:
                f.write(paths_lst_content)
                logging.info(f"Created paths.lst file with content: {paths_lst_content}")

            # Run the refined test in Docker
            issue_id = test_case_generator.github_issue_id
            docker_runner = DockerTestRunner(SWEBENCH_PATH, new_test_file_path, issue_id)
            docker_runner.run_tests_in_docker(generated_tests_folder)

            # Check the test results
            test_failures, results_summary, result_content = docker_runner.check_test_results(generated_tests_folder)
            test_failures = test_failures or naive_contains_error(result_content)

            if test_case_generator.project_name == "sympy":
                test_failures = has_test_failures_naive(result_content)
                # test_status_map = parse_log_sympy(result_content)
                # test_failures = has_test_failures(test_status_map)

            if test_failures:
                # If the test now fails (expected behavior in TDD), exit the loop
                logging.info("Test now fails as expected (TDD). Stop the refinement process.")
                status_data["steps"][-1]["test_failures"] = True

                error_category, reason, root_cause, repair_steps = self.categorize_error(result_content, iteration, test_code)
                if error_category == 'compilation' or error_category == 'runtime':
                    logging.info("Handling compilation error...")

                    is_compilation_fixed, fix = self.handle_compilation_error(
                        test_execution_logs=result_content,
                        source_code=test_case_generator.get_source_code(),
                        test_code=refined_test_case,
                        iteration=iteration,
                        test_case_generator=test_case_generator,
                        generated_tests_folder=generated_tests_folder,
                        new_test_file_path=new_test_file_path,
                        github_issue=github_issue,
                        search_manager=search_manager
                    )
                    status_data["steps"][-1]["compilation_error"] = is_compilation_fixed
                    status_data["steps"][-1]["compilation_fix"] = fix

                # elif error_category == 'runtime':
                #     logging.info("Handling runtime error...")
                #     fix = self.handle_runtime_error(result_content, test_case_generator.github_issue_id,
                #                                     test_case_generator.github_issue, iteration)
                #     status_data["steps"][-1]["runtime_error"] = True
                #     status_data["steps"][-1]["runtime_fix"] = fix

                elif error_category == 'assertion':
                    logging.info("Handling assertion error...")
                    is_related_to_issue = self.handle_assertion_error(result_content,
                                                                      test_case_generator.github_issue_id,
                                                                      test_case_generator.github_issue,
                                                                      iteration)
                    is_direct_match = is_related_to_issue.get("is_direct_match", False)

                    if not is_direct_match:
                        logging.info(
                            "Assertion failure is not directly related to the GitHub issue. Refining test case...")
                        self.refine_test_case_until_related_assertion_generated(test_case_generator,
                                                                                refined_test_case,
                                                                                iteration,
                                                                                trajectory_folder,
                                                                                status_data)
                    else:
                        logging.info("Assertion failure is directly related to the GitHub issue.")
                        break  # Exit once we achieve failure (TDD principle)
            else:
                # If the test still passes, refine the test case further
                test_code = refined_test_case
                logging.info("Test passed unexpectedly. Refining test case again...")
                refinement_attempts += 1

        # If max refinements reached and the test still passes
        if refinement_attempts == max_refinements:
            logging.warning(f"Max refinements ({max_refinements}) reached, but the test case still passes.")
            status_data["steps"][-1]["test_failures"] = False  # Mark as no failures
            return False
        else:
            return True
