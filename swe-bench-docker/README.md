# SWE-Bench-Docker
This script simplifies the creation, customization, and management of SWE-Bench Docker containers for testing software issues.

---

## Prerequisites
- Python 3.10 or higher
- Docker installed and configured
- Required Python packages (install via `requirements.txt`)
- Input files: `files_to_copy`, `test_paths`, `test_folders` (see examples below)

---

## Setup Instructions

### 1. Create a Virtual Environment
```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./SWE-bench
```

## Usage
```bash
usage: execute_in_docker.py [-h] [--fixed] instance_id test_paths files_to_copy test_folders

positional arguments:
  instance_id    Instance ID of the issue (e.g., django__django-14752)
  test_paths     File mapping host test paths to container test paths
  files_to_copy  List of files to copy from host to container
  test_folders   File mapping project names to default parent test folder paths

optional arguments:
  -h, --help     Show help message and exit
  --fixed        Run tests on the fixed version

# Example
python execute_in_docker.py django__django-14752 test_paths files_to_copy test_folders --fixed
```

### Structure of 'files_to_copy' file
One pair per line. The pair is separated by '#'.
The two first lines should always be present, but, do not forget to replace "pytest-dev__pytest-7432" with the actual issue_id you are working on.
```txt
build_files/pytest-dev__pytest-7432/eval.sh#/testbed/eval.sh
build_files/pytest-dev__pytest-7432/patch.diff#/testbed/patch.diff
PATH/TO/SOME/FILE/ON/YOUR/MACHINE#DESTINATION/PATH/ON/DOCKER/CONTAINER
...#...
...#...
```

### Structure of 'test_paths' file
```
PATH/TO/GENERATED/TEST/FILE#DESTINATION/PATH/ON/DOCKER
...#...
```
The destionation path should not include the prefix path which is found in test_folders file (respect this rule especially for django).

Example files are given: test_folders, test_paths, and files_to_copy

### Finding missing files

This script `find_missing_files.sh` checks all instances in `build_files/` and reports if any required files are missing. It also provides a summary of affected instances.

1. Run the script:
   ```bash
   ./find_missing_files.sh
   ```

2. The script will output missing files per instance and display a summary like this:
```
⚠️  Missing files in: build_files/scikit-learn__scikit-learn-25500
   - eval.sh
   - report.json

⚠️  Missing files in: build_files/sphinx-doc__sphinx-11445
   - test_output.txt

--------------------------------------
📊 Total instances checked: 50
❌ Instances with missing files: 8 (16%)
✅ Instances with all files present: 42 (84%)
--------------------------------------
```
