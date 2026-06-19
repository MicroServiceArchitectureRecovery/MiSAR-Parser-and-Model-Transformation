# MiSAR Test Suite

This folder adds a starter pytest-based test suite for MiSAR.

The tests cover:

- Recursive language/framework detection
- Python route and HTTP-call extraction
- Docker Compose parsing
- Parser runtime PSM path configuration
- GUI input-validation rules through a pure validation helper
- PSM generation smoke testing
- QVTo transformation-file sanity checks
- Optional QVTo runtime testing if a headless QVTo command is provided

## Install test dependencies

From the project root:

`python -m pip install -r tests/requirementst.txt`

## Run the normal test suite

`python -m pytest -q`

## Run only quick unit tests

`python -m pytest -q -m "not integration and not qvto"`

## Run optional QVTo runtime test

The QVTo runtime test is skipped by default because Eclipse/QVTo is environment-specific.

If you have a working headless transformation command, set:

`MISAR_QVTO_COMMAND="your command here"`

Then run:

`python -m pytest -q -m qvto`

The command may use these placeholders:

- `{source}` for the generated/source PSM path
- `{target}` for the target PIM path
- `{transform}` for the QVTo transformation file path

Example shape:

`MISAR_QVTO_COMMAND="eclipse -nosplash -application org.eclipse.m2m.qvt.oml.TransformationExecutor -source {source} -target {target} -transformation {transform}"`

Adjust the command to match the QVTo runtime available on your machine.

> Note: Headless Eclipse is not available on all platforms. By default, the QVTo runtime test is skipped.

## Recommended CI command

For GitHub Actions or local checks where Eclipse is not installed:

`python -m pytest -q -m "not qvto"`

## Why GUI validation is tested through a helper

The current Tkinter GUI creates widgets at import time, which makes direct GUI unit testing fragile. The provided `ParserNecessities/MisarParserValidation.py` module extracts the validation rules into a pure function. This allows the validation behaviour to be tested without opening a GUI window.

The GUI can later call this helper from `create_psm_instance_final_checks()` without changing the visible UI behaviour.
