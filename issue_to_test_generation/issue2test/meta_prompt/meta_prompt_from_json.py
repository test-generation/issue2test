import argparse
import json
import os

from chat_completion import query_model


def generate_unit_test_guideline(issue_id,
                                 project_name,
                                 project_version,
                                 issue_description):
    """Generates a unit test guideline using an LLM and saves it as a Markdown file."""

    # Load meta-prompt template
    with open("prompts/meta_prompt", "r") as prompt_file:
        meta_prompt = prompt_file.read()

    # Construct system and user prompts
    system_prompt = "You are an experienced software engineer specializing in automated unit test generation."
    user_prompt = (
        meta_prompt.replace("{project_name}", project_name)
        .replace("{version}", project_version)
        .replace("{problem_statement}", issue_description)
    )

    # Query the language model
    response = query_model(system_prompt,
                           user_prompt,
                           model="gpt-4o-mini")

    # Ensure output directories exist
    output_dir = "generated_unit_test_guidelines"
    os.makedirs(output_dir, exist_ok=True)

    # Define output paths
    md_filename = f"{issue_id}.md"
    json_filename = f"{issue_id}.json"
    md_output_path = os.path.join(output_dir, md_filename)
    json_output_path = os.path.join(output_dir, json_filename)

    # Save Markdown file
    with open(md_output_path, "w") as md_file:
        md_file.write(f"project_name: {project_name}\n")
        md_file.write(f"version: {project_version}\n\n")
        md_file.write(response)  # The response should already be in Markdown format

    # Save metadata in JSON file
    with open(json_output_path, "w") as json_file:
        json.dump({
            "project_name": project_name,
            "version": project_version,
            "unit_test_guideline_file": md_filename
        }, json_file, indent=4)

    print(f"Saved Markdown: {md_output_path}")
    print(f"Saved Metadata: {json_output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate unit test guidelines for issues from a JSON file.")
    parser.add_argument("json_file",
                        nargs="?",
                        default="input_files/swt_lite_instances.json",
                        help="Path to the input JSON file containing issues (default: input_files/issues.json)")

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
        project_name = issue.get("repo", "unknown/repo").split("/")[-1]  # Extract project name
        project_version = issue.get("version", "unknown_version")
        issue_description = issue.get("problem_statement", "").strip()

        if project_name == "django":
            continue

        if not issue_description:
            print(f"Skipping {issue_id} (no problem statement found)")
            continue

        print(f"Processing issue: {issue_id} from {project_name} (version {project_version})")
        generate_unit_test_guideline(issue_id, project_name, project_version, issue_description)

    print("Unit test guideline generation completed for all issues.")
