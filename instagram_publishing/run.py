#!/usr/bin/env python3
# run.py
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union

# =======================
# Configuration (edit me)
# =======================
POST_KIND  = "reel"   # "carousel" | "video" | "reel" | "image" | "story"
MEDIA_KIND = "video"   # "img" | "video"
URL: Union[str, List[str]] = "https://www.exit109.com/~dnn/clips/RW20seconds_1.mp4"
# Examples:
# POST_KIND = "image";  MEDIA_KIND = "img";   URL = "https://.../photo.jpg"
# POST_KIND = "reel";   MEDIA_KIND = "video"; URL = "https://.../clip.mp4"
# POST_KIND = "carousel"; MEDIA_KIND = "img"; URL = ["https://.../1.jpg","https://.../2.jpg"]
# POST_KIND = "carousel"; MEDIA_KIND = "video"; URL = ["https://.../1.mp4","https://.../2.mp4"]

CAPTION = "Posted via API"
SHARE_REEL_TO_FEED = True  # when POST_KIND == "reel"

# If you need a MIXED carousel, set this and ignore MEDIA_KIND/URL for carousel:
CAROUSEL_ITEMS: Optional[List[Tuple[str, str]]] = [
    ("video", "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"),
    ("img", "https://raw.githubusercontent.com/sethrobles/sample_images/main/new_image.jpg"),
    ("img", "https://raw.githubusercontent.com/sethrobles/sample_images/main/new_image.jpg"),

]
# CAROUSEL_ITEMS: Optional[List[Tuple[str, str]]] = None

# =======================
# Environment & imports
# =======================
try:
    from dotenv import load_dotenv, find_dotenv  # pip install python-dotenv
except ImportError:
    raise SystemExit("Please: pip install python-dotenv httpx")

env_loaded = load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
if not env_loaded:
    load_dotenv(find_dotenv(usecwd=True))

import httpx

API_VERSION = os.getenv("API_VERSION", "v23.0")


# =======================
# Small helpers
# =======================
def _need(name: str) -> str:
    v = os.getenv(name)
    if not v or v == "PASTE_YOUR_PAGE_TOKEN":
        raise ValueError(f"{name} is required (set it in .env or env)")
    return v

def _api_ok(resp: httpx.Response, ctx: str) -> Dict[str, Any]:
    t = resp.text
    try:
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"{ctx} | HTTP {resp.status_code} | body: {t}") from e

def _wait_ready(client: httpx.Client, container_id: str, page_token: str,
                timeout_s: int = 300, poll_s: int = 5) -> None:
    """Poll a media container until status_code == FINISHED."""
    url = f"https://graph.facebook.com/{API_VERSION}/{container_id}"
    params = {"fields": "status_code,status", "access_token": page_token}
    start = time.time()
    last = None
    while True:
        r = client.get(url, params=params)
        j = _api_ok(r, "Check container status failed")
        code = (j.get("status_code") or "").upper()
        desc = j.get("status")
        if code != last:
            print(f"Container {container_id} status: {code} - {desc}")
            last = code
        if code == "FINISHED":
            return
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Container processing failed: {j}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for container to be ready (last={j})")
        time.sleep(poll_s)


