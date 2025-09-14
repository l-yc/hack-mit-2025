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
        from backend.image_editor import cleanup_image
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
        from backend.image_editor import edit_image_with_prompt
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
        print(f"Error in photo selection: {e.__traceback__}")
        # Fallback: return most recent photos
        files_with_time = [(f, os.path.getmtime(f)) for f in files]
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        return [Path(f[0]) for f in files_with_time[:imgs]]


@app.route("/select", methods=["POST"])
def select_top_photos():
    """Select top n photos using AI agents and recommend accompanying songs"""
    try:
        data = request.get_json() or {}
        
        # Get parameters
        n_photos = data.get("n", 2)
        img_dir = data.get("directory", UPLOAD_FOLDER)
        post_type = data.get("post_type", "Instagram Story for a fun philosophy club.")
        agents = data.get("agents", None)
        include_songs = data.get("include_songs", True)
        song_count = data.get("song_count", 3)
        
        if agents is None:
            # Get available agents
            agent_files = glob.glob(os.path.join(AGENTS_FOLDER, "*.md"))
            if not agent_files:
                return jsonify({"error": f"No agent files found in {AGENTS_FOLDER}"}), 404
            agents = [Path(agent) for agent in agent_files]
        else:
            agents = [os.path.join(AGENTS_FOLDER, f"{agent}") for agent in agents]
        
        # Validate parameters
        if not isinstance(n_photos, int) or n_photos < 1:
            return jsonify({"error": 'Parameter "n" must be a positive integer'}), 400
        if n_photos > 50:
            return jsonify({"error": "Maximum 50 photos can be selected at once"}), 400
        if not isinstance(song_count, int) or song_count < 1:
            return jsonify({"error": 'Parameter "song_count" must be a positive integer'}), 400
        if song_count > 10:
            return jsonify({"error": "Maximum 10 songs can be recommended at once"}), 400
        
        # Check if directory exists
        if not os.path.exists(img_dir):
            return jsonify({"error": f"Directory not found: {img_dir}"}), 404
        
        # Check for required API key
        if not os.environ.get("CLAUDE_API_KEY"):
            return (
                jsonify({"error": "CLAUDE_API_KEY environment variable is required"}),
                500,
            )
        
        # Select photos and capture selection context
        try:
            selected_photos, selection_context = select_photos_from_directory_with_context(
                agents, n_photos, img_dir, post_type
            )
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
        
        # Format photo response
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
        
        # Get song recommendations if requested
        recommended_songs = []
        if include_songs:
            try:
                recommended_songs = get_song_recommendations(
                    selected_photos, post_type, agents, selection_context, song_count
                )
            except Exception as e:
                print(f"Song recommendation failed: {str(e)}")
                recommended_songs = []
        
        # Build response
        response_data = {
            "message": f"Selected top {len(result_photos)} photos",
            "requested_count": n_photos,
            "selected_count": len(result_photos),
            "agents_used": len(agents),
            "directory": img_dir,
            "post_type": post_type,
            "selected_photos": result_photos,
            "selection_time": datetime.now().isoformat(),
        }
        
        if recommended_songs:
            response_data["recommended_songs"] = recommended_songs
            response_data["song_count"] = len(recommended_songs)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({"error": f"Selection failed: {str(e)}"}), 500


def select_photos_from_directory_with_context(agents, n_photos, img_dir, post_type):
    """
    Modified version of select_photos_from_directory that also returns 
    the context/reasoning used in selection for song recommendation
    """
    # This function should be your existing photo selection logic
    # but modified to also return the agent reasoning/context
    
    # Placeholder - replace with your actual implementation
    # The key change is returning both selected photos AND the context
    selected_photos = select_photos_from_directory(agents, n_photos, img_dir)
    
    # Capture the selection context - this should include agent descriptions,
    # selection reasoning, identified themes, etc.
    selection_context = {
        "agent_descriptions": load_agent_descriptions(agents),
        "selection_reasoning": "Photos selected based on agent criteria",
        "identified_themes": [],
        "visual_elements": [],
        "post_type": post_type
    }
    
    return selected_photos, selection_context


def load_agent_descriptions(agents):
    """Load and return descriptions of the agents used for selection"""
    descriptions = {}
    for agent_path in agents:
        try:
            with open(agent_path, 'r', encoding='utf-8') as f:
                content = f.read()
                agent_name = Path(agent_path).stem
                descriptions[agent_name] = content
        except Exception as e:
            print(f"Error loading agent {agent_path}: {e}")
            descriptions[Path(agent_path).stem] = "Unable to load agent description"
    return descriptions


