import ast
import re
from typing import Optional

from models.ingestion_models import (
    ClassInfo,
    DocstringInfo,
    FunctionInfo,
    ImportInfo,
)


LANGUAGE_PATTERNS: dict[str, dict[str, re.Pattern]] = {
    "JavaScript": {
        "function": re.compile(
            r"(?:async\s+)?function\s+\*?\s*(\w+)\s*\([^)]*\)\s*\{",
            re.MULTILINE,
        ),
        "arrow_function": re.compile(
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>",
            re.MULTILINE,
        ),
        "class": re.compile(
            r"class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{",
            re.MULTILINE,
        ),
        "import": re.compile(
            r'(?:import\s+[\s\S]*?from\s+[\'"](\S+?)[\'"]|require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\))',
            re.MULTILINE,
        ),
    },
    "TypeScript": {
        "function": re.compile(
            r"(?:async\s+)?function\s+\*?\s*(\w+)\s*\([^)]*\)\s*\{",
            re.MULTILINE,
        ),
        "arrow_function": re.compile(
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>",
            re.MULTILINE,
        ),
        "class": re.compile(
            r"class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{",
            re.MULTILINE,
        ),
        "interface": re.compile(
            r"interface\s+(\w+)\s*\{",
            re.MULTILINE,
        ),
        "import": re.compile(
            r'import\s+[\s\S]*?from\s+[\'"](\S+?)[\'"]',
            re.MULTILINE,
        ),
    },
    "Java": {
        "class": re.compile(
            r"(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)",
            re.MULTILINE,
        ),
        "method": re.compile(
            r"(?:public|private|protected)?\s*(?:static)?\s*(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+\w+)?\s*\{",
            re.MULTILINE,
        ),
        "import": re.compile(
            r"import\s+(?:static\s+)?([\w.]+);",
            re.MULTILINE,
        ),
    },
    "C": {
        "function": re.compile(
            r"(?:static\s+)?(?:\w+(?:\s*\*)?)\s+(\w+)\s*\([^)]*\)\s*\{",
            re.MULTILINE,
        ),
        "struct": re.compile(
            r"struct\s+(\w+)\s*\{",
            re.MULTILINE,
        ),
        "include": re.compile(
            r'#include\s+[<"]([^>"]+)[>"]',
            re.MULTILINE,
        ),
    },
    "C++": {
        "function": re.compile(
            r"(?:virtual\s+)?(?:\w+(?:\s*\*)?(?:\s*&)?)\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{",
            re.MULTILINE,
        ),
        "class": re.compile(
            r"class\s+(\w+)(?:\s*:\s*(?:public|private|protected)\s+\w+)?\s*\{",
            re.MULTILINE,
        ),
        "include": re.compile(
            r'#include\s+[<"]([^>"]+)[>"]',
            re.MULTILINE,
        ),
    },
    "Ruby": {
        "method": re.compile(
            r"def\s+(self\.)?(\w+[\?!]?)",
            re.MULTILINE,
        ),
        "class": re.compile(
            r"class\s+(\w+)",
            re.MULTILINE,
        ),
        "module": re.compile(
            r"module\s+(\w+)",
            re.MULTILINE,
        ),
        "require": re.compile(
            r'require\s+[\'"](\S+?)[\'"]',
            re.MULTILINE,
        ),
    },
    "Go": {
        "function": re.compile(
            r"func\s+(?:\([^)]*\)\s+)?(\w+)\s*\([^)]*\)\s*(?:\w+\s*)?\{",
            re.MULTILINE,
        ),
        "struct": re.compile(
            r"type\s+(\w+)\s+struct\s*\{",
            re.MULTILINE,
        ),
        "import": re.compile(
            r'import\s+[\'"](\S+?)[\'"]',
            re.MULTILINE,
        ),
    },
    "Rust": {
        "function": re.compile(
            r"(?:pub\s+)?(?:unsafe\s+)?fn\s+(\w+)\s*<[^>]*>?\s*\([^)]*\)\s*(?:->\s*\w+)?\s*\{",
            re.MULTILINE,
        ),
        "struct": re.compile(
            r"(?:pub\s+)?struct\s+(\w+)",
            re.MULTILINE,
        ),
        "impl": re.compile(
            r"(?:pub\s+)?impl\s+(\w+)",
            re.MULTILINE,
        ),
        "use": re.compile(
            r"use\s+([\w:]+);",
            re.MULTILINE,
        ),
    },
}


