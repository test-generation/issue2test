import os
import yaml

# Get the absolute path to the `config.yaml` file
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))  # feedback_guided_test_gen/
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)  # issue2test/
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.yaml")  # Explicit path to config.yaml

# Global variables (initially None, will be set when apply_config() is called)
CONFIG_NAME = None
SWE_BENCH_DOCKER_DIR = None
ISSUE_TO_TEST_DIR = None
WORKSPACE_DIR = None
TRAJECTORIES_DIR = None
USE_META_PROMPTING = None
USE_HYPOTHESIS = None
HYPOTHESIS_INDEX = 0
MODEL = None


def load_config():
    """Loads configuration from YAML file."""
    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r") as f:
            return yaml.safe_load(f)
    raise FileNotFoundError(f"❌ Config file not found: {CONFIG_FILE_PATH}")


# Load settings from YAML
config_data = load_config()
DEFAULT_CONFIG_NAME = config_data.get("default", "dev-config")
CONFIGS = config_data.get("configs", {})


def apply_config(config_name):
    """Applies configuration based on the given config name."""
    global CONFIG_NAME, \
        SWE_BENCH_DOCKER_DIR, \
        ISSUE_TO_TEST_DIR, \
        WORKSPACE_DIR, \
        TRAJECTORIES_DIR, \
        USE_META_PROMPTING, \
        USE_HYPOTHESIS, \
        HYPOTHESIS_INDEX, \
        MODEL

    if config_name not in CONFIGS:
        raise ValueError(f"❌ Invalid config name: {config_name}. Available: {list(CONFIGS.keys())}")

    CONFIG_NAME = config_name
    selected_config = CONFIGS[config_name]

    # 🔥 Ensure these values are set
    SWE_BENCH_DOCKER_DIR = os.path.abspath(selected_config.get("SWE_BENCH_DOCKER_DIR", ""))
    ISSUE_TO_TEST_DIR = selected_config.get("ISSUE_TO_TEST", "")
    WORKSPACE_DIR = os.path.abspath(selected_config.get("WORKSPACE_DIR", ""))
    TRAJECTORIES_DIR = os.path.abspath(selected_config.get("TRAJECTORIES_DIR", ""))
    USE_META_PROMPTING = selected_config.get("USE_META_PROMPTING", False)
    USE_HYPOTHESIS = selected_config.get("USE_HYPOTHESIS", False)
    HYPOTHESIS_INDEX = selected_config.get("HYPOTHESIS_INDEX", 0)
    MODEL = selected_config.get("MODEL", "")

    print(f"✅ Config Applied: {CONFIG_NAME}")  # Debug print
    return CONFIG_NAME  # Return config name for debugging/logging


def get_config():
    """Returns the current config values, ensuring they are initialized."""
    if CONFIG_NAME is None:
        raise RuntimeError("❌ Configuration has not been initialized. Call apply_config(config_name) first!")

    return {
        "CONFIG_NAME": CONFIG_NAME,
        "SWE_BENCH_DOCKER_DIR": SWE_BENCH_DOCKER_DIR,
        "ISSUE_TO_TEST_DIR": ISSUE_TO_TEST_DIR,
        "WORKSPACE_DIR": WORKSPACE_DIR,
        "TRAJECTORIES_DIR": TRAJECTORIES_DIR,
        "USE_META_PROMPTING": USE_META_PROMPTING,
        "USE_HYPOTHESIS": USE_HYPOTHESIS,
        "HYPOTHESIS_INDEX": HYPOTHESIS_INDEX,
        "MODEL": MODEL
    }


# Constants (Independent of YAML Config)
RETRY_LIMIT = 5
MAX_RETRIES_LLM = 5
MAX_LLM_INVOCATION = 20
DOCKER_EXECUTION_TIME_OUT_IN_SECONDS = 1800

# Debugging: Print selected config (only when running config.py directly)
if __name__ == "__main__":
    print(f"📂 Project Root: {PROJECT_ROOT}")
    print(f"📂 Using Config File: {CONFIG_FILE_PATH}")
    print(f"🛠  Default Config Name: {DEFAULT_CONFIG_NAME} (Will be overridden by apply_config(config_name))")
    print(f"🔹 SWE_BENCH_DOCKER_DIR: {SWE_BENCH_DOCKER_DIR}")
    print(f"🔹 WORKSPACE_DIR: {WORKSPACE_DIR}")
    print(f"🔹 TRAJECTORIES_DIR: {TRAJECTORIES_DIR}")
    print(f"🔹 RETRY_LIMIT: {RETRY_LIMIT}")
    print(f"🔹 MAX_RETRIES_LLM: {MAX_RETRIES_LLM}")
    print(f"🔹 MAX_LLM_INVOCATION: {MAX_LLM_INVOCATION}")
    print(f"🔹 DOCKER_EXECUTION_TIME_OUT_IN_SECONDS: {DOCKER_EXECUTION_TIME_OUT_IN_SECONDS}")
