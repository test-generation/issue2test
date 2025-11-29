import json
import re

def extract_file_names_from_patch(patch):
    """
    Extract all filenames from the diff --git lines in a patch.
    """
    return re.findall(r'diff --git a/(.*?) b/', patch)

def augment_patch_info(input_file, output_file):
    """
    Reads a JSON file, augments it with patch_files and test_files, and writes to an output file.
    """
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    for entry in data:
        entry["source_files"] = extract_file_names_from_patch(entry.get("patch", ""))
        entry["test_files"] = extract_file_names_from_patch(entry.get("test_patch", ""))
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    input_json = "swt_lite_instances.json"  # Replace with your input JSON filename
    output_json = "swt_lite_instances-with-patch-info.json"  # Replace with your desired output JSON filename
    augment_patch_info(input_json, output_json)
    print(f"Augmented JSON with patch information saved to {output_json}")
