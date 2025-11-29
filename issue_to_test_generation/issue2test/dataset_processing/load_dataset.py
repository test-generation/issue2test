import os
import logging
from datasets import load_dataset


def process_github_issue_info(github_issue):
    """Processes a single GitHub issue to extract relevant information."""

    issue_info = {
        "instance_id": github_issue["instance_id"],
        "repo": github_issue["repo"],
        "base_commit": github_issue["base_commit"],
        "problem_statement": github_issue.get("problem_statement", ""),
    }

    logging.info(f"================ github issue {issue_info['instance_id']} ================")
    logging.info(f"repo: {issue_info['repo']}")
    logging.info(f"base commit: {issue_info['base_commit']}")
    logging.info(f"problem statement: {issue_info['problem_statement']}")

    return issue_info

def load_and_filter_issues(target_id=None):
    """
    Loads the SWE-bench Lite dataset and filters the issues by target_id if provided.

    Args:
        target_id (str, optional): The instance_id to filter the GitHub issues.
                                    If None, all issues are returned.

    Returns:
        list: A list of filtered GitHub issues.
    """
    # Load the dataset
    swe_bench_dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")

    # Filter issues based on target_id
    filtered_issues = []
    for github_issue in swe_bench_dataset:
        if target_id is not None:
            if target_id != github_issue["instance_id"]:
                continue
        filtered_issues.append(github_issue)

    return filtered_issues[0]

