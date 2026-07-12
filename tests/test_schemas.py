"""JSON Schema contract tests for all 5 agent output schemas.

All tests validate Draft-07 compliance and test valid/invalid data
for each schema. Schemas are self-contained (no $ref) per design decision.
"""

import jsonschema
import pytest

from services.evaluation.schemas import (
    REPO_UNDERSTANDING_SCHEMA,
    CODE_UNDERSTANDING_SCHEMA,
    COLLABORATION_SCHEMA,
    CRITERION_EVALUATION_SCHEMA,
    FEEDBACK_SCHEMA,
)

# List of all schemas for bulk validation
ALL_SCHEMAS = [
    REPO_UNDERSTANDING_SCHEMA,
    CODE_UNDERSTANDING_SCHEMA,
    COLLABORATION_SCHEMA,
    CRITERION_EVALUATION_SCHEMA,
    FEEDBACK_SCHEMA,
]


class TestSchemaValidity:
    """Meta-tests: schemas themselves must be valid Draft-07."""

    def test_all_schemas_are_valid_draft07(self):
        """Each schema passes jsonschema.Draft7Validator.check_schema()."""
        for schema in ALL_SCHEMAS:
            jsonschema.Draft7Validator.check_schema(schema)

    def test_all_schemas_self_contained(self):
        """No schema uses $ref — all self-contained per design decision."""
        for schema in ALL_SCHEMAS:
            schema_str = str(schema)
            assert "$ref" not in schema_str, (
                f"Schema contains $ref which is not allowed: {schema}"
            )


# ---------------------------------------------------------------------------
# RepoUnderstandingSchema tests
# ---------------------------------------------------------------------------

class TestRepoUnderstandingSchema:
    """Contract tests for REPO_UNDERSTANDING_SCHEMA."""

    VALID_DATA = {
        "languages": {"Python": 5, "JavaScript": 3},
        "key_files": [
            {"path": "src/main.py", "role": "entry point", "importance": "high"},
            {"path": "config.yaml", "role": "configuration", "importance": "medium"},
        ],
        "total_files": 10,
        "total_loc": 1500,
        "structural_summary": "Well-organized Python project with MVC structure.",
        "risk_flags": ["No tests directory found"],
    }

    def test_repo_understanding_valid_data(self):
        """Valid data with all required fields passes validation."""
        jsonschema.validate(instance=self.VALID_DATA, schema=REPO_UNDERSTANDING_SCHEMA)

    def test_repo_understanding_missing_required(self):
        """Data missing a required field fails validation."""
        invalid = dict(self.VALID_DATA)
        del invalid["languages"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=REPO_UNDERSTANDING_SCHEMA)

    def test_repo_understanding_missing_key_files(self):
        """Data missing key_files fails validation."""
        invalid = dict(self.VALID_DATA)
        del invalid["key_files"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=REPO_UNDERSTANDING_SCHEMA)

    def test_repo_understanding_invalid_importance(self):
        """key_files.importance must be one of 'high', 'medium', 'low'."""
        invalid = dict(self.VALID_DATA)
        invalid["key_files"] = [
            {"path": "src/main.py", "role": "entry point", "importance": "critical"},
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=REPO_UNDERSTANDING_SCHEMA)

    def test_repo_understanding_minimal_valid(self):
        """Minimal valid data (only required fields) passes."""
        minimal = {
            "languages": {},
            "key_files": [],
            "structural_summary": "Minimal repo.",
            "risk_flags": [],
        }
        jsonschema.validate(instance=minimal, schema=REPO_UNDERSTANDING_SCHEMA)


# ---------------------------------------------------------------------------
# CodeUnderstandingSchema tests
# ---------------------------------------------------------------------------

