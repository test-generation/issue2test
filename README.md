# Issue2Test: Generating Reproducing Test Cases from Issue Reports

Automated tools for solving GitHub issues are receiving significant attention by both researchers and practitioners, e.g., in the form of foundation models and LLM-based agents prompted with issues. A crucial step toward successfully solving an issue is creating a test case that accurately reproduces the issue. Such a test case can guide the search for an appropriate patch and help validate whether
the patch matches the issue’s intent. However, existing techniques for issue reproduction show only moderate success. This paper presents Issue2Test, an LLM-based technique for automatically generating a reproducing test case for a given issue report. Unlike automated regression test generators, which aim at creating passing tests, our approach aims at a test that fails, and that fails specifically for the reason described in the issue. To this end, Issue2Test performs three steps: (1) understand the issue and gather context (e.g., related files and project-specific guidelines) relevant for re-
producing it; (2) generate a candidate test case; and (3) iteratively refine the test case based on compilation and runtime feedback until it fails and the failure aligns with the problem described in
the issue. We evaluate Issue2Test on the SWT-bench-lite dataset, where it successfuly reproduces 30.4% of the issues, achieving a 40.1% relative improvement over the best existing technique. Our evaluation also shows that Issue2Test reproduces 28 issues that seven prior techniques fail to address, contributing a total of 68.3% of all issues reproduced by any tool. We envision our approach to contribute to enhancing the overall progress in the important task of automatically solving GitHub issues.

The project has two modules:

### issue_to_test_generation
- Use the scripts for test generation

### swe-bench-docker
- Use the scripts to run generated tests within the docker container

