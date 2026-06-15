# Runtime configuration helpers for selecting the MiSAR PSM Ecore used by the parser.

from __future__ import annotations

import argparse
from pathlib import Path

USER_HOME_DIR = Path.home()
MISAR_DIR = USER_HOME_DIR / "MiSAR"
PARSER_DIR = MISAR_DIR / "Parser"
TRANSFORMATION_SOURCE_DIR = PARSER_DIR / "TransformationEngineNecessities" / "source"

DEFAULT_PSM_ECORE_PATH = TRANSFORMATION_SOURCE_DIR / "PSM.ecore"

_ARGS: argparse.Namespace | None = None


def parse_misar_parser_args() -> argparse.Namespace:
    global _ARGS
    if _ARGS is not None:
        return _ARGS

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--psm-path",
        "--misar-psm-path",
        default=None,
        help="Path to the PSM Ecore file used by the parser. Defaults to ~/MiSAR/Parser/TransformationEngineNecessities/source/PSM.ecore.",
    )
    _ARGS, _ = parser.parse_known_args()
    return _ARGS


def _arg_value(name: str) -> str | None:
    value = getattr(parse_misar_parser_args(), name, None)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def resolve_psm_ecore_path(selected_path: str | Path | None = None) -> str:
    path_value = _arg_value("psm_path") or selected_path or DEFAULT_PSM_ECORE_PATH
    return str(Path(path_value).expanduser())


def describe_psm_selection(selected_path: str | Path | None = None) -> dict[str, str]:
    psm_path = Path(resolve_psm_ecore_path(selected_path))
    source = "argparse --psm-path" if _arg_value("psm_path") else "default PSM.ecore path"
    if selected_path and not _arg_value("psm_path"):
        source = "provided parser path"
    return {
        "psm_path": str(psm_path),
        "psm_source": source,
        "psm_exists": str(psm_path.is_file()),
    }
