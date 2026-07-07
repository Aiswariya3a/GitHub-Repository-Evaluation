"""JSON Schema definitions for all agent inputs and outputs.

All schemas use JSON Schema draft-07. Each schema is self-contained
(no $ref) to work directly with jsonschema.validate().

Exported schemas:
    - REPO_UNDERSTANDING_SCHEMA: Repository Understanding Agent output
    - CODE_UNDERSTANDING_SCHEMA: Code Understanding Agent output
    - COLLABORATION_SCHEMA: Collaboration Analysis Agent output
    - CRITERION_EVALUATION_SCHEMA: Rubric Evaluation Agent per-criterion output
    - FEEDBACK_SCHEMA: Feedback Agent output
"""

# ---------------------------------------------------------------------------
# Capability Extraction Agents
# ---------------------------------------------------------------------------

REPO_UNDERSTANDING_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["languages", "key_files", "structural_summary", "risk_flags"],
    "properties": {
        "languages": {
            "type": "object",
            "patternProperties": {"^.*$": {"type": "integer"}},
            "description": "Language -> file count mapping",
        },
        "key_files": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "role", "importance"],
                "properties": {
                    "path": {"type": "string"},
                    "role": {"type": "string"},
                    "importance": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                },
            },
            "description": "Key files identified in the repository",
        },
        "total_files": {"type": "integer"},
        "total_loc": {"type": "integer"},
        "structural_summary": {
            "type": "string",
            "description": "High-level structural overview of the repository",
        },
        "risk_flags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Potential risks or concerns identified",
        },
    },
}

CODE_UNDERSTANDING_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "capabilities",
        "algorithms",
        "apis",
        "data_structures",
        "error_handling",
    ],
    "properties": {
        "capabilities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "description", "files", "confidence"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
            },
            "description": "Core capabilities identified in the codebase",
        },
        "algorithms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Algorithms implemented in the codebase",
        },
        "apis": {
            "type": "array",
            "items": {"type": "string"},
            "description": "APIs or external services used",
        },
        "data_structures": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Data structures used in the codebase",
        },
        "file_operations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "File I/O patterns identified",
        },
        "error_handling": {
            "type": "object",
            "required": ["has_error_handling", "patterns"],
            "properties": {
                "has_error_handling": {
                    "type": "boolean",
                    "description": "Whether the codebase has error handling",
                },
                "patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Error handling patterns observed",
                },
            },
            "description": "Error handling analysis",
        },
    },
}

COLLABORATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "commit_analysis",
        "contributor_analysis",
        "collaboration_score",
    ],
    "properties": {
        "commit_analysis": {
            "type": "object",
            "required": ["total_commits"],
            "properties": {
                "total_commits": {
                    "type": "integer",
                    "description": "Total number of commits",
                },
                "commit_frequency": {
                    "type": "string",
                    "description": "How frequently commits are made",
                },
                "meaningful_commits": {
                    "type": "integer",
                    "description": "Number of substantive commits",
                },
                "patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Commit patterns observed",
                },
            },
            "description": "Analysis of commit history",
        },
        "contributor_analysis": {
            "type": "object",
            "required": ["total_contributors"],
            "properties": {
                "total_contributors": {
                    "type": "integer",
                    "description": "Total number of contributors",
                },
                "contributions_distribution": {
                    "type": "string",
                    "description": "Distribution of contributions",
                },
                "key_contributors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key contributors to the project",
                },
            },
            "description": "Analysis of contributor activity",
        },
        "pull_request_analysis": {
            "type": "object",
            "properties": {
                "total_prs": {
                    "type": "integer",
                    "description": "Total pull requests",
                },
                "merged_prs": {
                    "type": "integer",
                    "description": "Merged pull requests",
                },
                "review_quality": {
                    "type": "string",
                    "description": "Quality of code reviews",
                },
            },
            "description": "Analysis of pull request activity",
        },
        "collaboration_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Overall collaboration score (0-1)",
        },
        "summary": {
            "type": "string",
            "description": "Summary of collaboration analysis",
        },
    },
}

# ---------------------------------------------------------------------------
# Rubric Evaluation
# ---------------------------------------------------------------------------

CRITERION_EVALUATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "criterion_key",
        "category_code",
        "score",
        "max_score",
        "confidence",
        "evidence",
        "remarks",
    ],
    "properties": {
        "criterion_key": {
            "type": "string",
            "description": "Unique key identifying the rubric criterion",
        },
        "category_code": {
            "type": "string",
            "description": "Category code this criterion belongs to",
        },
        "score": {
            "type": "number",
            "minimum": 0,
            "description": "Score awarded for this criterion",
        },
        "max_score": {
            "type": "number",
            "minimum": 0,
            "description": "Maximum possible score for this criterion",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the score (0-1)",
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Evidence supporting the score",
        },
        "remarks": {
            "type": "string",
            "description": "Mini-feedback remarks for this criterion",
        },
    },
}

# ---------------------------------------------------------------------------
# Feedback Generation
# ---------------------------------------------------------------------------

FEEDBACK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["strengths", "weaknesses", "suggestions", "summary"],
    "properties": {
        "strengths": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["area", "description", "evidence_keys"],
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "Area of strength",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the strength",
                    },
                    "evidence_keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keys referencing evaluation evidence",
                    },
                },
            },
            "description": "Identified strengths in the submission",
        },
        "weaknesses": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["area", "description", "evidence_keys"],
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "Area of weakness",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the weakness",
                    },
                    "evidence_keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keys referencing evaluation evidence",
                    },
                },
            },
            "description": "Identified weaknesses in the submission",
        },
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["area", "suggestion", "priority"],
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "Area for improvement",
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "Actionable improvement suggestion",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Priority of the suggestion",
                    },
                },
            },
            "description": "Actionable improvement suggestions",
        },
        "summary": {
            "type": "string",
            "description": "Overall summary of the feedback",
        },
    },
}
