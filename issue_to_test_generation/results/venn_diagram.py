import json
import csv
import matplotlib.pyplot as plt



# Load SWT Lite instances
with open("swt_lite_instances.json", "r") as f:
    swt_lite_instances = {instance["instance_id"] for instance in json.load(f)}

# Load resolved instances from different techniques
with open("resolved-per-instances.json", "r") as f:
    technique_data = json.load(f)

# Load "Issue2Test" (our technique) from issue2test.csv
with open("issue2test.csv", "r") as f:
    issue2test_issues = {row.strip() for row in f} & swt_lite_instances  # Filter only SWT Lite issues

# Define data for the Venn diagram (filtering only SWT Lite instances)
data = {
    "LIBRO": set(technique_data.get("LIBRO", [])) & swt_lite_instances,
    "AutoCodeRover": set(technique_data.get("AutoCodeRover", [])) & swt_lite_instances,
    "Aider": set(technique_data.get("Aider", [])) & swt_lite_instances,
    "SWE-Agent+": set(technique_data.get("SWE-Agent+", [])) & swt_lite_instances,
    "SWE-Agent": set(technique_data.get("SWE-Agent", [])) & swt_lite_instances,
    "Issue2Test (Ours)": issue2test_issues if issue2test_issues else set(),
}

# 🛠 Debugging: Print instance counts
print("\n🔍 Processed Data for Petal Venn Diagram:")
for key, value in data.items():
    print(f"{key}: {len(value)} instances")

# 🎨 Create a professional 6-set petal Venn diagram
plt.figure(figsize=(12, 10))
venn(
    data,
    fmt="{size}",  # Show number of elements in each set
    cmap="plasma",  # Use a professional colormap for better readability
    fontsize=12,  # Adjust font size for clarity
    legend_loc="upper right",  # Place legend at a clear spot
    figsize=(10, 10),
)

# 📌 Final formatting
plt.title("Petal-Style 6-Set Venn Diagram for SWT Lite Issues", fontsize=14, fontweight="bold")
plt.savefig("swt_lite_6set_petal_venn_pyvenn.png", dpi=600, bbox_inches="tight")
plt.show()
