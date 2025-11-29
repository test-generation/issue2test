import argparse
import logging

# ✅ Step 1: Parse `--config-name` **before** importing config-dependent modules
parser = argparse.ArgumentParser(description="Feedback-Guided Test Generation for GitHub Issues")
parser.add_argument("--config-name",
                    type=str,
                    required=True,
                    help="Specify the configuration name from YAML (e.g., local-instance-1, vm-1)")
args, unknown = parser.parse_known_args()

# ✅ Step 2: Apply config **before** importing other modules
from feedback_guided_test_gen import config

config.apply_config(args.config_name)

logging.info(f"🔹 Using Config Name: {args.config_name}")

# ✅ Step 3: Now import everything else that depends on config
import json
import os
import shutil
import time

import logging
from datasets import load_dataset

from feedback_guided_test_gen import config
from issue2test_logger import LanceLogger

from error_handler import ErrorHandler
from feedback_loop import run_feedback_loop
from repo_setup import setup_repo_from_github_issue
from test_case_generator import TestCaseGenerator
from feedback_guided_test_gen.utils import create_final_status_file, create_trajectory_folder
from tools.repository_indexer import SearchManager

# ✅ Step 4: Access config values (which are now correctly loaded)
WORKSPACE_DIR = config.WORKSPACE_DIR
RETRY_LIMIT = config.RETRY_LIMIT


# LanceLogger.initialize_logger()


def load_json(filepath):
    """Utility to load JSON files."""
    logging.info(f"Loading JSON file from: {filepath}")
    return json.load(open(filepath, "r"))


def ensure_workspace_directory(issue_id, base_path="workspace"):
    """
    Ensures that a unique directory for the given issue_id is created inside the workspace.
    If a directory with the same issue_id already exists, it renames the old directory.
    """
    workspace_dir = WORKSPACE_DIR
    workspace_path = os.path.join(workspace_dir, issue_id)

    # If the directory exists, rename it by appending _previous_run_<timestamp>
    if os.path.exists(workspace_path):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        old_workspace_path = f"{workspace_path}_previous_run_{timestamp}"
        logging.info(
            f"Directory '{os.path.abspath(workspace_path)}' exists. Renaming it to '{os.path.abspath(old_workspace_path)}'")
        shutil.move(workspace_path, old_workspace_path)

    # Create a new directory for the current run
    os.makedirs(workspace_path)
    logging.info(f"Created new workspace directory: {os.path.abspath(workspace_path)}")

    return os.path.abspath(workspace_path)


