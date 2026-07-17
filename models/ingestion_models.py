from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RepositoryMetadata:
    url: str
    clone_url: str
    clone_timestamp: str
    status: str = "pending"
    base_repo_url: Optional[str] = None


@dataclass
class FunctionInfo:
    name: str
    lineno: int
    end_lineno: int
    complexity: int = 1
    docstring: Optional[str] = None


@dataclass
class ClassInfo:
    name: str
    lineno: int
    end_lineno: int
    docstring: Optional[str] = None
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ImportInfo:
    module: str
    names: list[str] = field(default_factory=list)
    alias: Optional[str] = None


@dataclass
class DocstringInfo:
    text: str
    lineno: int
    type: str = "docstring"


@dataclass
class FileRecord:
    path: str
    language: str
    loc: int = 0
    code_loc: int = 0
    comment_lines: int = 0
    comment_ratio: float = 0.0
    cyclomatic_complexity: int = 0
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    docstrings: list[DocstringInfo] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    content: str = ""


@dataclass
class GitHubMetadata:
    commits_count: int = 0
    recent_commits: list[dict] = field(default_factory=list)
    contributors: list[dict] = field(default_factory=list)
    pull_requests_count: int = 0
    pull_requests: list[dict] = field(default_factory=list)
    issues_count: int = 0
    issues: list[dict] = field(default_factory=list)


@dataclass
class RepoStats:
    total_loc: int = 0
    code_loc: int = 0
    file_count: int = 0
    total_complexity: int = 0
    average_complexity: float = 0.0
    comment_ratio: float = 0.0
    language_breakdown: dict[str, int] = field(default_factory=dict)


@dataclass
class DeltaRepoLevel:
    added_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    renamed_files: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class DeltaFileLevelEntry:
    added_sections: list[str] = field(default_factory=list)
    removed_sections: list[str] = field(default_factory=list)
    modified_regions: list[dict] = field(default_factory=list)
    line_diff: Optional[str] = None


@dataclass
class DeltaSymbolEntry:
    name: str
    type: str
    signature_hash: Optional[str] = None


@dataclass
class DeltaSymbolLevel:
    added: list[DeltaSymbolEntry] = field(default_factory=list)
    modified: list[DeltaSymbolEntry] = field(default_factory=list)
    removed: list[DeltaSymbolEntry] = field(default_factory=list)
    unchanged: list[DeltaSymbolEntry] = field(default_factory=list)


@dataclass
class DeltaFileLevel:
    files: dict[str, DeltaFileLevelEntry] = field(default_factory=dict)


@dataclass
class DeltaSymbolLevelMap:
    files: dict[str, DeltaSymbolLevel] = field(default_factory=dict)


@dataclass
class DeltaResult:
    repo_level: DeltaRepoLevel = field(default_factory=DeltaRepoLevel)
    file_level: DeltaFileLevel = field(default_factory=DeltaFileLevel)
    symbol_level: DeltaSymbolLevelMap = field(default_factory=DeltaSymbolLevelMap)


@dataclass
class IngestionMetadata:
    version: str = "1.0"
    timestamp: str = ""
    duration_ms: int = 0
    pipeline_version: str = "1"


@dataclass
class ProjectSnapshot:
    repository_metadata: RepositoryMetadata = field(default_factory=RepositoryMetadata)
    github_metadata: GitHubMetadata = field(default_factory=GitHubMetadata)
    repo_stats: RepoStats = field(default_factory=RepoStats)
    files: list[FileRecord] = field(default_factory=list)
    delta: Optional[DeltaResult] = None
    ingestion_metadata: IngestionMetadata = field(default_factory=IngestionMetadata)
