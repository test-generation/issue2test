from abc import ABC, abstractmethod


class Locate(ABC):
    def __init__(self, instance_id, structure, problem_statement, **kwargs):
        self.instance_id = instance_id
        self.structure = structure
        self.problem_statement = problem_statement

    @abstractmethod
    def localize(self, top_n=1, mock=False) -> tuple[list, list, list, any]:
        pass
