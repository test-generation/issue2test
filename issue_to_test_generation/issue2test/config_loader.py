import sys
from os.path import dirname, abspath, join, exists
from dynaconf import Dynaconf

SETTINGS_FILES = [
    "language_extensions.toml",
    "python_templates/test_generation_prompt_if_test_code_already_exixts.toml",
    "python_templates/test_headers_indentation_prompt.toml",
    "python_templates/analyze_suite_test_insert_line.toml",
    "python_templates/test_generation_prompt_github_issue.toml"
]


class SingletonSettings:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SingletonSettings, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "settings"):
            # Determine the base directory for bundled app or normal environment
            base_dir = getattr(sys, "_MEIPASS", dirname(abspath(__file__)))

            # Path to the directory containing the prompt templates
            prompt_templates_dir = join(base_dir, "prompt_templates")

            settings_files = [join(prompt_templates_dir, f) for f in SETTINGS_FILES]

            # Ensure all settings files exist
            for file_path in settings_files:
                if not exists(file_path):
                    raise FileNotFoundError(f"Settings file not found: {file_path}")

            self.settings = Dynaconf(
                envvar_prefix=False, merge_enabled=True, settings_files=settings_files
            )


def get_settings():
    return SingletonSettings().settings
