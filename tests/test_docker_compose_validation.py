from pathlib import Path

from MisarParserValidation import (
    format_docker_compose_validation_messages,
    validate_docker_compose_file,
    validate_docker_compose_files,
)


def write_file(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_docker_compose_file_passes(tmp_path):
    service_dir = tmp_path / "api"
    service_dir.mkdir()
    compose_file = write_file(
        tmp_path / "docker-compose.yml",
        """
        services:
          api:
            build: ./api
            ports:
              - "8000:8000"
            depends_on:
              - redis
          redis:
            image: redis:7
        """,
    )

    result = validate_docker_compose_file(compose_file)

    assert result.is_valid
    assert result.services_count == 2
    assert result.runnable_services_count == 2
    assert result.errors == []


def test_missing_services_is_hard_error(tmp_path):
    compose_file = write_file(
        tmp_path / "docker-compose.yml",
        """
        version: "3.9"
        networks:
          default: {}
        """,
    )

    result = validate_docker_compose_file(compose_file)

    assert not result.is_valid
    assert any("services" in error for error in result.errors)


def test_no_runnable_service_is_hard_error_but_service_warning_is_kept(tmp_path):
    compose_file = write_file(
        tmp_path / "docker-compose.yml",
        """
        services:
          placeholder:
            environment:
              DEBUG: "true"
        """,
    )

    result = validate_docker_compose_file(compose_file)

    assert not result.is_valid
    assert any("no service with an 'image' or 'build'" in error for error in result.errors)
    assert any("no 'image' or 'build'" in warning for warning in result.warnings)


def test_missing_build_context_is_warning_not_error(tmp_path):
    compose_file = write_file(
        tmp_path / "docker-compose.yml",
        """
        services:
          api:
            build: ./missing-api
            ports: "8000:8000"
            depends_on: redis
        """,
    )

    result = validate_docker_compose_file(compose_file)

    assert result.is_valid
    assert any("build context does not exist" in warning for warning in result.warnings)
    assert any("'ports' should usually be a list" in warning for warning in result.warnings)
    assert any("'depends_on' should be a list or mapping" in warning for warning in result.warnings)


def test_invalid_yaml_is_hard_error(tmp_path):
    compose_file = write_file(
        tmp_path / "docker-compose.yml",
        """
        services:
          api:
            image: nginx
           bad-indent: true
        """,
    )

    result = validate_docker_compose_file(compose_file)

    assert not result.is_valid
    assert any("parse YAML" in error for error in result.errors)


def test_multiple_file_formatter_splits_errors_and_warnings(tmp_path):
    valid_dir = tmp_path / "api"
    valid_dir.mkdir()
    valid_file = write_file(
        tmp_path / "valid-compose.yml",
        """
        services:
          api:
            build: ./api
        """,
    )
    warning_file = write_file(
        tmp_path / "warning-compose.yml",
        """
        services:
          api:
            image: nginx
            ports: "80:80"
        """,
    )
    invalid_file = write_file(
        tmp_path / "broken-compose.yml",
        """
        services: []
        """,
    )

    results = validate_docker_compose_files([str(valid_file), str(warning_file), str(invalid_file)])
    errors, warnings = format_docker_compose_validation_messages(results)

    assert any(error.startswith("broken-compose.yml:") for error in errors)
    assert any(warning.startswith("warning-compose.yml:") for warning in warnings)
    assert not any(error.startswith("valid-compose.yml:") for error in errors)
