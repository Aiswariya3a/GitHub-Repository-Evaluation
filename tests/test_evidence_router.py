"""Unit tests for evidence routing — category-based routing and criterion-aware file selection.

Tests exact matching, substring matching, fallback behavior,
nested path extraction, edge cases, and CriterionFileSelector.
"""

import pytest

from services.evaluation.evidence_router import (
    route_evidence,
    _find_best_routing_key,
    _filter_snapshot,
    _set_nested,
    CriterionFileSelector,
    CRITERION_FILE_MAP,
    CRITERION_CONTENT_INCLUDE,
    FILE_METADATA_FIELDS,
    EVIDENCE_ROUTING_MAP,
)


def _make_snapshot(overrides: dict | None = None) -> dict:
    """Build a minimal ProjectSnapshot for evidence routing tests."""
    snapshot = {
        "repository_metadata": {"url": "https://github.com/test/repo", "status": "success"},
        "repo_stats": {"total_loc": 500, "file_count": 5, "language_breakdown": {"C": 3}},
        "files": [
            {
                "path": "src/main.c",
                "language": "c",
                "loc": 200,
                "functions": [{"name": "main", "lineno": 1, "end_lineno": 50}],
                "classes": [],
                "imports": [],
            },
            {
                "path": "src/utils.py",
                "language": "python",
                "loc": 100,
                "functions": [{"name": "helper", "lineno": 1, "end_lineno": 20}],
                "classes": [{"name": "HelperClass", "methods": ["do_thing"]}],
                "imports": [{"module": "os", "names": [], "alias": None}],
            },
            {
                "path": "README.md",
                "language": "markdown",
                "loc": 50,
                "functions": [],
                "classes": [],
                "imports": [],
            },
            {
                "path": "tests/test_main.c",
                "language": "c",
                "loc": 80,
                "functions": [{"name": "test_banking", "lineno": 1, "end_lineno": 30}],
                "classes": [],
                "imports": [],
            },
            {
                "path": "pytest.ini",
                "language": "ini",
                "loc": 5,
                "functions": [],
                "classes": [],
                "imports": [],
            },
        ],
        "github_metadata": {"commits_count": 10, "contributors": []},
        "delta": None,
    }
    if overrides:
        snapshot.update(overrides)
    return snapshot


class TestFindBestRoutingKey:
    """Tests for the internal _find_best_routing_key function."""

    def test_exact_match(self):
        """Category code that exactly matches a routing key."""
        assert _find_best_routing_key("code_understanding") == "code_understanding"
        assert _find_best_routing_key("collaboration") == "collaboration"
        assert _find_best_routing_key("implementation") == "implementation"

    def test_substring_match_key_in_category(self):
        """Category contains a routing key → matching via substring."""
        # "code_understanding" is in "q1a_code_understanding"
        assert _find_best_routing_key("q1a_code_understanding") == "code_understanding"

    def test_substring_match_category_in_key(self):
        """A routing key contains the category → matching via reverse substring."""
        # Default routing keys contain repo, code, etc.
        assert _find_best_routing_key("repo") == "repository"  # "repo" in "repository"
        assert _find_best_routing_key("doc") == "documentation"  # "doc" in "documentation"

    def test_fallback_default(self):
        """Unknown category → falls back to 'implementation'."""
        key = _find_best_routing_key("xyz_unknown_category")
        assert key == "implementation"

    def test_case_insensitive(self):
        """Matching is case-insensitive (input is already lowercased by route_evidence)."""
        # _find_best_routing_key assumes lowercased input (route_evidence lowercases first)
        assert _find_best_routing_key("code_understanding") == "code_understanding"
        assert _find_best_routing_key("collaboration") == "collaboration"

    def test_fallback_numeric_code(self):
        """Category like 'Q1A' (no routing key match) → falls back to implementation."""
        assert _find_best_routing_key("Q1A") == "implementation"

    def test_empty_string(self):
        """Empty string matches first routing key (empty string is substring of every key)."""
        # Empty string is a substring of ALL routing keys, so it matches the first one
        result = _find_best_routing_key("")
        assert result in EVIDENCE_ROUTING_MAP  # It will match "code_understanding" (first key)


