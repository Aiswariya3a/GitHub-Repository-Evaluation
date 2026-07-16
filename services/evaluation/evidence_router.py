"""Evidence routing — maps rubric criteria categories to relevant Project Snapshot sections.

Two-stage filtering:
1. Category-based routing selects which snapshot sections are relevant.
2. Criterion-aware file selection further filters files[] to only those
   relevant to each specific rubric criterion, keeping prompt sizes small
   for SLMs.

The orchestrator uses this to pre-filter evidence before passing to the
Rubric Evaluation Agent, reducing token usage and focusing the SLM
on relevant data only (D-03, D-04).
"""

import fnmatch
import logging

logger = logging.getLogger(__name__)


# Category -> evidence section mapping (D-04)
# Extensible — add new mappings as rubric designs evolve
# Each key is a category code substring; matching is case-insensitive
# and fuzzy so criteria codes like "Q1A", "Q2B" match sensible defaults.
# Categories using `files[]` get the full file record including `content` (source code).
# Categories using `files[].*` get only specific sub-fields for token efficiency.
EVIDENCE_ROUTING_MAP = {
    "code_understanding": ["files[]", "repo_stats"],
    "collaboration": ["github_metadata", "repository_metadata"],
    "repository": ["repo_stats", "files[]", "repository_metadata"],
    "implementation": ["files[]", "delta"],
    "documentation": ["files[].docstrings", "repo_stats"],
    "testing": ["files[]"],
    "error_handling": ["files[]"],
    "structure": ["repo_stats", "files[]", "delta"],
    "commit_history": ["github_metadata", "repository_metadata"],
    "branching_practices": ["github_metadata", "repository_metadata"],
}


# Criterion -> file pattern mapping
# Each criterion key maps to a list of glob patterns for selecting relevant files.
# Empty list means the criterion needs NO source files (metadata only).
# Missing key means fall back to current behavior (all files from category routing).
# Patterns use fnmatch glob syntax (*, ?, [seq], [!seq]).
# Directory prefixes (e.g., "tests/") match any file under that directory.
CRITERION_FILE_MAP = {
    # --- Documentation ---
    "readme_quality": ["README.md", "README.txt", "README", "docs/*.md", "docs/*.txt"],
    "code_comments": ["*.c", "*.h", "*.py", "*.java", "*.js", "*.ts", "*.go", "*.rs", "*.rb"],

    # --- Code Quality ---
    "coding_standards": ["*.c", "*.h", "*.py", "*.java", "*.js", "*.ts"],
    "readability": ["*.c", "*.h", "*.py", "*.java", "*.js", "*.ts"],
    "modularity": ["*.c", "*.h", "*.py", "*.java", "*.js", "*.ts"],

    # --- Testing ---
    "testing_effort": ["tests/", "test_*", "*_test.*", "*_spec.*", "pytest.ini", "requirements.txt", "Makefile"],
    "display_and_testing": ["tests/", "test_*", "*_test.*", "*_spec.*"],

    # --- Repository Structure (metadata only) ---
    "repository_structure": ["*"],
    "file_organization": ["*"],

    # --- Git Practices (metadata only) ---
    "commit_history": [],
    "branching_practices": [],

    # --- Q1A: Compilation & Execution ---
    "successful_compilation_and_execution": ["Makefile", "CMakeLists.txt", "*.c", "*.h", "*.cpp", "*.hpp"],
    "demonstration_of_menu_operations": ["*main*", "*menu*", "*app*"],
    "explanation_of_control_structures": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "sample_testing_and_output": ["*.c", "*.txt", "*.md", "*.csv", "*.out"],

    # --- Q1B: Analysis & Debugging ---
    "identification_of_issues": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "corrected_logic_and_explanation": ["*.c", "*.h", "*.cpp", "*.hpp"],

    # --- Q2A: Arrays & Strings ---
    "proper_use_of_arrays_strings": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "searching_implementation": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "output_correctness": ["*.c", "*.txt", "*.out"],

    # --- Q2B: Sorting ---
    "sorting_logic": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "correct_implementation": ["*.c", "*.h", "*.cpp", "*.hpp"],

    # --- Q3A: Functional Decomposition ---
    "function_decomposition": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "modular_design_and_readability": ["*.c", "*.h", "*.cpp", "*.hpp"],

    # --- Q3B: Pointers ---
    "proper_pointer_implementation": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "explanation_and_correctness": ["*.c", "*.h", "*.cpp", "*.hpp"],

    # --- Q4A: Structure Enhancement ---
    "structure_modification": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "proper_implementation_and_testing": ["*.c", "*.h", "*.cpp", "*.hpp", "tests/", "test_*"],

    # --- Q4B: Feature Implementation ---
    "feature_implementation": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "functionality_and_innovation": ["*.c", "*.h", "*.cpp", "*.hpp"],

    # --- Q5A: File Handling ---
    "file_generation": ["*.c", "*.h", "*.cpp", "*.hpp", "*.txt", "*.csv", "*.dat", "*.log"],
    "file_update_verification": ["*.c", "*.h", "*.cpp", "*.hpp", "*.txt", "*.csv", "*.dat"],
    "correction_of_file_issues": ["*.c", "*.h", "*.cpp", "*.hpp", "*.txt", "*.csv", "*.dat"],

    # --- Q5B: Optimization & Error Handling ---
    "optimization_techniques": ["*.c", "*.h", "*.cpp", "*.hpp"],
    "error_handling_implementation": ["*.c", "*.h", "*.cpp", "*.hpp"],
}


