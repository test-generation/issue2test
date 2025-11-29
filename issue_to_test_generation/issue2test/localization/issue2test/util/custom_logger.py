import logging
import os


class CustomLogger:
    @classmethod
    def get_logger(cls, name):
        logger = logging.getLogger(name)
        logger.setLevel(
            logging.DEBUG
        )  # Set the logger to handle all messages of DEBUG level and above

        # Specify the log file path
        log_file_path = "run.log"

        # Check if handlers are already set up to avoid adding them multiple times
        if not logger.handlers:
            # File handler for writing to a file
            file_handler = logging.FileHandler(
                log_file_path, mode="w"
            )  # Use 'w' to overwrite the log file on each run
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # Stream handler for output to the console
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(
                logging.INFO
            )  # Set this to DEBUG if you want to see DEBUG messages in the console
            stream_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            stream_handler.setFormatter(stream_formatter)
            logger.addHandler(stream_handler)

        return logger