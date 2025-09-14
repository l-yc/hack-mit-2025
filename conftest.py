import os
import shutil
import tempfile
import pytest


@pytest.fixture()
def temp_uploads_dir(monkeypatch):
    tmpdir = tempfile.mkdtemp(prefix="uploads_")
    # Ensure nested dirs used by backend exist
    os.makedirs(os.path.join(tmpdir, "cleaned"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "edited"), exist_ok=True)
    monkeypatch.setenv("GCP_PROJECT", os.environ.get("GCP_PROJECT", "test-project"))
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture()
def app_client(temp_uploads_dir):
    # Import after env is set
    import backend

    backend.app.config.update({
        "TESTING": True,
        "UPLOAD_FOLDER": temp_uploads_dir,
    })
    client = backend.app.test_client()
    return client


