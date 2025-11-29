import argparse
import json
import logging
import os

from issue2test.locate.combine_predicted_locations import merge
from datasets import load_dataset

from issue2test.locate.locate_test_files_with_llm import LLMLocateTestFiles
from issue2test.locate.locate_test_functions_with_llm import LLMLocateTestFunctions
from issue2test.util.preprocess_data import (
    filter_none_python,
    filter_out_test_files,
)
from issue2test.util.utils import load_json, load_jsonl
from issue2test.repo_metadata.get_repo_structure import (
    get_project_structure_from_scratch,
)

# SET THIS IF YOU WANT TO USE THE PREPROCESSED FILES
PROJECT_FILE_LOC = os.environ.get("PROJECT_FILE_LOC", None)


def locate_test_code_files(args):
    swe_bench_dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")

    if args.start_file:
        start_file_locs = load_jsonl(args.start_file)

    for github_issue in swe_bench_dataset:
        if args.target_id is not None:
            if args.target_id != github_issue["instance_id"]:
                continue

        if PROJECT_FILE_LOC is not None:
            project_file = os.path.join(PROJECT_FILE_LOC,
                                        github_issue["instance_id"] + ".json")
            project_data = load_json(project_file)
        else:
            # we need to get the project structure directly
            project_data = get_project_structure_from_scratch(
                github_issue["repo"],
                github_issue["base_commit"],
                github_issue["instance_id"],
                "workspace"
            )

        instance_id = project_data["instance_id"]

        logging.info(f"================ related test code files for {instance_id} ================")

        repo_bench_data = [x for x in swe_bench_dataset if x["instance_id"] == instance_id][0]
        problem_statement = repo_bench_data["problem_statement"]
        structure = project_data["structure"]
        filter_none_python(structure)

        # some basic filtering steps
        # filter out test files (unless its pytest)
        if not project_data["instance_id"].startswith("pytest"):
            filter_out_test_files(structure)

        found_files = []
        found_related_locs = []
        found_edit_locs = []

        additional_artifact_loc_file = None
        additional_artifact_loc_related = None
        additional_artifact_loc_edit_location = None
        file_trajectory, related_loc_traj, edit_loc_traj = {}, {}, {}

        # file level localization
        if args.file_level:
            fl = LLMLocateTestFiles(
                project_data["instance_id"],
                structure,
                problem_statement,
            )
            found_files, additional_artifact_loc_file, file_trajectory = fl.localize_test_files(
                mock=args.mock
            )
        else:
            # assume start_file is provided
            for locs in start_file_locs:
                if locs["instance_id"] == project_data["instance_id"]:
                    found_files = locs["found_files"]
                    additional_artifact_loc_file = locs["additional_artifact_loc_file"]
                    file_trajectory = locs["file_trajectory"]

                    if "found_related_locs" in locs:
                        found_related_locs = locs["found_related_locs"]
                        additional_artifact_loc_related = locs[
                            "additional_artifact_loc_related"
                        ]
                        related_loc_traj = locs["related_loc_traj"]
                    break

        # related functions/methods localization within test files
        if args.related_level:
            if len(found_files) != 0:
                pred_files = found_files[: args.top_n]
                fl = LLMLocateTestFunctions(
                    project_data["instance_id"],
                    structure,
                    problem_statement,
                )

                additional_artifact_loc_related = []
                found_related_locs = []
                related_loc_traj = {}

                if args.compress:
                    (
                        found_related_locs,
                        additional_artifact_loc_related,
                        related_loc_traj,
                    ) = fl.localize_test_functions_for_files(
                        pred_files,
                        mock=args.mock,
                    )
                    additional_artifact_loc_related = [additional_artifact_loc_related]
                else:
                    assert False, "Not implemented yet."

        if args.fine_grain_line_level:
            # More granular localization within test files
            pred_files = found_files[: args.top_n]
            fl = LLMLocateTestFunctions(
                instance_id,
                structure,
                problem_statement,
            )
            coarse_found_locs = {}
            for i, pred_file in enumerate(pred_files):
                if len(found_related_locs) > i:
                    coarse_found_locs[pred_file] = found_related_locs[i]
            (
                found_edit_locs,
                additional_artifact_loc_edit_location,
                edit_loc_traj,
            ) = fl.localize_test_functions_for_files(
                pred_files,
                mock=args.mock
            )

            additional_artifact_loc_edit_location = [
                additional_artifact_loc_edit_location
            ]

        with open(args.output_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "instance_id": project_data["instance_id"],
                        "found_files": found_files,
                        "additional_artifact_loc_file": additional_artifact_loc_file,
                        "file_trajectory": file_trajectory,
                        "found_related_locs": found_related_locs,
                        "additional_artifact_loc_related": additional_artifact_loc_related,
                        "related_loc_traj": related_loc_traj,
                        "found_edit_locs": found_edit_locs,
                        "additional_artifact_loc_edit_location": additional_artifact_loc_edit_location,
                        "edit_loc_traj": edit_loc_traj,
                    }
                )
                + "\n"
            )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--output_folder",
                        type=str,
                        required=True)

    parser.add_argument("--output_file",
                        type=str,
                        default="loc_test_outputs.jsonl")

    parser.add_argument(
        "--start_file",
        type=str,
        help="""previous output file to start with to reduce
        the work, should use in combination without --file_level""",
    )

    parser.add_argument("--file_level",
                        action="store_true")

    parser.add_argument("--related_level",
                        action="store_true")

    parser.add_argument("--fine_grain_line_level",
                        action="store_true")

    parser.add_argument("--top_n",
                        type=int,
                        default=3)

    parser.add_argument("--temperature",
                        type=float,
                        default=0.0)

    parser.add_argument("--num_samples",
                        type=int,
                        default=1)

    parser.add_argument("--compress",
                        action="store_true")

    parser.add_argument("--merge",
                        action="store_true")

    parser.add_argument("--add_space",
                        action="store_true")

    parser.add_argument("--no_line_number",
                        action="store_true")

    parser.add_argument("--sticky_scroll",
                        action="store_true")

    parser.add_argument("--context_window",
                        type=int,
                        default=10)

    parser.add_argument("--target_id",
                        type=str)

    parser.add_argument("--mock",
                        action="store_true",
                        help="Mock run to compute prompt tokens.")

    args = parser.parse_args()

    args.output_file = os.path.join(args.output_folder, args.output_file)

    assert not os.path.exists(args.output_file), "Output file already exists"

    assert not (args.file_level and args.start_file), \
        "Cannot use both file_level and start_file"

    assert not (
            args.file_level and args.fine_grain_line_level and not args.related_level
    ), "Cannot use both file_level and fine_grain_line_level without related_level"

    assert not (
            (not args.file_level) and (not args.start_file)
    ), "Must use either file_level or start_file"

    os.makedirs(args.output_folder, exist_ok=True)

    # write the arguments
    with open(f"{args.output_folder}/args.json", "w") as f:
        json.dump(vars(args), f, indent=4)

    logging.basicConfig(
        filename=f"{args.output_folder}/localize.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    if args.merge:
        merge(args)
    else:
        locate_test_code_files(args)


if __name__ == "__main__":
    main()
