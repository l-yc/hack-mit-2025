import glob
import os
import re
import uuid
import yaml

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from PIL import Image

app = Flask(__name__)

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


@app.route("/photos/<filename>", methods=["GET"])
def get_photo(filename):
    """Serve uploaded photos"""
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except FileNotFoundError:
        return jsonify({"error": "Photo not found"}), 404


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


@app.route("/photos/<filename>", methods=["DELETE"])
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

        # Validate parameters
        if not isinstance(n_photos, int) or n_photos < 1:
            return jsonify({"error": 'Parameter "n" must be a positive integer'}), 400

        if n_photos > 50:  # Reasonable limit
            return jsonify({"error": "Maximum 50 photos can be selected at once"}), 400

        # Check if directory exists
        if not os.path.exists(img_dir):
            return jsonify({"error": f"Directory not found: {img_dir}"}), 404

        # Get available agents
        agent_files = glob.glob(os.path.join(AGENTS_FOLDER, "*.md"))
        if not agent_files:
            return jsonify({"error": f"No agent files found in {AGENTS_FOLDER}"}), 404

        agents = [Path(agent) for agent in agent_files]

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