def get_song_recommendations(selected_photos, post_type, agents, selection_context, song_count=3):
    """Generate song recommendations that cohere the selected photos"""
    try:
        # Analyze photos in context of their selection
        photo_analysis = analyze_photos_for_musical_coherence(
            selected_photos, selection_context
        )
        
        # Create comprehensive prompt for song recommendation
        song_prompt = create_coherence_based_song_prompt(
            photo_analysis, post_type, selection_context, song_count
        )
        
        # Get recommendations from Claude API
        recommendations = query_claude_for_songs(song_prompt)
        
        # Validate and format recommendations
        formatted_songs = format_song_recommendations(recommendations)
        
        return formatted_songs
        
    except Exception as e:
        raise Exception(f"Failed to get song recommendations: {str(e)}")


def analyze_photos_for_musical_coherence(selected_photos, selection_context):
    """
    Analyze photos with focus on musical coherence based on why they were selected
    """
    try:
        analysis_prompt = f"""
        Analyze these {len(selected_photos)} selected photos for musical accompaniment.
        
        Context of Selection:
        - Post Type: {selection_context['post_type']}
        - Agent Criteria: {list(selection_context['agent_descriptions'].keys())}
        - Selection Reasoning: {selection_context['selection_reasoning']}
        
        For musical coherence, identify:
        1. Unifying visual themes across all photos
        2. Common emotional tone or mood
        3. Energy level and pacing implications
        4. Cultural or temporal context
        5. Target audience based on post type
        6. Narrative flow between images
        7. Aesthetic style (modern, vintage, artistic, etc.)
        
        Focus on elements that create coherence and would benefit from 
        unified musical accompaniment.
        """
        
        # Use your existing photo analysis system with this specific prompt
        coherence_analysis = perform_agent_analysis(
            selected_photos, selection_context['agent_descriptions'], analysis_prompt
        )
        
        return coherence_analysis
        
    except Exception as e:
        return f"Basic analysis: {len(selected_photos)} photos selected for {selection_context['post_type']}"


def create_coherence_based_song_prompt(photo_analysis, post_type, selection_context, song_count):
    """Create a detailed prompt for coherent song recommendations"""
    
    agent_context = ""
    for agent_name, description in selection_context['agent_descriptions'].items():
        # Extract key characteristics from agent descriptions
        agent_summary = extract_agent_musical_preferences(description)
        agent_context += f"- {agent_name}: {agent_summary}\n"
    
    prompt = f"""
    Recommend {song_count} songs that will create COHERENCE for this photo collection.

    PHOTO SELECTION CONTEXT:
    {photo_analysis}
    
    POST DETAILS:
    - Type: {post_type}
    - Number of photos: {len(selection_context.get('selected_photos', []))}
    
    AGENT PERSPECTIVES USED IN SELECTION:
    {agent_context}
    
    COHERENCE REQUIREMENTS:
    The songs should act as a "musical thread" that ties the photos together by:
    1. Reinforcing the common themes identified by the selection agents
    2. Creating emotional continuity across the photo sequence
    3. Matching the intended audience and platform for "{post_type}"
    4. Supporting the narrative or aesthetic flow between images
    
    For each song recommendation, provide:
    {{
        "title": "Song Title",
        "artist": "Artist Name",
        "genre": "Musical Genre",
        "coherence_reason": "Specific explanation of how this song creates coherence between the selected photos",
        "energy_level": 1-10,
        "mood_keywords": ["keyword1", "keyword2"],
        "target_moment": "Which part of the photo sequence this song best accompanies",
        "platform_appropriate": true/false,
        "licensing_note": "Brief note about typical social media usage"
    }}
    
    Prioritize songs that:
    - Are recognizable and emotionally resonant
    - Have appropriate licensing for social media
    - Create thematic unity without overwhelming the visual content
    - Match the sophistication level implied by the agent selection criteria
    
    Return as valid JSON array.
    """
    
    return prompt


def extract_agent_musical_preferences(agent_description):
    """Extract musical preferences or style implications from agent description"""
    # Simple keyword-based extraction - you could make this more sophisticated
    musical_indicators = {
        "aesthetic": "values visual harmony",
        "modern": "contemporary sensibilities", 
        "classical": "traditional/timeless preferences",
        "energetic": "high-energy musical choices",
        "contemplative": "reflective musical taste",
        "social": "mainstream/popular music",
        "artistic": "creative/indie musical preferences",
        "professional": "polished/commercial music",
        "casual": "relaxed musical atmosphere"
    }
    
    description_lower = agent_description.lower()
    found_indicators = []
    
    for keyword, musical_implication in musical_indicators.items():
        if keyword in description_lower:
            found_indicators.append(musical_implication)
    
    return "; ".join(found_indicators) if found_indicators else "general musical taste"


