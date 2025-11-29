import re
from collections import defaultdict, namedtuple
from collections.abc import MutableMapping
from feedback_guided_test_gen.search import search_utils
from feedback_guided_test_gen.search.search_utils import SearchResult
import difflib  # Added for fuzzy searching

from tools.search_utils import get_direct_and_aliased_imports

LineRange = namedtuple("LineRange", ["start", "end"])

ClassIndexType = MutableMapping[str, list[tuple[str, LineRange]]]
ClassFuncIndexType = MutableMapping[str, MutableMapping[str, list[tuple[str, LineRange]]]]
FuncIndexType = MutableMapping[str, list[tuple[str, LineRange]]]

RESULT_SHOW_LIMIT = 5


class SearchManager:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.parsed_files: list[str] = []
        self.class_index: ClassIndexType = {}
        self.class_func_index: ClassFuncIndexType = {}
        self.function_index: FuncIndexType = {}
        self._build_index()

    def _build_index(self):
        self._update_indices(*self._build_python_index())

    def _update_indices(
            self,
            class_index: ClassIndexType,
            class_func_index: ClassFuncIndexType,
            function_index: FuncIndexType,
            parsed_files: list[str],
    ) -> None:
        self.class_index.update(class_index)
        self.class_func_index.update(class_func_index)
        self.function_index.update(function_index)
        self.parsed_files.extend(parsed_files)

    def _build_python_index(
            self,
    ) -> tuple[ClassIndexType, ClassFuncIndexType, FuncIndexType, list[str]]:
        class_index: ClassIndexType = defaultdict(list)
        class_func_index: ClassFuncIndexType = defaultdict(lambda: defaultdict(list))
        function_index: FuncIndexType = defaultdict(list)

        py_files = search_utils.find_python_files(self.project_path)
        parsed_py_files = []
        for py_file in py_files:
            file_info = search_utils.parse_python_file(py_file)
            if file_info is None:
                continue
            parsed_py_files.append(py_file)
            classes, class_to_funcs, top_level_funcs = file_info

            for c, start, end in classes:
                class_index[c].append((py_file, LineRange(start, end)))

            for c, class_funcs in class_to_funcs.items():
                for f, start, end in class_funcs:
                    class_func_index[c][f].append((py_file, LineRange(start, end)))

            for f, start, end in top_level_funcs:
                function_index[f].append((py_file, LineRange(start, end)))

        return class_index, class_func_index, function_index, parsed_py_files

    def file_line_to_class_and_func(
            self, file_path: str, line_no: int
    ) -> tuple[str | None, str | None]:
        for class_name in self.class_func_index:
            func_dict = self.class_func_index[class_name]
            for func_name, func_info in func_dict.items():
                for file_name, (start, end) in func_info:
                    if file_name == file_path and start <= line_no <= end:
                        return class_name, func_name

        for func_name in self.function_index:
            for file_name, (start, end) in self.function_index[func_name]:
                if file_name == file_path and start <= line_no <= end:
                    return None, func_name

        return None, None

    def _search_func_in_class(
            self, function_name: str, class_name: str
    ) -> list[SearchResult]:
        result: list[SearchResult] = []
        if class_name not in self.class_func_index:
            return result
        if function_name not in self.class_func_index[class_name]:
            return result
        for fname, (start, end) in self.class_func_index[class_name][function_name]:
            func_code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, class_name, function_name, func_code)
            result.append(res)
        return result

    def _search_func_in_all_classes(self, function_name: str) -> list[SearchResult]:
        result: list[SearchResult] = []
        for class_name in self.class_index:
            res = self._search_func_in_class(function_name, class_name)
            result.extend(res)
        return result

    def _search_top_level_func(self, function_name: str) -> list[SearchResult]:
        result: list[SearchResult] = []
        if function_name not in self.function_index:
            return result

        for fname, (start, end) in self.function_index[function_name]:
            func_code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, None, function_name, func_code)
            result.append(res)
        return result

    def _search_func_in_code_base(self, function_name: str) -> list[SearchResult]:
        result: list[SearchResult] = []
        top_level_res = self._search_top_level_func(function_name)
        class_res = self._search_func_in_all_classes(function_name)
        result.extend(top_level_res)
        result.extend(class_res)
        return result

    ###############################
    ### Interfaces ################
    ###############################

    def get_class_full_snippet(self, class_name: str) -> tuple[str, str, bool]:
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False

        search_res: list[SearchResult] = []
        for fname, (start, end) in self.class_index[class_name]:
            code = search_utils.get_code_snippets(fname, start, end)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            return tool_result, summary, False

        tool_result = f"Found {len(search_res)} classes with name {class_name} in the codebase:\n\n"
        summary = tool_result
        if len(search_res) > 2:
            tool_result += "Too many results, showing full code for 2 of them:\n"
        for idx, res in enumerate(search_res[:2]):
            res_str = res.to_tagged_str(self.project_path)
            tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```"
        return tool_result, summary, True

    def search_class(self, class_name: str) -> tuple[str, str, bool]:
        summary = f"Class {class_name} did not appear in the codebase."
        tool_result = f"Could not find class {class_name} in the codebase."

        if class_name not in self.class_index:
            return tool_result, summary, False

        search_res: list[SearchResult] = []
        for fname, _ in self.class_index[class_name]:
            code = search_utils.get_class_signature(fname, class_name)
            res = SearchResult(fname, class_name, None, code)
            search_res.append(res)

        if not search_res:
            return tool_result, summary, False

        tool_result = f"Found {len(search_res)} classes with name {class_name} in the codebase:\n\n"
        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_result += "They appeared in the following files:\n"
            tool_result += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_result += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        summary = f"The tool returned information about class `{class_name}`."
        return tool_result, summary, True

    def search_class_in_file(self, class_name, file_name: str) -> tuple[str, str, bool]:
        candidate_py_abs_paths = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        search_res: list[SearchResult] = []
        for fname, (start_line, end_line) in self.class_index[class_name]:
            if fname in candidate_py_abs_paths:
                class_code = search_utils.get_code_snippets(fname, start_line, end_line)
                res = SearchResult(fname, class_name, None, class_code)
                search_res.append(res)

        if not search_res:
            tool_output = f"Could not find class {class_name} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} classes with name {class_name} in file {file_name}:\n\n"
        summary = tool_output
        for idx, res in enumerate(search_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_method_in_file(
            self, method_name: str, file_name: str
    ) -> tuple[str, str, bool]:
        candidate_py_abs_paths = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_abs_paths:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"The method {method_name} does not appear in the codebase."
            summary = tool_output
            return tool_output, summary, False

        filtered_res: list[SearchResult] = [
            res for res in search_res if res.file_path in candidate_py_abs_paths
        ]

        if not filtered_res:
            tool_output = (
                f"There is no method with name `{method_name}` in file {file_name}."
            )
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(filtered_res)} methods with name `{method_name}` in file {file_name}:\n\n"
        summary = tool_output

        for idx, res in enumerate(filtered_res):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_method_in_class(
            self, method_name: str, class_name: str
    ) -> tuple[str, str, bool]:
        if class_name not in self.class_index:
            tool_output = f"Could not find class {class_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        search_res: list[SearchResult] = self._search_func_in_class(
            method_name, class_name
        )
        if not search_res:
            tool_output = f"Could not find method {method_name} in class `{class_name}`."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} methods with name {method_name} in class {class_name}:\n\n"
        summary = tool_output

        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += f"Too many results, showing full code for {RESULT_SHOW_LIMIT} of them, and the rest just file names:\n"
        first_five = search_res[:RESULT_SHOW_LIMIT]
        for idx, res in enumerate(first_five):
            res_str = res.to_tagged_str(self.project_path)
            tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        if rest := search_res[RESULT_SHOW_LIMIT:]:
            tool_output += "Other results are in these files:\n"
            tool_output += SearchResult.collapse_to_file_level(rest, self.project_path)
        return tool_output, summary, True

    def search_method(self, method_name: str) -> tuple[str, str, bool]:
        search_res: list[SearchResult] = self._search_func_in_code_base(method_name)
        if not search_res:
            tool_output = f"Could not find method {method_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(search_res)} methods with name {method_name} in the codebase:\n\n"
        summary = tool_output

        if len(search_res) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                search_res, self.project_path
            )
        else:
            for idx, res in enumerate(search_res):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"

        return tool_output, summary, True

    def search_code(self, code_str: str) -> tuple[str, str, bool]:
        all_search_results: list[SearchResult] = []
        for file_path in self.parsed_files:
            searched_line_and_code: list[tuple[int, str]] = (
                search_utils.get_code_region_containing_code(file_path, code_str)
            )
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                class_name, func_name = self.file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(all_search_results)} snippets containing `{code_str}` in the codebase:\n\n"
        summary = tool_output

        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += SearchResult.collapse_to_file_level(
                all_search_results, self.project_path
            )
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def search_code_in_file(
            self, code_str: str, file_name: str
    ) -> tuple[str, str, bool]:
        code_str = code_str.removesuffix(")")

        candidate_py_files = [f for f in self.parsed_files if f.endswith(file_name)]
        if not candidate_py_files:
            tool_output = f"Could not find file {file_name} in the codebase."
            summary = tool_output
            return tool_output, summary, False

        all_search_results: list[SearchResult] = []
        for file_path in candidate_py_files:
            searched_line_and_code: list[tuple[int, str]] = (
                search_utils.get_code_region_containing_code(file_path, code_str)
            )
            if not searched_line_and_code:
                continue
            for searched in searched_line_and_code:
                line_no, code_region = searched
                class_name, func_name = self.file_line_to_class_and_func(
                    file_path, line_no
                )
                res = SearchResult(file_path, class_name, func_name, code_region)
                all_search_results.append(res)

        if not all_search_results:
            tool_output = f"Could not find code {code_str} in file {file_name}."
            summary = tool_output
            return tool_output, summary, False

        tool_output = f"Found {len(all_search_results)} snippets with code {code_str} in file {file_name}:\n\n"
        summary = tool_output
        if len(all_search_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following methods:\n"
            tool_output += SearchResult.collapse_to_method_level(
                all_search_results, self.project_path
            )
        else:
            for idx, res in enumerate(all_search_results):
                res_str = res.to_tagged_str(self.project_path)
                tool_output += f"- Search result {idx + 1}:\n```\n{res_str}\n```\n"
        return tool_output, summary, True

    def retrieve_code_snippet(
            self, file_path: str, start_line: int, end_line: int
    ) -> str:
        return search_utils.get_code_snippets(file_path, start_line, end_line)

    # New functionality - Fuzzy module search
    def fuzzy_module_search(self, target_module: str) -> list[str]:
        all_modules = list(self.class_func_index.keys())
        return difflib.get_close_matches(target_module, all_modules, n=3, cutoff=0.6)

    # New functionality - Search function in module
    def search_function_in_module(self, module_path: str, func_name: str) -> list[tuple[str, str, LineRange]]:
        module_funcs = self.class_func_index.get(module_path, {})
        return [(fname, f"{func_name} (direct or alias)", line_range)
                for fname, line_range in module_funcs.get(func_name, [])]

    def search_for_imported_symbol(self, module_name, symbol_name):
        """
        Searches for specific imports of a symbol from a module across the codebase.
        Args:
            module_name (str): The name of the module (e.g., 'sklearn.utils._testing').
            symbol_name (str): The symbol imported from the module (e.g., 'assert_array_equal').
        Returns:
            A tuple of the structured result and a summary for found imports.
        """
        import_results = defaultdict(int)  # file_path -> count of matches
        symbol_pattern = rf"from\s+{re.escape(module_name)}\s+import\s+{re.escape(symbol_name)}"

        for file_path in self.parsed_files:
            with open(file_path, 'r') as file:
                content = file.read()
                if re.search(symbol_pattern, content):
                    import_results[file_path] += 1

        # Prepare result output
        if not import_results:
            return f"No imports of '{symbol_name}' from '{module_name}' found in the codebase.", "", False

        tool_output = f"Found {len(import_results)} files with imports of '{symbol_name}' from '{module_name}':\n\n"
        summary = tool_output
        if len(import_results) > RESULT_SHOW_LIMIT:
            tool_output += "They appeared in the following files:\n"
            tool_output += "\n".join(
                f"- <file>{path}</file> ({count} matches)"
                for path, count in list(import_results.items())[:RESULT_SHOW_LIMIT]
            )
            tool_output += "\n...and more."
        else:
            for path, count in import_results.items():
                tool_output += f"- <file>{path}</file> ({count} matches)\n"

        return tool_output, summary, True

    def search_import_and_alias_usages(self, symbol_name: str) -> tuple[str, str, bool]:
        all_results = []
        for file_path in self.parsed_files:
            usages = get_direct_and_aliased_imports(file_path, symbol_name)
            all_results.extend([(file_path, module, alias_name, line_range, line_text) for module, alias_name, line_range, line_text in usages])

        if not all_results:
            return f"No imports or aliases for '{symbol_name}' found.", "", False

        tool_output = f"[Import Search] Found import or alias of '{symbol_name}':\n"
        tool_output += f"Found {len(all_results)} usages of '{symbol_name}' in the codebase:\n\n"

        # Display limit for matches
        matches_to_show = all_results[:RESULT_SHOW_LIMIT]
        tool_output += f"Detailed import lines for the first {len(matches_to_show)} matches:\n"
        for file_path, module, alias_name, line_range, line_text in matches_to_show:
            # Convert absolute path to relative path
            relative_path = file_path.replace(self.project_path, "").lstrip("/")
            tool_output += f"- <file>{relative_path}</file> ({line_range[0]}-{line_range[1]})\n"
            tool_output += f"    {line_text}\n"  # Display the full line of code

        return tool_output, "", True











