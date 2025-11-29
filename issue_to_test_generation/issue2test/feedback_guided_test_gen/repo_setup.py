import os
import uuid
import subprocess
from repo_metadata.get_repo_structure import create_structure

repo_to_top_folder = {
    "django/django": "django",
    "sphinx-doc/sphinx": "sphinx",
    "scikit-learn/scikit-learn": "scikit-learn",
    "sympy/sympy": "sympy",
    "pytest-dev/pytest": "pytest",
    "matplotlib/matplotlib": "matplotlib",
    "astropy/astropy": "astropy",
    "pydata/xarray": "xarray",
    "mwaskom/seaborn": "seaborn",
    "psf/requests": "requests",
    "pylint-dev/pylint": "pylint",
    "pallets/flask": "flask",
}

def checkout_commit(repo_path, commit_id):
    """Checkout the specified commit in the given local git repository."""
    try:
        print(f"Checking out commit {commit_id} in repository at {repo_path}...")
        subprocess.run(["git", "-C", repo_path, "checkout", commit_id], check=True)
        print("Commit checked out successfully.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"An error occurred while running git command: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: {e}")

def clone_repo(repo_name, repo_workspace):
    """Clone the given repository from GitHub to the workspace directory."""
    try:
        print(f"Cloning repository from https://github.com/{repo_name}.git to {repo_workspace}/{repo_to_top_folder[repo_name]}...")
        subprocess.run(
            ["git", "clone", f"https://github.com/{repo_name}.git", f"{repo_workspace}/{repo_to_top_folder[repo_name]}"],
            check=True,
        )
        print("Repository cloned successfully.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"An error occurred while running git command: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: {e}")

def setup_repo_from_github_issue(repo_name, commit_id, instance_id, repo_workspace="workspace"):
    """
    Sets up the repository for a given GitHub issue.
    This involves cloning the repository, checking out the specified commit, and generating the project structure.

    :param repo_name: Name of the GitHub repository (e.g., "django/django").
    :param commit_id: Commit ID to checkout for the issue.
    :param instance_id: Unique ID of the GitHub issue.
    :param repo_workspace: Directory where the repository should be cloned (default: "workspace").
    :return: Dictionary representing the project structure.
    """
    # Create a temporary folder with a UUID to avoid collisions
    unique_workspace = os.path.join(repo_workspace, str(uuid.uuid4()))

    # Ensure the workspace doesn't already exist
    assert not os.path.exists(unique_workspace), f"{unique_workspace} already exists"

    # Create the workspace directory
    os.makedirs(unique_workspace)

    # Clone the repository and checkout the specific commit
    clone_repo(repo_name, unique_workspace)
    repo_top_folder = os.path.join(unique_workspace, repo_to_top_folder[repo_name])
    checkout_commit(repo_top_folder, commit_id)

    # Extract the project structure (parse the repo for classes, functions, and file structure)
    structure = create_structure(repo_top_folder)

    return {
        "repo": repo_name,
        "base_commit": commit_id,
        "structure": structure,
        "instance_id": instance_id,
        "repo_base_path": unique_workspace  # Return the full path including the UUID
    }

