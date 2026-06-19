import tempfile
from pathlib import Path

import pytest

from conftest import FakeEntry, FakeListbox, TRANSFORMATION_SOURCE_DIR


@pytest.mark.integration
def test_create_psm_generates_non_empty_xmi(monkeypatch):
    pytest.importorskip("pyecore")

    import MisarParserMain

    psm_ecore = TRANSFORMATION_SOURCE_DIR / "PSM.ecore"
    if not psm_ecore.is_file():
        pytest.skip("TransformationEngineNecessities/source/PSM.ecore is not available.")

    # MiSAR's Python file scanner currently ignores any path containing "/test".
    # Pytest tmp_path commonly contains "/test_*", so this smoke fixture uses
    # a neutral temp folder to exercise the real parser path.
    with tempfile.TemporaryDirectory(prefix="misar_smoke_") as temp_dir:
        workspace = Path(temp_dir)
        project_root = workspace / "simple_fastapi_project"
        service = project_root / "user_service"
        output_dir = workspace / "out"
        service.mkdir(parents=True)
        output_dir.mkdir()

        compose = project_root / "docker-compose.yml"
        compose.write_text("""version: '3.8'
services:
  user_service:
    build: ./user_service
    ports:
      - '8000:8000'
""", encoding="utf-8")

        requirements = service / "requirements.txt"
        requirements.write_text("""fastapi
uvicorn
""", encoding="utf-8")

        (service / "main.py").write_text("""from fastapi import FastAPI
app = FastAPI()

@app.get('/users')
def list_users():
    return []
""", encoding="utf-8")

        monkeypatch.setattr(MisarParserMain.messagebox, "showinfo", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            MisarParserMain.messagebox,
            "showerror",
            lambda *args, **kwargs: pytest.fail("Unexpected parser error: " + " ".join(map(str, args))),
        )

        MisarParserMain.create_psm_instance(
            FakeEntry("simple-fastapi"),
            FakeEntry(str(project_root)),
            FakeEntry(str(psm_ecore)),
            FakeListbox([str(compose)]),
            FakeListbox([]),
            FakeListbox([str(service)]),
            FakeListbox([str(requirements)]),
            FakeListbox([]),
            FakeEntry(str(output_dir)),
        )

        psm_file = output_dir / "simple-fastapi-PSM.xmi"

        assert psm_file.is_file()
        assert psm_file.stat().st_size > 0

        content = psm_file.read_text(encoding="utf-8", errors="ignore")
        assert "RootPSM" in content
        assert "simple-fastapi" in content
        assert "user_service" in content
        assert "/users" in content