# Criteria that should receive parsed metadata (functions, classes, imports, metrics)
# instead of full source code content. This prevents prompt overflow when a criterion
# needs to assess many files (e.g., coding_standards across all C files).
# Default for unmapped criteria is True (include full content) for backward compatibility.
CRITERION_CONTENT_INCLUDE = {
    # Documentation — README is small, include content
    "readme_quality": True,
    # Code comments — need comment_ratio, docstrings, not full source
    "code_comments": False,
    # Code Quality — metadata (functions, complexity, imports) is sufficient
    "coding_standards": False,
    "readability": False,
    "modularity": False,
    # Testing — test files are small, include content
    "testing_effort": True,
    "display_and_testing": True,
    # File organization — needs paths/languages/LOC only
    "file_organization": False,
    # Repository structure — needs paths/languages/LOC only
    "repository_structure": False,
    # Q-rubric — need to see specific implementations
    "successful_compilation_and_execution": True,
    "demonstration_of_menu_operations": True,
    "explanation_of_control_structures": True,
    "sample_testing_and_output": True,
    "identification_of_issues": True,
    "corrected_logic_and_explanation": True,
    "proper_use_of_arrays_strings": True,
    "searching_implementation": True,
    "output_correctness": True,
    "sorting_logic": True,
    "correct_implementation": True,
    "function_decomposition": True,
    "modular_design_and_readability": True,
    "proper_pointer_implementation": True,
    "explanation_and_correctness": True,
    "structure_modification": True,
    "proper_implementation_and_testing": True,
    "feature_implementation": True,
    "functionality_and_innovation": True,
    "file_generation": True,
    "file_update_verification": True,
    "correction_of_file_issues": True,
    "optimization_techniques": True,
    "error_handling_implementation": True,
}


# Parsed metadata fields preserved when content is stripped from file records.
# These are the fields the ingestion pipeline computed during parsing.
FILE_METADATA_FIELDS = frozenset({
    "path", "language", "loc", "code_loc", "comment_lines",
    "comment_ratio", "cyclomatic_complexity", "functions",
    "classes", "imports", "docstrings", "capabilities",
})


