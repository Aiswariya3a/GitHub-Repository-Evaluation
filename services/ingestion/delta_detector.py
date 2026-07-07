import difflib
import hashlib
import os
from pathlib import Path


class DeltaDetector:
    def __init__(self, file_discoverer=None, code_parser=None):
        self._file_discoverer = file_discoverer
        self._code_parser = code_parser

    def detect_delta(
        self,
        student_repo_path: str,
        base_repo_path: str,
        student_parsed_files: dict[str, dict] | None = None,
        base_parsed_files: dict[str, dict] | None = None,
    ) -> dict:
        student_files = self._get_file_list(student_repo_path)
        base_files = self._get_file_list(base_repo_path)

        student_set = set(student_files)
        base_set = set(base_files)

        added_files = sorted(student_set - base_set)
        removed_files = sorted(base_set - student_set)
        common_files = sorted(student_set & base_set)

        modified_files = []
        for fpath in common_files:
            student_hash = self._file_hash(os.path.join(student_repo_path, fpath))
            base_hash = self._file_hash(os.path.join(base_repo_path, fpath))
            if student_hash != base_hash:
                modified_files.append(fpath)

        renamed_files = self._detect_renames(removed_files, added_files, student_repo_path, base_repo_path)
        true_added = [f for f in added_files if not any(r[1] == f for r in renamed_files)]
        true_removed = [f for f in removed_files if not any(r[0] == f for r in renamed_files)]

        repo_level = {
            "added_files": true_added,
            "removed_files": true_removed,
            "modified_files": modified_files,
            "renamed_files": [list(r) for r in renamed_files],
        }

        file_level = {"files": {}}
        for fpath in modified_files:
            student_content = self._read_file(os.path.join(student_repo_path, fpath))
            base_content = self._read_file(os.path.join(base_repo_path, fpath))
            file_level["files"][fpath] = self._compute_file_level_delta(
                student_content, base_content
            )

        symbol_level = {"files": {}}
        all_modified = modified_files + [r[1] for r in renamed_files]
        for fpath in all_modified:
            base_path = fpath
            for old, new in renamed_files:
                if fpath == new:
                    base_path = old
                    break

            student_parsed = None
            base_parsed = None

            if student_parsed_files and fpath in student_parsed_files:
                student_parsed = student_parsed_files[fpath]
            elif self._code_parser:
                content = self._read_file(os.path.join(student_repo_path, fpath))
                lang = self._detect_language(fpath)
                if lang:
                    student_parsed = self._code_parser.parse_file(content, lang)

            if base_parsed_files and base_path in base_parsed_files:
                base_parsed = base_parsed_files[base_path]
            elif self._code_parser:
                content = self._read_file(os.path.join(base_repo_path, base_path))
                lang = self._detect_language(fpath)
                if lang:
                    base_parsed = self._code_parser.parse_file(content, lang)

            if student_parsed is not None and base_parsed is not None:
                symbol_level["files"][fpath] = self._compute_symbol_level_delta(
                    student_parsed, base_parsed
                )

        return {
            "repo_level": repo_level,
            "file_level": file_level,
            "symbol_level": symbol_level,
        }

    def _get_file_list(self, repo_path: str) -> list[str]:
        if self._file_discoverer:
            files = self._file_discoverer.discover(repo_path)
            return [f.path for f in files]
        results = []
        root = Path(repo_path)
        if not root.exists():
            return []
        for filepath in root.rglob("*"):
            if filepath.is_file() and not filepath.is_symlink():
                rel = filepath.relative_to(root)
                parts = rel.parts
                skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}
                if not any(p in skip_dirs for p in parts):
                    results.append(str(rel.as_posix()))
        return sorted(results)

    def _file_hash(self, filepath: str) -> str:
        try:
            content = Path(filepath).read_bytes()
            return hashlib.sha256(content).hexdigest()
        except (OSError, IOError):
            return ""

    def _read_file(self, filepath: str) -> str:
        try:
            return Path(filepath).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return Path(filepath).read_text(encoding="latin-1")
            except (OSError, IOError):
                return ""
        except (OSError, IOError):
            return ""

    def _detect_language(self, filepath: str) -> str | None:
        ext = os.path.splitext(filepath)[1].lower()
        ext_map = {
            ".py": "Python", ".pyw": "Python",
            ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
            ".ts": "TypeScript", ".tsx": "TypeScript",
            ".java": "Java",
            ".c": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
            ".h": "C", ".hpp": "C++",
            ".rb": "Ruby",
            ".go": "Go",
            ".rs": "Rust",
        }
        return ext_map.get(ext)

    def _detect_renames(
        self,
        removed_files: list[str],
        added_files: list[str],
        student_path: str,
        base_path: str,
    ) -> list[tuple[str, str]]:
        renames = []
        if not removed_files or not added_files:
            return renames

        removed_hashes: dict[str, str] = {}
        for fpath in removed_files:
            h = self._file_hash(os.path.join(base_path, fpath))
            if h:
                removed_hashes[h] = fpath

        matched_added = set()
        for fpath in added_files:
            h = self._file_hash(os.path.join(student_path, fpath))
            if h and h in removed_hashes and fpath not in matched_added:
                renames.append((removed_hashes[h], fpath))
                matched_added.add(fpath)

        return renames

    def _compute_file_level_delta(self, student_content: str, base_content: str) -> dict:
        student_lines = student_content.splitlines(keepends=True)
        base_lines = base_content.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            base_lines, student_lines,
            fromfile="base", tofile="student",
            n=3,
        ))

        added_sections = []
        removed_sections = []
        modified_regions = []

        for line in diff:
            if line.startswith("@@"):
                parts = line.split(" ")
                if len(parts) >= 4:
                    old_info = parts[1]
                    new_info = parts[2]
                    try:
                        old_start = int(old_info.split(",")[0])
                        new_start = int(new_info.split(",")[0])
                        modified_regions.append({
                            "old_start": old_start,
                            "new_start": new_start,
                        })
                    except (ValueError, IndexError):
                        pass

        return {
            "added_sections": added_sections,
            "removed_sections": removed_sections,
            "modified_regions": modified_regions,
            "line_diff": "\n".join(diff) if diff else None,
        }

    def _compute_symbol_level_delta(self, student_parsed: dict, base_parsed: dict) -> dict:
        def make_entry(name: str, sym_type: str, parsed_item: dict | None = None) -> dict:
            entry = {"name": name, "type": sym_type, "signature_hash": None}
            if parsed_item:
                body_str = str(parsed_item)
                normalized = " ".join(body_str.split())
                entry["signature_hash"] = hashlib.sha256(
                    normalized.encode("utf-8")
                ).hexdigest()[:16]
            return entry

        def index_symbols(parsed: dict) -> dict[str, list[dict]]:
            indexed: dict[str, list[dict]] = {}
            for func in parsed.get("functions", []):
                indexed.setdefault(func.get("name", "?"), []).append(func)
            for cls in parsed.get("classes", []):
                indexed.setdefault(cls.get("name", "?"), []).append(cls)
            return indexed

        student_index = index_symbols(student_parsed)
        base_index = index_symbols(base_parsed)

        student_names = set(student_index.keys())
        base_names = set(base_index.keys())

        added_names = student_names - base_names
        removed_names = base_names - student_names
        common_names = student_names & base_names

        added = [make_entry(name, "symbol") for name in sorted(added_names)]
        removed = [make_entry(name, "symbol") for name in sorted(removed_names)]

        modified = []
        unchanged = []
        for name in sorted(common_names):
            s_items = student_index[name]
            b_items = base_index[name]
            s_sig = make_entry(name, "symbol", s_items[0] if s_items else None)["signature_hash"]
            b_sig = make_entry(name, "symbol", b_items[0] if b_items else None)["signature_hash"]
            entry = {"name": name, "type": "symbol", "signature_hash": s_sig}
            if s_sig != b_sig:
                modified.append(entry)
            else:
                unchanged.append(entry)

        return {
            "added": added,
            "modified": modified,
            "removed": removed,
            "unchanged": unchanged,
        }