class TestRouteEvidence:
    """Tests for the main route_evidence() function."""

    def test_route_exact_match(self):
        """Category code that exactly matches a routing key → returns correct sections."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "collaboration")

        # Should contain github_metadata section
        assert "github_metadata" in result
        assert result["github_metadata"]["commits_count"] == 10
        # Should NOT contain unrelated sections
        assert "files" not in result

    def test_route_substring_match(self):
        """Category 'q1a_implementation' routes to implementation sections."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "q1a_implementation")

        # Implementation routes to: files[], delta
        # Note: _filter_snapshot strips '[]' notation for clean JSON keys
        assert "files" in result
        assert "delta" in result

    def test_route_fallback_default(self):
        """Unknown category → falls back to 'implementation' sections."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "Q1A_unknown")

        # Should contain implementation sections (clean key without [] notation)
        assert "files" in result

    def test_route_case_insensitive(self):
        """Category 'CODE_UNDERSTANDING' matches 'code_understanding' case-insensitively."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "CODE_UNDERSTANDING")

        # code_understanding routes to: files[], repo_stats
        # Note: _filter_snapshot now strips '[]' notation (key is 'files', not 'files[]')
        assert "files" in result
        assert "repo_stats" in result

    def test_route_extracts_correct_sections(self):
        """Verify returned dict contains only the mapped sections for 'documentation'."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "documentation")
        # documentation routes to: files[].docstrings, repo_stats
        # Note: _filter_snapshot now strips '[]' notation (key is 'files', not 'files[]')
        assert "files" in result

    def test_route_repository_key(self):
        """'repository' key routes to repo_stats, files[], repository_metadata."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "repository")

        assert "repo_stats" in result
        assert "repository_metadata" in result
        assert result["repository_metadata"]["url"] == "https://github.com/test/repo"

    def test_route_nested_paths(self):
        """Section path like 'files[].functions' correctly extracts nested data."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "code_understanding")

        # code_understanding routes to: files[], repo_stats
        # Note: _filter_snapshot now strips '[]' notation (key is 'files', not 'files[]')
        assert "files" in result
        assert isinstance(result["files"], list)
        assert len(result["files"]) == 5

    def test_route_empty_snapshot(self):
        """Empty snapshot → returns empty dict without error."""
        result = route_evidence({}, "Q1A")
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_route_missing_section_in_snapshot(self):
        """Snapshot missing a section referenced by routing key → no crash."""
        snapshot = {"repo_stats": {"total_loc": 100}}
        result = route_evidence(snapshot, "code_understanding")
        # Should not crash; should return whatever it can find
        assert "repo_stats" in result
        assert isinstance(result, dict)

    def test_route_implementation_contains_functions_and_classes(self):
        """'implementation' routing key returns full file records under clean 'files' key."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "implementation")

        assert "files" in result
        assert "delta" in result
        assert isinstance(result["files"], list)
        assert len(result["files"]) >= 1


class TestFilterSnapshot:
    """Tests for _filter_snapshot — internal function."""

    def test_filter_simple_key(self):
        """Simple single-level key extracts value correctly."""
        snapshot = {"repo_stats": {"loc": 100}}
        result = _filter_snapshot(snapshot, ["repo_stats"])
        assert result == {"repo_stats": {"loc": 100}}

    def test_filter_array_wildcard(self):
        """Array wildcard notation navigates into array elements."""
        snapshot = {
            "files": [
                {"name": "a.txt", "size": 100},
                {"name": "b.txt", "size": 200},
            ],
        }
        result = _filter_snapshot(snapshot, ["files[].name"])
        assert "files" in result
        assert len(result["files"]) == 2
        assert result["files"] == ["a.txt", "b.txt"]

    def test_filter_nonexistent_key(self):
        """Nonexistent key → omitted from result."""
        snapshot = {"a": 1}
        result = _filter_snapshot(snapshot, ["b.c"])
        assert result == {}

    def test_filter_partial_existing(self):
        """Mix of existing and nonexistent sections → only existing returned."""
        snapshot = {"repo_stats": {"loc": 100}, "other": "data"}
        result = _filter_snapshot(snapshot, ["repo_stats", "nonexistent"])
        assert "repo_stats" in result
        assert "nonexistent" not in result


