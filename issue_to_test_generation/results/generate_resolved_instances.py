import json

# Input and output file names
INPUT_FILE = "resolved-per-instances-all.json"
OUTPUT_FILE = "resolved-instances-by-repo.json"

def process_resolved_instances(input_file, output_file):
    # Load the input JSON
    with open(input_file, "r") as f:
        data = json.load(f)

    # Initialize the repository-first structure
    repo_data = {}

    # Iterate through each technique and its resolved instances
    for technique, instances in data.items():
        for instance in instances:
            repo_name, _ = instance.split("__", 1)  # Extract repository name

            # Initialize repository if not exists
            if repo_name not in repo_data:
                repo_data[repo_name] = {"instances": {}}

            # Initialize instance if not exists
            if instance not in repo_data[repo_name]["instances"]:
                repo_data[repo_name]["instances"][instance] = {"techniques": []}

            # Add the technique if not already listed
            if technique not in repo_data[repo_name]["instances"][instance]["techniques"]:
                repo_data[repo_name]["instances"][instance]["techniques"].append(technique)

    # Save the processed data
    with open(output_file, "w") as f:
        json.dump({"repositories": repo_data}, f, indent=2)

    print(f"Processed data saved to {output_file}")

# Run the script
if __name__ == "__main__":
    process_resolved_instances(INPUT_FILE, OUTPUT_FILE)
