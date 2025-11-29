import subprocess
import os
import logging
from feedback_guided_test_gen.config import SWE_BENCH_DOCKER_DIR
from feedback_guided_test_gen.tools.test_output_analyzer import parse_pytest_summary


class EvaluationDockerExecutor:
    """
    This class handles running test cases inside Docker specifically for evaluation.
    It assumes that `test_paths` already exists and does not regenerate files.
    """

    def __init__(self, swebench_folder, issue_id):
        self.swebench_folder = swebench_folder
        self.issue_id = issue_id
        self.logger = logging.getLogger(__name__)

    def run_docker_tests_for_evaluation(self,
                                        swe_bench_docker_path,
                                        test_folder,
                                        fixed=False):
        """
        Runs test cases in Docker using the existing `test_paths` file.
        - If `fixed=True`, runs the fixed version.
        - Handles errors gracefully and logs critical failures LOUDLY.
        """
        test_paths_file = os.path.join(test_folder, "test_paths")
        test_folder_mapping = os.path.join(swe_bench_docker_path, "test_folders")

        if not os.path.exists(test_paths_file):
            self.logger.error(f"❌ MISSING FILE: test_paths not found in {test_folder}")
            return {"successful_tests": [], "failed_tests": [], "has_failures": True}

        docker_command = [
            "python",
            "execute_in_docker.py",
            self.issue_id,
            test_paths_file,
            test_paths_file,
            test_folder_mapping
        ]

        if fixed:
            docker_command.append("--fixed")  # Add flag for fixed version

        os.chdir(self.swebench_folder)
        self.logger.info(f"🐳 Running Docker test: {' '.join(docker_command)}")

        try:
            result = subprocess.run(docker_command, check=True, capture_output=True, text=True)
            self.logger.info(f"✅ Docker execution successful:\n{result.stdout}")

        except subprocess.CalledProcessError as e:
            error_message = e.stderr or str(e)  # Prefer stderr for meaningful errors

            # 🚨🚨🚨 If it's a 404 Client Error or access issue, MAKE IT LOUD!!! 🚨🚨🚨
            if "404 Client Error" in error_message or "access denied" in error_message or "not found" in error_message:
                self.logger.critical("\n\n🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥")
                self.logger.critical(f"🚨🚨🚨 BIG PROBLEM: Docker Image Not Found! 🚨🚨🚨\n{error_message}")
                self.logger.critical("🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥\n\n")

            else:
                self.logger.error(f"🚨 Docker test execution failed: {error_message}")

    def parse_test_results(self,
                           swe_bench_docker_path,
                           fixed=False):
        """
        Parses the test results after running the test cases.
        - Returns the number of passing and failing tests.
        - Also returns `has_failures` (True if any test FAILED/ERROR, else False).
        """
        result_type = "fixed" if fixed else "buggy"
        test_results_filename = f"{swe_bench_docker_path}/{self.issue_id}_test_results_{result_type}"
        test_results_file = os.path.join(self.swebench_folder, test_results_filename)

        if not os.path.exists(test_results_file):
            self.logger.warning(f"⚠️ Missing Test Results File: {test_results_file}")
            return [], [], True

        parsed_results = parse_pytest_summary(test_results_file)

        successful_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] == "PASSED"]
        failed_tests = [test["name"] for test in parsed_results["tests"] if test["outcome"] in ["FAILED", "ERROR"]]

        # Get failure flag (`true` if failure/error, else `false`)
        has_failures = parsed_results.get("has_failures", False)

        return successful_tests, failed_tests, has_failures
