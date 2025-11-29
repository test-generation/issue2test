import json
from collections import Counter

# Input JSON file
INPUT_FILE = "resolved-instances-by-repo.json"

def load_data(file_path):
    """Load the JSON file into a Python dictionary."""
    with open(file_path, "r") as f:
        return json.load(f)

def count_repositories(data):
    """Count the number of repositories."""
    return len(data["repositories"])

def count_instances_per_repository(data):
    """Count the number of instances per repository."""
    return {repo: len(info["instances"]) for repo, info in data["repositories"].items()}

def count_total_instances(data):
    """Count total unique instances across all repositories."""
    all_instances = [instance for repo in data["repositories"].values() for instance in repo["instances"]]
    return len(set(all_instances))

def find_instances_with_multiple_techniques(data):
    """Find instances solved by multiple techniques."""
    return {
        instance: details["techniques"]
        for repo in data["repositories"].values()
        for instance, details in repo["instances"].items()
        if len(details["techniques"]) > 1
    }

def find_instances_solved_by_only_one_technique(data):
    """Find instances solved by only one technique."""
    return {
        instance: details["techniques"][0]  # Since there's only one technique
        for repo in data["repositories"].values()
        for instance, details in repo["instances"].items()
        if len(details["techniques"]) == 1
    }

def count_technique_usage(data):
    """Count how many times each technique is used across all instances."""
    technique_counter = Counter()
    for repo in data["repositories"].values():
        for details in repo["instances"].values():
            technique_counter.update(details["techniques"])
    return dict(technique_counter)

def display_analysis(data):
    """Print all extracted insights in a structured way."""
    print("\n=== Resolved Instances Analysis ===\n")

    # 1. Total number of repositories
    num_repos = count_repositories(data)
    print(f"Total Repositories: {num_repos}\n")

    # 2. Instances per repository
    repo_instances = count_instances_per_repository(data)
    print("Instances per Repository:")
    for repo, count in repo_instances.items():
        print(f"  - {repo}: {count} instances")
    print()

    # 3. Total unique instances
    total_instances = count_total_instances(data)
    print(f"Total Unique Instances: {total_instances}\n")

    # 4. Instances solved by multiple techniques
    overlapping_instances = find_instances_with_multiple_techniques(data)
    print(f"Instances Solved by Multiple Techniques ({len(overlapping_instances)} total):")
    for instance, techniques in overlapping_instances.items():
        print(f"  - {instance}: {', '.join(techniques)}")
    print()

    # 5. Instances solved by only one technique
    single_tech_instances = find_instances_solved_by_only_one_technique(data)
    print(f"Instances Solved by Only One Technique ({len(single_tech_instances)} total):")
    for instance, technique in single_tech_instances.items():
        print(f"  - {instance}: {technique}")
    print()

    # 6. Most common techniques
    technique_usage = count_technique_usage(data)
    print("Technique (Success):")
    for technique, count in sorted(technique_usage.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {technique}: {count}")
    print()

    # 7. Total number of techniques applied
    print(f"Total Unique Techniques Used: {len(technique_usage)}\n")

# Run the script
if __name__ == "__main__":
    data = load_data(INPUT_FILE)
    display_analysis(data)
