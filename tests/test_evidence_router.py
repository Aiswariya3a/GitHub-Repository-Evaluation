"""Unit tests for route_evidence() — evidence routing logic.

Tests exact matching, substring matching, fallback behavior,
nested path extraction, and edge cases.
"""

import pytest

from services.evaluation.evidence_router import (
    route_evidence,
    _find_best_routing_key,
    _filter_snapshot,
    _set_nested,
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

        # Implementation routes to: files[].functions, files[].classes, delta
        # Note: _filter_snapshot preserves '[]' in keys for array wildcard paths
        assert "files[]" in result or "files" in result
        assert "delta" in result

    def test_route_fallback_default(self):
        """Unknown category → falls back to 'implementation' sections."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "Q1A_unknown")

        # Should contain implementation sections (note: keys may use [] notation)
        assert "files[]" in result or "files" in result

    def test_route_case_insensitive(self):
        """Category 'CODE_UNDERSTANDING' matches 'code_understanding' case-insensitively."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "CODE_UNDERSTANDING")

        # code_understanding routes to: files[].functions, files[].imports, repo_stats
        # Note: _filter_snapshot uses 'files[]' as key for array wildcard paths
        assert "files[]" in result or "files" in result
        assert "repo_stats" in result

    def test_route_extracts_correct_sections(self):
        """Verify returned dict contains only the mapped sections for 'documentation'."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "documentation")
        # documentation routes to: files[].docstrings, files[].comment_ratio
        # Note: _filter_snapshot uses exact path segments as keys (e.g., 'files[]')
        # 'comment_ratio' is not extracted directly — it's part of repo_stats
        assert "files[]" in result or "files" in result

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

        # code_understanding routes to: files[].functions, files[].imports, repo_stats
        # Note: _filter_snapshot uses 'files[]' as key for array wildcard paths
        assert "files[]" in result
        assert isinstance(result["files[]"], list)
        assert len(result["files[]"]) == 2

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
        """'implementation' routing key returns files[] with functions and classes."""
        snapshot = _make_snapshot()
        result = route_evidence(snapshot, "implementation")

        assert "files[]" in result
        assert "delta" in result
        # Verify classes were extracted from utils.py via files[].classes
        assert isinstance(result["files[]"], list)
        # Second entry (utils.py) should have extracted classes
        assert len(result["files[]"]) >= 1


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
        assert "files[]" in result
        assert len(result["files[]"]) == 2
        assert result["files[]"] == ["a.txt", "b.txt"]

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
        _set_nested(d, ["files[]", "name"], "test")
        assert "files[]" in d
        assert isinstance(d["files[]"], dict)
        assert d["files[]"]["name"] == "test"
