import argparse

from lance import Lance
#from issue2test import Lance
from version import __version__


def parse_args():
    parser = argparse.ArgumentParser(description=f"Lance v{__version__}")
    parser.add_argument(
        "--source-code-file",
        # required=True,
        help="Path to the source file.",
        default="../105_freemind/src/main/java/freemind/main/Base64Coding.java"
    )

    parser.add_argument(
        "--test-code-file",
        # required=True,
        help="Path to the input test file.",
        default="../105_freemind/src/test/java/tests/freemind/Base64Tests.java"
    )

    parser.add_argument(
        "--test-file-output-path",
        required=False,
        help="Path to the output test file.",
        default="",
        type=str,
    )

    parser.add_argument(
        "--code-coverage-report-path",
        # required=True,
        help="Path to the code coverage report file.",
    )

    parser.add_argument(
        "--test-execution-command",
        # required=True,
        help="The command to run tests and generate coverage report.",
        default="gradle clean build jacocoTestReport"
    )

    parser.add_argument(
        "--test-code-command-dir",
        # default=os.getcwd(),
        default="../105_freemind/src/test/java/tests/",
        help="The directory to run the test command in. Default: %(default)s.",
    )

    parser.add_argument(
        "--included-files",
        default=None,
        nargs="*",
        help='List of files to include in the coverage. For example, "--included-files library1.c library2.c." Default: %(default)s.',
    )

    parser.add_argument(
        "--model",
        # default="gpt-4o",
        # default="gpt-3.5-turbo",
        default="gpt-4o",
        help="LLM model to use. Default: %(default)s.",
    )

    parser.add_argument(
        "--coverage-type",
        default="jacoco",
        help="Type of coverage report. Default: %(default)s.",
    )

    parser.add_argument(
        "--report-filepath",
        default="test_results.html",
        help="Path to the output report file. Default: %(default)s.",
    )

    parser.add_argument(
        "--target-coverage",
        type=int,
        default=50,
        help="The desired coverage percentage. Default: %(default)s.",
    )

    parser.add_argument(
        "--maximum-iterations",
        type=int,
        default=3,
        help="The maximum number of iterations. Default: %(default)s.",
    )

    parser.add_argument(
        "--additional-instructions",
        default="",
        help="Any additional instructions you wish to append at the end of the prompt. Default: %(default)s.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    lance = Lance(args)
    lance.run()