class CriterionFileSelector:
    """Selects only files relevant to a specific rubric criterion from the snapshot.

    Two-level optimization:
    1. File selection: glob pattern matching to pick only relevant files.
    2. Content stripping: for criteria like code_comments, sends parsed
       metadata instead of full source to avoid prompt overflow.

    Empty pattern lists indicate the criterion needs no source files
    (metadata-only evaluation like Git practices). Criteria without an entry
    in CRITERION_FILE_MAP fall back to current behavior (all files from
    category routing).

    Designed so new criteria can be added by configuration
    (CRITERION_FILE_MAP, CRITERION_CONTENT_INCLUDE) rather than
    changing routing logic.
    """

    def __init__(
        self,
        file_map: dict[str, list[str]] | None = None,
        content_map: dict[str, bool] | None = None,
    ):
        self._file_map = file_map or CRITERION_FILE_MAP
        self._content_map = content_map or CRITERION_CONTENT_INCLUDE

    def get_patterns(self, criterion_key: str) -> list[str] | None:
        """Return file patterns for a criterion key, or None if no mapping exists."""
        return self._file_map.get(criterion_key)

    def should_include_content(self, criterion_key: str) -> bool:
        """Whether full source content should be included for this criterion.

        Returns True (include content) for unmapped criteria to maintain
        backward compatibility.
        """
        return self._content_map.get(criterion_key, True)

    def select_files(self, files: list[dict], patterns: list[str]) -> list[dict]:
        """Filter files list to only those matching at least one glob pattern.

        Args:
            files: List of file records from the snapshot (each has 'path' key).
            patterns: Glob patterns to match against file paths.
                Empty list returns no files (metadata-only criterion).
                Pattern like 'tests/' matches any file starting with 'tests/'.

        Returns:
            Filtered list of file records. Empty list if no files match or
            patterns is empty.
        """
        if not patterns:
            return []
        selected = []
        for f in files:
            raw_path = f.get("path", "")
            normalized = raw_path.replace("\\", "/")
            for pattern in patterns:
                if fnmatch.fnmatch(normalized, pattern):
                    selected.append(f)
                    break
                dir_prefix = pattern.rstrip("/")
                if dir_prefix and (normalized == dir_prefix or normalized.startswith(dir_prefix + "/")):
                    selected.append(f)
                    break
        return selected

    @staticmethod
    def _strip_content(files: list[dict]) -> list[dict]:
        """Remove source content from file records, keeping only parsed metadata.

        The ingestion pipeline already computed functions, classes, imports,
        comment ratio, and complexity metrics. For code quality evaluation
        these are sufficient — the raw source is not needed.

        Args:
            files: List of file record dicts with 'content' field.

        Returns:
            Same list with 'content' removed from each record.
        """
        result = []
        for f in files:
            stripped = {k: v for k, v in f.items() if k in FILE_METADATA_FIELDS}
            result.append(stripped)
        return result

    def filter_evidence(self, evidence: dict, criterion_key: str) -> dict:
        """Apply criterion-specific file filtering to an evidence dict.

        After category-based routing has selected snapshot sections, this method:
        1. Selects only files matching the criterion's glob patterns
        2. Strips full source content for criteria that only need parsed metadata

        If no files match, the files key is dropped so the SLM sees metadata
        only and returns a lower-confidence assessment.

        Only filters when the files list contains full FileRecord dicts (with a
        'path' key). When the category routing extracted subfields like
        files[].docstrings, the entries won't have paths so filtering is skipped.

        Args:
            evidence: Evidence dict from category-based routing.
            criterion_key: Rubric criterion key for file selection.

        Returns:
            Filtered evidence dict with only relevant files.
            Falls back to original evidence if no mapping exists for criterion_key.
        """
        patterns = self.get_patterns(criterion_key)
        if patterns is None:
            return evidence

        if "files" not in evidence:
            return evidence

        original_files = evidence["files"]
        if not isinstance(original_files, list) or not original_files:
            return evidence

        # Only filter when files are full records with path keys (not extracted subfields)
        if not isinstance(original_files[0], dict) or "path" not in original_files[0]:
            return evidence

        original_count = len(original_files)
        selected = self.select_files(original_files, patterns)

        if selected:
            include_content = self.should_include_content(criterion_key)
            if not include_content:
                selected = self._strip_content(selected)
                logger.info(
                    "CriterionFileSelector: %s → %d/%d files (content stripped to metadata)",
                    criterion_key,
                    len(selected),
                    original_count,
                )
            else:
                logger.info(
                    "CriterionFileSelector: %s → %d/%d files selected (with content)",
                    criterion_key,
                    len(selected),
                    original_count,
                )
            evidence["files"] = selected
        else:
            logger.info(
                "CriterionFileSelector: %s → 0/%d files matched — "
                "dropping files section, evaluator will use metadata only",
                criterion_key,
                original_count,
            )
            del evidence["files"]

        return evidence


# Module-level singleton for convenience
_criterion_selector = CriterionFileSelector()