class TestCodeUnderstandingSchema:
    """Contract tests for CODE_UNDERSTANDING_SCHEMA."""

    VALID_DATA = {
        "capabilities": [
            {
                "name": "File processing",
                "description": "Reads and parses CSV files",
                "files": ["src/parser.py"],
                "confidence": 0.85,
            },
        ],
        "algorithms": ["Quick sort", "Binary search"],
        "apis": ["pandas", "numpy"],
        "data_structures": ["Array", "Dictionary"],
        "file_operations": ["read", "write"],
        "error_handling": {
            "has_error_handling": True,
            "patterns": ["Try/except blocks"],
        },
    }

    def test_code_understanding_valid_data(self):
        """Valid capabilities data passes validation."""
        jsonschema.validate(instance=self.VALID_DATA, schema=CODE_UNDERSTANDING_SCHEMA)

    def test_code_understanding_missing_required(self):
        """Data missing a required field fails."""
        invalid = dict(self.VALID_DATA)
        del invalid["capabilities"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=CODE_UNDERSTANDING_SCHEMA)

    def test_code_understanding_invalid_confidence_above_1(self):
        """Confidence > 1 fails validation."""
        invalid = dict(self.VALID_DATA)
        invalid["capabilities"] = [
            {
                "name": "File processing",
                "description": "Reads CSV files",
                "files": ["src/parser.py"],
                "confidence": 1.5,  # exceeds maximum of 1
            },
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=CODE_UNDERSTANDING_SCHEMA)

    def test_code_understanding_invalid_confidence_below_0(self):
        """Confidence < 0 fails validation."""
        invalid = dict(self.VALID_DATA)
        invalid["capabilities"] = [
            {
                "name": "File processing",
                "description": "Reads CSV files",
                "files": ["src/parser.py"],
                "confidence": -0.5,  # below minimum of 0
            },
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=CODE_UNDERSTANDING_SCHEMA)

    def test_code_understanding_minimal_valid(self):
        """Minimal valid data (empty arrays allowed) passes."""
        minimal = {
            "capabilities": [],
            "algorithms": [],
            "apis": [],
            "data_structures": [],
            "error_handling": {
                "has_error_handling": False,
                "patterns": [],
            },
        }
        jsonschema.validate(instance=minimal, schema=CODE_UNDERSTANDING_SCHEMA)


# ---------------------------------------------------------------------------
# CollaborationSchema tests
# ---------------------------------------------------------------------------

class TestCollaborationSchema:
    """Contract tests for COLLABORATION_SCHEMA."""

    VALID_DATA = {
        "commit_analysis": {
            "total_commits": 25,
            "commit_frequency": "regular",
            "meaningful_commits": 20,
            "patterns": ["Feature branches", "Atomic commits"],
        },
        "contributor_analysis": {
            "total_contributors": 3,
            "contributions_distribution": "60/30/10",
            "key_contributors": ["alice", "bob"],
        },
        "pull_request_analysis": {
            "total_prs": 5,
            "merged_prs": 4,
            "review_quality": "thorough",
        },
        "collaboration_score": 0.8,
        "summary": "Good team collaboration with balanced contributions.",
    }

    def test_collaboration_valid_data(self):
        """Valid collaboration data passes validation."""
        jsonschema.validate(instance=self.VALID_DATA, schema=COLLABORATION_SCHEMA)

    def test_collaboration_missing_commit_analysis(self):
        """Missing commit_analysis fails."""
        invalid = dict(self.VALID_DATA)
        del invalid["commit_analysis"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=COLLABORATION_SCHEMA)

    def test_collaboration_missing_contributor_analysis(self):
        """Missing contributor_analysis fails."""
        invalid = dict(self.VALID_DATA)
        del invalid["contributor_analysis"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=COLLABORATION_SCHEMA)

    def test_collaboration_score_out_of_range(self):
        """collaboration_score must be between 0 and 1."""
        invalid = dict(self.VALID_DATA)
        invalid["collaboration_score"] = 1.5
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=COLLABORATION_SCHEMA)

    def test_collaboration_minimal_valid(self):
        """Minimal valid data (only required fields for nested objects) passes."""
        minimal = {
            "commit_analysis": {"total_commits": 0},
            "contributor_analysis": {"total_contributors": 0},
            "collaboration_score": 0.0,
        }
        jsonschema.validate(instance=minimal, schema=COLLABORATION_SCHEMA)


# ---------------------------------------------------------------------------
# CriterionEvaluationSchema tests
# ---------------------------------------------------------------------------