def perform_agent_analysis(selected_photos, agent_descriptions, analysis_prompt):
    """Perform analysis using the agent system with specific prompt"""
    # This should integrate with your existing agent analysis system
    # Placeholder implementation
    try:
        # Use your existing agent analysis pipeline here
        # This is where you'd call your prompter/templater system
        return f"Analysis of {len(selected_photos)} photos using {len(agent_descriptions)} agents for musical coherence"
    except Exception as e:
        return f"Unable to perform detailed analysis: {str(e)}"


def query_claude_for_songs(prompt):
    """Query Claude API for song recommendations"""
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('CLAUDE_API_KEY')}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 3000
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            songs_text = result["content"][0]["text"]
            
            # Extract JSON from the response
            try:
                # Look for JSON array in the response
                start_idx = songs_text.find('[')
                end_idx = songs_text.rfind(']') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = songs_text[start_idx:end_idx]
                    songs = json.loads(json_str)
                    return songs
                else:
                    # Fallback: try to parse entire response as JSON
                    return json.loads(songs_text)
            except json.JSONDecodeError:
                # Fallback: create structured response from text
                return parse_song_text_response(songs_text)
                
        else:
            raise Exception(f"Claude API error: {response.status_code} - {response.text}")
            
    except Exception as e:
        raise Exception(f"Claude query failed: {str(e)}")


def parse_song_text_response(songs_text):
    """Fallback parser for non-JSON song responses"""
    # Simple parser for when Claude doesn't return valid JSON
    songs = []
    lines = songs_text.split('\n')
    
    current_song = {}
    for line in lines:
        line = line.strip()
        if 'title:' in line.lower() or 'song:' in line.lower():
            if current_song:
                songs.append(current_song)
            current_song = {"title": line.split(':', 1)[1].strip()}
        elif 'artist:' in line.lower():
            current_song["artist"] = line.split(':', 1)[1].strip()
        elif 'genre:' in line.lower():
            current_song["genre"] = line.split(':', 1)[1].strip()
        elif 'reason:' in line.lower() or 'coherence:' in line.lower():
            current_song["coherence_reason"] = line.split(':', 1)[1].strip()
    
    if current_song:
        songs.append(current_song)
    
    return songs


def generate_photo_captions(photo_paths, post_type, selection_context):
    """Generate coherent captions for selected photos"""
    try:
        # Create caption generation prompt
        caption_prompt = create_caption_prompt(photo_paths, post_type, selection_context)
        
        # Get captions from Claude API
        captions_response = query_claude_for_captions(caption_prompt)
        
        # Format and validate captions
        formatted_captions = format_photo_captions(captions_response, photo_paths)
        
        return formatted_captions
        
    except Exception as e:
        raise Exception(f"Failed to generate captions: {str(e)}")


def create_caption_prompt(photo_paths, post_type, selection_context):
    """Create a prompt for generating coherent photo captions"""
    
    agent_context = ""
    for agent_name, description in selection_context['agent_descriptions'].items():
        # Extract key characteristics from agent descriptions for captioning
        agent_summary = extract_agent_caption_style(description)
        agent_context += f"- {agent_name}: {agent_summary}\n"
    
    prompt = f"""
    Generate captions for {len(photo_paths)} selected photos that create coherence for this collection.

    CONTEXT:
    - Post Type: {post_type}
    - Selection Agents Used: {list(selection_context['agent_descriptions'].keys())}
    - Selection Reasoning: {selection_context['selection_reasoning']}

    AGENT CAPTION STYLES:
    {agent_context}

    CAPTION REQUIREMENTS:
    1. Each caption should complement the overall narrative of the photo collection
    2. Maintain consistent tone and style across all captions
    3. Reference themes identified by the selection agents
    4. Be appropriate for the platform and audience of "{post_type}"
    5. Create flow and connection between photos when read sequentially
    6. Length: 1-2 sentences per caption, suitable for social media

    PHOTO SEQUENCE:
    {[f"Photo {i+1}: {os.path.basename(path)}" for i, path in enumerate(photo_paths)]}

    For each photo, provide:
    {{
        "filename": "exact_filename.jpg",
        "caption": "The actual caption text",
        "caption_style": "tone/style used",
        "connection_to_theme": "how this caption connects to overall theme",
        "sequence_role": "role in the photo sequence (opening, middle, conclusion, etc.)"
    }}

    Focus on creating captions that:
    - Work individually but flow together as a sequence
    - Reflect the sophistication level of the selection agents
    - Support the intended use case of "{post_type}"
    - Enhance rather than compete with any potential musical accompaniment

    Return as valid JSON array.
    """
    
    return prompt


