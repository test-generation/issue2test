import subprocess
import time


class CommandExecutor:
    @staticmethod
    def run_command(command, cwd=None):
        """
        Returns:
            tuple: A tuple containing the standard output ('stdout'), standard error ('stderr'),
            exit code ('exit_code'), and the time of the executed command ('command_start_time').
        """
        command_start_time = int(round(time.time() * 1000))

        result = subprocess.run(
            command, shell=True, cwd=cwd, text=True, capture_output=True
        )

        return (result.stdout,
                result.stderr, result.returncode, command_start_time)
