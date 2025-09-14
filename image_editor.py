import os
import base64
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from io import BytesIO

# Optional Gemini (google-genai) import
try:
    from google import genai as google_genai  # type: ignore
except Exception:
    google_genai = None  # type: ignore

from PIL import Image as PILImage  # type: ignore


DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image-preview")

GENERAL_CLEANUP_PROMPT = (
    "Clean up the photo: remove noise and compression artifacts, fix white balance, enhance sharpness, "
    "improve exposure and contrast, recover natural skin tones and preserve realistic colors and lighting."
)


_vertex_initialized = False


def _ensure_vertex_initialized(project: Optional[str] = None, location: Optional[str] = None) -> None:
    global _vertex_initialized
    if _vertex_initialized:
        return
    if vertexai is None:
        raise ImportError(
            f"google-cloud-aiplatform not available: {_IMPORT_ERROR}. Install and retry."
        )
    project_to_use = project or DEFAULT_PROJECT
    if not project_to_use:
        raise EnvironmentError(
            "Missing GCP project. Set GCP_PROJECT or GOOGLE_CLOUD_PROJECT environment variable."
        )
    location_to_use = location or DEFAULT_LOCATION
    vertexai.init(project=project_to_use, location=location_to_use)
    _vertex_initialized = True


def _get_model(model_name: Optional[str] = None) -> Any:
    _ensure_vertex_initialized()
    # Try provided name, then sensible defaults/fallbacks
    candidates = [
        model_name,
        DEFAULT_MODEL_NAME,
        "imagen-4.0-edit-001",
        "imagen-4.0-generate-001",
        "imagegeneration@002",
    ]
    last_error: Optional[Exception] = None
    for name in candidates:
        if not name:
            continue
        try:
            return ImageGenerationModel.from_pretrained(name)
        except Exception as e:  # pragma: no cover - depends on environment availability
            last_error = e
            continue
    raise RuntimeError(
        f"Failed to load an Imagen model from candidates {candidates}. Last error: {last_error}"
    )


def _should_use_gemini(explicit_provider: Optional[str]) -> bool:
    return True


def _gemini_client() -> Any:
    if google_genai is None:
        raise ImportError(
            "google-genai not installed. Add google-genai to requirements.txt and install."
        )
    api_key = os.environ.get("NANO_BANANA_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Missing Gemini API key. Set NANO_BANANA_KEY or GEMINI_API_KEY."
        )
    return google_genai.Client(api_key=api_key)