def extract_agent_caption_style(agent_description):
    """Extract caption style preferences from agent description"""
    style_indicators = {
        "professional": "formal, polished captions",
        "casual": "informal, friendly tone",
        "aesthetic": "artistic, descriptive language", 
        "modern": "contemporary, trendy language",
        "classical": "timeless, elegant phrasing",
        "energetic": "dynamic, action-oriented captions",
        "contemplative": "thoughtful, reflective tone",
        "social": "engaging, shareable content",
        "technical": "precise, informative descriptions",
        "creative": "imaginative, expressive language"
    }
    
    description_lower = agent_description.lower()
    found_styles = []
    
    for keyword, style_implication in style_indicators.items():
        if keyword in description_lower:
            found_styles.append(style_implication)
    
    return "; ".join(found_styles) if found_styles else "adaptable caption style"


def query_claude_for_captions(prompt):
    """Query Claude API for photo captions"""
    try:
        headers = {
            "Authorization": f"Bearer {os.environ.get('CLAUDE_API_KEY')}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            captions_text = result["content"][0]["text"]
            
            # Extract JSON from the response
            try:
                start_idx = captions_text.find('[')
                end_idx = captions_text.rfind(']') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = captions_text[start_idx:end_idx]
                    captions = json.loads(json_str)
                    return captions
                else:
                    return json.loads(captions_text)
            except json.JSONDecodeError:
                return parse_caption_text_response(captions_text)
                
        else:
            raise Exception(f"Claude API error: {response.status_code} - {response.text}")
            
    except Exception as e:
        raise Exception(f"Claude query for captions failed: {str(e)}")


def parse_caption_text_response(captions_text):
    """Fallback parser for non-JSON caption responses"""
    captions = []
    lines = captions_text.split('\n')
    
    current_caption = {}
    for line in lines:
        line = line.strip()
        if 'filename:' in line.lower() or 'photo' in line.lower():
            if current_caption:
                captions.append(current_caption)
            # Extract filename from line
            if 'filename:' in line.lower():
                current_caption = {"filename": line.split(':', 1)[1].strip()}
            else:
                current_caption = {"filename": f"photo_{len(captions) + 1}"}
        elif 'caption:' in line.lower():
            current_caption["caption"] = line.split(':', 1)[1].strip()
        elif 'style:' in line.lower():
            current_caption["caption_style"] = line.split(':', 1)[1].strip()
    
    if current_caption:
        captions.append(current_caption)
    
    return captions


def format_photo_captions(captions_response, photo_paths):
    """Format and validate photo captions"""
    formatted_captions = {}
    
    # Create filename mapping
    filenames = [os.path.basename(path) for path in photo_paths]
    
    for i, caption_data in enumerate(captions_response):
        if isinstance(caption_data, dict):
            filename = caption_data.get("filename", "")
            caption_text = caption_data.get("caption", "")
            
            # Match filename to actual files
            if filename in filenames:
                formatted_captions[filename] = {
                    "text": caption_text,
                    "style": caption_data.get("caption_style", ""),
                    "theme_connection": caption_data.get("connection_to_theme", ""),
                    "sequence_role": caption_data.get("sequence_role", "")
                }
            elif i < len(filenames):
                # Fallback to index matching
                formatted_captions[filenames[i]] = {
                    "text": caption_text,
                    "style": caption_data.get("caption_style", ""),
                    "theme_connection": caption_data.get("connection_to_theme", ""), 
                    "sequence_role": caption_data.get("sequence_role", "")
                }
    
    # Ensure all photos have captions, even if just basic ones
    for filename in filenames:
        if filename not in formatted_captions:
            formatted_captions[filename] = {
                "text": f"Selected for {formatted_captions.get('post_type', 'sharing')}",
                "style": "default",
                "theme_connection": "part of curated collection",
                "sequence_role": "supporting image"
            }
    
    return formatted_captions


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
