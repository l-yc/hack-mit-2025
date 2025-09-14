# Instagram Publishing: `run.py` Usage Guide

## Overview
`run.py` is a flexible Python script for publishing posts to Instagram using the Graph API. It supports posting single images, videos, stories, reels, and carousels (including mixed image/video carousels).

## Requirements
- Python 3.8+
- Install dependencies:
	```sh
	pip install python-dotenv httpx
	```
- Instagram Graph API access (with a valid IG user ID and page token)

## Environment Variables
Create a `.env` file in the same directory as `run.py` with the following keys:

```
IG_USER_ID=your_instagram_user_id
PAGE_TOKEN=your_long_lived_page_token
API_VERSION=v23.0  # (optional, default is v23.0)
```

## Configuring `run.py`
Edit the configuration section at the top of `run.py`:

- `POST_KIND`: Type of post. One of: `carousel`, `video`, `reel`, `image`, `story`
- `MEDIA_KIND`: For non-mixed carousels, set to `img` or `video` (applies to all items)
- `URL`:
	- For single posts: a string URL to the image or video
	- For carousels: a list of URLs (all images or all videos, unless using `CAROUSEL_ITEMS`)
- `CAPTION`: (Optional) Caption for the post (not used for stories)
- `SHARE_REEL_TO_FEED`: (Optional, for reels) Whether to share the reel to the feed
- `CAROUSEL_ITEMS`: (Optional) List of tuples for mixed carousels, e.g.:
	```python
	CAROUSEL_ITEMS = [
			("img", "https://.../photo1.jpg"),
			("video", "https://.../clip.mp4"),
			("img", "https://.../photo2.jpg"),
	]
	# If set, this overrides MEDIA_KIND and URL for carousels
	```

## Example Configurations
**Single image post:**
```python
POST_KIND = "image"
MEDIA_KIND = "img"
URL = "https://.../photo.jpg"
```

**Carousel of images:**
```python
POST_KIND = "carousel"
MEDIA_KIND = "img"
URL = ["https://.../1.jpg", "https://.../2.jpg"]
```

**Mixed carousel:**
```python
POST_KIND = "carousel"
CAROUSEL_ITEMS = [
		("img", "https://.../1.jpg"),
		("video", "https://.../2.mp4")
]
```

**Reel:**
```python
POST_KIND = "reel"
MEDIA_KIND = "video"
URL = "https://.../clip.mp4"
SHARE_REEL_TO_FEED = True
```

## Running the Script
```sh
python3 run.py
```

## Notes
- For carousels, you must provide 2–10 items.
- For videos, ensure your files meet Instagram's requirements (H.264/AAC, .mp4, correct aspect ratio, etc.).
- The script will print the published media ID and permalink (if available).

---
For more details, see comments in `run.py`.
