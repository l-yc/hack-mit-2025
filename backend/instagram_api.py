import os
import time
from typing import Dict, Any, List, Optional, Tuple

import httpx


API_VERSION = os.getenv("API_VERSION", "v23.0")


def _need(name: str) -> str:
    v = os.getenv(name)
    if not v or v == "PASTE_YOUR_PAGE_TOKEN":
        raise ValueError(f"{name} is required (set it in env)")
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


def publish_single(*, is_story: bool, media_kind: str, url: str, caption: Optional[str] = None) -> Dict[str, Any]:
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
        # Instagram ignores caption for stories
    else:
        if media_kind != "img":
            raise ValueError("Use publish_video_or_reel for feed videos.")
        data["image_url"] = url
        if caption:
            data["caption"] = caption

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        r = client.post(create_url, data=data)
        j = _api_ok(r, "Create media container failed")
        container_id = j.get("id") or ""
        print(f"Create response: {j}")

        if is_story and media_kind == "video":
            _wait_ready(client, container_id, page_token, timeout_s=300, poll_s=5)
            time.sleep(2)

        r = client.post(
            f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": page_token},
        )
        print("Publish response:", r.text)
        pub = _api_ok(r, "Publish failed")
        media_id = pub.get("id")

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


def publish_video_or_reel(*, url: str, caption: Optional[str], reel: bool, share_to_feed: bool = True, thumb_offset_ms: Optional[int] = None) -> Dict[str, Any]:
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
        r = client.post(f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media", data=data)
        j = _api_ok(r, "Create video container failed")
        container_id = j.get("id") or ""
        print(f"Create response: {j}")

        _wait_ready(client, container_id, page_token, timeout_s=300, poll_s=5)

        r = client.post(
            f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": page_token},
        )
        print("Publish response:", r.text)
        pub = _api_ok(r, "Publish failed")
        media_id = pub.get("id")

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


def publish_carousel_items(items: List[Tuple[str, str]], caption: Optional[str] = None) -> Dict[str, Any]:
    """Publish an image/video (or mixed) carousel (2–10 items). Waits for video children to finish."""
    ig_user_id = _need("IG_USER_ID")
    page_token = _need("PAGE_TOKEN")
    if not (2 <= len(items) <= 10):
        raise ValueError("Carousel requires 2–10 items.")

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        child_ids: List[str] = []

        for kind, url in items:
            kind_l = kind.strip().lower()
            data: Dict[str, str] = {"access_token": page_token, "is_carousel_item": "true"}

            if kind_l == "video":
                data.update({"media_type": "VIDEO", "video_url": url})
            elif kind_l == "img":
                data["image_url"] = url
            else:
                raise ValueError("Each item kind must be 'img' or 'video'.")

            r = client.post(f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media", data=data)
            j = _api_ok(r, "Create child failed")
            cid = j.get("id")
            if not cid:
                raise RuntimeError(f"Child create returned no id: {j}")
            print(f"Child created: {cid} ({kind_l})")

            if kind_l == "video":
                _wait_ready(client, cid, page_token, timeout_s=300, poll_s=5)

            child_ids.append(cid)

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

        r = client.post(
            f"https://graph.facebook.com/{API_VERSION}/{ig_user_id}/media_publish",
            data={"creation_id": parent_id, "access_token": page_token},
        )
        print("Publish response:", r.text)
        pub = _api_ok(r, "Publish failed")
        media_id = pub.get("id")
        if not media_id:
            raise RuntimeError(f"Publish returned no id: {pub}")

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


