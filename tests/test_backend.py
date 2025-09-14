import io
import os
from PIL import Image


def _make_image_bytes(color=(255, 0, 0), size=(64, 64)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_health_check(app_client):
    resp = app_client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


def test_upload_list_get_delete_flow(app_client):
    # Upload
    img_buf = _make_image_bytes()
    resp = app_client.post(
        "/upload",
        data={"photo": (img_buf, "test.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    payload = resp.get_json()
    filename = payload["filename"]

    # List
    resp = app_client.get("/photos")
    assert resp.status_code == 200
    listed = resp.get_json()
    assert listed["total_count"] >= 1

    # Get
    resp = app_client.get(f"/photos/{filename}")
    assert resp.status_code == 200

    # Delete
    resp = app_client.delete(f"/photos/{filename}")
    assert resp.status_code == 200


def test_cleanup_endpoint_with_uploaded_file(app_client, mocker, tmp_path):
    # Mock cleanup_image to avoid calling Vertex
    mock_cleanup = mocker.patch("image_editor.cleanup_image")
    mock_cleanup.return_value = mocker.Mock(
        input_path="/tmp/in.jpg",
        output_path=os.path.join(app_client.application.config["UPLOAD_FOLDER"], "cleaned", "out.jpg"),
        prompt="clean",
        model_name="imagen-4.0-edit-001",
        seed=None,
    )

    img_buf = _make_image_bytes()
    resp = app_client.post(
        "/images/cleanup",
        data={"photo": (img_buf, "to_clean.jpg"), "prompt": "clean"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["message"] == "Cleanup completed"
    assert data["output_url"].startswith("/photos/")
    mock_cleanup.assert_called_once()


def test_edit_endpoint_with_prompt_and_mask(app_client, mocker):
    # Mock edit_image_with_prompt
    mock_edit = mocker.patch("image_editor.edit_image_with_prompt")
    mock_edit.return_value = mocker.Mock(
        input_path="/tmp/in.jpg",
        output_path=os.path.join(app_client.application.config["UPLOAD_FOLDER"], "edited", "out.jpg"),
        prompt="add a sun",
        model_name="imagen-4.0-edit-001",
        seed=123,
    )

    img_buf = _make_image_bytes()
    mask_buf = _make_image_bytes(color=(0, 0, 0))
    resp = app_client.post(
        "/images/edit",
        data={
            "photo": (img_buf, "to_edit.jpg"),
            "mask": (mask_buf, "mask.png"),
            "prompt": "add a sun",
            "seed": "123",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["message"] == "Edit completed"
    assert data["seed"] == 123
    mock_edit.assert_called_once()


def test_edit_endpoint_requires_prompt(app_client):
    img_buf = _make_image_bytes()
    resp = app_client.post(
        "/images/edit",
        data={"photo": (img_buf, "to_edit.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Prompt is required" in data["error"]


