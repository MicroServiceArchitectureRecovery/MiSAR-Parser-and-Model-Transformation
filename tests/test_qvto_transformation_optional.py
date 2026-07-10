import os
import shlex
import subprocess

import pytest

from conftest import TRANSFORMATION_SOURCE_DIR, TRANSFORMATION_TRANSFORMS_DIR


@pytest.mark.qvto
def test_optional_qvto_transformation_command_runs(tmp_path):
    command_template = os.environ.get('MISAR_QVTO_COMMAND', '').strip()
    if not command_template:
        pytest.skip('Set MISAR_QVTO_COMMAND to run the optional QVTo runtime test.')

    source = TRANSFORMATION_SOURCE_DIR / 'artifacts-trainticket.xmi'
    transform = TRANSFORMATION_TRANSFORMS_DIR / 'MisarTransformationEngine.qvto'
    target = tmp_path / 'architecture-trainticket-test.xmi'

    if not source.is_file():
        pytest.skip('Sample PSM source file is not available.')
    if not transform.is_file():
        pytest.skip('QVTo transformation file is not available.')

    command = command_template.format(
        source=str(source),
        target=str(target),
        transform=str(transform),
    )

    result = subprocess.run(
        shlex.split(command),
        cwd=str(tmp_path),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )

    assert result.returncode == 0, result.stdout
    assert target.is_file()
    assert target.stat().st_size > 0