def _save_image_bytes_to_file(data: bytes, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = PILImage.open(BytesIO(data))
    img.save(output_path)
    return str(output_path)


def _normalize_gemini_model_name(name: Optional[str]) -> str:
    n = (name or DEFAULT_GEMINI_MODEL).strip()
    return n


def _gemini_generate_image_bytes(
    prompt: str,
    base_image_path: Optional[str] = None,
    mask_path: Optional[str] = None,  # ignored
    model_name: Optional[str] = None,
) -> bytes:
    client = _gemini_client()
    model = _normalize_gemini_model_name(
        model_name or os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-2.5-flash-image-preview"
    )

    contents: list[Any] = [prompt]
    img_handle = None
    if base_image_path:
        try:
            if PILImage is not None:
                img_handle = PILImage.open(base_image_path)
                img_handle.load()
                contents.append(img_handle)
            else:
                img_bytes, mime = _read_image_bytes_and_mime(base_image_path)
                contents.append({"inline_data": {"mime_type": mime, "data": img_bytes}})
        except Exception as e:
            raise RuntimeError(f"Failed to read base image: {e}")

    try:
        resp = client.models.generate_content(model=model, contents=contents)
    except Exception as e:
        raise RuntimeError(f"Gemini generate_content failed: {e}")
    finally:
        if img_handle is not None:
            try:
                img_handle.close()
            except Exception:
                pass

    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", []) or []
        for part in parts:
            inline = getattr(part, "inline_data", None) or (part.get("inline_data") if isinstance(part, dict) else None)
            if inline:
                data = inline.get("data") if isinstance(inline, dict) else getattr(inline, "data", None)
                if isinstance(data, bytes):
                    return data
                if isinstance(data, str):
                    try:
                        return base64.b64decode(data)
                    except Exception:
                        continue
    raise RuntimeError("Gemini did not return an image in inline_data.")


@dataclass
class EditResult:
    input_path: str
    output_path: str
    prompt: str
    model_name: str
    seed: Optional[int]


def _save_vertex_image(img_obj: Any, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Vertex Image object exposes save() and/or .as_bytes()
    if hasattr(img_obj, "save"):
        img_obj.save(str(output_path))
    else:
        data = img_obj.as_bytes() if hasattr(img_obj, "as_bytes") else bytes(img_obj)
        with open(output_path, "wb") as f:
            f.write(data)
    return str(output_path)


def cleanup_image(
    input_path: str,
    output_dir: Optional[str] = None,
    prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    seed: Optional[int] = None,
    negative_prompt: Optional[str] = None,
    provider: Optional[str] = None,
) -> EditResult:
    """
    Perform a global cleanup on the image using Imagen edit without a mask.

    Args:
        input_path: Path to the source image.
        output_dir: Directory where the cleaned image will be written. Defaults to sibling 'uploads/cleaned'.
        prompt: Optional override; otherwise uses a default cleanup instruction.
        model_name: Optional Imagen model name. Defaults to IMAGEN_MODEL env or library default.
        seed: Optional deterministic seed.
        negative_prompt: Optional negative prompt.

    Returns:
        EditResult with output location and metadata.
    """
    instruction = prompt or GENERAL_CLEANUP_PROMPT

    input_path_obj = Path(input_path)
    if output_dir is None:
        # Default next to uploads in a "cleaned" subdir
        output_dir = str(input_path_obj.parent / "cleaned")
    output_dir_path = Path(output_dir)
    output_filename = f"{input_path_obj.stem}_cleaned_{uuid.uuid4().hex[:8]}{input_path_obj.suffix}"
    output_path = output_dir_path / output_filename

    image_bytes = _gemini_generate_image_bytes(
        prompt=instruction,
        base_image_path=input_path,
        model_name=model_name,
    )
    saved_path = _save_image_bytes_to_file(image_bytes, output_path)
    return EditResult(
        input_path=str(input_path_obj),
        output_path=saved_path,
        prompt=instruction,
        model_name=model_name or DEFAULT_GEMINI_MODEL,
        seed=seed,
    )


def edit_image_with_prompt(
    input_path: str,
    prompt: str,
    mask_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    model_name: Optional[str] = None,
    seed: Optional[int] = None,
    negative_prompt: Optional[str] = None,
    provider: Optional[str] = None,
) -> EditResult:
    """
    Prompt-based editing with optional mask for localized edits.

    Args:
        input_path: Path to the source image.
        prompt: Text instruction for the edit.
        mask_path: Optional path to a black/white mask image (white=editable).
        output_dir: Output directory. Defaults to sibling 'uploads/edited'.
        model_name: Optional Imagen model name.
        seed: Optional deterministic seed.
        negative_prompt: Optional negative prompt.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt must be a non-empty string.")
    input_path_obj = Path(input_path)
    if output_dir is None:
        output_dir = str(input_path_obj.parent / "edited")
    output_dir_path = Path(output_dir)
    output_filename = f"{input_path_obj.stem}_edit_{uuid.uuid4().hex[:8]}{input_path_obj.suffix}"
    output_path = output_dir_path / output_filename

    image_bytes = _gemini_generate_image_bytes(
        prompt=prompt,
        base_image_path=input_path,
        model_name=model_name,
    )
    saved_path = _save_image_bytes_to_file(image_bytes, output_path)
    return EditResult(
        input_path=str(input_path_obj),
        output_path=saved_path,
        prompt=prompt,
        model_name=model_name or DEFAULT_GEMINI_MODEL,
        seed=seed,
    )