class TestSetNested:
    """Tests for _set_nested — internal function for building nested dicts."""

    def test_set_single_key(self):
        """Single key sets value at top level."""
        d = {}
        _set_nested(d, ["key1"], "value1")
        assert d == {"key1": "value1"}

    def test_set_two_levels(self):
        """Two-level path creates intermediate dict and sets value."""
        d = {}
        _set_nested(d, ["level1", "level2"], "deep")
        assert d == {"level1": {"level2": "deep"}}

    def test_set_three_levels(self):
        """Three-level path creates all intermediate dicts correctly."""
        d = {}
        _set_nested(d, ["a", "b", "c"], 42)
        assert d == {"a": {"b": {"c": 42}}}

    def test_set_overwrites_existing(self):
        """Setting on an existing key overwrites the value."""
        d = {"a": {"b": 1}}
        _set_nested(d, ["a", "b"], 2)
        assert d["a"]["b"] == 2

    def test_set_appends_to_existing(self):
        """Setting a sibling key preserves existing structure."""
        d = {"a": {"b": 1}}
        _set_nested(d, ["a", "c"], 2)
        assert d["a"] == {"b": 1, "c": 2}

    def test_set_deep_with_existing_intermediate(self):
        """Setting deep path when intermediate already exists."""
        d = {"x": {"y": {}}}
        _set_nested(d, ["x", "y", "z"], "val")
        assert d["x"]["y"]["z"] == "val"

    def test_set_empty_keys(self):
        """Empty keys list does nothing."""
        d = {"a": 1}
        _set_nested(d, [], "value")
        assert d == {"a": 1}

    def test_set_with_array_intermediate_keys(self):
        """Keys with [] notation — should create dict, not list."""
        d = {}
        _set_nested(d, ["files", "name"], "test")
        assert "files" in d
        assert isinstance(d["files"], dict)
        assert d["files"]["name"] == "test"


