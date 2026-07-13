"""Code Understanding Agent — extracts code capabilities from parsed source analysis.

Reads a ProjectSnapshot (ingestion JSON) and identifies capabilities,
algorithms, APIs, data structures, file operations, and error handling
patterns present in the student's code.

This agent uses the "code" Ollama model (Qwen2.5-Coder 3B) for code
understanding tasks.
"""

import json
import logging
from typing import Optional

from services.evaluation.agent_base import BaseAgent
from services.evaluation.schemas import CODE_UNDERSTANDING_SCHEMA
from services.evaluation.ollama_router import CODE_UNDERSTANDING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Maximum files to include in prompt to avoid context window overflow
MAX_FILES_IN_PROMPT = 10


class CodeUnderstandingAgent(BaseAgent):
    """Extracts code capabilities, algorithms, APIs, and error handling patterns.

    Analyzes parsed code structures (functions, classes, imports, metrics)
    and delta information to identify what the student's code can do.

    This agent is designed to run independently (AGN-04), reads only from
    input_data (AGN-05), and writes validated structured output.
    """

    def run(
        self,
        input_data: dict,
        output_path: Optional[str] = None,
    ) -> dict:
        """Execute code understanding analysis.

        Args:
            input_data: ProjectSnapshot dict containing:
                - files: List of file records with parsed functions, classes, imports
                - repo_stats: Repository statistics
                - delta: Optional delta information (student vs template code)
            output_path: If provided, writes validated output to this path.

        Returns:
            dict: Validated code understanding output conforming to
                CODE_UNDERSTANDING_SCHEMA.
        """
        files = input_data.get("files", [])
        repo_stats = input_data.get("repo_stats", {})
        delta = input_data.get("delta")

        # Build structured user prompt (token-efficient — no raw source code)
        user_prompt = self._build_code_analysis_prompt(files, repo_stats, delta)

        logger.info(
            "CodeUnderstandingAgent running: %d files available, %d in prompt",
            len(files),
            min(len(files), MAX_FILES_IN_PROMPT),
        )

        # Call Ollama with "code" model per OLL-02
        result = self.ollama.infer(
            model_role="code",
            system_prompt=CODE_UNDERSTANDING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )
        result = self._normalize_output(result)

        # Validate against schema (T-02-02 mitigation)
        is_valid, errors = self._validate_output(result, CODE_UNDERSTANDING_SCHEMA)
        if not is_valid:
            logger.error(
                "CodeUnderstandingAgent output failed schema validation: %s",
                "; ".join(errors),
            )
            result = {
                "capabilities": [
                    {
                        "name": "Schema validation failed",
                        "description": (
                            "Agent output did not validate against schema"
                        ),
                        "files": [],
                        "confidence": 0,
                    }
                ],
                "algorithms": [],
                "apis": [],
                "data_structures": [],
                "error_handling": {
                    "has_error_handling": False,
                    "patterns": ["Analysis failed"],
                },
            }

        # Write output if path provided (AGN-05, D-11)
        if output_path:
            self._write_output(result, output_path)

        return result

    @staticmethod
    def _normalize_output(result: dict) -> dict:
        if not isinstance(result, dict):
            return result
        key_map = {
            "capabilities": ["capabilities", "Capabilities"],
            "algorithms": ["algorithms", "Algorithms", "algorithms_used"],
            "apis": ["apis", "APIs", "Apis", "api_and_libraries_leveraged", "api_and_libraries"],
            "data_structures": ["data_structures", "DataStructures", "dataStructures",
                                "data_structures_implemented_or_used"],
            "error_handling": ["error_handling", "ErrorHandling", "errorHandling",
                               "error_handling_approaches_and_coverage"],
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

        # Fix nested structure: LLM sometimes puts algorithms/apis/etc under a single "capabilities" key
        caps = normalized.get("capabilities")
        if isinstance(caps, dict):
            for key in ("algorithms", "apis", "data_structures", "error_handling"):
                if key in caps and key not in normalized:
                    normalized[key] = caps[key]
            normalized["capabilities"] = caps.get("capabilities", caps.get("Capabilities", []))

        # Normalize capabilities items
        cap_list = normalized.get("capabilities", [])
        if isinstance(cap_list, list):
            rebuilt = []
            for item in cap_list:
                if isinstance(item, dict):
                    rebuilt.append({
                        "name": item.get("name", item.get("Name", item.get("capability", ""))),
                        "description": item.get("description", item.get("Description", "")),
                        "files": item.get("files", item.get("Files", item.get("file", []))),
                        "confidence": item.get("confidence", item.get("Confidence",
                                        item.get("confidence_level", item.get("ConfidenceLevel", 0)))),
                    })
            normalized["capabilities"] = rebuilt

        # Normalize error_handling
        eh = normalized.get("error_handling", {})
        if isinstance(eh, dict):
            has = eh.get("has_error_handling", eh.get("HasErrorHandling"))
            if has is None:
                has = bool(eh.get("patterns", eh.get("Patterns", [])))
            normalized["error_handling"] = {
                "has_error_handling": has,
                "patterns": eh.get("patterns", eh.get("Patterns", [])),
            }
        elif isinstance(eh, list):
            normalized["error_handling"] = {
                "has_error_handling": bool(eh),
                "patterns": [str(e) for e in eh],
            }

        # Ensure arrays
        for k in ("algorithms", "apis", "data_structures"):
            val = normalized.get(k)
            if isinstance(val, list):
                normalized[k] = [str(v) if not isinstance(v, str) else v for v in val]
            elif val is None:
                normalized[k] = []
            elif isinstance(val, dict):
                normalized[k] = list(val.values()) if any(isinstance(v, str) for v in val.values()) else [str(val)]
        return normalized

    def _build_code_analysis_prompt(
        self,
        files: list[dict],
        repo_stats: dict,
        delta: Optional[dict],
    ) -> str:
        """Build a structured code analysis prompt from parsed data.

        Selects the most significant files (by LOC) up to MAX_FILES_IN_PROMPT
        to stay within context window. Uses parsed structures only, not raw
        source code (Pitfall 2 mitigation / T-02-04).

        Args:
            files: List of file record dicts.
            repo_stats: Repository statistics dict.
            delta: Optional delta result dict.

        Returns:
            str: Formatted user prompt for code analysis.
        """
        # Sort by LOC descending, take top N
        sorted_files = sorted(
            files,
            key=lambda f: f.get("loc", f.get("code_loc", 0)) or 0,
            reverse=True,
        )
        selected_files = sorted_files[:MAX_FILES_IN_PROMPT]

        lines = [
            "Repository Statistics:",
            f"  Total files: {repo_stats.get('file_count', len(files))}",
            f"  Total LOC: {repo_stats.get('total_loc', 0)}",
            f"  Code LOC: {repo_stats.get('code_loc', 0)}",
            f"  Average complexity: {repo_stats.get('average_complexity', 0)}",
            "",
            "Top Files (by LOC):",
        ]

        for f in selected_files:
            path = f.get("path", "unknown")
            language = f.get("language", "unknown")
            loc = f.get("loc", f.get("code_loc", 0))
            lines.append(f"File: {path} ({language}, {loc} LOC)")

            # Functions
            functions = f.get("functions", [])
            if functions:
                func_strs = []
                for func in functions[:8]:  # limit per file
                    name = func.get("name", "?")
                    lineno = func.get("lineno", 0)
                    end = func.get("end_lineno", 0)
                    complexity = func.get("complexity", 1)
                    func_strs.append(
                        f"{name} (line {lineno}-{end}, complexity {complexity})"
                    )
                lines.append(f"  Functions: {', '.join(func_strs)}")
                if len(functions) > 8:
                    lines.append(f"  ... and {len(functions) - 8} more functions")

            # Classes
            classes = f.get("classes", [])
            if classes:
                class_strs = []
                for cls in classes:
                    name = cls.get("name", "?")
                    methods = cls.get("methods", [])
                    method_names = [m.get("name", "?") for m in methods]
                    methods_str = (
                        f", methods: {', '.join(method_names)}" if method_names else ""
                    )
                    class_strs.append(f"{name}{methods_str}")
                lines.append(f"  Classes: {'; '.join(class_strs)}")

            # Imports
            imports = f.get("imports", [])
            if imports:
                imp_strs = [imp.get("module", "?") for imp in imports]
                lines.append(f"  Imports: {', '.join(imp_strs)}")

            lines.append("---")

        # Include delta information if available
        if delta:
            lines.extend(self._format_delta(delta))

        # Note if we truncated files
        if len(files) > MAX_FILES_IN_PROMPT:
            lines.append(
                f"\nNote: {len(files) - MAX_FILES_IN_PROMPT} additional files "
                "not shown (context window limit)"
            )

        return "\n".join(lines)

    def _format_delta(self, delta: dict) -> list[str]:
        """Format delta information for the prompt.

        Args:
            delta: Delta result dict with repo_level, file_level, symbol_level.

        Returns:
            list[str]: Formatted delta lines.
        """
        lines = ["\nDelta (student changes vs template code):"]

        repo_level = delta.get("repo_level", {})
        if repo_level:
            added = repo_level.get("added_files", [])
            modified = repo_level.get("modified_files", [])
            removed = repo_level.get("removed_files", [])
            if added:
                lines.append(f"  ADDED files: {', '.join(added[:5])}")
            if modified:
                lines.append(f"  MODIFIED files: {', '.join(modified[:5])}")
            if removed:
                lines.append(f"  REMOVED files: {', '.join(removed[:5])}")

        # Symbol-level delta for fine-grained changes
        symbol_level = delta.get("symbol_level", {})
        symbol_files = symbol_level.get("files", {}) if isinstance(symbol_level, dict) else {}
        if symbol_files:
            # Show first 3 files with symbol changes
            count = 0
            for file_path, symbols in symbol_files.items():
                if count >= 3:
                    lines.append(f"  ... and {len(symbol_files) - 3} more files with symbol changes")
                    break
                added_syms = symbols.get("added", [])
                modified_syms = symbols.get("modified", [])
                parts = []
                if added_syms:
                    parts.append(f"ADDED: {', '.join(s.get('name', '?') for s in added_syms)}")
                if modified_syms:
                    parts.append(f"MODIFIED: {', '.join(s.get('name', '?') for s in modified_syms)}")
                if parts:
                    lines.append(f"  {file_path}: {'; '.join(parts)}")
                count += 1

        return lines
