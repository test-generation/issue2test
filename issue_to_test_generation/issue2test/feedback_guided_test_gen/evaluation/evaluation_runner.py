import os
import sys
import csv
import logging
import shutil
import time
import argparse

# Dynamically add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from feedback_guided_test_gen.evaluation.evaluation_docker_executor import EvaluationDockerExecutor

# arse command-line arguments
parser = argparse.ArgumentParser(description="Run test evaluation using Docker.")
parser.add_argument("--swe_bench_docker_path",
                    type=str,
                    required=True,
                    help="Path to SWE Bench Docker directory (e.g., /path/to/swe-bench-docker)")
args = parser.parse_args()


# Define paths
# SWE_BENCH_DOCKER_PATH = "/Volumes/nashid-g40/ubc-works/repos/swe-bench-docker"
# SWE_BENCH_DOCKER_PATH = "/Volumes/nashid-g40/ubc-works/repos/instance-2/swe-bench-docker"
SWE_BENCH_DOCKER_PATH = os.path.abspath(args.swe_bench_docker_path)


CSV_FILE_PATH = f"{SWE_BENCH_DOCKER_PATH}/evaluation_results.csv"  # Save results here

# Generate a timestamped backup filename
timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")  # Format: YYYY-MM-DD_HH-MM-SS
BACKUP_CSV_FILE_PATH = f"{CSV_FILE_PATH}.{timestamp}.bak"  # Backup file with timestamp

# Configure logging
logging.basicConfig(level=logging.INFO)

# Backup old results before overwriting
if os.path.exists(CSV_FILE_PATH):
    logging.info(f"🔄 Backing up old results to {BACKUP_CSV_FILE_PATH}")
    shutil.copy(CSV_FILE_PATH, BACKUP_CSV_FILE_PATH)

# Get all test folders for GitHub issues
test_case_folders = [f for f in os.listdir(SWE_BENCH_DOCKER_PATH) if f.startswith("generated_tests_")]

# Track test results
total_issues_evaluated = len(test_case_folders)
successful_fix_validations = 0

# Prepare CSV file
csv_headers = [
    "Issue ID", "Test Folder", "Total Tests Before", "Failures Before",
    "Total Tests After", "Failures After", "Failures Fixed", "Fail->Pass"
]
with open(CSV_FILE_PATH, mode="w", newline="") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(csv_headers)  # Write header row
    logging.info(f"✅ Evaluation results will be saved in: {CSV_FILE_PATH}")

try:
    for index, test_folder in enumerate(test_case_folders, start=1):
        issue_id = test_folder.replace("generated_tests_", "")
        test_folder_path = os.path.join(SWE_BENCH_DOCKER_PATH, test_folder)

        logging.info(f"🔍 ({index}/{total_issues_evaluated}) Processing: {test_folder}")

        # Initialize Docker Executor
        docker_executor = EvaluationDockerExecutor(SWE_BENCH_DOCKER_PATH, issue_id)

        # Step 1: Run tests on the buggy version
        logging.info(f"🚧 Running test case BEFORE patch")
        docker_executor.run_docker_tests_for_evaluation(SWE_BENCH_DOCKER_PATH, test_folder_path, fixed=False)

        # Parse results for buggy version
        successful_tests_before, failed_tests_before, has_failures_before = docker_executor.parse_test_results(
            SWE_BENCH_DOCKER_PATH, fixed=False)

        total_tests_before = len(successful_tests_before) + len(failed_tests_before)

        logging.info(f"📌 {issue_id} | Before Patch | Total: {total_tests_before} | Failures: {len(failed_tests_before)}")

        # Step 2: Run tests on the fixed version
        logging.info(f"✅ Running test case AFTER patch")
        docker_executor.run_docker_tests_for_evaluation(SWE_BENCH_DOCKER_PATH, test_folder_path, fixed=True)

        # Parse results for fixed version
        successful_tests_after, failed_tests_after, has_failures_after = docker_executor.parse_test_results(
            SWE_BENCH_DOCKER_PATH, fixed=True)

        total_tests_after = len(successful_tests_after) + len(failed_tests_after)

        logging.info(f"📌 {issue_id} | After Patch | Total: {total_tests_after} | Failures: {len(failed_tests_after)}")

        # **Calculate how many failures turned into passes**
        failures_fixed = len(failed_tests_before) - len(failed_tests_after)

        # **Fail-to-Pass Validation (Fix must cause a test to pass)**
        fail_to_pass = (has_failures_before is True) and (has_failures_after is False)

        if fail_to_pass:
            successful_fix_validations += 1
            logging.info(f"🎯 {issue_id} Full Fix! All failures resolved. (Fail → Pass ✅)")
        elif failures_fixed > 0:
            successful_fix_validations += 1  # Still count as a successful validation
            logging.info(f"🎯 {issue_id} Partial Fix! {failures_fixed} failures fixed. (Fail → Partial Pass 🔄)")
        else:
            logging.warning(f"⚠️ {issue_id} No fixes detected! (Fail → Fail ❌ or Pass → Pass 🔄)")

        # Log results in CSV **with immediate flushing**
        try:
            with open(CSV_FILE_PATH, mode="a", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow([
                    issue_id, test_folder, total_tests_before, len(failed_tests_before),
                    total_tests_after, len(failed_tests_after), failures_fixed, fail_to_pass
                ])
                csv_file.flush()  # 🔥 Ensures immediate writing
        except Exception as e:
            logging.error(f"❌ Error writing to CSV for {issue_id}: {e}")

        # Always print progress update
        logging.info(f"📢 Status Update: {index}/{total_issues_evaluated} issues processed.")

finally:
    logging.info(f"📁 Final Results saved in {CSV_FILE_PATH}")

# Final Summary
logging.info(f"📊 Evaluation Summary:")
logging.info(f"🔹 Total Issues Evaluated: {total_issues_evaluated}")
logging.info(f"🔹 Successfully Validated Fixes (FAIL → PASS): {successful_fix_validations}")

# python feedback_guided_test_gen/evaluation/evaluation_runner.py --swe_bench_docker_path /Volumes/nashid-g40/ubc-works/repos/instance-3/swe-bench-docker