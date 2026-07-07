import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from services.github_service import GitHubService
from services.ingestion import FileDiscoverer, CodeParser, MetricsCalculator, DeltaDetector
from services.ingestion.snapshot_builder import SnapshotBuilder
from repositories.ingestion_repository import IngestionRepository


class IngestionService:
    def __init__(
        self,
        github_service: Optional[GitHubService] = None,
        file_discoverer: Optional[FileDiscoverer] = None,
        code_parser: Optional[CodeParser] = None,
        metrics_calculator: Optional[MetricsCalculator] = None,
        delta_detector: Optional[DeltaDetector] = None,
        snapshot_builder: Optional[SnapshotBuilder] = None,
        ingestion_repository: Optional[IngestionRepository] = None,
    ):
        self.github = github_service or GitHubService()
        self.discoverer = file_discoverer or FileDiscoverer()
        self.parser = code_parser or CodeParser()
        self.metrics = metrics_calculator or MetricsCalculator()
        self.delta = delta_detector or DeltaDetector(
            file_discoverer=self.discoverer,
            code_parser=self.parser,
        )
        self.snapshot_builder = snapshot_builder or SnapshotBuilder()
        self.ingestion_repo = ingestion_repository or IngestionRepository()

    def ingest(
        self,
        repo_url: str,
        roll_number: str,
        base_repo_url: Optional[str] = None,
        working_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        repository_id: Optional[str] = None,
    ) -> dict:
        overall_start = time.monotonic()
        clone_path: Optional[str] = None
        status = "pending"
        error: Optional[str] = None
        snapshot_path: Optional[str] = None
        ingestion_record_id: Optional[str] = None
        stats = {}

        working_dir = working_dir or os.getcwd()
        output_dir = output_dir or os.path.join(working_dir, "snapshots")
        os.makedirs(output_dir, exist_ok=True)

        try:
            # Stage 1: Clone
            clone_start = time.monotonic()
            try:
                clone_path = self.github.clone(repo_url, roll_number)
                if not clone_path:
                    raise RuntimeError(f"Clone failed for {repo_url}")
            except Exception as e:
                error = f"Clone failed: {e}"
                return {
                    "status": "failed",
                    "snapshot_path": None,
                    "ingestion_record_id": None,
                    "error": error,
                    "stats": {"clone_duration_ms": int((time.monotonic() - clone_start) * 1000)},
                }
            clone_duration = int((time.monotonic() - clone_start) * 1000)
            clone_timestamp = datetime.now(timezone.utc).isoformat()

            # Stage 2: GitHub Metadata
            meta_start = time.monotonic()
            github_metadata = {"commits_count": 0, "contributors": [], "pull_requests_count": 0, "pull_requests": [], "issues_count": 0, "issues": []}
            try:
                github_metadata = self.github.get_full_metadata(repo_url)
            except Exception:
                pass
            meta_duration = int((time.monotonic() - meta_start) * 1000)

            # Stage 3: File Discovery
            discover_start = time.monotonic()
            discovered_files = []
            try:
                discovered_files = self.discoverer.discover(clone_path)
            except Exception as e:
                error = f"File discovery failed: {e}"
                status = "partial"
            discover_duration = int((time.monotonic() - discover_start) * 1000)

            if not discovered_files:
                error = (error or "") + "; No source files discovered"
                status = "partial"

            # Stage 4 & 5: Parse + Metrics
            parse_metrics_start = time.monotonic()
            file_records: list[dict] = [f.to_dict() for f in discovered_files]
            metrics_results: list[dict] = []
            parse_errors = 0

            for file_info in discovered_files:
                file_path = os.path.join(clone_path, file_info.path)
                file_result = {
                    "loc": 0, "code_loc": 0, "comment_lines": 0,
                    "comment_ratio": 0.0, "cyclomatic_complexity": 0,
                    "functions": [], "classes": [], "imports": [], "docstrings": [],
                }

                try:
                    source = self._read_source_file(file_path)
                    if source is None:
                        continue

                    parsed = self.parser.parse_file(source, file_info.language)
                    file_result.update(parsed)

                    comment_syntax = self.discoverer.get_comment_syntax(file_info.language)
                    mc = MetricsCalculator(comment_syntax=comment_syntax)
                    metrics = mc.compute_metrics(source, parsed)
                    file_result.update(metrics)

                except Exception:
                    parse_errors += 1

                metrics_results.append(file_result)

            parse_metrics_duration = int((time.monotonic() - parse_metrics_start) * 1000)

            if parse_errors > 0:
                status = "partial"
                error = (error or "") + f"; {parse_errors} file(s) had parse errors"

            # Stage 6: Delta Detection
            delta_start = time.monotonic()
            delta_result: Optional[dict] = None
            if base_repo_url:
                base_clone_path: Optional[str] = None
                try:
                    base_clone_path = self.github.clone(base_repo_url, "BASE")
                    if base_clone_path:
                        base_discovered = self.discoverer.discover(base_clone_path)
                        base_parsed: dict[str, dict] = {}
                        for bf in base_discovered:
                            bp = os.path.join(base_clone_path, bf.path)
                            bsource = self._read_source_file(bp)
                            if bsource:
                                base_parsed[bf.path] = self.parser.parse_file(bsource, bf.language)

                        student_parsed: dict[str, dict] = {}
                        for i, fi in enumerate(discovered_files):
                            if i < len(metrics_results):
                                student_parsed[fi.path] = metrics_results[i]

                        delta_result = self.delta.detect_delta(
                            student_repo_path=clone_path,
                            base_repo_path=base_clone_path,
                            student_parsed_files=student_parsed,
                            base_parsed_files=base_parsed,
                        )
                except Exception as e:
                    error = (error or "") + f"; Delta detection failed: {e}"
                finally:
                    if base_clone_path and os.path.exists(base_clone_path):
                        shutil.rmtree(base_clone_path, ignore_errors=True)
            delta_duration = int((time.monotonic() - delta_start) * 1000)

            # Stage 7: Build Snapshot
            build_start = time.monotonic()
            if not error:
                status = "success"
            elif status != "partial":
                status = "partial"

            snapshot = self.snapshot_builder.build(
                repo_url=repo_url,
                clone_url=repo_url,
                clone_timestamp=clone_timestamp,
                status=status,
                base_repo_url=base_repo_url,
                file_records=file_records,
                metrics_results=metrics_results,
                github_metadata=github_metadata,
                delta_result=delta_result,
            )
            build_duration = int((time.monotonic() - build_start) * 1000)

            # Stage 8: Write JSON
            json_start = time.monotonic()
            safe_name = self.github.sanitize_name(roll_number, repo_url)
            json_filename = f"{safe_name}_snapshot.json"
            snapshot_path = os.path.join(output_dir, json_filename)

            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, default=str)
            json_duration = int((time.monotonic() - json_start) * 1000)

            # Stage 9: PostgreSQL Persistence
            db_start = time.monotonic()
            if repository_id:
                try:
                    ingestion_record_id = self.ingestion_repo.save_ingestion(
                        repository_id=repository_id,
                        snapshot_dict=snapshot,
                    )
                except Exception as e:
                    error = (error or "") + f"; DB persistence failed: {e}"
            db_duration = int((time.monotonic() - db_start) * 1000)

            total_duration = int((time.monotonic() - overall_start) * 1000)
            stats = {
                "clone_duration_ms": clone_duration,
                "metadata_duration_ms": meta_duration,
                "discover_duration_ms": discover_duration,
                "parse_metrics_duration_ms": parse_metrics_duration,
                "delta_duration_ms": delta_duration,
                "build_duration_ms": build_duration,
                "json_duration_ms": json_duration,
                "db_duration_ms": db_duration,
                "total_duration_ms": total_duration,
                "files_discovered": len(discovered_files),
                "parse_errors": parse_errors,
            }

            return {
                "status": status,
                "snapshot_path": snapshot_path,
                "ingestion_record_id": ingestion_record_id,
                "error": error,
                "stats": stats,
            }

        except Exception as e:
            total_duration = int((time.monotonic() - overall_start) * 1000)
            return {
                "status": "failed",
                "snapshot_path": snapshot_path,
                "ingestion_record_id": None,
                "error": f"Unexpected error: {e}",
                "stats": {"total_duration_ms": total_duration},
            }

        finally:
            if clone_path and os.path.exists(clone_path):
                shutil.rmtree(clone_path, ignore_errors=True)

    def _read_source_file(self, file_path: str) -> Optional[str]:
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return Path(file_path).read_text(encoding="latin-1")
            except (OSError, IOError):
                return None
        except (OSError, IOError):
            return None
