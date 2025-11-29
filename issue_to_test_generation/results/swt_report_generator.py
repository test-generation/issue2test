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

# Organize data by project
project_counts = defaultdict(lambda: {"total": 0, "solved": 0})

for instance in all_instances:
    project = instance.split("__")[0]  # Extract project name
    project_counts[project]["total"] += 1
    if instance in solvable_instances:
        project_counts[project]["solved"] += 1

# Convert data to a sorted list by Total Instances (Descending)
sorted_projects = sorted(
    project_counts.items(),
    key=lambda item: item[1]["total"],
    reverse=True
)

# Generate LaTeX table with numeric alignment
latex_code = r"""\begin{table*}
    \caption{Summary of SWT Lite Instances Per Project (Sorted by Total Instances)}
    \label{tab:swt_summary}
    \centering
    \small
    \setlength\tabcolsep{3.5pt}
    \begin{tabular}{@{}lrrr@{}} \toprule
        \multirow{2}{*}{\bf Project} & \multirow{2}{*}{\bf Total} & \multirow{2}{*}{\bf Solved} & \multirow{2}{*}{\bf Accuracy (\%)} \\  
        \\ \midrule
"""

for project, counts in sorted_projects:
    total = counts["total"]
    solved = counts["solved"]
    accuracy = (solved / total * 100) if total > 0 else 0
    latex_code += f"        {project:20} & {total:4} & {solved:4} & {accuracy:6.2f} \\\\\n"

latex_code += r"""        \bottomrule
    \end{tabular}
\end{table*}
"""

# Save to file
with open("swt_lite_summary_aligned.tex", "w") as f:
    f.write(latex_code)

print("LaTeX table generated and saved as swt_lite_summary_aligned.tex")
