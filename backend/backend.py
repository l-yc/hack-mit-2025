import glob
import os
import re
import uuid
import yaml

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from PIL import Image

# Reels engine (import with package-aware fallback)
job_manager = None  # type: ignore
JobRequest = None  # type: ignore
try:  # Prefer relative import when running as a package (python -m backend.backend)
    from .reels_engine import job_manager as _jm  # type: ignore
    from .reels_engine.schemas import JobRequest as _JR  # type: ignore
    job_manager = _jm
    JobRequest = _JR
except Exception:
    try:
        from reels_engine import job_manager as _jm2  # type: ignore
        from reels_engine.schemas import JobRequest as _JR2  # type: ignore
        job_manager = _jm2
        JobRequest = _JR2
    except Exception as _e:
        print(f"Reels engine unavailable: {_e}")

try:
    # Load .env if present
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
# Configure CORS
CORS(app, origins=[
    "http://localhost:3000",  # React development server
    "http://localhost:8080",  # Alternative dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    # Add your production frontend URLs here
    "http://3.146.82.97:6741"
])

# Configuration
UPLOAD_FOLDER = "uploads"
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/bmp",
    "image/webp",
}
AGENTS_FOLDER = Path(__file__).parent / "prompts" / "agents"
PROMPTS_FOLDER = Path(__file__).parent / "prompts"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "cleaned"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "edited"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "reels"), exist_ok=True)

