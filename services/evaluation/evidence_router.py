"""Evidence routing — maps rubric criteria categories to relevant Project Snapshot sections.

The orchestrator uses this to pre-filter evidence before passing to the
Rubric Evaluation Agent, reducing token usage and focusing the SLM
on relevant data only (D-03, D-04).
"""

import logging

logger = logging.getLogger(__name__)


# Category -> evidence section mapping (D-04)
# Extensible — add new mappings as rubric designs evolve
# Each key is a category code substring; matching is case-insensitive
# and fuzzy so criteria codes like "Q1A", "Q2B" match sensible defaults.
EVIDENCE_ROUTING_MAP = {
    "code_understanding": ["files[].functions", "files[].imports", "repo_stats"],
    "collaboration": ["github_metadata"],
    "repository": ["repo_stats", "files[]", "repository_metadata"],
    "implementation": ["files[].functions", "files[].classes", "delta"],
    "documentation": ["files[].docstrings", "files[].comment_ratio"],
    "testing": ["files[].functions", "files[].imports"],
    "error_handling": ["files[].functions", "files[].imports"],
    "structure": ["repo_stats", "files[]", "delta"],
}


def route_evidence(snapshot: dict, criterion_category: str) -> dict:
    """Extract relevant evidence from snapshot based on criterion category.

    Args:
        snapshot: ProjectSnapshot as dict (the full ingestion output).
        criterion_category: Category code from rubric (e.g., 'Q1A', 'Q2B',
            'code_understanding', 'collaboration').

    Returns:
        Subset of snapshot with only relevant sections for this criterion.
    """
    category_lower = criterion_category.lower()

    # Find best matching routing key using substring matching
    routing_key = _find_best_routing_key(category_lower)
    evidence_sections = EVIDENCE_ROUTING_MAP[routing_key]

    logger.debug(
        "Routing criterion '%s' -> key '%s' -> %d sections",
        criterion_category,
        routing_key,
        len(evidence_sections),
    )

    return _filter_snapshot(snapshot, evidence_sections)


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
    logger.warning(
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
                        _set_nested(result, parts[:parts.index(part) + 1], extracted)
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
            current[key] = {} if key != keys[-2] else []
        current = current[key]
    if keys:
        current[keys[-1]] = value
