from typing import Tuple
from coverage.coverage import Coverage


class PycovCoverage(Coverage):
    def __init__(self, file_path: str, src_file_path: str):
        super().__init__(file_path, src_file_path, coverage_type="pycov")

    def parse_coverage_report(self) -> Tuple[list, list, float]:
        pass
