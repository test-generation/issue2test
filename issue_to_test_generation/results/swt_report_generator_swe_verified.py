import json
import csv
from collections import defaultdict

# Load the complete list of instances from swt_lite_instances.json
with open("swt_lite_instances.json", "r") as f:
    swt_lite_instances = json.load(f)

# Extract all instances from JSON
all_instances = {instance["instance_id"] for instance in swt_lite_instances}

# Load solvable instances from issue2test.csv
solvable_instances = set()
with open("issue2test.csv", "r") as f:
    reader = csv.reader(f)
    for row in reader:
        solvable_instances.add(row[0].strip())  # First column has the instance_id

# Load verified common issues
with open("common_issues_between_lite_and_verified.json", "r") as f:
    verified_issues = json.load(f)

# Extract verified instance IDs
verified_instances = {issue["instance_id"] for issue in verified_issues}

# Organize data by project
project_counts = defaultdict(lambda: {"verified": 0, "total": 0, "verified_solved": 0, "solved": 0})

for instance in all_instances:
    project = instance.split("__")[0]  # Extract project name
    project_counts[project]["total"] += 1
    if instance in verified_instances:
        project_counts[project]["verified"] += 1
    if instance in solvable_instances:
        project_counts[project]["solved"] += 1
        if instance in verified_instances:
            project_counts[project]["verified_solved"] += 1  # Count how many verified issues we can solve

# Convert data to a sorted list by Verified (Descending)
sorted_projects = sorted(
    project_counts.items(),
    key=lambda item: item[1]["verified"],
    reverse=True
)

# Compute total sums for final row
total_verified = sum(counts["verified"] for _, counts in sorted_projects)
total_total = sum(counts["total"] for _, counts in sorted_projects)
total_verified_solved = sum(counts["verified_solved"] for _, counts in sorted_projects)
total_solved = sum(counts["solved"] for _, counts in sorted_projects)

# Compute overall accuracies
overall_verified_accuracy = (total_verified_solved / total_verified * 100) if total_verified > 0 else 0
overall_accuracy = (total_solved / total_total * 100) if total_total > 0 else 0

# Generate LaTeX table with a vertical border after "Project"
latex_code = r"""\begin{table*}
    \caption{Summary of SWT Lite Instances Per Project (Including Verified Issues)}
    \label{tab:swt_summary}
    \centering
    \small
    \setlength\tabcolsep{4.5pt}
    \begin{tabular}{@{}l|ccc|ccc@{}} \toprule
        \multirow{2}{*}{\bf Project} & \multicolumn{3}{c}{\bf Verified} & \multicolumn{3}{c}{\bf Overall} \\  
        \cmidrule(lr){2-4} \cmidrule(lr){5-7}
        & \bf Issues & \bf F->P & \bf Accuracy (\%) & \bf Issues & \bf F->P & \bf Accuracy (\%) \\  
        \midrule
"""

for project, counts in sorted_projects:
    verified = counts["verified"]
    total = counts["total"]
    verified_solved = counts["verified_solved"]
    solved = counts["solved"]
    verified_accuracy = (verified_solved / verified * 100) if verified > 0 else 0
    accuracy = (solved / total * 100) if total > 0 else 0

    latex_code += f"        {project:20} & {verified:4} & {verified_solved:4} & {verified_accuracy:6.2f} & {total:4} & {solved:4} & {accuracy:6.2f} \\\\\n"

# Add final row for total accuracy
latex_code += r"""        \midrule
        \textbf{Total/Average} &"""
latex_code += f" {total_verified:4} & {total_verified_solved:4} & {overall_verified_accuracy:6.2f} & {total_total:4} & {total_solved:4} & {overall_accuracy:6.2f} \\\\\n"

latex_code += r"""        \bottomrule
    \end{tabular}
\end{table*}
"""

# Save LaTeX table to file
with open("swt_lite_summary_final.tex", "w") as f:
    f.write(latex_code)

print("Updated LaTeX table generated and saved as swt_lite_summary_final.tex")