# =======================
# Publish primitives
# =======================
def publish_single(
    *,
    is_story: bool,
    media_kind: str,     # "img" | "video"
    url: str,
    caption: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish a single IMAGE (feed) or STORY (image or video)."""
    ig_user_id = _need("IG_USER_ID")
    page_token = _need("PAGE_TOKEN")

    create_url = f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media"
    data: Dict[str, str] = {"access_token": page_token}

    if is_story:
        data["media_type"] = "STORIES"
        if media_kind == "video":
            data["video_url"] = url
        elif media_kind == "img":
            data["image_url"] = url
        else:
            raise ValueError("media_kind must be 'img' or 'video' for stories")
        # (Instagram ignores caption for stories)
    else:
        # feed single: support images only here; use publish_video_or_reel for videos
        if media_kind != "img":
            raise ValueError("Use POST_KIND='video' or 'reel' for feed videos.")
        data["image_url"] = url
        if caption:
            data["caption"] = caption

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        # 1) Create container
        r = client.post(create_url, data=data)
        j = _api_ok(r, "Create media container failed")
        container_id = j.get("id") or ""
        print(f"Create response: {j}")

        # 2) If it's a Story VIDEO, wait until processed before publishing
        if is_story and media_kind == "video":
            _wait_ready(client, container_id, page_token, timeout_s=300, poll_s=5)
            time.sleep(2)  # small grace

        # 3) Publish
        r = client.post(
            f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": page_token},
        )
        print("Publish response:", r.text)
        pub = _api_ok(r, "Publish failed")
        media_id = pub.get("id")

        # 4) Permalink (stories generally won't have one)
        permalink = None
        try:
            r = client.get(
                f"https://graph.facebook.com/{API_VERSION}/{media_id}",
                params={"fields": "id,permalink,media_type,timestamp", "access_token": page_token},
            )
            r.raise_for_status()
            permalink = r.json().get("permalink")
        except Exception:
            pass

    return {"media_id": media_id, "permalink": permalink, "container_id": container_id}

def publish_video_or_reel(
    *,
    url: str,
    caption: Optional[str],
    reel: bool,
    share_to_feed: bool = True,
    thumb_offset_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """Publish a feed VIDEO or a REEL (waits for processing)."""
    ig_user_id = _need("IG_USER_ID")
    page_token = _need("PAGE_TOKEN")

    data: Dict[str, str] = {
        "access_token": page_token,
        "video_url": url,
    }
    if caption:
        data["caption"] = caption
    if reel:
        data["media_type"] = "REELS"
        data["share_to_feed"] = "true" if share_to_feed else "false"
    if thumb_offset_ms is not None:
        data["thumb_offset"] = str(thumb_offset_ms)

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        # 1) Create container
        r = client.post(f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media", data=data)
        j = _api_ok(r, "Create video container failed")
        container_id = j.get("id") or ""
        print(f"Create response: {j}")

        # 2) Wait for processing
        _wait_ready(client, container_id, page_token, timeout_s=300, poll_s=5)

        # 3) Publish
        r = client.post(
            f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": page_token},
        )
        print("Publish response:", r.text)
        pub = _api_ok(r, "Publish failed")
        media_id = pub.get("id")

        # 4) Permalink
        permalink = None
        try:
            r = client.get(
                f"https://graph.facebook.com/{API_VERSION}/{media_id}",
                params={"fields": "id,permalink,media_type,caption,timestamp", "access_token": page_token},
            )
            r.raise_for_status()
            permalink = r.json().get("permalink")
        except Exception:
            pass

    return {"media_id": media_id, "permalink": permalink, "container_id": container_id}

def publish_carousel_items(
    items: List[Tuple[str, str]],  # [("img","https://..."), ("video","https://...")]
    caption: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish an image/video (or mixed) carousel (2–10 items). Waits for video children to finish."""
    ig_user_id = _need("IG_USER_ID")
    page_token = _need("PAGE_TOKEN")
    if not (2 <= len(items) <= 10):
        raise ValueError("Carousel requires 2–10 items.")

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        child_ids: List[str] = []

        # 1) Create children
        for kind, url in items:
            kind_l = kind.strip().lower()
            data: Dict[str, str] = {"access_token": page_token, "is_carousel_item": "true"}

            if kind_l == "video":
                # 🔧 critical: some API versions require media_type=VIDEO for video children
                data.update({"media_type": "VIDEO", "video_url": url})
            elif kind_l == "img":
                data["image_url"] = url
            else:
                raise ValueError("Each item kind must be 'img' or 'video'.")

            # (optional) quick debug
            # print("DEBUG child payload:", data)

            r = client.post(f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media", data=data)
            j = _api_ok(r, "Create child failed")
            cid = j.get("id")
            if not cid:
                raise RuntimeError(f"Child create returned no id: {j}")
            print(f"Child created: {cid} ({kind_l})")

            # Videos need processing; wait until FINISHED
            if kind_l == "video":
                _wait_ready(client, cid, page_token, timeout_s=300, poll_s=5)

            child_ids.append(cid)

        # 2) Create parent
        payload: Dict[str, str] = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "access_token": page_token,
        }
        if caption:
            payload["caption"] = caption

        r = client.post(f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media", data=payload)
        parent = _api_ok(r, "Parent carousel create failed")
        parent_id = parent.get("id")
        if not parent_id:
            raise RuntimeError(f"Parent create returned no id: {parent}")
        print(f"Parent container: {parent_id}")

        # 3) Publish
        r = client.post(
            f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": parent_id, "access_token": page_token},
        )
        print("Publish response:", r.text)
        pub = _api_ok(r, "Publish failed")
        media_id = pub.get("id")
        if not media_id:
            raise RuntimeError(f"Publish returned no id: {pub}")

        # 4) Permalink (best-effort)
        permalink = None
        try:
            r = client.get(
                f"https://graph.facebook.com/{API_VERSION}/{media_id}",
                params={"fields": "id,permalink,media_type,caption,timestamp", "access_token": page_token},
            )
            r.raise_for_status()
            permalink = r.json().get("permalink")
        except Exception:
            pass

    return {"published_id": media_id, "permalink": permalink, "parent_container_id": parent_id, "child_ids": child_ids}


# =======================
# Driver
# =======================
def main():
    kind = POST_KIND.lower()
    media = MEDIA_KIND.lower()

    if kind == "carousel":
        if CAROUSEL_ITEMS:
            items = [(k.lower(), u) for (k, u) in CAROUSEL_ITEMS]
        else:
            # Build items from MEDIA_KIND + URL(s)
            if isinstance(URL, str):
                urls = [u.strip() for u in URL.split(",") if u.strip()]
            else:
                urls = list(URL)
            items = [(media, u) for u in urls]
        res = publish_carousel_items(items, CAPTION)
        print("Published:", res["published_id"])
        print("Permalink:", res.get("permalink"))

    elif kind == "video":
        if not isinstance(URL, str):
            raise SystemExit("Provide a single video URL string for POST_KIND=video.")
        res = publish_video_or_reel(url=URL, caption=CAPTION, reel=False)
        print("Published:", res["media_id"])
        print("Permalink:", res.get("permalink"))

    elif kind == "reel":
        if not isinstance(URL, str):
            raise SystemExit("Provide a single video URL string for POST_KIND=reel.")
        res = publish_video_or_reel(url=URL, caption=CAPTION, reel=True, share_to_feed=SHARE_REEL_TO_FEED)
        print("Published:", res["media_id"])
        print("Permalink:", res.get("permalink"))

    elif kind in ("image", "photo"):
        if not isinstance(URL, str):
            raise SystemExit("Provide a single image URL string for POST_KIND=image.")
        res = publish_single(is_story=False, media_kind="img", url=URL, caption=CAPTION)
        print("Published:", res["media_id"])
        print("Permalink:", res.get("permalink"))

    elif kind == "story":
        if not isinstance(URL, str):
            raise SystemExit("Provide a single URL string for POST_KIND=story.")
        res = publish_single(is_story=True, media_kind=media, url=URL, caption=None)
        if media == "video":
            print("Published (story video):", res["media_id"])
        else:
            print("Published (story image):", res["media_id"])

    else:
        raise SystemExit("Unknown POST_KIND. Use: carousel | video | reel | image | story")

if __name__ == "__main__":
    main()