# Start minimal reels worker if available
if job_manager is not None:
    try:
        job_manager.start()
    except Exception as _e:
        print(f"Failed to start reels engine: {_e}")


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_image(file_path):
    """Validate that the uploaded file is actually an image"""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving the extension"""
    file_ext = original_filename.rsplit(".", 1)[1].lower()
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{unique_id}.{file_ext}"


@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "message": "Photo Upload API is running",
                "version": "1.0.0",
            }
        ),
        200,
    )


@app.route("/upload", methods=["POST"])
def upload_photo():
    """Upload a single photo"""
    try:
        # Check if file is present in request
        if "photo" not in request.files:
            return jsonify({"error": "No photo file provided"}), 400

        file = request.files["photo"]

        # Check if file was selected
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Validate file extension
        if not allowed_file(file.filename):
            return (
                jsonify(
                    {
                        "error": "Invalid file type",
                        "allowed_types": list(ALLOWED_EXTENSIONS),
                    }
                ),
                400,
            )

        # Validate MIME type
        if file.mimetype not in ALLOWED_MIME_TYPES:
            return (
                jsonify(
                    {
                        "error": "Invalid MIME type",
                        "received": file.mimetype,
                        "allowed_types": list(ALLOWED_MIME_TYPES),
                    }
                ),
                400,
            )

        # Generate unique filename
        original_filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(original_filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)

        # Save file
        file.save(file_path)

        # Validate that it's actually an image
        if not validate_image(file_path):
            os.remove(file_path)  # Clean up invalid file
            return jsonify({"error": "Invalid image file"}), 400

        # Get file size
        file_size = os.path.getsize(file_path)

        return (
            jsonify(
                {
                    "message": "Photo uploaded successfully",
                    "filename": unique_filename,
                    "original_filename": original_filename,
                    "size_bytes": file_size,
                    "upload_time": datetime.now().isoformat(),
                    "file_url": f"/photos/{unique_filename}",
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route("/upload/multiple", methods=["POST"])
def upload_multiple_photos():
    """Upload multiple photos at once"""
    try:
        if "photos" not in request.files:
            return jsonify({"error": "No photos provided"}), 400

        files = request.files.getlist("photos")

        if not files:
            return jsonify({"error": "No files selected"}), 400

        uploaded_files = []
        errors = []

        for i, file in enumerate(files):
            try:
                if file.filename == "":
                    errors.append(f"File {i+1}: No filename")
                    continue

                if not allowed_file(file.filename):
                    errors.append(f"File {i+1}: Invalid file type")
                    continue

                if file.mimetype not in ALLOWED_MIME_TYPES:
                    errors.append(f"File {i+1}: Invalid MIME type")
                    continue

                original_filename = secure_filename(file.filename)
                unique_filename = generate_unique_filename(original_filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)

                file.save(file_path)

                if not validate_image(file_path):
                    os.remove(file_path)
                    errors.append(f"File {i+1}: Invalid image file")
                    continue

                file_size = os.path.getsize(file_path)

                uploaded_files.append(
                    {
                        "filename": unique_filename,
                        "original_filename": original_filename,
                        "size_bytes": file_size,
                        "file_url": f"/photos/{unique_filename}",
                    }
                )

            except Exception as e:
                errors.append(f"File {i+1}: {str(e)}")

        return jsonify(
            {
                "message": f"Processed {len(files)} files",
                "uploaded_count": len(uploaded_files),
                "uploaded_files": uploaded_files,
                "errors": errors,
                "upload_time": datetime.now().isoformat(),
            }
        ), (201 if uploaded_files else 400)

    except Exception as e:
        return jsonify({"error": f"Multiple upload failed: {str(e)}"}), 500


@app.route("/photos/<path:filename>", methods=["GET"])
def get_photo(filename):
    """Serve uploaded photos"""
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except FileNotFoundError:
        return jsonify({"error": "Photo not found"}), 404


@app.route("/videos/upload", methods=["POST"])
def upload_video():
    """Upload mp4/mov video into uploads/ and return its path for reels input."""
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    allowed_ext = {"mp4", "mov", "m4v"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_ext:
        return jsonify({"error": "Unsupported video type", "allowed": list(allowed_ext)}), 400
    original_filename = secure_filename(file.filename)
    unique_filename = generate_unique_filename(original_filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(path)
    return jsonify({
        "message": "Video uploaded",
        "filename": unique_filename,
        "video_url": path.replace("\\", "/")
    }), 201


@app.route("/photos", methods=["GET"])
def list_photos():
    """List all uploaded photos"""
    try:
        photos = []
        for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                photos.append(
                    {
                        "filename": filename,
                        "size_bytes": stat.st_size,
                        "modified_time": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "file_url": f"/photos/{filename}",
                    }
                )

        return (
            jsonify(
                {
                    "photos": sorted(
                        photos, key=lambda x: x["modified_time"], reverse=True
                    ),
                    "total_count": len(photos),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to list photos: {str(e)}"}), 500


@app.route("/photos/<path:filename>", methods=["DELETE"])
def delete_photo(filename):
    """Delete a specific photo"""
    try:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        if not os.path.exists(file_path):
            return jsonify({"error": "Photo not found"}), 404

        os.remove(file_path)

        return (
            jsonify({"message": "Photo deleted successfully", "filename": filename}),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to delete photo: {str(e)}"}), 500


@app.errorhandler(413)
def too_large(e):
    return (
        jsonify(
            {"error": "File too large", "max_size_mb": MAX_FILE_SIZE / (1024 * 1024)}
        ),
        413,
    )


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


@app.route("/images/cleanup", methods=["POST"])
def images_cleanup():
    """Run initial cleanup sweep on an uploaded image.

    Accepts either a multipart form with file field 'photo' or JSON with {'filename': '...'}
    pointing to an image already present in uploads/.
    """
    try:
        from image_editor import cleanup_image
    except Exception as e:
        return jsonify({"error": f"Imagen integration unavailable: {str(e)}"}), 500

    try:
        input_path = None

        if "photo" in request.files:
            file = request.files["photo"]
            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400
            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type", "allowed_types": list(ALLOWED_EXTENSIONS)}), 400
            if file.mimetype not in ALLOWED_MIME_TYPES:
                return jsonify({"error": "Invalid MIME type", "received": file.mimetype, "allowed_types": list(ALLOWED_MIME_TYPES)}), 400
            original_filename = secure_filename(file.filename)
            unique_filename = generate_unique_filename(original_filename)
            input_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            file.save(input_path)
            if not validate_image(input_path):
                os.remove(input_path)
                return jsonify({"error": "Invalid image file"}), 400
        else:
            data = request.get_json() or {}
            filename = data.get("filename")
            if not filename:
                return jsonify({"error": "Provide multipart 'photo' or JSON {'filename': ...}"}), 400
            input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            if not os.path.exists(input_path):
                return jsonify({"error": f"File not found: {filename}"}), 404
            if not validate_image(input_path):
                return jsonify({"error": "Invalid image file"}), 400

        data = request.form if request.form else (request.get_json() or {})
        prompt = data.get("prompt")
        negative_prompt = data.get("negative_prompt")
        seed = data.get("seed")
        model = data.get("model")
        provider = data.get("provider")
        if isinstance(seed, str) and seed.isdigit():
            seed = int(seed)

        result = cleanup_image(
            input_path=input_path,
            output_dir=os.path.join(app.config["UPLOAD_FOLDER"], "cleaned"),
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            model_name=model,
            provider=provider,
        )

        rel_output = os.path.relpath(result.output_path, start=app.config["UPLOAD_FOLDER"]).replace("\\", "/")
        return (
            jsonify(
                {
                    "message": "Cleanup completed",
                    "input_filename": os.path.basename(result.input_path),
                    "output_filename": os.path.basename(result.output_path),
                    "output_url": f"/photos/{rel_output}",
                    "model": result.model_name,
                    "seed": result.seed,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500


@app.route("/images/edit", methods=["POST"])
def images_edit():
    """Prompt-based editing sweep with optional mask.

    Accepts multipart with fields:
      - 'photo': image to edit (optional if 'filename' JSON provided)
      - 'mask': mask image (white = editable) (optional)
      - 'prompt': required text instruction
    Or JSON: {'filename': '...', 'prompt': '...', 'mask_filename': 'optional'}
    """
    try:
        from image_editor import edit_image_with_prompt
    except Exception as e:
        return jsonify({"error": f"Imagen integration unavailable: {str(e)}"}), 500

    try:
        input_path = None
        mask_path = None
        prompt = None

        if request.files:
            if "photo" in request.files and request.files["photo"].filename:
                photo = request.files["photo"]
                if not allowed_file(photo.filename):
                    return jsonify({"error": "Invalid file type", "allowed_types": list(ALLOWED_EXTENSIONS)}), 400
                if photo.mimetype not in ALLOWED_MIME_TYPES:
                    return jsonify({"error": "Invalid MIME type", "received": photo.mimetype, "allowed_types": list(ALLOWED_MIME_TYPES)}), 400
                original_filename = secure_filename(photo.filename)
                unique_filename = generate_unique_filename(original_filename)
                input_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                photo.save(input_path)
                if not validate_image(input_path):
                    os.remove(input_path)
                    return jsonify({"error": "Invalid image file"}), 400
            if "mask" in request.files and request.files["mask"].filename:
                mask = request.files["mask"]
                if not allowed_file(mask.filename):
                    return jsonify({"error": "Invalid mask file type", "allowed_types": list(ALLOWED_EXTENSIONS)}), 400
                original_mask_name = secure_filename(mask.filename)
                stored_mask = f"mask_{uuid.uuid4().hex[:8]}_{original_mask_name}"
                mask_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_mask)
                mask.save(mask_path)
                if not validate_image(mask_path):
                    os.remove(mask_path)
                    return jsonify({"error": "Invalid mask image file"}), 400
            form = request.form
            prompt = form.get("prompt")
            negative_prompt = form.get("negative_prompt")
            seed = form.get("seed")
            model = form.get("model")
            provider = form.get("provider")
            seed = int(seed) if seed and str(seed).isdigit() else None
        else:
            data = request.get_json() or {}
            filename = data.get("filename")
            prompt = data.get("prompt")
            mask_filename = data.get("mask_filename")
            negative_prompt = data.get("negative_prompt")
            seed = data.get("seed")
            model = data.get("model")
            provider = data.get("provider")
            seed = int(seed) if isinstance(seed, int) or (isinstance(seed, str) and seed.isdigit()) else None
            if filename:
                input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                if not os.path.exists(input_path):
                    return jsonify({"error": f"File not found: {filename}"}), 404
            if mask_filename:
                mask_path = os.path.join(app.config["UPLOAD_FOLDER"], mask_filename)
                if not os.path.exists(mask_path):
                    return jsonify({"error": f"Mask not found: {mask_filename}"}), 404

        if not input_path:
            return jsonify({"error": "No input image provided"}), 400
        if not prompt or not prompt.strip():
            return jsonify({"error": "Prompt is required"}), 400

        result = edit_image_with_prompt(
            input_path=input_path,
            prompt=prompt,
            mask_path=mask_path,
            output_dir=os.path.join(app.config["UPLOAD_FOLDER"], "edited"),
            negative_prompt=negative_prompt,
            seed=seed,
            model_name=model,
            provider=provider,
        )

        rel_output = os.path.relpath(result.output_path, start=app.config["UPLOAD_FOLDER"]).replace("\\", "/")
        return (
            jsonify(
                {
                    "message": "Edit completed",
                    "input_filename": os.path.basename(result.input_path),
                    "output_filename": os.path.basename(result.output_path),
                    "output_url": f"/photos/{rel_output}",
                    "model": result.model_name,
                    "seed": result.seed,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": f"Edit failed: {str(e)}"}), 500


# ------------------ Reels API ------------------
@app.route("/api/reels/jobs", methods=["POST"])
def create_reels_job():
    if 'job_manager' not in globals() or JobRequest is None:
        return jsonify({"error": "Reels engine not available"}), 500

    try:
        data = request.get_json(force=True)
        # Normalize postpass
        postpass = data.get("postpass") or {}
        try:
            from .reels_engine.schemas import Postpass as _PP  # type: ignore
        except Exception:
            try:
                from reels_engine.schemas import Postpass as _PP  # type: ignore
            except Exception:
                _PP = None  # type: ignore
        if _PP is not None and isinstance(postpass, dict):
            postpass_obj = _PP(**{k: v for k, v in postpass.items() if k in {"nano_banana", "tone"}})
        else:
            postpass_obj = postpass

        video_url = data.get("video_url")
        video_urls = data.get("video_urls") or []
        directory = data.get("directory")
        if not video_url and not video_urls and not directory:
            return jsonify({"error": "Provide 'video_url' or 'video_urls' or 'directory'"}), 400

        req = JobRequest(
            video_url=video_url,
            video_urls=video_urls,
            directory=directory,
            mode=data.get("mode", "single"),
            target_duration_sec=float(data.get("target_duration_sec", 15)),
            min_duration_sec=float(data.get("min_duration_sec", 9)),
            max_duration_sec=float(data.get("max_duration_sec", 20)),
            aspect=data.get("aspect", "9:16"),
            speech_mode=bool(data.get("speech_mode", True)),
            music_mode=bool(data.get("music_mode", False)),
            top_k_candidates=int(data.get("top_k_candidates", 3)),
            per_segment_sec=float(data.get("per_segment_sec", 3.0)),
            max_files=int(data.get("max_files", 12)),
            keywords=list(data.get("keywords", [])),
            brand_faces_whitelist=list(data.get("brand_faces_whitelist", [])),
            crop_safe_margin_pct=float(data.get("crop_safe_margin_pct", 0.05)),
            postpass=postpass_obj,  # ignored in minimal MVP
            webhook_url=data.get("webhook_url"),
            music_url=data.get("music_url"),
            music_gain_db=float(data.get("music_gain_db", -8.0)),
            duck_music=bool(data.get("duck_music", True)),
            music_only=bool(data.get("music_only", False)),
        )
        job = job_manager.enqueue(req)
        return jsonify({"job_id": job.id, "status": job.status}), 202
    except Exception as e:
        return jsonify({"error": f"Failed to create job: {e}"}), 400


@app.route("/api/reels/jobs/<job_id>", methods=["GET"])
def get_reels_job(job_id: str):
    if 'job_manager' not in globals():
        return jsonify({"error": "Reels engine not available"}), 500
    job = job_manager.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    resp = {
        "status": job.status,
        "error": job.error,
        "artifacts": {
            "best_reel_mp4": job.artifacts.best_reel_mp4,
            "alt_candidates": job.artifacts.alt_candidates,
            "captions_srt": job.artifacts.captions_srt,
            "timeline_json": job.artifacts.timeline_json,
            "cover_jpg": job.artifacts.cover_jpg,
        },
    }
    return jsonify(resp), 200

def poll(agents: list[Path], files: list[str]) -> dict:
    """Poll agents to rate photos"""
    print(f"Found {len(files)} image files")

    # Check if required environment variables and modules are available
    if not os.environ.get("CLAUDE_API_KEY"):
        raise ValueError("CLAUDE_API_KEY environment variable is required")

    try:
        from prompter import prompt_claude_haiku_with_images
        from templater import partial_render
    except ImportError as e:
        raise ImportError(f"Required modules not found: {e}")

    ratings = {}

    # Check if template file exists
    template_path = os.path.join(PROMPTS_FOLDER, "template.jinja")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")

    template_content = open(template_path).read()

    for agent in agents:
        if not os.path.exists(agent):
            continue

        try:
            response = prompt_claude_haiku_with_images(
                partial_render(
                    partial_render(
                        template_content, {"personality": open(agent).read()}
                    ),
                    context={"post_type": "Instagram Story for a fun philosophy club."},
                ),
                image_paths=files,
                api_key=os.environ["CLAUDE_API_KEY"],
                max_tokens=4096,
                model="claude-3-haiku-20240307",
                stream=False,
            )

            # Extract YAML from code blocks if present
            yaml_content = response
            if "```yaml" in response:
                match = re.search(r"```yaml\s*\n(.*?)\n```", response, re.DOTALL)
                if match:
                    yaml_content = match.group(1)
            elif "```" in response:
                match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
                if match:
                    yaml_content = match.group(1)

            try:
                ratings[agent] = defaultdict(lambda: 0, yaml.safe_load(yaml_content))
            except yaml.YAMLError:
                print(f"Warning: Could not parse YAML from agent {agent}")
                ratings[agent] = defaultdict(lambda: 0)

        except Exception as e:
            print(f"Error processing agent {agent}: {e}")
            ratings[agent] = defaultdict(lambda: 0)

    return ratings


def select_photos_from_directory(
    agents: list[Path], imgs: int = 2, img_dir: str = None
) -> list[Path]:
    """Select top n photos using agent ratings"""
    if img_dir is None:
        img_dir = UPLOAD_FOLDER

    # Match common image extensions
    image_extensions = (
        "*.jpg",
        "*.jpeg",
        "*.png",
        "*.heic",
        "*.gif",
        "*.bmp",
        "*.tiff",
        "*.webp",
    )

    # Collect all images
    files = []
    for ext in image_extensions:
        files.extend(glob.glob(os.path.join(img_dir, ext)))
        # Also check uppercase extensions
        files.extend(glob.glob(os.path.join(img_dir, ext.upper())))

    if not files:
        return []

    try:
        ratings = poll(agents, files)

        score_per_file = sorted(
            [
                (file, sum(ratings[agent].get(file, 0) for agent in agents))
                for file in files
            ],
            key=lambda pair: pair[1],
            reverse=True,
        )

        return [Path(file) for file, score in score_per_file[:imgs]]

    except Exception as e:
        print(f"Error in photo selection: {e}")
        # Fallback: return most recent photos
        files_with_time = [(f, os.path.getmtime(f)) for f in files]
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        return [Path(f[0]) for f in files_with_time[:imgs]]


@app.route("/select", methods=["POST"])
def select_top_photos():
    """Select top n photos using AI agents"""
    try:
        data = request.get_json() or {}

        # Get parameters
        n_photos = data.get("n", 2)
        img_dir = data.get("directory", UPLOAD_FOLDER)
        post_type = data.get("post_type", "Instagram Story for a fun philosophy club.")
        agents = data.get("agents", None)

        if agents is None:
            # Get available agents
            agent_files = glob.glob(os.path.join(AGENTS_FOLDER, "*.md"))
            if not agent_files:
                return jsonify({"error": f"No agent files found in {AGENTS_FOLDER}"}), 404

            agents = [Path(agent) for agent in agent_files]
        else:
            agents = [os.path.join(AGENTS_FOLDER, f"{agent}.md") for agent in agents]

        # Validate parameters
        if not isinstance(n_photos, int) or n_photos < 1:
            return jsonify({"error": 'Parameter "n" must be a positive integer'}), 400

        if n_photos > 50:  # Reasonable limit
            return jsonify({"error": "Maximum 50 photos can be selected at once"}), 400

        # Check if directory exists
        if not os.path.exists(img_dir):
            return jsonify({"error": f"Directory not found: {img_dir}"}), 404

        # Check for required API key
        if not os.environ.get("CLAUDE_API_KEY"):
            return (
                jsonify({"error": "CLAUDE_API_KEY environment variable is required"}),
                500,
            )

        # Select photos
        try:
            selected_photos = select_photos_from_directory(agents, n_photos, img_dir)
        except ImportError as e:
            return (
                jsonify(
                    {
                        "error": "Required modules not available",
                        "details": str(e),
                        "required_modules": ["prompter", "templater"],
                    }
                ),
                500,
            )
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            return jsonify({"error": f"Photo selection failed: {str(e)}"}), 500

        if not selected_photos:
            return (
                jsonify(
                    {"message": "No photos found in directory", "directory": img_dir}
                ),
                404,
            )

        # Format response
        result_photos = []
        for photo_path in selected_photos:
            filename = os.path.basename(photo_path)
            file_size = os.path.getsize(photo_path)
            modified_time = datetime.fromtimestamp(
                os.path.getmtime(photo_path)
            ).isoformat()

            result_photos.append(
                {
                    "filename": filename,
                    "file_path": str(photo_path),
                    "size_bytes": file_size,
                    "modified_time": modified_time,
                    "file_url": (
                        f"/photos/{filename}" if img_dir == UPLOAD_FOLDER else None
                    ),
                }
            )

        return (
            jsonify(
                {
                    "message": f"Selected top {len(result_photos)} photos",
                    "requested_count": n_photos,
                    "selected_count": len(result_photos),
                    "agents_used": len(agents),
                    "directory": img_dir,
                    "post_type": post_type,
                    "selected_photos": result_photos,
                    "selection_time": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Selection failed: {str(e)}"}), 500


@app.route("/agents", methods=["GET"])
def list_agents():
    """List available AI agents"""
    try:
        agent_files = glob.glob(os.path.join(AGENTS_FOLDER, "*.md"))
        agents = []

        for agent_file in agent_files:
            agent_name = os.path.basename(agent_file)
            try:
                with open(agent_file, "r") as f:
                    content = f.read()
                    # Try to extract first line as description
                    first_line = content.split("\n")[0].strip()
                    if first_line.startswith("#"):
                        description = first_line.lstrip("#").strip()
                    else:
                        description = first_line[:100] + (
                            "..." if len(first_line) > 100 else ""
                        )

                agents.append(
                    {"name": agent_name, "path": agent_file, "description": description}
                )
            except Exception as e:
                agents.append(
                    {
                        "name": agent_name,
                        "path": agent_file,
                        "description": f"Error reading file: {e}",
                    }
                )

        return (
            jsonify(
                {
                    "agents": agents,
                    "total_count": len(agents),
                    "agents_folder": str(AGENTS_FOLDER),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to list agents: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6741)
