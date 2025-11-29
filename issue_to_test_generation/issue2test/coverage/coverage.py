import csv
import os
import re
from typing import Literal, Tuple
from abc import ABC, abstractmethod

from custom_errors import FatalError
from issue2test_logger import LanceLogger


class Coverage(ABC):
    def __init__(self, file_path: str, src_file_path: str, coverage_type: Literal["pycov", "jacoco"]):
        self.file_path = file_path
        self.src_file_path = src_file_path
        self.coverage_type = coverage_type
        self.logger = LanceLogger.initialize_logger(__name__)
        self.validate_attributes()

    def validate_attributes(self):
        if not all([self.file_path, self.src_file_path, self.coverage_type]):
            raise FatalError("Fatal: One or more required attributes are None.")

    def process_coverage_report(
            self, time_of_test_execution_command: int) -> Tuple[list, list, float]:
        """
        Returns:
            Tuple[list, list, float]: A tuple containing lists of covered and missed line numbers, and the coverage percentage.
        """
        self.verify_report_update(time_of_test_execution_command)
        return self.parse_coverage_report()

    def verify_report_update(self, time_of_test_execution_command: int):
        """
        Returns:
            Tuple[list, list, float]: A tuple containing lists of covered and missed line numbers, and the coverage percentage.

        Raises:
            AssertionError: If the coverage report does not exist or was not updated after the test command.
        """
        self.logger.info(f"Checking if coverage report exists at: {self.file_path}")

        if not os.path.exists(self.file_path):
            self.logger.error(f"Fatal: Coverage report \"{self.file_path}\" was not generated.")
            raise AssertionError(f'Fatal: Coverage report "{self.file_path}" was not generated.')

        # Convert file modification time to milliseconds for comparison
        file_mod_time_ms = int(round(os.path.getmtime(self.file_path) * 1000))

        assert (
                file_mod_time_ms > time_of_test_execution_command
        ), (f"Fatal: The coverage report file was not updated after running the the test execution command. "
            f"file_mod_time_ms: {file_mod_time_ms}, "
            f"time_of_test_execution_command: {time_of_test_execution_command}. "
            f"{file_mod_time_ms > time_of_test_execution_command}")

    @abstractmethod
    def parse_coverage_report(self) -> Tuple[list, list, float]:
        pass
