import os
import io
from PIL import Image
import types


def _save_temp_image(tmp_path, name="in.jpg", size=(32, 32)):
    p = tmp_path / name
    img = Image.new("RGB", size, (128, 128, 128))
    img.save(p, format="JPEG")
    return str(p)


def test_cleanup_image_calls_model_and_saves(mocker, tmp_path, monkeypatch):
    # Prepare a temp input image
    input_path = _save_temp_image(tmp_path, "in.jpg")

    # Mock vertex init env
    monkeypatch.setenv("GCP_PROJECT", "test-project")

    # Mock model and Image
    mock_image_cls = mocker.patch("image_editor.Image")
    mock_image_obj = mocker.Mock()
    mock_image_cls.load_from_file.return_value = mock_image_obj

    mock_model_cls = mocker.patch("image_editor.ImageGenerationModel")
    mock_model = mocker.Mock()
    mock_model_cls.from_pretrained.return_value = mock_model

    # Mock returned image object with save()
    mock_generated = mocker.Mock()
    # Ensure save() writes something to disk
    def _save(path):
        Image.new("RGB", (8, 8), (0, 0, 0)).save(path, format="JPEG")
    mock_generated.save.side_effect = _save
    mock_model.edit_image.return_value = [mock_generated]

    from image_editor import cleanup_image

    result = cleanup_image(input_path=input_path, output_dir=str(tmp_path / "out"), prompt="clean")
    assert os.path.exists(result.output_path)
    mock_image_cls.load_from_file.assert_called_once_with(input_path)
    mock_model_cls.from_pretrained.assert_called()
    mock_model.edit_image.assert_called()


def test_edit_image_with_prompt_requires_prompt(mocker, tmp_path, monkeypatch):
    from image_editor import edit_image_with_prompt
    input_path = _save_temp_image(tmp_path, "in.jpg")
    monkeypatch.setenv("GCP_PROJECT", "test-project")

    try:
        edit_image_with_prompt(input_path=input_path, prompt="  ")
        assert False, "Expected ValueError for empty prompt"
    except ValueError:
        pass


def test_edit_image_with_mask_calls_model(mocker, tmp_path, monkeypatch):
    from image_editor import edit_image_with_prompt

    input_path = _save_temp_image(tmp_path, "in.jpg")
    mask_path = _save_temp_image(tmp_path, "mask.png")
    monkeypatch.setenv("GCP_PROJECT", "test-project")

    mock_image_cls = mocker.patch("image_editor.Image")
    mock_image_obj = mocker.Mock()
    mock_mask_obj = mocker.Mock()
    def _lf(path):
        return mock_mask_obj if path.endswith("mask.png") else mock_image_obj
    mock_image_cls.load_from_file.side_effect = _lf

    mock_model_cls = mocker.patch("image_editor.ImageGenerationModel")
    mock_model = mocker.Mock()
    mock_model_cls.from_pretrained.return_value = mock_model
    mock_generated = mocker.Mock()
    def _save2(path):
        Image.new("RGB", (8, 8), (0, 0, 0)).save(path, format="JPEG")
    mock_generated.save.side_effect = _save2
    mock_model.edit_image.return_value = [mock_generated]

    res = edit_image_with_prompt(
        input_path=input_path,
        prompt="add a tree",
        mask_path=mask_path,
        output_dir=str(tmp_path / "out"),
        model_name="imagen-4.0-edit-001",
    )
    assert os.path.exists(res.output_path)
    calls = mock_model.edit_image.call_args.kwargs
    assert "mask" in calls
    assert calls["prompt"] == "add a tree"


