import logging
import os


class LanceLogger:
    log_file = os.path.join("trajectories", "issue2test.log")  # Save log in Trajectories folder

    @classmethod
    def initialize_logger(cls):
        os.makedirs(os.path.dirname(cls.log_file), exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

        # File handler
        file_handler = logging.FileHandler(cls.log_file, mode="w")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Stream handler for console output
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_formatter = logging.Formatter(log_format)
        stream_handler.setFormatter(stream_formatter)
        root_logger.addHandler(stream_handler)

        return root_logger
