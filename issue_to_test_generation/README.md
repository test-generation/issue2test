# issue2test

### Environment setup
Create the environment using the following command:

```bash
conda env create -f issue_to_test_generation/issue2test/issue2test-env.yml --name issue2test-env
```

Then activate the environment:
```
conda activate issue2test-env
```

## Issue2test Application

The system consists of several components:

### Meta Prompt Generation
**Path:** `issue2test/meta_prompt/meta_prompt_from_json.py`  
**Description:** Constructs meta prompts from GitHub issue data for input to LLMs.

### Hypothesis Generation
**Path:** `issue2test/meta_prompt/causes_analysis_from_json.py`  
**Description:** Generates hypotheses about root causes of the issue.

### Related File Localization
**Path:** `issue2test/localization/run_find_related_files.py`  
**Description:** Identifies source code files relevant to the issue using repository structure.

### Test Code Generation via Feedback Loop
**Path:** `issue2test/feedback_guided_test_gen/main.py`  
**Description:** Synthesizes test cases using LLMs, incorporating runtime feedback and assertion validation.


### Results
- Results are in the `results` folder
- List of instances where the tool successfully generates failing-to-passing (F→P) test cases is available in `results/issue2test.csv`.
- A list of instances where other tools successfully generate failing-to-passing (F→P) test cases is provided in `results/resolved-per-instances-all.json`.