class TestCriterionFileSelector:
    """Tests for CriterionFileSelector — criterion-aware file filtering."""

    def _make_files(self) -> list[dict]:
        return [
            {"path": "README.md", "language": "markdown"},
            {"path": "src/main.c", "language": "c"},
            {"path": "src/utils.py", "language": "python"},
            {"path": "tests/test_main.c", "language": "c"},
            {"path": "pytest.ini", "language": "ini"},
        ]

    # --- select_files ---

    def test_select_files_glob_c(self):
        """Glob pattern '*.c' matches C source files."""
        selector = CriterionFileSelector()
        files = self._make_files()
        result = selector.select_files(files, ["*.c"])
        assert len(result) == 2
        assert all(f["path"].endswith(".c") for f in result)

    def test_select_files_directory_prefix(self):
        """Directory prefix 'tests/' matches files under tests/."""
        selector = CriterionFileSelector()
        files = self._make_files()
        result = selector.select_files(files, ["tests/"])
        assert len(result) == 1
        assert result[0]["path"] == "tests/test_main.c"

    def test_select_files_readme(self):
        """Pattern 'README.md' matches only the readme."""
        selector = CriterionFileSelector()
        files = self._make_files()
        result = selector.select_files(files, ["README.md"])
        assert len(result) == 1
        assert result[0]["path"] == "README.md"

    def test_select_files_multiple_patterns(self):
        """Multiple patterns union together."""
        selector = CriterionFileSelector()
        files = self._make_files()
        result = selector.select_files(files, ["*.md", "pytest.ini"])
        assert len(result) == 2
        paths = {f["path"] for f in result}
        assert "README.md" in paths
        assert "pytest.ini" in paths

    def test_select_files_empty_patterns(self):
        """Empty patterns list returns no files (metadata-only criterion)."""
        selector = CriterionFileSelector()
        files = self._make_files()
        result = selector.select_files(files, [])
        assert result == []

    def test_select_files_no_match(self):
        """Pattern matching nothing returns empty list."""
        selector = CriterionFileSelector()
        files = self._make_files()
        result = selector.select_files(files, ["*.rs"])
        assert result == []

    def test_select_files_empty_file_list(self):
        """Empty file list returns empty list."""
        selector = CriterionFileSelector()
        result = selector.select_files([], ["*.c"])
        assert result == []

    def test_select_files_windows_paths(self):
        """Windows backslash paths normalized before matching."""
        selector = CriterionFileSelector()
        files = [
            {"path": "src\\main.c", "language": "c"},
            {"path": "README.md", "language": "markdown"},
        ]
        result = selector.select_files(files, ["*.c"])
        assert len(result) == 1
        assert result[0]["path"] == "src\\main.c"

    def test_select_files_star_prefix_match(self):
        """Pattern '*main*' matches files with 'main' in the name."""
        selector = CriterionFileSelector()
        files = self._make_files()
        result = selector.select_files(files, ["*main*"])
        assert len(result) == 2
        paths = {f["path"] for f in result}
        assert "src/main.c" in paths
        assert "tests/test_main.c" in paths

    # --- get_patterns ---

    def test_get_patterns_known_criterion(self):
        """Known criterion key returns its patterns."""
        selector = CriterionFileSelector()
        patterns = selector.get_patterns("readme_quality")
        assert patterns is not None
        assert len(patterns) > 0
        assert "README.md" in patterns

    def test_get_patterns_metadata_only_criterion(self):
        """Metadata-only criterion returns all-files pattern."""
        selector = CriterionFileSelector()
        patterns = selector.get_patterns("repository_structure")
        assert patterns is not None
        assert patterns == ["*"]

    def test_get_patterns_unknown_criterion(self):
        """Unknown criterion key returns None (fallback)."""
        selector = CriterionFileSelector()
        patterns = selector.get_patterns("nonexistent_criterion")
        assert patterns is None

    # --- filter_evidence ---

    def test_filter_evidence_filters_files(self):
        """filter_evidence keeps only files matching criterion patterns."""
        selector = CriterionFileSelector({"test_criterion": ["*.md"]})
        evidence = {
            "files": self._make_files(),
            "repo_stats": {"total_loc": 500},
        }
        result = selector.filter_evidence(evidence, "test_criterion")
        assert result["repo_stats"] == {"total_loc": 500}
        assert len(result["files"]) == 1
        assert result["files"][0]["path"] == "README.md"

    def test_filter_evidence_no_files_section(self):
        """filter_evidence handles evidence with no files key gracefully."""
        selector = CriterionFileSelector({"test_criterion": ["*.md"]})
        evidence = {"repo_stats": {"total_loc": 500}}
        result = selector.filter_evidence(evidence, "test_criterion")
        assert result == {"repo_stats": {"total_loc": 500}}

    def test_filter_evidence_no_match_drops_files(self):
        """When no files match, files key is dropped entirely."""
        selector = CriterionFileSelector({"test_criterion": ["*.rs"]})
        evidence = {
            "files": self._make_files(),
            "repo_stats": {"total_loc": 500},
        }
        result = selector.filter_evidence(evidence, "test_criterion")
        assert "files" not in result
        assert result["repo_stats"] == {"total_loc": 500}

    def test_filter_evidence_empty_patterns_drops_files(self):
        """Empty patterns (metadata-only) drop files section."""
        selector = CriterionFileSelector({"test_criterion": []})
        evidence = {
            "files": self._make_files(),
            "repo_stats": {"total_loc": 500},
        }
        result = selector.filter_evidence(evidence, "test_criterion")
        assert "files" not in result

    def test_filter_evidence_unknown_criterion(self):
        """Unknown criterion returns evidence unchanged (fallback)."""
        selector = CriterionFileSelector()
        evidence = {
            "files": self._make_files(),
            "repo_stats": {"total_loc": 500},
        }
        result = selector.filter_evidence(evidence, "nonexistent")
        assert result is evidence  # same object, no copy

    def test_filter_evidence_custom_file_map(self):
        """Custom file_map injected via constructor."""
        custom_map = {"custom_criterion": ["*.py"]}
        selector = CriterionFileSelector(custom_map)
        evidence = {
            "files": self._make_files(),
        }
        result = selector.filter_evidence(evidence, "custom_criterion")
        assert len(result["files"]) == 1
        assert result["files"][0]["path"] == "src/utils.py"

    # --- should_include_content ---

    def test_should_include_content_known_false(self):
        """Metadata-only criterion returns False."""
        selector = CriterionFileSelector()
        assert selector.should_include_content("code_comments") is False

    def test_should_include_content_known_true(self):
        """Content-included criterion returns True."""
        selector = CriterionFileSelector()
        assert selector.should_include_content("readme_quality") is True

    def test_should_include_content_unknown_defaults_true(self):
        """Unknown criterion defaults to True (backward compatible)."""
        selector = CriterionFileSelector()
        assert selector.should_include_content("nonexistent_key") is True

    # --- _strip_content ---

    def _make_file_with_content(self) -> dict:
        return {
            "path": "src/main.c",
            "language": "c",
            "loc": 200,
            "code_loc": 180,
            "comment_lines": 20,
            "comment_ratio": 0.1,
            "cyclomatic_complexity": 15,
            "functions": [{"name": "main", "lineno": 1}],
            "classes": [],
            "imports": [{"module": "stdio.h"}],
            "docstrings": [],
            "capabilities": ["io"],
            "content": "int main() { printf('hello'); }",
            "extra_field": "should_be_removed",
        }

    def test_strip_content_removes_content(self):
        """_strip_content removes 'content' field from file records."""
        file_record = self._make_file_with_content()
        result = CriterionFileSelector._strip_content([file_record])
        assert len(result) == 1
        assert "content" not in result[0]

    def test_strip_content_keeps_metadata_fields(self):
        """_strip_content preserves all FILE_METADATA_FIELDS."""
        file_record = self._make_file_with_content()
        result = CriterionFileSelector._strip_content([file_record])
        for field in FILE_METADATA_FIELDS:
            assert field in result[0], f"Field '{field}' missing after strip"

    def test_strip_content_removes_non_metadata(self):
        """_strip_content removes fields not in FILE_METADATA_FIELDS."""
        file_record = self._make_file_with_content()
        result = CriterionFileSelector._strip_content([file_record])
        assert "extra_field" not in result[0]

    def test_strip_content_multiple_files(self):
        """_strip_content handles multiple file records."""
        files = [
            {"path": "a.c", "content": "code_a", "loc": 10},
            {"path": "b.c", "content": "code_b", "loc": 20},
        ]
        result = CriterionFileSelector._strip_content(files)
        assert len(result) == 2
        assert all("content" not in f for f in result)
        assert result[0]["loc"] == 10
        assert result[1]["loc"] == 20

    def test_strip_content_no_content_field(self):
        """_strip_content handles files without content field gracefully."""
        files = [{"path": "a.c", "loc": 10}]
        result = CriterionFileSelector._strip_content(files)
        assert len(result) == 1
        assert result[0]["path"] == "a.c"

    # --- filter_evidence with content stripping ---

    def test_filter_evidence_strips_content_for_metadata_criterion(self):
        """Metadata-only criterion strips content from selected files."""
        custom_map = {"test_criterion": ["*.c"]}
        custom_content = {"test_criterion": False}
        selector = CriterionFileSelector(custom_map, custom_content)
        files = [
            {"path": "src/main.c", "loc": 200, "content": "int main() {}", "functions": [{"name": "main"}]},
            {"path": "src/utils.c", "loc": 100, "content": "void helper() {}", "functions": [{"name": "helper"}]},
        ]
        evidence = {"files": files, "repo_stats": {}}
        result = selector.filter_evidence(evidence, "test_criterion")
        assert "content" not in result["files"][0]
        assert "content" not in result["files"][1]
        assert result["files"][0]["path"] == "src/main.c"
        assert result["files"][0]["loc"] == 200
        assert result["files"][1]["path"] == "src/utils.c"

    def test_filter_evidence_keeps_content_for_content_criterion(self):
        """Content-included criterion keeps content in selected files."""
        custom_map = {"test_criterion": ["*.md"]}
        custom_content = {"test_criterion": True}
        selector = CriterionFileSelector(custom_map, custom_content)
        files = [
            {"path": "README.md", "content": "# Project", "loc": 50},
        ]
        evidence = {"files": files, "repo_stats": {}}
        result = selector.filter_evidence(evidence, "test_criterion")
        assert "content" in result["files"][0]
        assert result["files"][0]["content"] == "# Project"