def route_evidence(snapshot: dict, criterion_category: str, criterion_key: str | None = None) -> dict:
    """Extract relevant evidence from snapshot based on criterion category and key.

    Two-stage filtering:
    1. Category-based routing selects which snapshot sections are relevant.
    2. If criterion_key is provided, criterion-specific file selection further
       filters the files[] section to only files matching the criterion's patterns.

    Args:
        snapshot: ProjectSnapshot as dict (the full ingestion output).
        criterion_category: Category code from rubric (e.g., 'Q1A', 'Q2B',
            'code_understanding', 'collaboration').
        criterion_key: Optional rubric criterion key (e.g., 'readme_quality',
            'testing_effort'). When provided, files are filtered to only those
            matching the criterion's patterns. When None, falls back to
            current behavior (all files from category routing).

    Returns:
        Subset of snapshot with only relevant sections for this criterion.
    """
    category_lower = criterion_category.lower()

    # Stage 1: Category-based routing (existing behavior)
    routing_key = _find_best_routing_key(category_lower)
    evidence_sections = EVIDENCE_ROUTING_MAP[routing_key]

    logger.debug(
        "Routing criterion '%s' (key=%s) -> routing key '%s' -> %d sections",
        criterion_category,
        criterion_key,
        routing_key,
        len(evidence_sections),
    )

    evidence = _filter_snapshot(snapshot, evidence_sections)

    # Stage 2: Criterion-specific file selection
    if criterion_key:
        evidence = _criterion_selector.filter_evidence(evidence, criterion_key)

    # Stage 3: Merge in supplemental evidence for criteria that need data
    # beyond what their category routing provides. This handles custom rubric
    # categories (e.g., "C1", "C5") whose codes don't match any routing key
    # and fall back to "implementation" (files[] + delta).
    # Only adds keys NOT already present in evidence to avoid overwriting
    # the files[] selected by Stage 2.
    if criterion_key in ("commit_history", "branching_practices"):
        collab_sections = EVIDENCE_ROUTING_MAP.get("collaboration", ["github_metadata"])
        collab_data = _filter_snapshot(snapshot, collab_sections)
        for k, v in collab_data.items():
            if k not in evidence:
                evidence[k] = v
    if criterion_key in ("readme_quality", "code_comments"):
        doc_sections = EVIDENCE_ROUTING_MAP.get("documentation", ["files[].docstrings", "repo_stats"])
        doc_data = _filter_snapshot(snapshot, doc_sections)
        for k, v in doc_data.items():
            if k not in evidence:
                evidence[k] = v
    if criterion_key in ("repository_structure", "file_organization"):
        struct_sections = ["repo_stats"]
        struct_data = _filter_snapshot(snapshot, struct_sections)
        for k, v in struct_data.items():
            if k not in evidence:
                evidence[k] = v
        # Strip files to just path+language to fit within context window
        if "files" in evidence and isinstance(evidence["files"], list):
            evidence["files"] = [
                {k: f[k] for k in ("path", "language") if k in f}
                for f in evidence["files"]
            ]

    return evidence


def _find_best_routing_key(category_lower: str) -> str:
    """Find the best matching routing key for a given category.

    Tries exact match first, then substring match in both directions.
    Falls back to 'implementation' as a sensible default.

    Args:
        category_lower: Lowercase criterion category string.

    Returns:
        str: Best matching routing key from EVIDENCE_ROUTING_MAP.
    """
    # Exact match
    if category_lower in EVIDENCE_ROUTING_MAP:
        return category_lower

    # Substring match: does category contain a routing key?
    for key in EVIDENCE_ROUTING_MAP:
        if key in category_lower:
            return key

    # Substring match: does a routing key contain the category?
    for key in EVIDENCE_ROUTING_MAP:
        if category_lower in key:
            return key

    # Fallback default
    logger.debug(
        "No matching routing key for '%s', using default 'implementation'",
        category_lower,
    )
    return "implementation"


def _filter_snapshot(snapshot: dict, sections: list[str]) -> dict:
    """Filter snapshot to only include specified sections.

    Navigates dotted paths through the snapshot dict and extracts only
    the requested sections into a new dict.

    Args:
        snapshot: Full ProjectSnapshot dict.
        sections: List of dotted path strings (e.g., 'files[].functions').

    Returns:
        dict: Filtered snapshot containing only the requested sections.
    """
    result = {}
    for section in sections:
        parts = section.split(".")
        current = snapshot
        valid = True
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, dict) and "[]" in part:
                # Handle array wildcard notation: files[].functions
                array_key = part.replace("[]", "")
                if array_key in current and isinstance(current[array_key], list):
                    # Navigate into array elements
                    extracted = _extract_from_array(
                        current[array_key], parts[parts.index(part) + 1:]
                    )
                    if extracted is not None:
                        clean_key = array_key  # strip '[]' notation for clean JSON key
                        _set_nested(result, [clean_key], extracted)
                    valid = False  # already handled — skip outer _set_nested at line 130
                    break
                else:
                    valid = False
                    break
            else:
                valid = False
                break
        if valid:
            _set_nested(result, parts, current)
    return result


def _extract_from_array(arr: list, remaining_parts: list[str]):
    """Extract a nested field from each element of an array.

    Args:
        arr: List of dicts to extract from.
        remaining_parts: Remaining path parts after the array accessor.

    Returns:
        list: Extracted values from each array element.
    """
    if not remaining_parts:
        return arr

    result = []
    field = remaining_parts[0]
    for item in arr:
        if isinstance(item, dict) and field in item:
            result.append(item[field])
    return result


def _set_nested(d: dict, keys: list[str], value) -> None:
    """Set value in nested dict using key path.

    Creates intermediate dicts as needed.

    Args:
        d: Target dict to set value in.
        keys: List of nested keys.
        value: Value to set at the final key.
    """
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    if keys:
        current[keys[-1]] = value
