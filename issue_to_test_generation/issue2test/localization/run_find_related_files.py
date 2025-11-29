import os
import json
import subprocess

# Input JSON file
json_file = "input_files/swt_lite_instances-with-patch-info.json"

# Output base folder
base_output_folder = "repo_based_localization"
os.makedirs(base_output_folder, exist_ok=True)

# Load JSON file
try:
    with open(json_file, "r") as file:
        issues = json.load(file)
except json.JSONDecodeError as e:
    print(f"❌ Error: Failed to parse JSON file '{json_file}' - {e}")
    exit(1)

# Process each instance sequentially
for issue in issues:
    instance_id = issue.get("instance_id", "unknown_id")

    # Create an output folder for each instance
    instance_output_folder = os.path.join(base_output_folder, instance_id)
    os.makedirs(instance_output_folder, exist_ok=True)

    # Command to run find_related_files.py
    command = [
        "python", "issue2test/locate/find_related_files.py",
        "--target_id", instance_id,
        "--output_folder", instance_output_folder,
        "--file_level"
    ]

    print(f"🚀 Running for instance: {instance_id}")

    try:
        subprocess.run(command, check=True)
        print(f"✅ Completed: {instance_id}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error processing {instance_id}: {e}")

print("🎉 All instances processed sequentially!")
