"""
Python extension parser for MiSAR: detects Flask, FastAPI and Django services, extracts dependencies, configuration, AST elements, routes and call relationships into the extended PSM metamodel.

Since: V2026-05-31
Author: Alex Javadi <alex.javadimoghadam@brunel.ac.uk>
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

PYTHON_DEPENDENCY_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
)

PYTHON_CONFIG_FILES = (
    ".env",
    ".flaskenv",
    "config.py",
    "settings.py",
    "local_settings.py",
    "application.yml",
    "application.yaml",
    "config.yml",
    "config.yaml",
)

HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
FASTAPI_DECORATORS = {"get", "post", "put", "patch", "delete", "options", "head", "api_route"}
FLASK_ROUTE_DECORATORS = {"route"}
DJANGO_URL_FUNCTIONS = {"path", "re_path", "url"}
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", "dist", "build", ".mypy_cache", ".pytest_cache"}


@dataclass
class PythonDependency:
    filename: str
    name: str
    version: str = ""
    scope: str = "COMPILE"


@dataclass
class PythonParameter:
    name: str
    type_hint: str = "NOT_AVAILABLE"
    default_value: str = "NOT_AVAILABLE"
    order: int = 1


@dataclass
class PythonDecoratorData:
    name: str
    route_path: str = ""
    http_method: str = ""
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass
class PythonCallData:
    target_name: str
    call_type: str = "FUNCTION_CALL"
    endpoint_url: str = ""


@dataclass
class PythonFunctionData:
    name: str
    is_async: bool = False
    line_number: int = 0
    return_type: str = "NOT_AVAILABLE"
    route_path: str = ""
    http_method: str = ""
    parameters: list[PythonParameter] = field(default_factory=list)
    decorators: list[PythonDecoratorData] = field(default_factory=list)
    calls: list[PythonCallData] = field(default_factory=list)


@dataclass
class PythonClassData:
    name: str
    line_number: int = 0
    bases: list[str] = field(default_factory=list)
    decorators: list[PythonDecoratorData] = field(default_factory=list)
    methods: list[PythonFunctionData] = field(default_factory=list)


@dataclass
class PythonImportData:
    module_name: str
    imported_name: str = ""
    alias: str = ""


@dataclass
class PythonModuleData:
    filename: str
    module_name: str
    package_name: str = ""
    framework: str = "PYTHON"
    imports: list[PythonImportData] = field(default_factory=list)
    functions: list[PythonFunctionData] = field(default_factory=list)
    classes: list[PythonClassData] = field(default_factory=list)


@dataclass
class PythonProjectDetection:
    language: str
    framework: str
    score: int
    evidence: list[str] = field(default_factory=list)

@dataclass
class DjangoMetadata:
    module_prefixes: dict[str, list[str]] = field(default_factory=dict)
    viewset_types: dict[str, str] = field(default_factory=dict)
    view_methods: dict[str, set[str]] = field(default_factory=dict)
    viewset_actions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@dataclass
class PythonAnalysisContext:
    module_name: str
    module_dir: str
    environment: dict[str, str] = field(default_factory=dict)
    service_ports: dict[str, str] = field(default_factory=dict)
    django: DjangoMetadata = field(default_factory=DjangoMetadata)



def normalise_path(path: str | Path) -> str:
    return str(Path(path)).replace("\\", "/")


def fetch_artifacts(filename_part: str, filepath_part: str, app_root_dir: str | Path) -> list[str]:
    artifact_list: list[str] = []
    for root, dirs, files in os.walk(app_root_dir, topdown=True):
        dirs[:] = [directory for directory in dirs if directory not in IGNORED_DIRECTORIES]
        for file in files:
            if filename_part in file:
                root_path = normalise_path(root)
                if filepath_part in root_path:
                    artifact_list.append(root_path + "/" + file)
    return artifact_list


def read_text_file(file_path: str | Path) -> str:
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Path(file_path).read_text(encoding="latin-1")
    except Exception:
        return ""


def parse_python_source(source: str, file_path: str | Path = "", parser_context: str = "python") -> ast.AST | None:
    """Parse Python source and emit consistent MiSAR parser diagnostics on failure."""
    filename = str(file_path or "<unknown>")
    try:
        return ast.parse(source, filename=filename)
    except SyntaxError as error:
        line_number = getattr(error, "lineno", 0) or 0
        offset = getattr(error, "offset", 0) or 0
        message = getattr(error, "msg", str(error))
        print(
            "python_parse_error = {}:{}:{} {} [{}]".format(
                filename, line_number, offset, message, parser_context
            )
        )
        return None
    except ValueError as error:
        print("python_parse_error = {} {} [{}]".format(filename, str(error), parser_context))
        return None


def constant_to_string(node: ast.AST | None, none_value: str = "") -> str:
    """Return a stable string representation for ast.Constant values."""
    if not isinstance(node, ast.Constant):
        return ""
    return none_value if node.value is None else str(node.value)


def is_string_literal(node: ast.AST | None) -> bool:
    # Python 3.14 removed the legacy string literal AST node, so string checks must use ast.Constant.
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def string_literal_to_string(node: ast.AST | None) -> str:
    if is_string_literal(node):
        return str(node.value)
    return ""


def is_runtime_ast_type(node: ast.AST | None, type_name: str) -> bool:
    runtime_type = getattr(ast, type_name, None)
    return runtime_type is not None and isinstance(node, runtime_type)


def evaluate_interpolated_string_values(values: Iterable[ast.AST], constants: dict[str, str], context: PythonAnalysisContext) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, ast.Constant):
            parts.append(constant_to_string(value))
        elif isinstance(value, ast.FormattedValue) or is_runtime_ast_type(value, "Interpolation"):
            expression_node = getattr(value, "value", None)
            expression = expression_to_string(expression_node)
            if expression:
                parts.append(constants.get(expression, "{" + expression + "}"))
        elif is_runtime_ast_type(value, "TemplateStr"):
            # Python 3.14 added template-string AST nodes; keep this guarded for Python 3.11-3.13.
            parts.append(evaluate_interpolated_string_values(getattr(value, "values", []), constants, context))
        else:
            parts.append(expression_to_string(value))
    return "".join(parts)


def is_python_dependency_file(file_path: str | Path) -> bool:
    return Path(file_path).name in PYTHON_DEPENDENCY_FILES


def find_python_dependency_files(module_dir: str | Path) -> list[str]:
    module_path = Path(module_dir)
    dependency_files: list[str] = []
    for candidate in PYTHON_DEPENDENCY_FILES:
        file_path = module_path / candidate
        if file_path.is_file():
            dependency_files.append(str(file_path))
    return dependency_files


def find_python_files(module_dir: str | Path) -> list[str]:
    python_files: list[str] = []
    module_path = Path(module_dir)
    if not module_path.is_dir():
        return python_files
    for root, dirs, files in os.walk(module_path, topdown=True):
        dirs[:] = [directory for directory in dirs if directory not in IGNORED_DIRECTORIES]
        root_path = normalise_path(root)
        if "/tests" in root_path or "/test" in root_path:
            continue
        for file in files:
            if file.endswith(".py"):
                python_files.append(str(Path(root) / file))
    return python_files


def extract_dependency_name(requirement: str) -> tuple[str, str]:
    clean_requirement = requirement.strip()
    clean_requirement = clean_requirement.split(";", 1)[0].strip()
    clean_requirement = re.sub(r"\[[^\]]+\]", "", clean_requirement)
    match = re.match(r"^([A-Za-z0-9_.-]+)\s*([<>=!~^].+)?$", clean_requirement)
    if not match:
        return clean_requirement.lower().replace("_", "-"), ""
    name = match.group(1).lower().replace("_", "-")
    version = (match.group(2) or "").strip()
    return name, version


def append_dependency(dependencies: list[PythonDependency], filename: str, package_spec: str, scope: str = "COMPILE") -> None:
    package_spec = package_spec.strip().strip('"').strip("'")
    if not package_spec or package_spec.startswith(("#", "-r", "--", "git+", "http://", "https://", "-e")):
        return
    name, version = extract_dependency_name(package_spec)
    if not name or name.lower() == "python":
        return
    if any(dependency.name == name and dependency.filename == filename for dependency in dependencies):
        return
    dependencies.append(PythonDependency(filename=filename, name=name, version=version, scope=scope))


def parse_requirements_file(file_path: str | Path) -> list[PythonDependency]:
    dependencies: list[PythonDependency] = []
    for line in read_text_file(file_path).splitlines():
        line = line.strip()
        if " #" in line:
            line = line.split(" #", 1)[0].strip()
        append_dependency(dependencies, str(file_path), line)
    return dependencies


def parse_pyproject_file(file_path: str | Path) -> list[PythonDependency]:
    dependencies: list[PythonDependency] = []
    if tomllib is None:
        return dependencies
    try:
        data = tomllib.loads(read_text_file(file_path))
    except Exception:
        return dependencies
    for package_spec in data.get("project", {}).get("dependencies", []) or []:
        append_dependency(dependencies, str(file_path), str(package_spec))
    optional_dependencies = data.get("project", {}).get("optional-dependencies", {}) or {}
    for group_name, group_dependencies in optional_dependencies.items():
        for package_spec in group_dependencies or []:
            append_dependency(dependencies, str(file_path), str(package_spec), str(group_name).upper())
    poetry_dependencies = data.get("tool", {}).get("poetry", {}).get("dependencies", {}) or {}
    for package_name, package_version in poetry_dependencies.items():
        if package_name.lower() == "python":
            continue
        if isinstance(package_version, str):
            append_dependency(dependencies, str(file_path), f"{package_name}{package_version}" if package_version.startswith(("<", ">", "=", "!", "~", "^")) else package_name)
        else:
            append_dependency(dependencies, str(file_path), package_name)
    return dependencies


def parse_pipfile(file_path: str | Path) -> list[PythonDependency]:
    dependencies: list[PythonDependency] = []
    if tomllib is None:
        return dependencies
    try:
        data = tomllib.loads(read_text_file(file_path))
    except Exception:
        return dependencies
    for section_name in ("packages", "dev-packages"):
        for package_name, package_version in (data.get(section_name, {}) or {}).items():
            scope = "TEST" if section_name == "dev-packages" else "COMPILE"
            if isinstance(package_version, str) and package_version != "*":
                append_dependency(dependencies, str(file_path), f"{package_name}{package_version}", scope)
            else:
                append_dependency(dependencies, str(file_path), package_name, scope)
    return dependencies


def parse_setup_cfg(file_path: str | Path) -> list[PythonDependency]:
    dependencies: list[PythonDependency] = []
    in_install_requires = False
    for line in read_text_file(file_path).splitlines():
        if line.strip().startswith("install_requires"):
            in_install_requires = True
            possible_value = line.partition("=")[2].strip()
            if possible_value:
                append_dependency(dependencies, str(file_path), possible_value)
            continue
        if in_install_requires:
            if line.startswith(" ") or line.startswith("\t"):
                append_dependency(dependencies, str(file_path), line.strip())
            elif line.strip().startswith("["):
                in_install_requires = False
    return dependencies


def parse_setup_py(file_path: str | Path) -> list[PythonDependency]:
    dependencies: list[PythonDependency] = []
    source = read_text_file(file_path)
    tree = parse_python_source(source, file_path, "setup.py dependency analysis")
    if tree is None:
        return dependencies
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and get_callable_name(node.func).endswith("setup"):
            for keyword in node.keywords:
                if keyword.arg == "install_requires" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                    for element in keyword.value.elts:
                        value = literal_to_string(element)
                        if value:
                            append_dependency(dependencies, str(file_path), value)
    return dependencies


def get_python_library_list(module_dir: str | Path, module_build_file: str = "", app_root_dir: str | Path = "") -> list[dict[str, str]]:
    dependency_files: list[str] = []
    if module_build_file and is_python_dependency_file(module_build_file):
        dependency_files.append(str(module_build_file))
    dependency_files.extend(file_path for file_path in find_python_dependency_files(module_dir) if file_path not in dependency_files)
    dependencies: list[PythonDependency] = []
    for dependency_file in dependency_files:
        name = Path(dependency_file).name
        if name == "requirements.txt":
            dependencies.extend(parse_requirements_file(dependency_file))
        elif name == "pyproject.toml":
            dependencies.extend(parse_pyproject_file(dependency_file))
        elif name == "Pipfile":
            dependencies.extend(parse_pipfile(dependency_file))
        elif name == "setup.cfg":
            dependencies.extend(parse_setup_cfg(dependency_file))
        elif name == "setup.py":
            dependencies.extend(parse_setup_py(dependency_file))
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for dependency in dependencies:
        key = dependency.name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "filename": dependency.filename,
            "groupId": "pypi",
            "artifactId": dependency.name,
            "scope": dependency.scope,
            "version": dependency.version,
        })
    return result


def get_dependency_names(libraries: Iterable[dict[str, str]]) -> set[str]:
    return {library.get("artifactId", "").lower().replace("_", "-") for library in libraries}


def build_python_analysis_context(module_name: str, module_dir: str | Path, application_containers: dict[str, Any], python_files: list[str]) -> PythonAnalysisContext:
    module_dir_str = str(module_dir)
    context = PythonAnalysisContext(
        module_name=module_name,
        module_dir=module_dir_str,
        environment=collect_docker_environment_for_module(module_name, module_dir_str, application_containers),
        service_ports=collect_service_port_map(application_containers),
    )
    context.django = build_django_metadata(module_dir_str, python_files)
    return context


def collect_service_port_map(application_containers: dict[str, Any]) -> dict[str, str]:
    service_ports: dict[str, str] = {}
    for container_name, container_data in application_containers.items():
        for port_value in container_data.get("ports", []) or []:
            for port in re.findall(r"\d+", str(port_value)):
                service_ports.setdefault(port, container_name)
    return service_ports


def collect_docker_environment_for_module(module_name: str, module_dir: str, application_containers: dict[str, Any]) -> dict[str, str]:
    environment: dict[str, str] = {}
    module_path = Path(module_dir).resolve()
    for container_name, container_data in application_containers.items():
        if not docker_container_matches_module(container_name, container_data, module_name, module_path):
            continue
        compose_file = container_data.get("filename", "")
        if not compose_file:
            continue
        environment.update(read_compose_service_environment(compose_file, container_name))
    return environment


def docker_container_matches_module(container_name: str, container_data: dict[str, Any], module_name: str, module_path: Path) -> bool:
    if container_name == module_name:
        return True
    build_context = str(container_data.get("build", "") or "").strip()
    if not build_context:
        return False
    compose_file = str(container_data.get("filename", "") or "")
    compose_dir = Path(compose_file).parent if compose_file else module_path.parent
    candidate = (compose_dir / build_context).resolve()
    return candidate == module_path or candidate.name == module_path.name


def read_compose_service_environment(compose_file: str | Path, container_name: str) -> dict[str, str]:
    environment: dict[str, str] = {}
    if yaml is None:
        return environment
    try:
        compose_data = yaml.safe_load(read_text_file(compose_file)) or {}
    except Exception:
        return environment
    service_data = (compose_data.get("services", {}) or {}).get(container_name, {}) or {}
    raw_environment = service_data.get("environment", {}) or {}
    if isinstance(raw_environment, dict):
        for key, value in raw_environment.items():
            environment[str(key)] = "" if value is None else str(value)
    elif isinstance(raw_environment, list):
        for item in raw_environment:
            key, separator, value = str(item).partition("=")
            if separator:
                environment[key] = value
    return environment


def build_django_metadata(module_dir: str | Path, python_files: list[str]) -> DjangoMetadata:
    metadata = DjangoMetadata()
    url_files: list[tuple[str, ast.AST]] = []
    for python_file in python_files:
        source = read_text_file(python_file)
        tree = parse_python_source(source, python_file, "django metadata analysis")
        if tree is None:
            continue
        module_path = path_to_module_name(python_file, module_dir)
        collect_django_view_metadata(tree, metadata)
        if Path(python_file).name == "urls.py":
            url_files.append((module_path, tree))
    for module_path, tree in url_files:
        collect_django_include_prefixes(tree, module_path, metadata)
    return metadata


def collect_django_view_metadata(tree: ast.AST, metadata: DjangoMetadata) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = {expression_to_string(base).lower() for base in node.bases}
        if any(base.endswith("modelviewset") for base in base_names):
            metadata.viewset_types[node.name] = "MODELVIEWSET"
        elif any(base.endswith("viewset") for base in base_names):
            metadata.viewset_types[node.name] = "VIEWSET"
        elif any(base.endswith(("apiview", "view")) for base in base_names):
            metadata.viewset_types[node.name] = "VIEW"
        methods = {child.name.upper() for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.upper() in HTTP_METHODS}
        if methods:
            metadata.view_methods[node.name] = methods
        actions = collect_django_viewset_actions(node)
        if actions:
            metadata.viewset_actions[node.name] = actions


def collect_django_viewset_actions(class_node: ast.ClassDef) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for child in class_node.body:
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in child.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if get_callable_name(decorator.func).split(".")[-1] != "action":
                continue
            detail = False
            methods = {"GET"}
            url_path = child.name.replace("_", "-")
            for keyword in decorator.keywords:
                if keyword.arg == "detail":
                    detail_value = evaluate_python_expression(keyword.value, {}, PythonAnalysisContext(module_name="", module_dir=""))
                    detail = detail_value == "True"
                elif keyword.arg == "methods":
                    extracted_methods = extract_http_methods(keyword.value)
                    if extracted_methods:
                        methods = set(extracted_methods)
                elif keyword.arg in {"url_path", "url_name"}:
                    value = literal_to_string(keyword.value)
                    if value:
                        url_path = value
            actions.append({"name": child.name, "detail": detail, "methods": methods, "url_path": url_path})
    return actions


def collect_django_include_prefixes(tree: ast.AST, module_path: str, metadata: DjangoMetadata) -> None:
    if module_path not in metadata.module_prefixes:
        metadata.module_prefixes[module_path] = [""]
    for call_node in ast.walk(tree):
        if not isinstance(call_node, ast.Call):
            continue
        if get_callable_name(call_node.func).split(".")[-1] not in DJANGO_URL_FUNCTIONS:
            continue
        if len(call_node.args) < 2:
            continue
        route_path = literal_to_string(call_node.args[0])
        include_target = extract_django_include_target(call_node.args[1])
        if include_target:
            for parent_prefix in metadata.module_prefixes.get(module_path, [""]):
                combined_prefix = combine_url_paths(parent_prefix, route_path)
                metadata.module_prefixes.setdefault(include_target, [])
                if combined_prefix not in metadata.module_prefixes[include_target]:
                    metadata.module_prefixes[include_target].append(combined_prefix)


def extract_django_include_target(node: ast.AST) -> str:
    if not isinstance(node, ast.Call):
        return ""
    if get_callable_name(node.func).split(".")[-1] != "include" or not node.args:
        return ""
    first_arg = node.args[0]
    # Python 3.14 removed the legacy string literal AST node, so include() targets must be checked as Constant strings.
    if not is_string_literal(first_arg):
        return ""
    target = string_literal_to_string(first_arg)
    if target.endswith(".urls"):
        return target
    return ""


def path_to_module_name(file_path: str | Path, module_dir: str | Path) -> str:
    file_path_obj = Path(file_path)
    try:
        relative_file = file_path_obj.relative_to(Path(module_dir))
        return ".".join(relative_file.with_suffix("").parts)
    except ValueError:
        return file_path_obj.stem


def parse_python_file(file_path: str | Path, module_dir: str | Path, framework_hint: str = "PYTHON", context: PythonAnalysisContext | None = None) -> PythonModuleData | None:
    source = read_text_file(file_path)
    if not source.strip():
        return None
    tree = parse_python_source(source, file_path, "python module analysis")
    if tree is None:
        return None
    module_path = path_to_module_name(file_path, module_dir)
    if context is None:
        context = PythonAnalysisContext(module_name="", module_dir=str(module_dir))
    file_constants = collect_python_constants(tree, context)
    module_data = PythonModuleData(filename=str(file_path), module_name=module_path, framework=framework_hint)
    module_data.imports = extract_imports(tree)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            module_data.classes.append(extract_class(node, framework_hint, file_constants, context))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module_data.functions.append(extract_function(node, framework_hint, file_constants, context))
    if Path(file_path).name == "urls.py":
        module_data.functions.extend(extract_django_urlpatterns(tree, module_path, context.django))
    return module_data


def collect_python_constants(tree: ast.AST, context: PythonAnalysisContext) -> dict[str, str]:
    constants: dict[str, str] = dict(context.environment)
    changed = True
    while changed:
        changed = False
        for node in getattr(tree, "body", []):
            if isinstance(node, ast.Assign):
                value = evaluate_python_expression(node.value, constants, context)
                if value == "":
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and constants.get(target.id) != value:
                        constants[target.id] = value
                        changed = True
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                value = evaluate_python_expression(node.value, constants, context)
                if value and constants.get(node.target.id) != value:
                    constants[node.target.id] = value
                    changed = True
    return constants


def extract_imports(tree: ast.AST) -> list[PythonImportData]:
    imports: list[PythonImportData] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(PythonImportData(module_name=alias.name, alias=alias.asname or ""))
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                imports.append(PythonImportData(module_name=module_name, imported_name=alias.name, alias=alias.asname or ""))
    return imports


def extract_class(node: ast.ClassDef, framework_hint: str, constants: dict[str, str] | None = None, context: PythonAnalysisContext | None = None) -> PythonClassData:
    constants = constants or {}
    context = context or PythonAnalysisContext(module_name="", module_dir="")
    decorators = [extract_decorator(decorator, framework_hint) for decorator in node.decorator_list]
    methods: list[PythonFunctionData] = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_data = extract_function(child, framework_hint, constants, context)
            if is_django_http_method(function_data.name, node):
                function_data.http_method = function_data.name.upper()
            methods.append(function_data)
    return PythonClassData(
        name=node.name,
        line_number=getattr(node, "lineno", 0),
        bases=[expression_to_string(base) for base in node.bases],
        decorators=[decorator for decorator in decorators if decorator is not None],
        methods=methods,
    )


def extract_function(node: ast.FunctionDef | ast.AsyncFunctionDef, framework_hint: str, constants: dict[str, str] | None = None, context: PythonAnalysisContext | None = None) -> PythonFunctionData:
    constants = constants or {}
    context = context or PythonAnalysisContext(module_name="", module_dir="")
    decorators = [extract_decorator(decorator, framework_hint) for decorator in node.decorator_list]
    decorators = [decorator for decorator in decorators if decorator is not None]
    route_decorator = next((decorator for decorator in decorators if decorator.route_path), None)
    parameters = extract_parameters(node)
    calls = extract_calls(node, constants, context)
    return PythonFunctionData(
        name=node.name,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        line_number=getattr(node, "lineno", 0),
        return_type=expression_to_string(node.returns) if node.returns else "NOT_AVAILABLE",
        route_path=route_decorator.route_path if route_decorator else "",
        http_method=route_decorator.http_method if route_decorator else "",
        parameters=parameters,
        decorators=decorators,
        calls=calls,
    )


def extract_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[PythonParameter]:
    parameters: list[PythonParameter] = []
    positional_args = list(node.args.posonlyargs) + list(node.args.args)
    defaults = [None] * (len(positional_args) - len(node.args.defaults)) + list(node.args.defaults)
    order = 1
    for argument, default in zip(positional_args, defaults):
        if argument.arg == "self":
            continue
        parameters.append(PythonParameter(
            name=argument.arg,
            type_hint=expression_to_string(argument.annotation) if argument.annotation else "NOT_AVAILABLE",
            default_value=expression_to_string(default) if default else "NOT_AVAILABLE",
            order=order,
        ))
        order += 1
    for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        parameters.append(PythonParameter(
            name=argument.arg,
            type_hint=expression_to_string(argument.annotation) if argument.annotation else "NOT_AVAILABLE",
            default_value=expression_to_string(default) if default else "NOT_AVAILABLE",
            order=order,
        ))
        order += 1
    return parameters


def extract_decorator(node: ast.AST, framework_hint: str) -> PythonDecoratorData | None:
    decorator_name = get_callable_name(node.func) if isinstance(node, ast.Call) else expression_to_string(node)
    if not decorator_name:
        return None
    decorator_data = PythonDecoratorData(name=decorator_name)
    call_node = node if isinstance(node, ast.Call) else None
    if call_node is None:
        return decorator_data
    first_arg = literal_to_string(call_node.args[0]) if call_node.args else ""
    last_name = decorator_name.split(".")[-1]
    if framework_hint == "FASTAPI" and last_name in FASTAPI_DECORATORS:
        decorator_data.route_path = first_arg
        decorator_data.http_method = "GET" if last_name == "api_route" else last_name.upper()
    elif framework_hint == "FLASK" and last_name in FLASK_ROUTE_DECORATORS:
        decorator_data.route_path = first_arg
        decorator_data.http_method = "GET"
    elif last_name in FASTAPI_DECORATORS:
        decorator_data.route_path = first_arg
        decorator_data.http_method = "GET" if last_name == "api_route" else last_name.upper()
    elif last_name in FLASK_ROUTE_DECORATORS:
        decorator_data.route_path = first_arg
        decorator_data.http_method = "GET"
    for keyword in call_node.keywords:
        value = expression_to_string(keyword.value)
        if keyword.arg:
            decorator_data.parameters[keyword.arg] = value
        if keyword.arg == "methods":
            methods = extract_http_methods(keyword.value)
            if methods:
                decorator_data.http_method = ";".join(methods)
        elif keyword.arg == "method":
            decorator_data.http_method = value.upper().strip('"').strip("'")
    return decorator_data


def extract_http_methods(node: ast.AST) -> list[str]:
    methods: list[str] = []
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for element in node.elts:
            value = literal_to_string(element).upper().strip('"').strip("'")
            if value in HTTP_METHODS:
                methods.append(value)
    else:
        value = literal_to_string(node).upper().strip('"').strip("'")
        if value in HTTP_METHODS:
            methods.append(value)
    return methods


def extract_calls(node: ast.AST, constants: dict[str, str] | None = None, context: PythonAnalysisContext | None = None) -> list[PythonCallData]:
    constants = constants or {}
    context = context or PythonAnalysisContext(module_name="", module_dir="")
    calls: list[PythonCallData] = []
    body_nodes = getattr(node, "body", [node])
    for body_node in body_nodes:
        for child in ast.walk(body_node):
            if isinstance(child, ast.Call):
                target_name = get_callable_name(child.func)
                if not target_name:
                    continue
                endpoint_url = extract_endpoint_url_from_call(child, constants, context)
                call_type = classify_call(target_name)
                calls.append(PythonCallData(target_name=target_name, call_type=call_type, endpoint_url=endpoint_url))
    return calls


def extract_endpoint_url_from_call(call_node: ast.Call, constants: dict[str, str], context: PythonAnalysisContext) -> str:
    candidate_node: ast.AST | None = call_node.args[0] if call_node.args else None
    for keyword in call_node.keywords:
        if keyword.arg in {"url", "uri", "endpoint"}:
            candidate_node = keyword.value
            break
    if candidate_node is None:
        return ""
    endpoint_url = evaluate_python_expression(candidate_node, constants, context)
    if endpoint_url.startswith(("http://", "https://")) or "://" in endpoint_url:
        return normalise_endpoint_url(endpoint_url, context)
    return ""


def evaluate_python_expression(node: ast.AST | None, constants: dict[str, str], context: PythonAnalysisContext) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        # Python 3.14 removed the legacy literal AST classes, so Constant is the supported literal path.
        return constant_to_string(node)
    if isinstance(node, ast.Name):
        return constants.get(node.id, "{" + node.id + "}")
    if isinstance(node, ast.Attribute):
        return constants.get(expression_to_string(node), "{" + expression_to_string(node) + "}")
    if isinstance(node, ast.JoinedStr):
        # Python 3.14 removed the legacy string-literal branch; f-string text now flows through Constant.
        return evaluate_interpolated_string_values(node.values, constants, context)
    if is_runtime_ast_type(node, "TemplateStr"):
        # Python 3.14 added template-string AST nodes; this guard keeps Python 3.11-3.13 compatible.
        return evaluate_interpolated_string_values(getattr(node, "values", []), constants, context)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return evaluate_python_expression(node.left, constants, context) + evaluate_python_expression(node.right, constants, context)
    if isinstance(node, ast.Call):
        callable_name = get_callable_name(node.func)
        if callable_name in {"os.environ.get", "os.getenv"} and node.args:
            env_key = evaluate_python_expression(node.args[0], constants, context)
            default_value = evaluate_python_expression(node.args[1], constants, context) if len(node.args) > 1 else ""
            return context.environment.get(env_key, os.environ.get(env_key, default_value))
        if callable_name in {"str", "int", "float"} and node.args:
            value = evaluate_python_expression(node.args[0], constants, context)
            if value.startswith("{") and value.endswith("}"):
                return value
            return str(value)
    return expression_to_string(node)


def normalise_endpoint_url(endpoint_url: str, context: PythonAnalysisContext) -> str:
    endpoint_url = endpoint_url.strip().strip('"').strip("'")
    match = re.match(r"^(https?://)([^/:{}]+):(\d+)(.*)$", endpoint_url)
    if not match:
        return endpoint_url
    scheme, host, port, suffix = match.groups()
    if host in {"localhost", "127.0.0.1", "0.0.0.0"} and port in context.service_ports:
        return f"{scheme}{context.service_ports[port]}:{port}{suffix}"
    return endpoint_url


def classify_call(target_name: str) -> str:
    lower_name = target_name.lower()
    if any(client in lower_name for client in ("requests.", "httpx.", "aiohttp.")):
        return "HTTP_CLIENT_CALL"
    if any(queue in lower_name for queue in ("celery", "kombu", "pika", "kafka", "redis")):
        return "MESSAGING_CALL"
    return "FUNCTION_CALL"


def select_public_django_prefixes(module_path: str, django: DjangoMetadata) -> list[str]:
    prefixes = django.module_prefixes.get(module_path, [""])
    non_empty_prefixes = [prefix for prefix in prefixes if str(prefix).strip("/")]
    return non_empty_prefixes if non_empty_prefixes else prefixes


def extract_django_urlpatterns(tree: ast.AST, module_path: str, django: DjangoMetadata) -> list[PythonFunctionData]:
    routes: list[PythonFunctionData] = []
    prefixes = select_public_django_prefixes(module_path, django)
    router_registers = collect_django_router_registers(tree)
    route_index = 1
    for router_name, register_path, viewset_name in router_registers:
        base_methods = django_methods_for_viewset(viewset_name, django)
        for parent_prefix in prefixes:
            base_path = ensure_route_path(combine_url_paths(parent_prefix, register_path))
            detail_path = ensure_detail_route_path(base_path)
            for method in sorted(base_methods.get("list", set())):
                routes.append(make_django_route_function(viewset_name, method, base_path, route_index, "list"))
                route_index += 1
            for method in sorted(base_methods.get("detail", set())):
                routes.append(make_django_route_function(viewset_name, method, detail_path, route_index, "detail"))
                route_index += 1
            for action in django.viewset_actions.get(viewset_name, []):
                action_base = detail_path if action.get("detail") else base_path.rstrip("/") + "/"
                action_path = ensure_route_path(combine_url_paths(action_base, str(action.get("url_path", ""))))
                if not action_path.endswith("/"):
                    action_path += "/"
                for method in sorted(action.get("methods", {"HTTP"})):
                    routes.append(make_django_route_function(viewset_name, method, action_path, route_index, str(action.get("name", "action"))))
                    route_index += 1
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "urlpatterns" for target in node.targets):
            for call_node in ast.walk(node.value):
                if not isinstance(call_node, ast.Call):
                    continue
                if get_callable_name(call_node.func).split(".")[-1] not in DJANGO_URL_FUNCTIONS:
                    continue
                route_path = literal_to_string(call_node.args[0]) if call_node.args else ""
                view_node = call_node.args[1] if len(call_node.args) > 1 else None
                view_name = expression_to_string(view_node) if view_node is not None else "NOT_AVAILABLE"
                if should_skip_django_path(route_path, view_node):
                    continue
                if is_router_include(view_node):
                    continue
                if extract_django_include_target(view_node):
                    continue
                http_methods = django_methods_for_view_reference(view_name, django)
                if not http_methods:
                    http_methods = {"HTTP"}
                for parent_prefix in prefixes:
                    combined_path = ensure_route_path(combine_url_paths(parent_prefix, route_path))
                    for method in sorted(http_methods):
                        routes.append(PythonFunctionData(
                            name=f"django_urlpattern_{route_index}",
                            line_number=getattr(call_node, "lineno", 0),
                            route_path=combined_path,
                            http_method=method,
                            calls=[PythonCallData(target_name=view_name, call_type="DJANGO_VIEW_REFERENCE")],
                            decorators=[PythonDecoratorData(name=get_callable_name(call_node.func), route_path=combined_path, http_method=method)],
                        ))
                        route_index += 1
    return deduplicate_routes(routes)


def collect_django_router_registers(tree: ast.AST) -> list[tuple[str, str, str]]:
    registers: list[tuple[str, str, str]] = []
    router_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if get_callable_name(node.value.func).endswith("DefaultRouter") or get_callable_name(node.value.func).endswith("SimpleRouter"):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        router_names.add(target.id)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            callable_name = get_callable_name(node.func)
            parts = callable_name.split(".")
            if len(parts) >= 2 and parts[-1] == "register" and parts[-2] in router_names:
                register_path = literal_to_string(node.args[0]) if node.args else ""
                viewset_name = expression_to_string(node.args[1]).split(".")[-1] if len(node.args) > 1 else "NOT_AVAILABLE"
                registers.append((parts[-2], register_path, viewset_name))
    return registers


def django_methods_for_viewset(viewset_name: str, django: DjangoMetadata) -> dict[str, set[str]]:
    viewset_type = django.viewset_types.get(viewset_name, "VIEWSET")
    explicit_methods = django.view_methods.get(viewset_name, set())
    if viewset_type == "MODELVIEWSET":
        return {"list": {"GET", "POST"}, "detail": {"GET", "PUT", "PATCH", "DELETE"}}
    if explicit_methods:
        list_methods = {method for method in explicit_methods if method in {"GET", "POST"}}
        detail_methods = {method for method in explicit_methods if method in {"GET", "PUT", "PATCH", "DELETE"}}
        return {"list": list_methods, "detail": detail_methods}
    return {"list": {"HTTP"}, "detail": set()}


def django_methods_for_view_reference(view_name: str, django: DjangoMetadata) -> set[str]:
    view_name = view_name.split(".")[-1].replace(".as_view()", "")
    return django.view_methods.get(view_name, set())


def make_django_route_function(viewset_name: str, method: str, route_path: str, route_index: int, route_type: str) -> PythonFunctionData:
    function_name = f"django_{viewset_name}_{route_type}_{method.lower()}_{route_index}"
    return PythonFunctionData(
        name=function_name,
        line_number=0,
        route_path=route_path,
        http_method=method,
        decorators=[PythonDecoratorData(name="django.router", route_path=route_path, http_method=method)],
        calls=[PythonCallData(target_name=viewset_name, call_type="DJANGO_VIEWSET_REFERENCE")],
    )


def should_skip_django_path(route_path: str, view_node: ast.AST | None) -> bool:
    route_path = route_path.strip("/")
    view_name = expression_to_string(view_node) if view_node is not None else ""
    return route_path == "admin" or view_name.startswith("admin.")


def is_router_include(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if get_callable_name(node.func).split(".")[-1] != "include" or not node.args:
        return False
    first_arg = node.args[0]
    return isinstance(first_arg, ast.Attribute) and first_arg.attr == "urls"


def combine_url_paths(prefix: str, suffix: str) -> str:
    prefix = str(prefix or "").strip()
    suffix = str(suffix or "").strip()
    if not prefix:
        return suffix
    if not suffix:
        return prefix
    return prefix.rstrip("/") + "/" + suffix.lstrip("/")


def ensure_route_path(route_path: str) -> str:
    route_path = route_path or "/"
    if not route_path.startswith("/"):
        route_path = "/" + route_path
    return route_path


def ensure_detail_route_path(base_path: str) -> str:
    if not base_path.endswith("/"):
        base_path += "/"
    return base_path + "{id}/"


def deduplicate_routes(routes: list[PythonFunctionData]) -> list[PythonFunctionData]:
    unique_routes: list[PythonFunctionData] = []
    seen: set[tuple[str, str]] = set()
    for route in routes:
        key = (route.http_method, route.route_path)
        if key in seen:
            continue
        seen.add(key)
        unique_routes.append(route)
    return unique_routes


def is_django_http_method(method_name: str, class_node: ast.ClassDef) -> bool:
    if method_name.upper() not in HTTP_METHODS:
        return False
    base_names = {expression_to_string(base).lower() for base in class_node.bases}
    return any(base.endswith(("view", "apiview", "viewset", "modelviewset")) for base in base_names)


def get_callable_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = get_callable_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return get_callable_name(node.func)
    return expression_to_string(node)


def literal_to_string(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        # Python 3.14 removed the legacy literal AST classes, so Constant is the supported literal path.
        return constant_to_string(node)
    if is_runtime_ast_type(node, "TemplateStr"):
        # Python 3.14 added template-string AST nodes; keep this guarded for Python 3.11-3.13.
        return evaluate_interpolated_string_values(getattr(node, "values", []), {}, PythonAnalysisContext(module_name="", module_dir=""))
    return expression_to_string(node)


def expression_to_string(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = expression_to_string(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        if isinstance(node, ast.Constant):
            return str(node.value)
        return "NOT_AVAILABLE"


def detect_python_project(module_dir: str | Path, module_build_file: str = "") -> PythonProjectDetection:
    module_path = Path(module_dir)
    score = 0
    evidence: list[str] = []
    dependency_files = find_python_dependency_files(module_path)
    if module_build_file and is_python_dependency_file(module_build_file):
        dependency_files.append(module_build_file)
    python_files = find_python_files(module_path)
    if dependency_files:
        score += 3
        evidence.append("python_dependency_file")
    if python_files:
        score += 2
        evidence.append("python_source_file")
    libraries = get_python_library_list(module_path, module_build_file)
    dependency_names = get_dependency_names(libraries)
    imported_names = collect_import_names(python_files[:50])
    framework = detect_python_framework_from_evidence(module_path, dependency_names, imported_names, python_files)
    if framework != "PYTHON":
        score += 4
        evidence.append(framework.lower())
    language = "python" if score >= 2 else "generic"
    return PythonProjectDetection(language=language, framework=framework, score=score, evidence=evidence)


def detect_python_framework(module_dir: str | Path, module_build_file: str = "") -> str:
    return detect_python_project(module_dir, module_build_file).framework


def detect_python_framework_from_evidence(module_path: Path, dependency_names: set[str], imported_names: set[str], python_files: list[str]) -> str:
    has_django_structure = (module_path / "manage.py").is_file() and any(Path(file).name in {"settings.py", "urls.py", "asgi.py", "wsgi.py"} for file in python_files)
    if has_django_structure or "django" in dependency_names or any(name == "django" or name.startswith("django.") for name in imported_names):
        return "DJANGO"
    if "fastapi" in dependency_names or any(name == "fastapi" or name.startswith("fastapi.") for name in imported_names):
        return "FASTAPI"
    if "flask" in dependency_names or any(name == "flask" or name.startswith("flask.") for name in imported_names):
        return "FLASK"
    return "PYTHON"


def collect_import_names(python_files: list[str]) -> set[str]:
    imported_names: set[str] = set()
    for python_file in python_files:
        source = read_text_file(python_file)
        tree = parse_python_source(source, python_file, "python import discovery")
        if tree is None:
            continue
        for import_data in extract_imports(tree):
            if import_data.module_name:
                imported_names.add(import_data.module_name.lower())
            if import_data.imported_name:
                imported_names.add(f"{import_data.module_name}.{import_data.imported_name}".lower().strip("."))
    return imported_names


def python_main_parser(metamodel: Any, module_name: str, module_project: Any, multi_module_project: dict[str, Any], app_root_dir: str, app_config_dirs: list[str], application_containers: dict[str, Any], module_build_dir: str = "", module_build_file: str = "") -> None:
    module_dir = module_build_dir or resolve_module_dir(module_name, app_root_dir)
    framework = detect_python_framework(module_dir, module_build_file)
    ensure_python_model_available(metamodel)
    add_python_configuration_properties(metamodel, module_name, module_project, module_dir, app_config_dirs)
    layer = metamodel.PythonApplicationLayer()
    layer.ParentProjectName = module_name
    layer.ArtifactFileName = module_dir
    layer.LayerName = framework + "ApplicationLayer"
    module_project.layers.append(layer)
    python_files = find_python_files(module_dir)
    log_python_parser_start(module_name, module_dir, framework, python_files)
    analysis_context = build_python_analysis_context(module_name, module_dir, application_containers, python_files)
    for python_file in python_files:
        print('python_file = {}'.format(os.path.basename(python_file)))
        module_data = parse_python_file(python_file, module_dir, framework, analysis_context)
        if module_data is None:
            print('python_parse_skipped = {}'.format(os.path.basename(python_file)))
            continue
        log_python_module_details(module_data)
        module_element = create_python_module_element(metamodel, module_name, module_data)
        layer.elements.append(module_element)


def log_python_parser_start(module_name: str, module_dir: str | Path, framework: str, python_files: list[str]) -> None:
    dependency_files = find_python_dependency_files(module_dir)
    print('python_framework = {}'.format(framework))
    print('python_source_files = {}'.format(len(python_files)))
    if dependency_files:
        for dependency_file in dependency_files:
            print('python_dependency_file = {}'.format(os.path.basename(dependency_file)))
    else:
        print('python_dependency_file = NOT_AVAILABLE')


def log_python_module_details(module_data: PythonModuleData) -> None:
    for function_data in module_data.functions:
        log_python_function_details(function_data)
    for class_data in module_data.classes:
        print('python_class = {}'.format(class_data.name))
        for method_data in class_data.methods:
            log_python_function_details(method_data)


def log_python_function_details(function_data: PythonFunctionData) -> None:
    if function_data.route_path:
        method = function_data.http_method or 'HTTP'
        print('python_route = {} {}'.format(method, function_data.route_path))
    for call_data in function_data.calls:
        if call_data.call_type == 'HTTP_CLIENT_CALL' and call_data.endpoint_url:
            print('python_http_call = {}'.format(call_data.endpoint_url))


def resolve_module_dir(module_name: str, app_root_dir: str | Path) -> str:
    direct_path = Path(app_root_dir) / module_name
    if direct_path.is_dir():
        return str(direct_path)
    for root, dirs, files in os.walk(app_root_dir, topdown=True):
        dirs[:] = [directory for directory in dirs if directory not in IGNORED_DIRECTORIES]
        if Path(root).name == module_name:
            return str(Path(root))
    return str(direct_path)


def ensure_python_model_available(metamodel: Any) -> None:
    required = ["PythonApplicationLayer", "PythonSourceModule", "PythonFunction", "PythonClass"]
    missing = [name for name in required if not hasattr(metamodel, name)]
    if missing:
        raise RuntimeError("The selected PSM Ecore file does not include the Python extension classes: " + ", ".join(missing))


def add_python_configuration_properties(metamodel: Any, module_name: str, module_project: Any, module_dir: str, app_config_dirs: list[str]) -> None:
    properties = collect_python_configuration_properties(module_name, module_dir, app_config_dirs)
    if not properties:
        properties.append({"filename": module_dir, "property": "python.configuration", "value": "NOT_AVAILABLE", "profile": "COMPILE"})
    for property_data in properties:
        configuration_property = metamodel.ConfigurationProperty()
        set_xmi_text_attribute(configuration_property, "ParentProjectName", module_name, "NOT_AVAILABLE")
        set_xmi_text_attribute(configuration_property, "ArtifactFileName", property_data["filename"], "NOT_AVAILABLE")
        set_xmi_text_attribute(configuration_property, "FullyQualifiedPropertyName", property_data["property"], "NOT_AVAILABLE")
        set_xmi_text_attribute(configuration_property, "PropertyValue", property_data["value"], "NOT_AVAILABLE")
        set_xmi_text_attribute(configuration_property, "ConfigurationProfile", property_data["profile"], "COMPILE")
        module_project.properties.append(configuration_property)


def collect_python_configuration_properties(module_name: str, module_dir: str | Path, app_config_dirs: list[str]) -> list[dict[str, str]]:
    config_files: list[str] = []
    search_dirs = [str(module_dir)] + [directory for directory in app_config_dirs if directory]
    for search_dir in search_dirs:
        path = Path(search_dir)
        if not path.is_dir():
            continue
        for root, dirs, files in os.walk(path, topdown=True):
            dirs[:] = [directory for directory in dirs if directory not in IGNORED_DIRECTORIES]
            for file in files:
                if file in PYTHON_CONFIG_FILES:
                    config_files.append(str(Path(root) / file))
    properties: list[dict[str, str]] = []
    for config_file in config_files:
        file_name = Path(config_file).name
        if file_name in {".env", ".flaskenv"}:
            properties.extend(parse_env_config(config_file))
        elif file_name.endswith((".yml", ".yaml")):
            properties.extend(parse_yaml_config(config_file))
        elif file_name.endswith(".py"):
            properties.extend(parse_python_assignment_config(config_file))
    return properties


def parse_env_config(config_file: str | Path) -> list[dict[str, str]]:
    properties: list[dict[str, str]] = []
    for line in read_text_file(config_file).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        properties.append({"filename": str(config_file), "property": name.strip(), "value": value.strip().strip('"').strip("'"), "profile": "COMPILE"})
    return properties


def parse_yaml_config(config_file: str | Path) -> list[dict[str, str]]:
    properties: list[dict[str, str]] = []
    if yaml is None:
        return properties
    try:
        data = yaml.safe_load(read_text_file(config_file)) or {}
    except Exception:
        return properties
    for key, value in flatten_mapping(data).items():
        properties.append({"filename": str(config_file), "property": key, "value": str(value), "profile": "COMPILE"})
    return properties


def flatten_mapping(data: Any, prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            child_key = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_mapping(value, child_key))
    else:
        flattened[prefix] = data
    return flattened


def parse_python_assignment_config(config_file: str | Path) -> list[dict[str, str]]:
    properties: list[dict[str, str]] = []
    source = read_text_file(config_file)
    tree = parse_python_source(source, config_file, "python assignment configuration analysis")
    if tree is None:
        return properties
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    properties.append({"filename": str(config_file), "property": target.id, "value": expression_to_string(node.value), "profile": "COMPILE"})
    return properties


XML_FORBIDDEN_CHARACTER_PATTERN = re.compile(
    "[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)


def to_xmi_safe_text(value: Any, fallback: str = "") -> str:
    """Return text that is safe to store in XML/XMI attributes.

    UTF-8/non-ASCII text is preserved. Characters forbidden by XML 1.0 are
    removed so the XMI writer cannot produce a model that later fails to load.
    Standard XML entities such as &, < and > are intentionally left as text
    because the XMI/XML serializer is responsible for escaping them once.
    """
    if value is None:
        return fallback

    text = str(value)
    if not text:
        return fallback

    text = XML_FORBIDDEN_CHARACTER_PATTERN.sub(" ", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    text = text.replace("\ufffe", " ").replace("\uffff", " ")
    text = re.sub(r"\s+", " ", text).strip()

    return text if text else fallback


def set_xmi_text_attribute(element: Any, attribute_name: str, value: Any, fallback: str = "") -> None:
    setattr(element, attribute_name, to_xmi_safe_text(value, fallback))


def append_xmi_text(target: Any, value: Any, fallback: str = "") -> None:
    target.append(to_xmi_safe_text(value, fallback))


def create_python_module_element(metamodel: Any, module_name: str, module_data: PythonModuleData) -> Any:
    module_element = metamodel.PythonSourceModule()
    set_python_element_fields(module_element, module_name, module_data.filename, module_data.module_name, "COMPILE", 0)
    set_xmi_text_attribute(module_element, "ModuleName", module_data.module_name, "NOT_AVAILABLE")
    set_xmi_text_attribute(module_element, "PackageName", module_data.package_name)
    set_xmi_text_attribute(module_element, "FrameworkName", module_data.framework, "PYTHON")
    for import_data in module_data.imports:
        import_element = metamodel.PythonImport()
        set_python_element_fields(import_element, module_name, module_data.filename, import_data.module_name, "COMPILE", 0)
        set_xmi_text_attribute(import_element, "ModuleName", import_data.module_name, "NOT_AVAILABLE")
        set_xmi_text_attribute(import_element, "ImportedName", import_data.imported_name)
        set_xmi_text_attribute(import_element, "Alias", import_data.alias)
        module_element.imports.append(import_element)
    for function_data in module_data.functions:
        module_element.functions.append(create_python_function_element(metamodel, module_name, module_data.filename, function_data))
    for class_data in module_data.classes:
        module_element.classes.append(create_python_class_element(metamodel, module_name, module_data.filename, class_data))
    return module_element


def create_python_class_element(metamodel: Any, module_name: str, filename: str, class_data: PythonClassData) -> Any:
    class_element = metamodel.PythonClass()
    set_python_element_fields(class_element, module_name, filename, class_data.name, "COMPILE", class_data.line_number)
    for base in class_data.bases:
        append_xmi_text(class_element.BaseClasses, base, "NOT_AVAILABLE")
    for decorator_data in class_data.decorators:
        class_element.decorators.append(create_python_decorator_element(metamodel, module_name, filename, decorator_data))
    for method_data in class_data.methods:
        class_element.methods.append(create_python_function_element(metamodel, module_name, filename, method_data))
    return class_element


def create_python_function_element(metamodel: Any, module_name: str, filename: str, function_data: PythonFunctionData) -> Any:
    function_element = metamodel.PythonFunction()
    set_python_element_fields(function_element, module_name, filename, function_data.name, "COMPILE", function_data.line_number)
    function_element.IsAsync = function_data.is_async
    set_xmi_text_attribute(function_element, "RoutePath", function_data.route_path)
    set_xmi_text_attribute(function_element, "HttpMethod", function_data.http_method or "NOT_AVAILABLE", "NOT_AVAILABLE")
    set_xmi_text_attribute(function_element, "ReturnTypeHint", function_data.return_type, "NOT_AVAILABLE")
    for parameter_data in function_data.parameters:
        parameter_element = metamodel.PythonFunctionParameter()
        set_python_element_fields(parameter_element, module_name, filename, parameter_data.name, "COMPILE", 0)
        set_xmi_text_attribute(parameter_element, "ParameterName", parameter_data.name, "NOT_AVAILABLE")
        parameter_element.ParameterOrder = parameter_data.order
        set_xmi_text_attribute(parameter_element, "TypeHint", parameter_data.type_hint, "NOT_AVAILABLE")
        set_xmi_text_attribute(parameter_element, "DefaultValue", parameter_data.default_value, "NOT_AVAILABLE")
        function_element.parameters.append(parameter_element)
    for decorator_data in function_data.decorators:
        function_element.decorators.append(create_python_decorator_element(metamodel, module_name, filename, decorator_data))
    for call_data in function_data.calls:
        call_element = metamodel.PythonCall()
        set_python_element_fields(call_element, module_name, filename, call_data.target_name, "COMPILE", 0)
        set_xmi_text_attribute(call_element, "TargetName", call_data.target_name, "NOT_AVAILABLE")
        set_xmi_text_attribute(call_element, "RootCallingFunction", function_data.name, "NOT_AVAILABLE")
        set_xmi_text_attribute(call_element, "CallType", call_data.call_type, "FUNCTION_CALL")
        set_xmi_text_attribute(call_element, "EndpointURL", call_data.endpoint_url)
        function_element.invokes.append(call_element)
    return function_element


def create_python_decorator_element(metamodel: Any, module_name: str, filename: str, decorator_data: PythonDecoratorData) -> Any:
    decorator_element = metamodel.PythonDecorator()
    set_python_element_fields(decorator_element, module_name, filename, decorator_data.name, "COMPILE", 0)
    set_xmi_text_attribute(decorator_element, "DecoratorName", decorator_data.name, "NOT_AVAILABLE")
    set_xmi_text_attribute(decorator_element, "RoutePath", decorator_data.route_path)
    set_xmi_text_attribute(decorator_element, "HttpMethod", decorator_data.http_method or "NOT_AVAILABLE", "NOT_AVAILABLE")
    for parameter_name, parameter_value in decorator_data.parameters.items():
        parameter_element = metamodel.PythonDecoratorParameter()
        set_python_element_fields(parameter_element, module_name, filename, parameter_name, "COMPILE", 0)
        set_xmi_text_attribute(parameter_element, "ParameterName", parameter_name, "NOT_AVAILABLE")
        set_xmi_text_attribute(parameter_element, "ParameterValue", parameter_value, "NOT_AVAILABLE")
        decorator_element.parameters.append(parameter_element)
    return decorator_element


def set_python_element_fields(element: Any, parent_project_name: str, artifact_file_name: str, identifier: str, profile: str, line_number: int) -> None:
    set_xmi_text_attribute(element, "ParentProjectName", parent_project_name, "NOT_AVAILABLE")
    set_xmi_text_attribute(element, "ArtifactFileName", artifact_file_name, "NOT_AVAILABLE")
    set_xmi_text_attribute(element, "ElementIdentifier", identifier, "NOT_AVAILABLE")
    set_xmi_text_attribute(element, "ElementProfile", profile, "COMPILE")
    element.LineNumber = int(line_number or 0)