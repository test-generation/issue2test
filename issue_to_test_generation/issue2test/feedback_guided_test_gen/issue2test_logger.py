import logging
import os
import json
from feedback_guided_test_gen import config


class LanceLogger:
    # TRAJECTORIES_PATH = config.TRAJECTORIES_DIR
    # log_file = os.path.join(TRAJECTORIES_PATH, "issue2test.log")
    log_file = None  # Will be set dynamically for each issue

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_entry = {
                "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "file": record.filename,
                "line": record.lineno,
                "message": record.getMessage(),
            }
            return json.dumps(log_entry)

    @classmethod
    def initialize_logger(cls, workspace_path):
        """
        Initializes the logger with a log file inside the workspace's trajectories folder.
        """
        trajectories_path = os.path.join(workspace_path, "trajectories")
        cls.log_file = os.path.join(trajectories_path, "issue2test.log")

        # Ensure the trajectories directory exists
        os.makedirs(trajectories_path, exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        json_formatter = cls.JSONFormatter()

        # Remove previous handlers to prevent duplicate logs
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        # File handler (JSON format)
        file_handler = logging.FileHandler(cls.log_file, mode="w")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)

        # Console handler (JSON format)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(json_formatter)
        root_logger.addHandler(stream_handler)

        # Ensure LiteLLM logs at INFO level
        logging.getLogger("LiteLLM").setLevel(logging.INFO)

        return root_logger