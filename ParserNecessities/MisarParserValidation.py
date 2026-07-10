"""Pure validation helpers for MiSAR Parser GUI inputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


FORBIDDEN_PROJECT_NAME_CHARACTERS = set('<>:"/\\|?*')


@dataclass
class DockerComposeValidationResult:
    file_path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    services_count: int = 0
    runnable_services_count: int = 0

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


def has_forbidden_project_name_characters(project_name: str) -> bool:
    return any(character in FORBIDDEN_PROJECT_NAME_CHARACTERS for character in project_name)


def log_validation_message(level: str, message: str) -> None:
    print("misar_validation_{} = {}".format(str(level).lower(), message))


def normalise_compose_path(file_path: str | Path) -> Path:
    return Path(str(file_path)).expanduser()


def compose_service_has_runnable_source(service_definition: dict[str, Any]) -> bool:
    return bool(service_definition.get("image") or service_definition.get("build"))


def extract_compose_build_context(service_definition: dict[str, Any]) -> str:
    build_definition = service_definition.get("build", "")
    if isinstance(build_definition, str):
        return build_definition.strip()
    if isinstance(build_definition, dict):
        context = build_definition.get("context", "")
        return str(context).strip() if context is not None else ""
    return ""


def validate_compose_ports_shape(service_name: str, service_definition: dict[str, Any], result: DockerComposeValidationResult) -> None:
    # Compose allows strings, integers and long-form dictionaries inside ports/expose lists.
    # We only warn on unsupported shapes because the Docker parser can still recover other fields.
    for field_name in ("ports", "expose"):
        if field_name not in service_definition:
            continue

        field_value = service_definition.get(field_name)
        if not isinstance(field_value, list):
            result.warnings.append(
                f"{service_name}: '{field_name}' should usually be a list in Docker Compose."
            )
            continue

        for index, item in enumerate(field_value, start=1):
            if not isinstance(item, (str, int, dict)):
                result.warnings.append(
                    f"{service_name}: '{field_name}' item {index} has an unusual type: {type(item).__name__}."
                )


def validate_compose_depends_on_shape(service_name: str, service_definition: dict[str, Any], result: DockerComposeValidationResult) -> None:
    # Compose supports both list and mapping styles for depends_on. Other shapes are suspicious,
    # but they should not block model generation when the service itself is otherwise recoverable.
    if "depends_on" not in service_definition:
        return

    depends_on = service_definition.get("depends_on")
    if not isinstance(depends_on, (list, dict)):
        result.warnings.append(
            f"{service_name}: 'depends_on' should be a list or mapping."
        )


def validate_compose_build_context(service_name: str, service_definition: dict[str, Any], compose_file: Path, result: DockerComposeValidationResult) -> None:
    if "build" not in service_definition:
        return

    build_definition = service_definition.get("build")
    if not isinstance(build_definition, (str, dict)):
        result.warnings.append(
            f"{service_name}: 'build' should be a string path or a mapping with context."
        )
        return

    build_context = extract_compose_build_context(service_definition)
    if not build_context:
        result.warnings.append(
            f"{service_name}: build context is empty or missing."
        )
        return

    # Build contexts can be remote URLs, Git URLs, absolute paths or relative paths.
    # MiSAR only checks local relative/absolute paths; remote contexts are allowed as warnings-free.
    if "://" in build_context or build_context.startswith("git@"):
        return

    context_path = Path(build_context)
    if not context_path.is_absolute():
        context_path = compose_file.parent / context_path

    if not context_path.exists():
        result.warnings.append(
            f"{service_name}: build context does not exist relative to the compose file: {build_context}"
        )


def validate_docker_compose_file(file_path: str | Path, log: bool = False) -> DockerComposeValidationResult:
    """Validate the Docker Compose shape before the legacy Docker parser receives it.

    This is intentionally a light MiSAR validator, not a full Docker Compose specification validator.
    Hard errors block parser execution only when the file cannot provide usable service/container data.
    Warnings are logged but allowed, because advanced Compose files may contain valid syntax that MiSAR
    does not need to fully understand.
    """
    compose_file = normalise_compose_path(file_path)
    result = DockerComposeValidationResult(file_path=str(compose_file))

    if not compose_file.is_file():
        result.errors.append("Docker Compose file does not exist.")
        return log_docker_compose_validation_result(result) if log else result

    if compose_file.suffix.lower() not in {".yml", ".yaml"}:
        result.errors.append("Docker Compose file must use .yml or .yaml extension.")
        return log_docker_compose_validation_result(result) if log else result

    if yaml is None:
        result.errors.append("PyYAML is not available, so Docker Compose files cannot be validated.")
        return log_docker_compose_validation_result(result) if log else result

    try:
        compose_data = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        try:
            compose_data = yaml.safe_load(compose_file.read_text(encoding="latin-1"))
        except Exception as error:
            result.errors.append(f"Could not read or parse YAML: {error}")
            return log_docker_compose_validation_result(result) if log else result
    except Exception as error:
        result.errors.append(f"Could not parse YAML: {error}")
        return log_docker_compose_validation_result(result) if log else result

    if compose_data is None:
        result.errors.append("Docker Compose file is empty.")
        return log_docker_compose_validation_result(result) if log else result

    if not isinstance(compose_data, dict):
        result.errors.append("Docker Compose YAML root must be a mapping/object.")
        return log_docker_compose_validation_result(result) if log else result

    if "services" not in compose_data:
        result.errors.append("Docker Compose file must contain a top-level 'services' section.")
        return log_docker_compose_validation_result(result) if log else result

    services = compose_data.get("services")
    if not isinstance(services, dict):
        result.errors.append("Docker Compose 'services' section must be a mapping/object.")
        return log_docker_compose_validation_result(result) if log else result

    if not services:
        result.errors.append("Docker Compose 'services' section is empty.")
        return log_docker_compose_validation_result(result) if log else result

    result.services_count = len(services)
    runnable_services = 0

    for service_name, service_definition in services.items():
        service_name = str(service_name)

        # Extension fields should not normally live inside services, but ignore them if they do.
        if service_name.startswith("x-"):
            continue

        if not isinstance(service_definition, dict):
            result.warnings.append(
                f"{service_name}: service definition should be a mapping/object."
            )
            continue

        if compose_service_has_runnable_source(service_definition):
            runnable_services += 1
        else:
            result.warnings.append(
                f"{service_name}: service has no 'image' or 'build'; MiSAR may not recover it as a container."
            )

        validate_compose_build_context(service_name, service_definition, compose_file, result)
        validate_compose_ports_shape(service_name, service_definition, result)
        validate_compose_depends_on_shape(service_name, service_definition, result)

    result.runnable_services_count = runnable_services

    if runnable_services == 0:
        result.errors.append("Docker Compose file has no service with an 'image' or 'build' field.")

    return log_docker_compose_validation_result(result) if log else result


def validate_docker_compose_files(file_paths: list[str] | tuple[str, ...], log: bool = False) -> list[DockerComposeValidationResult]:
    results = [validate_docker_compose_file(file_path, log=False) for file_path in file_paths if str(file_path).strip()]
    if log:
        log_docker_compose_validation_results(results)
    return results


def format_docker_compose_validation_messages(results: list[DockerComposeValidationResult]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for result in results:
        file_label = Path(result.file_path).name
        for error in result.errors:
            errors.append(f"{file_label}: {error}")
        for warning in result.warnings:
            warnings.append(f"{file_label}: {warning}")

    return errors, warnings


def docker_compose_user_error_message(error: str) -> str:
    # Keep GUI errors short. The detailed parser/YAML exception is still logged
    # through log_docker_compose_validation_results() for debugging.
    if "Could not parse YAML" in error or "Could not read or parse YAML" in error:
        return "Could not parse YAML. Please select a valid Docker Compose file."
    if "does not exist" in error:
        return "Docker Compose file does not exist. Please select a valid Docker Compose file."
    if "must use .yml or .yaml" in error:
        return "Please select a .yml or .yaml Docker Compose file."
    if "empty" in error:
        return "Docker Compose file is empty. Please select a valid Docker Compose file."
    if "top-level 'services'" in error:
        return "Docker Compose file has no services section. Please select a valid Docker Compose file."
    if "'services' section must be a mapping" in error:
        return "Docker Compose services section is invalid. Please select a valid Docker Compose file."
    if "no service with an 'image' or 'build'" in error:
        return "Docker Compose file has no runnable service with image or build."
    if "YAML root must be a mapping" in error:
        return "Docker Compose YAML structure is invalid. Please select a valid Docker Compose file."
    return "Invalid Docker Compose file. Please select a valid Docker Compose file."


def format_docker_compose_user_messages(results: list[DockerComposeValidationResult]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for result in results:
        file_label = Path(result.file_path).name
        for error in result.errors:
            errors.append(f"{file_label}: {docker_compose_user_error_message(error)}")
        for warning in result.warnings:
            # Warnings are already concise enough for the user, and they do not block generation.
            warnings.append(f"{file_label}: {warning}")

    return errors, warnings


def log_docker_compose_validation_result(result: DockerComposeValidationResult) -> DockerComposeValidationResult:
    log_docker_compose_validation_results([result])
    return result


def log_docker_compose_validation_results(results: list[DockerComposeValidationResult]) -> None:
    for result in results:
        file_label = Path(result.file_path).name
        if result.is_valid:
            log_validation_message(
                "info",
                f"{file_label}: Docker Compose validation passed "
                f"({result.runnable_services_count}/{result.services_count} runnable services)."
            )
        for error in result.errors:
            log_validation_message("error", f"{file_label}: {error}")
        for warning in result.warnings:
            log_validation_message("warning", f"{file_label}: {warning}")


def validate_psm_inputs(
    project_name: str,
    project_dir: str,
    docker_compose_files: list[str] | tuple[str, ...],
    module_build_dirs: list[str] | tuple[str, ...],
    output_dir: str,
) -> list[str]:
    errors: list[str] = []

    if not str(project_name or "").strip():
        errors.append("Application Project Name missing")
    elif has_forbidden_project_name_characters(str(project_name)):
        errors.append("Application Project Name has forbidden characters: < > : \" / \\\\ | ? *")

    if not str(project_dir or "").strip():
        errors.append("Application Project Build Directory missing")

    if not docker_compose_files:
        errors.append("Docker Compose Files missing")

    if not module_build_dirs:
        errors.append("Microservice Projects Build Directories missing")

    if not str(output_dir or "").strip():
        errors.append("Output Directory missing")

    return errors


def is_psm_input_valid(
    project_name: str,
    project_dir: str,
    docker_compose_files: list[str] | tuple[str, ...],
    module_build_dirs: list[str] | tuple[str, ...],
    output_dir: str,
) -> bool:
    return not validate_psm_inputs(
        project_name=project_name,
        project_dir=project_dir,
        docker_compose_files=docker_compose_files,
        module_build_dirs=module_build_dirs,
        output_dir=output_dir,
    )
