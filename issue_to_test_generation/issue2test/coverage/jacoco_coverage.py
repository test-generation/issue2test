import csv
import re
from typing import Tuple
from coverage.coverage import Coverage


class JacocoCoverage(Coverage):
    def __init__(self, file_path: str, src_file_path: str):
        super().__init__(file_path, src_file_path, coverage_type="jacoco")

    def parse_coverage_report(self) -> Tuple[list, list, float]:
        """
        Parses a code coverage report to extract covered and missed line numbers for a specific file,
        and calculates the coverage percentage, based on the specified coverage report type.

        Parses a JaCoCo XML code coverage report to extract covered and missed line numbers for a specific file,
        and calculates the coverage percentage.

        Returns: Tuple[list, list, float]: A tuple containing empty lists of covered and missed line numbers,
        and the coverage percentage. The reason being the format of the report for jacoco gives the totals we do not
        sum them up. to stick with the current contract of the code and to do little change returning empty arrays.
        I expect this should bring up a discussion on introduce a factory for different CoverageProcessors. Where the
        total coverage percentage is returned to be evaluated only.
        """
        lines_covered, lines_missed = [], []

        package_name, class_name = self.extract_package_and_class_java()
        missed, covered = self.parse_missed_covered_lines_jacoco(package_name, class_name)

        total_lines = missed + covered
        coverage_percentage = (float(covered) / total_lines) if total_lines > 0 else 0

        return lines_covered, lines_missed, coverage_percentage

    def parse_missed_covered_lines_jacoco(self, package_name: str, class_name: str) -> tuple[int, int]:
        with open(self.file_path, 'r') as file:
            reader = csv.DictReader(file)
            missed, covered = 0, 0
            for row in reader:
                if row['PACKAGE'] == package_name and row['CLASS'] == class_name:
                    try:
                        missed = int(row['LINE_MISSED'])
                        covered = int(row['LINE_COVERED'])
                        break
                    except KeyError as e:
                        self.logger.error("Missing expected column in CSV: {e}")
                        raise

        return missed, covered

    def extract_package_and_class_java(self):
        """
        Very poor implementation of extracting package and class name from a java file.
        Lets move on to parsing using AST please.
        """
        package_pattern = re.compile(r'^\s*package\s+([\w\.]+)\s*;.*$')
        class_pattern = re.compile(r'^\s*public\s+class\s+(\w+).*')

        package_name = ""
        class_name = ""
        try:
            with open(self.src_file_path, 'r') as file:
                for line in file:
                    if not package_name:  # Only match package if not already found
                        package_match = package_pattern.match(line)
                        if package_match:
                            package_name = package_match.group(1)

                    if not class_name:  # Only match class if not already found
                        class_match = class_pattern.match(line)
                        if class_match:
                            class_name = class_match.group(1)

                    if package_name and class_name:  # Exit loop if both are found
                        break
        except (FileNotFoundError, IOError) as e:
            self.logger.error(f"Error reading file {self.src_file_path}: {e}")
            raise

        return package_name, class_name
