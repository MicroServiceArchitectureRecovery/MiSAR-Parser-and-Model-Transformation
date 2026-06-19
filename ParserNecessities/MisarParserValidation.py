"""Pure validation helpers for MiSAR Parser GUI inputs."""

from __future__ import annotations

FORBIDDEN_PROJECT_NAME_CHARACTERS = set('<>:"/\\|?*')


def has_forbidden_project_name_characters(project_name: str) -> bool:
    return any(character in FORBIDDEN_PROJECT_NAME_CHARACTERS for character in project_name)


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
