import json
import os
from pathlib import Path


SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".svn", ".hg", "target", "build", "dist", ".next",
    ".tox", "env", ".env", "eggs", ".eggs",
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".rar",
    ".woff", ".woff2", ".ttf", ".eot",
    ".lock", ".log",
}


class FileInfo:
    def __init__(self, path: str, language: str, size_bytes: int = 0):
        self.path = path
        self.language = language
        self.size_bytes = size_bytes

    def to_dict(self) -> dict:
        return {"path": self.path, "language": self.language, "size_bytes": self.size_bytes}


class FileDiscoverer:
    def __init__(self, config_path: str = "config/extensions.json"):
        self.config_path = config_path
        self._extension_map: dict[str, dict] = {}
        self._shebang_map: dict[str, str] = {}
        self._comment_syntax_map: dict[str, dict] = {}
        self._load_config()

    def _load_config(self) -> None:
        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to load extension config from {self.config_path}: {e}")

        for entry in config.get("extensions", []):
            name = entry.get("name", "")
            shebangs = entry.get("shebang_patterns", [])
            comment_syntax = entry.get("comment_syntax", {})

            for ext in entry.get("extensions", []):
                self._extension_map[ext.lower()] = {
                    "name": name,
                    "comment_syntax": comment_syntax,
                }

            for sb in shebangs:
                self._shebang_map[sb.lower()] = name

            self._comment_syntax_map[name] = comment_syntax

    def get_comment_syntax(self, language: str) -> dict:
        return self._comment_syntax_map.get(language, {"single": None, "multi_start": None, "multi_end": None})

    def discover(self, root_path: str) -> list[FileInfo]:
        root = Path(root_path)
        if not root.exists() or not root.is_dir():
            return []

        results: list[FileInfo] = []
        for filepath in root.rglob("*"):
            if filepath.is_dir() or filepath.is_symlink():
                continue

            rel = filepath.relative_to(root)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue

            if filepath.suffix.lower() in SKIP_EXTENSIONS:
                continue

            language = self._detect_language(filepath)
            if language:
                try:
                    size = filepath.stat().st_size
                except OSError:
                    size = 0
                results.append(FileInfo(
                    path=str(rel.as_posix()),
                    language=language,
                    size_bytes=size,
                ))

        return sorted(results, key=lambda f: f.path)

    def _detect_language(self, filepath: Path) -> str | None:
        ext = filepath.suffix.lower()
        if ext in self._extension_map:
            return self._extension_map[ext]["name"]

        try:
            with open(filepath, "rb") as f:
                first_bytes = f.readline(128)
            first_line = first_bytes.decode("utf-8", errors="replace").strip().strip("\r\n")
            if first_line.startswith("#!"):
                interpreter = first_line[2:].split("/")[-1].split()[0].lower()
                for pattern, lang in self._shebang_map.items():
                    if pattern in interpreter:
                        return lang
        except (OSError, UnicodeDecodeError):
            pass

        return None
