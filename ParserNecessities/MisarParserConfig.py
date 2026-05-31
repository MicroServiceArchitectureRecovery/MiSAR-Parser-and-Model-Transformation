# Runtime configuration helpers for selecting MiSAR metamodel and transformation files without replacing the original Java-only artefacts.

from __future__ import annotations

import os
from pathlib import Path

USER_HOME_DIR = Path.home()
MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
TRANSFORMATION_SOURCE_DIR = PARSER_DIR / "TransformationEngineNecessities" / "source"

PSM_ORIGINAL_ECORE_PATH = TRANSFORMATION_SOURCE_DIR / "PSM.ecore"
PSM_PYTHON_ECORE_PATH = TRANSFORMATION_SOURCE_DIR / "PSM-python.ecore"
PIM_ECORE_PATH = TRANSFORMATION_SOURCE_DIR / "PIM.ecore"
QVTO_V3_PATH = TRANSFORMATION_SOURCE_DIR / "MisarTransformation3.qvto"
QVTO_V4_PATH = TRANSFORMATION_SOURCE_DIR / "MisarTransformation4.qvto"

ENV_ECORE_MODE = "MISAR_ECORE_MODE"
ENV_PSM_ECORE = "MISAR_PSM_ECORE"
ENV_PIM_ECORE = "MISAR_PIM_ECORE"
ENV_QVTO_FILE = "MISAR_QVTO_FILE"


def _existing_path(path_value: str | Path | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser()
    return path if path.is_file() else None


def resolve_psm_ecore_path(project_uses_python: bool = False, selected_path: str | Path | None = None) -> str:
    override = _existing_path(os.environ.get(ENV_PSM_ECORE))
    if override is not None:
        return str(override)

    mode = os.environ.get(ENV_ECORE_MODE, "auto").strip().lower()
    if mode in {"python", "py", "extension"}:
        return str(PSM_PYTHON_ECORE_PATH if PSM_PYTHON_ECORE_PATH.is_file() else PSM_ORIGINAL_ECORE_PATH)
    if mode in {"original", "java", "legacy"}:
        return str(PSM_ORIGINAL_ECORE_PATH)

    selected = _existing_path(selected_path)
    original_selected = selected is not None and selected.resolve() == PSM_ORIGINAL_ECORE_PATH.resolve()
    if project_uses_python and PSM_PYTHON_ECORE_PATH.is_file() and (selected is None or original_selected):
        return str(PSM_PYTHON_ECORE_PATH)
    if selected is not None:
        return str(selected)
    return str(PSM_ORIGINAL_ECORE_PATH)


def resolve_pim_ecore_path(selected_path: str | Path | None = None) -> str:
    override = _existing_path(os.environ.get(ENV_PIM_ECORE))
    if override is not None:
        return str(override)
    selected = _existing_path(selected_path)
    if selected is not None:
        return str(selected)
    return str(PIM_ECORE_PATH)


def resolve_qvto_file_path(project_uses_python: bool = False, selected_path: str | Path | None = None) -> str:
    override = _existing_path(os.environ.get(ENV_QVTO_FILE))
    if override is not None:
        return str(override)
    selected = _existing_path(selected_path)
    if selected is not None:
        return str(selected)
    if project_uses_python and QVTO_V4_PATH.is_file():
        return str(QVTO_V4_PATH)
    return str(QVTO_V3_PATH)


def describe_model_selection(project_uses_python: bool = False, selected_psm_path: str | Path | None = None) -> dict[str, str]:
    return {
        "psm_ecore": resolve_psm_ecore_path(project_uses_python, selected_psm_path),
        "pim_ecore": resolve_pim_ecore_path(),
        "qvto_file": resolve_qvto_file_path(project_uses_python),
        "ecore_mode": os.environ.get(ENV_ECORE_MODE, "auto"),
    }