class TestCriterionEvaluationSchema:
    """Contract tests for CRITERION_EVALUATION_SCHEMA."""

    VALID_DATA = {
        "criterion_key": "code_quality",
        "category_code": "Q1A",
        "score": 3.5,
        "max_score": 5.0,
        "confidence": 0.9,
        "evidence": ["Well-structured functions", "Consistent naming"],
        "remarks": "Good code organization.",
    }

    def test_criterion_evaluation_valid_data(self):
        """Valid criterion evaluation passes validation."""
        jsonschema.validate(
            instance=self.VALID_DATA, schema=CRITERION_EVALUATION_SCHEMA
        )

    def test_criterion_evaluation_missing_required(self):
        """Missing required field fails."""
        invalid = dict(self.VALID_DATA)
        del invalid["score"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                instance=invalid, schema=CRITERION_EVALUATION_SCHEMA
            )

    def test_criterion_evaluation_out_of_range_score(self):
        """Negative score fails validation (minimum 0)."""
        invalid = dict(self.VALID_DATA)
        invalid["score"] = -1.0
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                instance=invalid, schema=CRITERION_EVALUATION_SCHEMA
            )

    def test_criterion_evaluation_confidence_above_1(self):
        """Confidence > 1 fails validation."""
        invalid = dict(self.VALID_DATA)
        invalid["confidence"] = 1.2
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                instance=invalid, schema=CRITERION_EVALUATION_SCHEMA
            )

    def test_criterion_evaluation_negative_max_score(self):
        """Negative max_score fails validation."""
        invalid = dict(self.VALID_DATA)
        invalid["max_score"] = -5.0
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                instance=invalid, schema=CRITERION_EVALUATION_SCHEMA
            )

    def test_criterion_evaluation_non_list_evidence(self):
        """Evidence must be an array."""
        invalid = dict(self.VALID_DATA)
        invalid["evidence"] = "single string instead of array"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(
                instance=invalid, schema=CRITERION_EVALUATION_SCHEMA
            )


# ---------------------------------------------------------------------------
# FeedbackSchema tests
# ---------------------------------------------------------------------------

class TestFeedbackSchema:
    """Contract tests for FEEDBACK_SCHEMA."""

    VALID_DATA = {
        "strengths": [
            {
                "area": "Code organization",
                "description": "Well-structured with clear separation of concerns",
                "evidence_keys": ["Q1A.code_quality"],
            },
        ],
        "weaknesses": [
            {
                "area": "Error handling",
                "description": "Limited error handling in I/O operations",
                "evidence_keys": ["Q1A.error_handling"],
            },
        ],
        "suggestions": [
            {
                "area": "Error handling",
                "suggestion": "Add try/except blocks to file operations",
                "priority": "high",
            },
        ],
        "summary": "Good overall structure but needs better error handling.",
    }

    def test_feedback_valid_data(self):
        """Valid feedback data passes validation."""
        jsonschema.validate(instance=self.VALID_DATA, schema=FEEDBACK_SCHEMA)

    def test_feedback_missing_strengths(self):
        """Missing strengths fails (required)."""
        invalid = dict(self.VALID_DATA)
        del invalid["strengths"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=FEEDBACK_SCHEMA)

    def test_feedback_missing_weaknesses(self):
        """Missing weaknesses fails (required)."""
        invalid = dict(self.VALID_DATA)
        del invalid["weaknesses"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=FEEDBACK_SCHEMA)

    def test_feedback_missing_suggestions(self):
        """Missing suggestions fails (required)."""
        invalid = dict(self.VALID_DATA)
        del invalid["suggestions"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=FEEDBACK_SCHEMA)

    def test_feedback_missing_summary(self):
        """Missing summary fails (required)."""
        invalid = dict(self.VALID_DATA)
        del invalid["summary"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=FEEDBACK_SCHEMA)

    def test_feedback_invalid_suggestion_priority(self):
        """Suggestion priority must be one of 'high', 'medium', 'low'."""
        invalid = dict(self.VALID_DATA)
        invalid["suggestions"] = [
            {
                "area": "Error handling",
                "suggestion": "Add try/except blocks",
                "priority": "urgent",  # not in enum
            },
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=FEEDBACK_SCHEMA)

    def test_feedback_minimal_valid(self):
        """Minimal valid data (empty arrays) passes."""
        minimal = {
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "summary": "No evaluation data.",
        }
        jsonschema.validate(instance=minimal, schema=FEEDBACK_SCHEMA)
