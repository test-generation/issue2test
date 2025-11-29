import json
import csv

# Load SWT Lite instances
with open("swt_lite_instances.json", "r") as f:
    swt_lite_instances = {instance["instance_id"] for instance in json.load(f)}

# Load resolved instances from different techniques
with open("resolved-per-instances-all.json", "r") as f:
    technique_data = json.load(f)

# Load "Issue2Test" (our technique) from issue2test.csv
with open("issue2test.csv", "r") as f:
    issue2test_issues = {row.strip() for row in f} & swt_lite_instances  # Filter only SWT Lite issues

# Define data for the Venn diagram (filtering only SWT Lite instances)
data = {
    "LIBRO": list(set(technique_data.get("LIBRO", [])) & swt_lite_instances),
    "AutoCodeRover": list(set(technique_data.get("AutoCodeRover", [])) & swt_lite_instances),
    "SWE-Agent+": list(set(technique_data.get("SWE-Agent+", [])) & swt_lite_instances),
    "Auto-TDD": list(set(technique_data.get("Auto-TDD", [])) & swt_lite_instances),
    "Issue2Test": list(issue2test_issues if issue2test_issues else set()),
}

# Save to CSV for R
with open("venn_data.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Technique", "Instances"])
    for key, values in data.items():
        for v in values:
            writer.writerow([key, v])

print("✅ Data saved to venn_data.csv for R!")
