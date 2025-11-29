import argparse
import json
import os

from chat_completion import query_model
from parsing_utils import parse_reason_sets


def root_cause_analysis(issue_id, project_name, issue_description):
    """Runs root cause analysis using an LLM and saves extracted reasons."""

    # Load prompt template
    with open("prompts/cause_analysis_prompt", "r") as cap:
        ca_prompt = cap.read()

    # Construct system and user prompts
    system_prompt = "You are an experienced software engineer, you can analyze, understand, write, and test software."
    user_prompt = ca_prompt.replace("###ISSUE DESCRIPTION###", issue_description).replace("###PROJECT NAME###", project_name)

    # Query the language model
    response = query_model(system_prompt, user_prompt, model = "gpt-4o-mini")

    # Extract structured reasons
    extracted_reasons = parse_reason_sets(response)

    # Ensure output directory exists
    output_dir = "extracted_causes_swt_lite"
    os.makedirs(output_dir, exist_ok=True)

    # Save results
    output_path = os.path.join(output_dir, f"{issue_id}.json")
    with open(output_path, "w") as aii:
        json.dump(extracted_reasons, aii, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform root cause analysis on issues from a JSON file.")
    parser.add_argument("json_file", nargs="?", default="input_files/swt_lite_instances.json",
                        help="Path to the input JSON file containing issues (default: input_files/swt_lite_instances.json)")

    args = parser.parse_args()

    # Ensure the input file exists
    if not os.path.exists(args.json_file):
        print(f"Error: JSON file '{args.json_file}' not found.")
        exit(1)

    # Load JSON file
    with open(args.json_file, "r") as file:
        try:
            issues = json.load(file)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON file '{args.json_file}' - {e}")
            exit(1)

    # Process each issue
    for issue in issues:
        issue_id = issue.get("instance_id", "unknown_id")
        project_name = issue.get("repo", "unknown/repo").split("/")[1]  # Extract project name
        issue_description = issue.get("problem_statement", "").strip()

        if not issue_description:
            print(f"Skipping {issue_id} (no problem statement found)")
            continue

        print(f"Processing issue: {issue_id} from {project_name}")
        root_cause_analysis(issue_id, project_name, issue_description)

    print("Root cause analysis completed for all issues.")