class PythonParser:
    def parse(self, source: str) -> dict:
        result = {
            "functions": [],
            "classes": [],
            "imports": [],
            "docstrings": [],
            "errors": [],
        }

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            result["errors"].append(f"SyntaxError at line {e.lineno}: {e.msg}")
            return result

        module_doc = ast.get_docstring(tree)
        if module_doc:
            result["docstrings"].append({
                "text": module_doc,
                "lineno": 1,
                "type": "docstring",
            })

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result["functions"].append(self._extract_function(node))
            elif isinstance(node, ast.AsyncFunctionDef):
                result["functions"].append(self._extract_function(node))
            elif isinstance(node, ast.ClassDef):
                result["classes"].append(self._extract_class(node))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append({
                        "module": alias.name,
                        "names": [],
                        "alias": alias.asname,
                    })
            elif isinstance(node, ast.ImportFrom):
                result["imports"].append({
                    "module": node.module or "",
                    "names": [alias.name for alias in node.names],
                    "alias": None,
                })

        return result

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
        return {
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno or node.lineno,
            "complexity": self._compute_complexity(node),
            "docstring": ast.get_docstring(node),
        }

    def _extract_class(self, node: ast.ClassDef) -> dict:
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(item))

        return {
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno or node.lineno,
            "docstring": ast.get_docstring(node),
            "methods": methods,
        }

    def _compute_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For,
                                   ast.ExceptHandler, ast.Assert)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        return complexity


class RegexParser:
    def __init__(self):
        self.patterns = LANGUAGE_PATTERNS

    def parse(self, source: str, language: str) -> dict:
        result = {
            "functions": [],
            "classes": [],
            "imports": [],
            "docstrings": [],
            "errors": [],
        }

        if language not in self.patterns:
            result["errors"].append(f"No parsing patterns defined for language: {language}")
            return result

        patterns = self.patterns[language]

        for key in ("function", "method", "arrow_function"):
            pattern = patterns.get(key)
            if pattern:
                for match in pattern.finditer(source):
                    name = match.group(1)
                    lineno = source[:match.start()].count("\n") + 1
                    result["functions"].append({
                        "name": name,
                        "lineno": lineno,
                        "end_lineno": lineno,
                        "complexity": 0,
                        "docstring": None,
                    })

        for key in ("class", "struct", "interface", "impl", "module"):
            pattern = patterns.get(key)
            if pattern:
                for match in pattern.finditer(source):
                    name = match.group(1)
                    lineno = source[:match.start()].count("\n") + 1
                    result["classes"].append({
                        "name": name,
                        "lineno": lineno,
                        "end_lineno": lineno,
                        "docstring": None,
                        "methods": [],
                    })

        for key in ("import", "include", "require", "use"):
            pattern = patterns.get(key)
            if pattern:
                for match in pattern.finditer(source):
                    module = match.group(1) or match.group(2) or ""
                    result["imports"].append({
                        "module": module,
                        "names": [],
                        "alias": None,
                    })

        return result


class CodeParser:
    def __init__(self):
        self._python_parser = PythonParser()
        self._regex_parser = RegexParser()

    def parse_file(self, source: str, language: str) -> dict:
        if language == "Python":
            return self._python_parser.parse(source)
        else:
            return self._regex_parser.parse(source, language)

    def get_supported_languages(self) -> list[str]:
        return ["Python"] + sorted(self._regex_parser.patterns.keys())