def main(args):
    """
    Main function to drive the feedback-guided test generation process.
    """
    logging.basicConfig(level=logging.INFO)

    logging.info("Initializing the feedback-guided test generation process.")

    issue_id = args.issue_id

    # Load the SWE-Bench dataset and select the GitHub issue based on issue ID
    logging.info("Loading the SWE-Bench dataset.")
    swe_bench_dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    logging.info(f"Dataset loaded successfully with {len(swe_bench_dataset)} entries.")

    # Filter dataset by issue ID
    github_issue = next((issue for issue in swe_bench_dataset if issue["instance_id"] == args.issue_id), None)

    if not github_issue:
        logging.error(f"GitHub issue with ID {args.issue_id} not found in the dataset.")
        return

    # Ensure required keys are present in the github_issue dictionary
    required_keys = ["repo", "base_commit", "instance_id"]
    for key in required_keys:
        if key not in github_issue:
            logging.error(f"GitHub issue is missing required key: {key}")
            return

    # Ensure the workspace folder is created for this issue
    workspace_path = ensure_workspace_directory(github_issue["instance_id"],
                                                base_path="workspace")

    # Initialize logger with workspace-specific trajectories folder
    LanceLogger.initialize_logger(workspace_path)

    # Clone or load the repository and set up the project
    if args.project_file_loc:
        logging.info(f"Loading project data from: {args.project_file_loc}")
        project_file = os.path.join(args.project_file_loc, f"{github_issue['instance_id']}.json")
        project_data = load_json(project_file)
    else:
        # Clone the repo and check out the base commit, then get the project structure
        project_data = setup_repo_from_github_issue(
            repo_name=github_issue["repo"],  # e.g., "django/django"
            commit_id=github_issue["base_commit"],  # Commit hash
            instance_id=github_issue["instance_id"],  # Issue instance ID
            repo_workspace=workspace_path  # Workspace path
        )

    # Use the UUID-based path returned by setup_repo_from_github_issue
    repo_base_path = project_data["repo_base_path"]

    project_path: str = os.path.join(repo_base_path, args.project)
    search_manager = SearchManager(project_path)

    # Set the paths for the source and test files relative to the cloned repository
    source_code_file = os.path.join(repo_base_path, args.project, args.source_code_file)
    test_code_file_full_path = os.path.join(repo_base_path, args.project, args.test_code_file)

    # Log if the source code and test code files are found
    if os.path.exists(source_code_file):
        logging.info(f"Source code file found: {source_code_file}")
    else:
        logging.error(f"Source code file not found: {source_code_file}")

    if os.path.exists(test_code_file_full_path):
        logging.info(f"Test code file found: {test_code_file_full_path}")
    else:
        logging.error(f"Test code file not found: {test_code_file_full_path}")

    # Get the GitHub issue description from the dataset
    github_issue_description = github_issue.get("problem_statement", "")

    trajectory_folder = create_trajectory_folder(github_issue, workspace_path)
    logging.info(f"Trajectory folder created: {os.path.abspath(trajectory_folder)}")

    # Initialize the TestCaseGenerator with the correct paths
    test_case_generator = TestCaseGenerator(
        project=args.project,
        github_issue=github_issue,
        source_code_file=source_code_file,
        test_code_file_full_path=test_code_file_full_path,
        github_issue_description=github_issue_description,
        model=args.model,
        workspace_path=workspace_path,
        test_code_file=args.test_code_file,
        trajectory_folder=trajectory_folder,
        configuration=config.get_config()
    )

    # Initialize the ErrorHandler
    error_handler = ErrorHandler(model=args.model,
                                 trajectory_folder=trajectory_folder,
                                 retry_limit=RETRY_LIMIT,
                                 configuration=config.get_config(),
                                 github_issue=github_issue)

    # Initialize status data
    status_data = {
        "github_issue_id": issue_id,
        "github_issue": github_issue_description,
        "steps": [],
        "final_status": "Pending"
    }

    # Run the feedback loop for test generation, error handling, and refinement
    final_status = run_feedback_loop(test_case_generator,
                                     error_handler,
                                     status_data,
                                     trajectory_folder,
                                     github_issue,
                                     search_manager=search_manager,
                                     max_iterations=args.maximum_iterations,
                                     configuration=config.get_config())

    # Save the final execution status
    create_final_status_file(trajectory_folder, final_status)
    logging.info(f"Execution completed for GitHub issue {args.issue_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Feedback-Guided Test Generation for GitHub Issues")

    parser.add_argument("--config-name",
                        type=str,
                        required=True,
                        help="Specify the configuration name from YAML (e.g., local-instance-1, vm-1)")

    parser.add_argument("--model",
                        type=str,
                        default="gpt-4o-mini-2024-07-18",
                        help="The model to use for test case generation ('gpt-4o-2024-08-06')")

    parser.add_argument("--project", type=str,
                        # default="astropy",
                        # default="sympy",
                        # default="matplotlib",
                        default="django",
                        help="name of the project from SWE-bench")

    parser.add_argument("--source-code-file", type=str,
                        # default="sympy/matrices/expressions/matexpr.py",
                        # default="astropy/io/fits/fitsrec.py",
                        # default="sympy/printing/latex.py",
                        # default="lib/mpl_toolkits/axes_grid1/axes_grid.py",
                        # default="sympy/physics/units/util.py",
                        default="django/core/management/templates.py",
                        help="The path to the source code file")

    parser.add_argument("--test-code-file", type=str,
                        # default="sympy/matrices/expressions/tests/test_matexpr.py",
                        # default="astropy/io/fits/tests/test_checksum.py",
                        # default="sympy/printing/tests/test_latex.py",
                        # default="lib/mpl_toolkits/axes_grid1/tests/test_axes_grid1.py",
                        # default="sympy/physics/units/tests/test_quantities.py",
                        default="tests/admin_scripts/tests.py",
                        help="The path to the test code file")

    parser.add_argument("--maximum-iterations",
                        type=int,
                        default=1,
                        help="The maximum number of iterations for the feedback loop")

    parser.add_argument("--issue-id",
                        type=str,
                        # default="sympy__sympy-12419",
                        # default="astropy__astropy-6938",
                        # default="sympy__sympy-14317",
                        # default="matplotlib__matplotlib-26011",
                        # default="sympy__sympy-20442",
                        # default="django__django-15347",
                        default="django__django-14382",
                        help="The GitHub issue instance ID to fetch from SWE-Bench")

    parser.add_argument("--project-file-loc",
                        type=str,
                        help="Path to preprocessed project files if available")

    args = parser.parse_args()

    logging.info(f"🔹 Using Config Name: {config.CONFIG_NAME}")

    config.apply_config(args.config_name)
    main(args)
