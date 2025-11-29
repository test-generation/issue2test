import logging
import re
from constants_config import MAX_DISPLAY_LINES

def extract_error_message_python(fail_message):
    try:
        pattern = r"={3,} FAILURES ={3,}(.*?)(={3,}|$)"
        match = re.search(pattern, fail_message, re.DOTALL)
        if match:
            err_str = match.group(1).strip("\n")
            error_lines = err_str.split("\n")
            if len(error_lines) > MAX_DISPLAY_LINES:
                # limit the number of lines to display so that we do not exceed the context window limit
                err_str = "...\n" + "\n".join(error_lines[-MAX_DISPLAY_LINES:])
            return err_str
        return ""
    except Exception as e:
        logging.error(f"Error extracting error message: {e}")
        return ""
