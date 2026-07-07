import time
from datetime import datetime, timezone
from typing import Optional


class SnapshotBuilder:
    def build(
        self,
        repo_url: str,
        clone_url: str,
        clone_timestamp: str,
        status: str,
        base_repo_url: Optional[str],
        file_records: list[dict],
        metrics_results: list[dict],
        github_metadata: dict,
        delta_result: Optional[dict],
        ingestion_version: str = "1.0",
    ) -> dict:
        start_time = time.monotonic()

        files_merged = self._merge_files_with_metrics(file_records, metrics_results)
        repo_stats = self._compute_repo_stats(files_merged)

        repository_metadata = {
            "url": repo_url,
            "clone_url": clone_url,
            "clone_timestamp": clone_timestamp,
            "status": status,
            "base_repo_url": base_repo_url,
        }

        gh_metadata = {
            "commits_count": github_metadata.get("commits_count", 0),
            "contributors": github_metadata.get("contributors", []),
            "pull_requests_count": github_metadata.get("pull_requests_count", 0),
            "pull_requests": github_metadata.get("pull_requests", []),
            "issues_count": github_metadata.get("issues_count", 0),
            "issues": github_metadata.get("issues", []),
        }

        duration_ms = int((time.monotonic() - start_time) * 1000)

        ingestion_metadata = {
            "version": ingestion_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "pipeline_version": "1",
        }

        snapshot = {
            "repository_metadata": repository_metadata,
            "github_metadata": gh_metadata,
            "repo_stats": repo_stats,
            "files": files_merged,
            "delta": delta_result,
            "ingestion_metadata": ingestion_metadata,
        }

        return snapshot

    def _merge_files_with_metrics(
        self,
        file_records: list[dict],
        metrics_results: list[dict],
    ) -> list[dict]:
        merged = []
        for i, f_rec in enumerate(file_records):
            entry = {
                "path": f_rec.get("path", ""),
                "language": f_rec.get("language", ""),
                "loc": 0,
                "code_loc": 0,
                "comment_lines": 0,
                "comment_ratio": 0.0,
                "cyclomatic_complexity": 0,
                "functions": [],
                "classes": [],
                "imports": [],
                "docstrings": [],
                "capabilities": [],
            }

            if i < len(metrics_results):
                m = metrics_results[i]
                entry["loc"] = m.get("loc", 0)
                entry["code_loc"] = m.get("code_loc", 0)
                entry["comment_lines"] = m.get("comment_lines", 0)
                entry["comment_ratio"] = m.get("comment_ratio", 0.0)
                entry["cyclomatic_complexity"] = m.get("cyclomatic_complexity", 0)
                entry["functions"] = m.get("functions", [])
                entry["classes"] = m.get("classes", [])
                entry["imports"] = m.get("imports", [])
                entry["docstrings"] = m.get("docstrings", [])

            merged.append(entry)

        return merged

    def _compute_repo_stats(self, files: list[dict]) -> dict:
        total_loc = sum(f.get("loc", 0) for f in files)
        code_loc = sum(f.get("code_loc", 0) for f in files)
        file_count = len(files)
        total_complexity = sum(f.get("cyclomatic_complexity", 0) for f in files)
        avg_complexity = round(total_complexity / file_count, 2) if file_count > 0 else 0.0
        total_comment_lines = sum(f.get("comment_lines", 0) for f in files)
        comment_ratio = round(total_comment_lines / total_loc, 4) if total_loc > 0 else 0.0

        language_breakdown: dict[str, int] = {}
        for f in files:
            lang = f.get("language", "Unknown")
            language_breakdown[lang] = language_breakdown.get(lang, 0) + 1

        return {
            "total_loc": total_loc,
            "code_loc": code_loc,
            "file_count": file_count,
            "total_complexity": total_complexity,
            "average_complexity": avg_complexity,
            "comment_ratio": comment_ratio,
            "language_breakdown": language_breakdown,
        }
