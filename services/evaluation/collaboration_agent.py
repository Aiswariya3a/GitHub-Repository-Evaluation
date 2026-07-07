"""Collaboration Analysis Agent — evaluates team collaboration patterns.

Reads GitHub metadata from a ProjectSnapshot and analyzes commit patterns,
contributor activity, pull request practices, and issue tracking.

This agent uses the "reasoning" Ollama model (Phi-4 Mini) because
collaboration analysis is analytical/synthesis work, not code understanding
(OLL-03).
"""

import json
import logging
from typing import Optional

from services.evaluation.agent_base import BaseAgent
from services.evaluation.schemas import COLLABORATION_SCHEMA
from services.evaluation.ollama_router import COLLABORATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class CollaborationAgent(BaseAgent):
    """Analyzes collaboration patterns from GitHub metadata.

    Evaluates commit patterns, contributor distribution, pull request
    practices, and issue tracking to produce a collaboration score (0-1).

    This agent is designed to run independently (AGN-04), reads only from
    input_data (AGN-05), and writes validated structured output.
    """

    def run(
        self,
        input_data: dict,
        output_path: Optional[str] = None,
    ) -> dict:
        """Execute collaboration analysis.

        Args:
            input_data: ProjectSnapshot dict containing:
                - github_metadata: GitHub API metadata (commits, contributors,
                  pull requests, issues)
                - repo_stats: Repository statistics for context
            output_path: If provided, writes validated output to this path.

        Returns:
            dict: Validated collaboration analysis output conforming to
                COLLABORATION_SCHEMA.
        """
        github_metadata = input_data.get("github_metadata", {})
        repo_stats = input_data.get("repo_stats", {})

        # Build user prompt with structured GitHub metadata
        user_prompt = self._build_collaboration_prompt(github_metadata, repo_stats)

        logger.info(
            "CollaborationAgent running: %d commits, %d contributors",
            github_metadata.get("commits_count", 0),
            len(github_metadata.get("contributors", [])),
        )

        # Call Ollama with "reasoning" model per OLL-03
        result = self.ollama.infer(
            model_role="reasoning",
            system_prompt=COLLABORATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        # Validate against schema (T-02-03 mitigation)
        is_valid, errors = self._validate_output(result, COLLABORATION_SCHEMA)
        if not is_valid:
            logger.error(
                "CollaborationAgent output failed schema validation: %s",
                "; ".join(errors),
            )
            result = {
                "commit_analysis": {
                    "total_commits": github_metadata.get("commits_count", 0),
                    "commit_frequency": "unknown",
                    "meaningful_commits": 0,
                    "patterns": ["Analysis failed — schema validation error"],
                },
                "contributor_analysis": {
                    "total_contributors": len(
                        github_metadata.get("contributors", [])
                    ),
                    "contributions_distribution": "unknown",
                    "key_contributors": [],
                },
                "collaboration_score": 0,
                "summary": "Schema validation failed — unable to generate analysis.",
            }

        # Write output if path provided (AGN-05, D-11)
        if output_path:
            self._write_output(result, output_path)

        return result

    def _build_collaboration_prompt(
        self,
        github_metadata: dict,
        repo_stats: dict,
    ) -> str:
        """Build a structured collaboration analysis prompt.

        Args:
            github_metadata: GitHub metadata dict with commits, contributors,
                PRs, and issues data.
            repo_stats: Repository statistics dict.

        Returns:
            str: Formatted user prompt for collaboration analysis.
        """
        lines = [
            "Collaboration Data:",
            "",
            "--- Commits ---",
            f"Total commits: {github_metadata.get('commits_count', 0)}",
        ]

        # Commit details (if available via recent_commits or similar)
        recent_commits = github_metadata.get("recent_commits", [])
        if recent_commits:
            lines.append(f"Recent commits ({len(recent_commits)} shown):")
            for commit in recent_commits[:10]:
                author = commit.get("author", "unknown")
                date = commit.get("date", "unknown")
                msg = commit.get("message", "")[:80]
                lines.append(f"  - [{date}] {author}: {msg}")

        lines.extend([
            "",
            "--- Contributors ---",
            f"Total contributors: {len(github_metadata.get('contributors', []))}",
        ])

        contributors = github_metadata.get("contributors", [])
        if contributors:
            lines.append("Contributors:")
            for c in contributors[:15]:
                login = c.get("login", c.get("username", "unknown"))
                contributions = c.get("contributions", c.get("count", 0))
                lines.append(f"  - {login}: {contributions} contributions")
            if len(contributors) > 15:
                lines.append(f"  ... and {len(contributors) - 15} more contributors")

        lines.extend([
            "",
            "--- Pull Requests ---",
            f"Total PRs: {github_metadata.get('pull_requests_count', 0)}",
        ])

        pull_requests = github_metadata.get("pull_requests", [])
        if pull_requests:
            merged = sum(
                1 for pr in pull_requests if pr.get("state") == "merged"
                or pr.get("merged_at") is not None
            )
            open_prs = sum(
                1 for pr in pull_requests if pr.get("state") == "open"
            )
            lines.append(f"Merged: {merged}")
            lines.append(f"Open: {open_prs}")

        lines.extend([
            "",
            "--- Issues ---",
            f"Total issues: {github_metadata.get('issues_count', 0)}",
        ])

        issues = github_metadata.get("issues", [])
        if issues:
            closed = sum(1 for i in issues if i.get("state") == "closed")
            open_issues = sum(1 for i in issues if i.get("state") == "open")
            lines.append(f"Closed: {closed}")
            lines.append(f"Open: {open_issues}")

        lines.extend([
            "",
            "--- Repository Context ---",
            f"Total LOC: {repo_stats.get('total_loc', 0)}",
            f"Total files: {repo_stats.get('file_count', 0)}",
        ])

        return "\n".join(lines)
