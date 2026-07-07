import re
from pathlib import Path

from models.ingestion_models import FileRecord


class MetricsCalculator:
    def __init__(self, comment_syntax: dict | None = None):
        self._single = comment_syntax.get("single") if comment_syntax else None
        self._multi_start = comment_syntax.get("multi_start") if comment_syntax else None
        self._multi_end = comment_syntax.get("multi_end") if comment_syntax else None
        self._single_pattern = re.compile(r"^\s*" + re.escape(self._single)) if self._single else None

    def compute_metrics(
        self,
        source: str,
        parsed_data: dict | None = None,
    ) -> dict:
        lines = source.split("\n")
        total_lines = len(lines)

        comment_lines = self._count_comment_lines(lines)
        blank_lines = sum(1 for line in lines if line.strip() == "")
        code_loc = total_lines - comment_lines - blank_lines

        complexity = 0
        if parsed_data:
            for func in parsed_data.get("functions", []):
                complexity += func.get("complexity", 0)

        comment_ratio = round(comment_lines / total_lines, 4) if total_lines > 0 else 0.0

        return {
            "loc": total_lines,
            "code_loc": code_loc,
            "comment_lines": comment_lines,
            "comment_ratio": comment_ratio,
            "cyclomatic_complexity": complexity,
        }

    def _count_comment_lines(self, lines: list[str]) -> int:
        count = 0
        in_multiline = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if in_multiline:
                count += 1
                if self._multi_end and self._multi_end in stripped:
                    in_multiline = False
                    end_idx = stripped.index(self._multi_end)
                    remaining = stripped[end_idx + len(self._multi_end):].strip()
                    if remaining:
                        count -= 1
                continue

            if self._single_pattern and self._single_pattern.match(stripped):
                count += 1
                continue

            if self._multi_start and self._multi_start in stripped:
                if self._multi_end and self._multi_end in stripped:
                    start_idx = stripped.index(self._multi_start)
                    end_idx = stripped.index(self._multi_end)
                    if start_idx == 0 and stripped[end_idx + len(self._multi_end):].strip() == "":
                        count += 1
                    continue
                else:
                    start_idx = stripped.index(self._multi_start)
                    if start_idx == 0:
                        count += 1
                        in_multiline = True
                    continue

        return count

    @classmethod
    def from_config_entry(cls, config_entry: dict | None) -> "MetricsCalculator":
        comment_syntax = config_entry.get("comment_syntax") if config_entry else None
        return cls(comment_syntax=comment_syntax)