class TestRouteEvidenceWithCriterionKey:
    """Tests for route_evidence() with criterion_key parameter."""

    def test_criterion_key_filters_files(self):
        """criterion_key filters files to only relevant ones."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "implementation", criterion_key="readme_quality")
        assert "files" in result
        assert len(result["files"]) == 1
        assert result["files"][0]["path"] == "README.md"

    def test_criterion_key_no_mapping_falls_back(self):
        """Unknown criterion_key returns all files (current behavior)."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "implementation", criterion_key="nonexistent_key")
        # No mapping for this key → fallback → all files from category routing
        assert "files" in result
        assert len(result["files"]) == 5

    def test_criterion_key_metadata_only(self):
        """Metadata-only criterion selects all files with content stripped."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "repository", criterion_key="repository_structure")
        assert "files" in result
        assert len(result["files"]) == 5
        # Content should be stripped — only metadata fields remain
        for f in result["files"]:
            assert "content" not in f
            assert "path" in f
        assert "repo_stats" in result

    def test_criterion_key_no_criterion_key_falls_back(self):
        """No criterion_key provided → current behavior (all files)."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "implementation")
        assert "files" in result
        assert len(result["files"]) == 5

    def test_criterion_key_with_documentation_category(self):
        """Documentation category routes to files[].docstrings (extracted subfields).

        Since the category routing extracts subfields (docstrings, not full file
        records), criterion-aware file filtering is skipped. Files is an empty
        list because none of the test snapshot files have docstrings defined.
        """
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "documentation", criterion_key="readme_quality")
        assert "files" in result
        assert len(result["files"]) == 0  # no files have docstrings in test snapshot

    def test_criterion_key_with_testing_category(self):
        """Testing category with testing_effort key keeps test files only."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "testing", criterion_key="testing_effort")
        assert "files" in result
        assert len(result["files"]) == 2
        paths = {f["path"] for f in result["files"]}
        assert "tests/test_main.c" in paths
        assert "pytest.ini" in paths

    def test_route_evidence_existing_tests_still_pass(self):
        """Existing call pattern (no criterion_key) works unchanged."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "collaboration")
        assert "github_metadata" in result
        assert "files" not in result

    def test_criterion_code_comments_strips_content(self):
        """code_comments criterion strips content from C files."""
        snapshot = _make_snapshot()
        snapshot["files"] = [
            {"path": "src/main.c", "content": "int main() {}", "comment_lines": 5, "comment_ratio": 0.1, "loc": 100},
            {"path": "README.md", "content": "# Project", "comment_lines": 0, "comment_ratio": 0.0, "loc": 10},
        ]
        result = route_evidence(snapshot, "code_understanding", criterion_key="code_comments")
        assert "files" in result
        for f in result["files"]:
            assert "content" not in f, f"Content should be stripped for code_comments: {f['path']}"
            assert "comment_lines" in f
            assert "comment_ratio" in f

    def test_criterion_readme_quality_keeps_content(self):
        """readme_quality criterion keeps content (README is small)."""
        snapshot = _make_snapshot()
        snapshot["files"] = [
            {"path": "README.md", "content": "# Project Title\n\nDescription here", "loc": 20},
            {"path": "src/main.c", "content": "int main() {}", "loc": 100},
        ]
        result = route_evidence(snapshot, "code_understanding", criterion_key="readme_quality")
        assert "files" in result
        assert len(result["files"]) == 1
        assert result["files"][0]["path"] == "README.md"
        assert "content" in result["files"][0]
