"""Repository Understanding Agent — analyzes repository structure from ingestion data.

Reads a ProjectSnapshot (ingestion JSON) and produces a structured summary of
the repository's architecture, languages, key files, and risk flags.

This agent uses the "code" Ollama model (Qwen2.5-Coder 3B) for structural
analysis of the codebase.
"""

import json
import logging
from typing import Optional

from services.evaluation.agent_base import BaseAgent
from services.evaluation.schemas import REPO_UNDERSTANDING_SCHEMA
from services.evaluation.ollama_router import REPO_UNDERSTANDING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class RepoUnderstandingAgent(BaseAgent):
    """Analyzes repository structure and identifies key characteristics.

    Reads ingestion ProjectSnapshot data and produces:
      - Language distribution
      - Key files with roles and importance
      - Structural summary of the codebase
      - Risk flags for potential concerns

    This agent is designed to run independently (AGN-04), reads only from
    input_data (AGN-05), and writes validated structured output.
    """

    MAX_CONTENT_CHARS_PER_FILE = 2000

    def run(
        self,
        input_data: dict,
        output_path: Optional[str] = None,
    ) -> dict:
        """Execute repository understanding analysis.

        Args:
            input_data: ProjectSnapshot dict containing:
                - repo_stats: Repository statistics (language breakdown, LOC, etc.)
                - files: List of file records with paths, languages, metrics, content
                - repository_metadata: Basic repo metadata
            output_path: If provided, writes validated output to this path.

        Returns:
            dict: Validated repository understanding output conforming to
                REPO_UNDERSTANDING_SCHEMA.
        """
        # Extract relevant sections from input_data (AGN-05: no DB access)
        repo_stats = input_data.get("repo_stats", {})
        files = input_data.get("files", [])
        repo_metadata = input_data.get("repository_metadata", {})
        print(
            f"[DIAG] RepoUnderstandingAgent snapshot: "
            f"file_count={repo_stats.get('file_count', 0)} "
            f"total_loc={repo_stats.get('total_loc', 0)} "
            f"languages={list(repo_stats.get('language_breakdown', {}).keys())} "
            f"files_in_snapshot={len(files)}"
        )
        if not files:
            print(
                f"[DIAG] RepoUnderstandingAgent: ZERO files in snapshot! "
                f"snapshot_keys={list(input_data.keys())} "
                f"repo_stats_keys={list(repo_stats.keys())}"
            )

        # Build a concise user prompt with repository overview
        file_summaries = self._build_file_summary(files)
        file_contents = self._build_file_contents(files)

        user_prompt = (
            "Repository Overview:\n"
            f"- Name: {repo_metadata.get('name', repo_metadata.get('url', 'unknown'))}\n"
            f"- Language breakdown: {json.dumps(repo_stats.get('language_breakdown', {}), indent=2)}\n"
            f"- Total files: {repo_stats.get('file_count', len(files))}\n"
            f"- Total LOC: {repo_stats.get('total_loc', 0)}\n"
            f"- Code LOC: {repo_stats.get('code_loc', 0)}\n"
            f"- Average complexity: {repo_stats.get('average_complexity', 0)}\n\n"
            "Files:\n"
            f"{file_summaries}\n\n"
            f"Repository URL: {repo_metadata.get('url', 'N/A')}\n"
            f"\nSource Code Contents (key files):\n{file_contents}\n"
        )

        logger.info(
            "RepoUnderstandingAgent running: %d files, %d LOC",
            repo_stats.get("file_count", 0),
            repo_stats.get("total_loc", 0),
        )

        # Call Ollama with "code" model per OLL-02
        result = self.ollama.infer(
            model_role="code",
            system_prompt=REPO_UNDERSTANDING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )
        result = self._normalize_output(result, repo_stats, files)

        # Validate against schema (T-02-01 mitigation)
        is_valid, errors = self._validate_output(result, REPO_UNDERSTANDING_SCHEMA)
        if not is_valid:
            logger.error(
                "RepoUnderstandingAgent output failed schema validation: %s",
                "; ".join(errors),
            )
            result = {
                "languages": repo_stats.get("language_breakdown", {}),
                "key_files": [
                    {
                        "path": f.get("path", "unknown"),
                        "role": "unknown",
                        "importance": "medium",
                    }
                    for f in files[:5]
                ],
                "total_files": repo_stats.get("file_count", len(files)),
                "total_loc": repo_stats.get("total_loc", 0),
                "structural_summary": "Schema validation failed — unable to generate analysis.",
                "risk_flags": ["Schema validation failed"],
            }

        # Write output if path provided (AGN-05, D-11)
        if output_path:
            self._write_output(result, output_path)

        return result

    @staticmethod
    def _normalize_output(result: dict, repo_stats: dict, files: list[dict]) -> dict:
        if not isinstance(result, dict):
            return result
        key_map = {
            "languages": ["languages", "Languages", "languageDistribution", "language_distribution"],
            "key_files": ["key_files", "KeyFiles", "keyFiles", "mostImportantFiles", "most_important_files"],
            "total_files": ["total_files", "TotalFiles", "totalFiles", "total_file_count"],
            "total_loc": ["total_loc", "TotalLoc", "totalLoc", "total_lines"],
            "structural_summary": ["structural_summary", "StructuralSummary", "structuralSummary",
                                   "codeStructure", "code_structure", "structuralOrganization",
                                   "structural_organization", "overallStructure"],
            "risk_flags": ["risk_flags", "RiskFlags", "riskFlags", "risksAndConcerns",
                          "risks_and_concerns", "potentialRisksOrConcerns", "potential_risks"],
        }
        normalized = {}
        recognized = False
        for target, aliases in key_map.items():
            for alias in aliases:
                if alias in result:
                    normalized[target] = result[alias]
                    recognized = True
                    break
        if not recognized:
            return result

        if isinstance(normalized.get("languages"), list):
            normalized["languages"] = {item.get("name", str(item)): item.get("count", 1)
                                       for item in normalized["languages"]} if normalized["languages"] else {}
        key_files = normalized.get("key_files")
        if isinstance(key_files, list):
            rebuilt = []
            for f in key_files:
                if isinstance(f, dict):
                    rebuilt.append({
                        "path": f.get("path", f.get("Path", "")),
                        "role": f.get("role", f.get("Role", f.get("description", ""))),
                        "importance": f.get("importance", f.get("Importance", "medium")),
                    })
            normalized["key_files"] = rebuilt
        return normalized

    def _build_file_contents(self, files: list[dict], max_files: int = 10) -> str:
        sorted_files = sorted(
            files,
            key=lambda f: f.get("loc", f.get("code_loc", 0)) or 0,
            reverse=True,
        )
        lines = []
        for i, f in enumerate(sorted_files):
            if i >= max_files:
                break
            content = f.get("content", "")
            if not content:
                continue
            path = f.get("path", "unknown")
            lang = f.get("language", "unknown")
            preview = content[:self.MAX_CONTENT_CHARS_PER_FILE]
            if len(content) > self.MAX_CONTENT_CHARS_PER_FILE:
                preview += "\n... [truncated]"
            lines.append(f"--- {path} ---\n```{lang}\n{preview}\n```")
        return "\n".join(lines) if lines else "(no source content available)"

    def _build_file_summary(self, files: list[dict], max_files: int = 30) -> str:
        """Build a concise file summary string.

        Limits listing to max_files to stay within token context window.
        Files are sorted by LOC descending so the most significant files
        appear first.

        Args:
            files: List of file record dicts.
            max_files: Maximum number of files to list individually.

        Returns:
            str: Formatted file summary.
        """
        # Sort by LOC descending
        sorted_files = sorted(
            files,
            key=lambda f: f.get("loc", f.get("code_loc", 0)) or 0,
            reverse=True,
        )

        lines = []
        for i, f in enumerate(sorted_files):
            if i >= max_files:
                remaining = len(sorted_files) - max_files
                lines.append(f"... and {remaining} more files")
                break
            path = f.get("path", "unknown")
            lang = f.get("language", "unknown")
            loc = f.get("loc", f.get("code_loc", 0))
            lines.append(f"  {path} ({lang}, {loc} LOC)")

        return "\n".join(lines)
