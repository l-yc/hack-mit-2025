import io


def test_upload_rejects_invalid_type(app_client):
    data = {
        "photo": (io.BytesIO(b"not an image"), "file.txt"),
    }
    resp = app_client.post("/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_cleanup_missing_payload(app_client):
    resp = app_client.post("/images/cleanup", json={})
    assert resp.status_code in (400, 404)


def test_edit_missing_image_and_filename(app_client):
    resp = app_client.post("/images/edit", json={"prompt": "something"})
    assert resp.status_code == 400


