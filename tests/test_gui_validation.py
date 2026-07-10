from MisarParserValidation import is_psm_input_valid, validate_psm_inputs


def test_gui_validation_detects_missing_required_fields():
    errors = validate_psm_inputs(
        project_name='',
        project_dir='',
        docker_compose_files=[],
        module_build_dirs=[],
        output_dir='',
    )

    assert 'Application Project Name missing' in errors
    assert 'Application Project Build Directory missing' in errors
    assert 'Docker Compose Files missing' in errors
    assert 'Microservice Projects Build Directories missing' in errors
    assert 'Output Directory missing' in errors


def test_gui_validation_rejects_forbidden_project_name_characters():
    errors = validate_psm_inputs(
        project_name='bad/project',
        project_dir='/tmp/project',
        docker_compose_files=['docker-compose.yml'],
        module_build_dirs=['service'],
        output_dir='/tmp/out',
    )

    assert any('forbidden characters' in error for error in errors)


def test_gui_validation_accepts_valid_inputs():
    assert is_psm_input_valid(
        project_name='valid-project',
        project_dir='/tmp/project',
        docker_compose_files=['docker-compose.yml'],
        module_build_dirs=['service'],
        output_dir='/tmp/out',
    )
