"""
Recursive language and framework discovery helpers for MiSAR module directories.

Since: V2026-06-11
Author: Alex Javadi <alex.javadimoghadam@brunel.ac.uk>
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

IGNORED_DIRECTORIES = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    "venv", ".venv", "env", ".env", "node_modules",
    "target", "build", "dist", "out", ".gradle",
}

PYTHON_DEPENDENCY_FILES = {
    "requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "setup.cfg", "poetry.lock",
}

JAVA_BUILD_FILES = {"pom.xml", "build.gradle", "build.gradle.kts"}

LANGUAGE_BADGE_PATTERN = re.compile(r"\s+\[(?:Python|Java|Unknown|Mixed|Languages):.*\]$")


@dataclass
class LanguageScope:
    language: str
    framework: str = "UNKNOWN"
    path: str = ""
    confidence: int = 0
    evidence: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        framework_label = "" if self.framework in {"", "UNKNOWN", self.language.upper()} else f": {self.framework}"
        return f"{self.language.title()}{framework_label}"


def strip_language_badge(value: str | Path) -> str:
    text = str(value).strip()
    return LANGUAGE_BADGE_PATTERN.sub("", text).strip()


def format_module_display_path(module_dir: str | Path) -> str:
    raw_path = strip_language_badge(module_dir)
    summary = format_language_summary(detect_language_scopes(raw_path))
    return f"{raw_path} [{summary}]"


def format_language_summary(scopes: Iterable[LanguageScope]) -> str:
    scopes = list(scopes)
    if not scopes:
        return "Unknown"

    grouped: dict[str, set[str]] = {}
    for scope in scopes:
        language = scope.language.title()
        framework = scope.framework if scope.framework and scope.framework != "UNKNOWN" else ""
        grouped.setdefault(language, set())
        if framework:
            grouped[language].add(framework)

    labels: list[str] = []
    for language in sorted(grouped):
        frameworks = sorted(grouped[language])
        if frameworks:
            labels.append(f"{language}: {', '.join(frameworks)}")
        else:
            labels.append(language)
    return "; ".join(labels)


def detect_language_scopes(module_dir: str | Path) -> list[LanguageScope]:
    module_path = Path(strip_language_badge(module_dir)).expanduser()
    if not module_path.is_dir():
        return []

    python_scope = detect_python_scope(module_path)
    java_scope = detect_java_scope(module_path)

    scopes = [scope for scope in [python_scope, java_scope] if scope is not None]
    scopes.sort(key=lambda item: (item.language, item.path))
    return scopes


def has_language(scopes: Iterable[LanguageScope], language: str) -> bool:
    language = language.lower()
    return any(scope.language.lower() == language for scope in scopes)


def primary_framework(scopes: Iterable[LanguageScope], language: str, default: str = "UNKNOWN") -> str:
    language = language.lower()
    matching_scopes = [scope for scope in scopes if scope.language.lower() == language]
    if not matching_scopes:
        return default
    matching_scopes.sort(key=lambda item: item.confidence, reverse=True)
    return matching_scopes[0].framework or default


def iter_source_files(module_path: Path):
    for root, dirs, files in os.walk(module_path, topdown=True):
        dirs[:] = [directory for directory in dirs if directory not in IGNORED_DIRECTORIES]
        root_path = Path(root)
        for filename in files:
            yield root_path / filename


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")
    except Exception:
        return ""


def detect_python_scope(module_path: Path) -> LanguageScope | None:
    evidence: list[str] = []
    score = 0
    frameworks: dict[str, int] = {}
    best_path = module_path

    for file_path in iter_source_files(module_path):
        filename = file_path.name
        relative_text = str(file_path.relative_to(module_path))
        lower_relative = relative_text.lower()

        if filename in PYTHON_DEPENDENCY_FILES:
            score += 20
            evidence.append(relative_text)
            best_path = best_scope_path(best_path, file_path.parent, module_path)
            dependency_text = read_text(file_path).lower()
            add_framework_evidence(frameworks, dependency_text, "FLASK", ["flask"])
            add_framework_evidence(frameworks, dependency_text, "FASTAPI", ["fastapi", "uvicorn"])
            add_framework_evidence(frameworks, dependency_text, "DJANGO", ["django", "djangorestframework"])

        if filename.endswith(".py"):
            score += 5
            if filename in {"app.py", "main.py", "manage.py", "settings.py", "urls.py", "asgi.py", "wsgi.py"}:
                score += 10
                evidence.append(relative_text)
            best_path = best_scope_path(best_path, file_path.parent, module_path)
            source_text = read_text(file_path)
            lower_source = source_text.lower()

            if filename == "manage.py" or "django.core.management" in lower_source:
                frameworks["DJANGO"] = frameworks.get("DJANGO", 0) + 35
            if filename in {"settings.py", "urls.py", "asgi.py", "wsgi.py"} and "django" in lower_source:
                frameworks["DJANGO"] = frameworks.get("DJANGO", 0) + 25
            if "from flask import flask" in lower_source or "flask(__name__)" in lower_source or "@app.route" in lower_source:
                frameworks["FLASK"] = frameworks.get("FLASK", 0) + 35
            if "from fastapi import" in lower_source or "fastapi()" in lower_source or "apirouter" in lower_source:
                frameworks["FASTAPI"] = frameworks.get("FASTAPI", 0) + 35
            if "rest_framework" in lower_source or "viewsets.modelviewset" in lower_source or "defaultrouter" in lower_source:
                frameworks["DJANGO"] = frameworks.get("DJANGO", 0) + 30

            import_frameworks = detect_python_import_frameworks(source_text)
            for framework in import_frameworks:
                frameworks[framework] = frameworks.get(framework, 0) + 20

    if score <= 0 and not frameworks:
        return None

    framework = highest_framework(frameworks, default="PYTHON")
    confidence = min(100, score + max(frameworks.values(), default=0))
    if framework != "PYTHON":
        evidence.append(framework)
    return LanguageScope(
        language="python",
        framework=framework,
        path=str(best_path),
        confidence=confidence,
        evidence=deduplicate(evidence),
    )


def detect_java_scope(module_path: Path) -> LanguageScope | None:
    evidence: list[str] = []
    score = 0
    framework = "JAVA"
    best_path = module_path

    for file_path in iter_source_files(module_path):
        filename = file_path.name
        relative_text = str(file_path.relative_to(module_path))
        lower_name = filename.lower()

        if filename in JAVA_BUILD_FILES or lower_name in JAVA_BUILD_FILES:
            score += 30
            evidence.append(relative_text)
            best_path = best_scope_path(best_path, file_path.parent, module_path)
            build_text = read_text(file_path).lower()
            if "spring-boot" in build_text or "springframework" in build_text:
                framework = "SPRING"
                score += 30

        if filename.endswith(".java"):
            score += 8
            best_path = best_scope_path(best_path, file_path.parent, module_path)
            source_text = read_text(file_path)
            if "@SpringBootApplication" in source_text or "org.springframework" in source_text:
                framework = "SPRING"
                score += 25
                evidence.append(relative_text)
            elif len(evidence) < 5:
                evidence.append(relative_text)

    if score <= 0:
        return None

    return LanguageScope(
        language="java",
        framework=framework,
        path=str(best_path),
        confidence=min(100, score),
        evidence=deduplicate(evidence),
    )


def detect_python_import_frameworks(source_text: str) -> set[str]:
    frameworks: set[str] = set()
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return frameworks

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                if name == "flask":
                    frameworks.add("FLASK")
                if name == "fastapi":
                    frameworks.add("FASTAPI")
                if name == "django" or name == "rest_framework":
                    frameworks.add("DJANGO")
        elif isinstance(node, ast.ImportFrom):
            name = (node.module or "").split(".")[0]
            if name == "flask":
                frameworks.add("FLASK")
            if name == "fastapi":
                frameworks.add("FASTAPI")
            if name == "django" or name == "rest_framework":
                frameworks.add("DJANGO")
    return frameworks


def add_framework_evidence(frameworks: dict[str, int], text: str, framework: str, terms: list[str]) -> None:
    if any(term in text for term in terms):
        frameworks[framework] = frameworks.get(framework, 0) + 25


def highest_framework(frameworks: dict[str, int], default: str = "UNKNOWN") -> str:
    if not frameworks:
        return default
    return sorted(frameworks.items(), key=lambda item: item[1], reverse=True)[0][0]


def best_scope_path(current: Path, candidate: Path, module_path: Path) -> Path:
    try:
        current_distance = len(current.relative_to(module_path).parts)
    except ValueError:
        current_distance = 999
    try:
        candidate_distance = len(candidate.relative_to(module_path).parts)
    except ValueError:
        candidate_distance = 999
    return candidate if candidate_distance < current_distance else current


def deduplicate(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
