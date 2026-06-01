import re
import json
import urllib.request
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


def extract_yt_id(url: str) -> str:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError("无效的 YouTube 链接")


LANGS_PREF = ["zh-Hans", "zh-Hant", "zh", "en", "ja", "ko"]


def get_video_info_and_subtitles(url: str) -> dict:
    video_id = extract_yt_id(url)

    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "")
    description = info.get("description", "") or ""
    duration = info.get("duration", 0)

    subtitles = _fetch_with_transcript_api(video_id)
    if not subtitles:
        subtitles = _fetch_with_ytdlp(info)

    return {
        "bvid": video_id,
        "title": title,
        "description": description[:500] if description else "-",
        "duration": duration,
        "cid": 0,
        "subtitles": subtitles,
    }


def _fetch_with_transcript_api(video_id: str) -> list[dict]:
    try:
        api = YouTubeTranscriptApi()
        result = api.fetch(video_id, languages=LANGS_PREF)
        if result and len(result) > 0:
            text = " ".join(s.text for s in result)
            if text and len(text.strip()) > 20:
                return [{"lang": result.language_code or "en", "text": text.strip(), "source": "manual"}]
    except Exception:
        pass

    try:
        api = YouTubeTranscriptApi()
        tl = api.list(video_id)
        for t in tl:
            try:
                tr = t.fetch()
                text = " ".join(s.text for s in tr)
                if text and len(text.strip()) > 20:
                    return [{"lang": t.language_code, "text": text.strip(), "source": "manual"}]
            except Exception:
                continue
    except Exception:
        pass

    return []


def _fetch_with_ytdlp(info: dict) -> list[dict]:
    results = []
    for src_name in ("subtitles", "automatic_captions"):
        src = info.get(src_name, {})
        if not src:
            continue
        for lang in LANGS_PREF:
            if lang not in src:
                continue
            for entry in src[lang]:
                url = entry.get("url", "")
                if not url:
                    continue
                text = _download_subtitle(url)
                if text and len(text.strip()) > 20:
                    results.append({"lang": lang, "text": text.strip(), "source": "auto" if src_name == "automatic_captions" else "manual"})
                    return results
    return results


def _download_subtitle(url: str) -> str | None:
    try:
        resp = urllib.request.urlopen(url, timeout=15)
        raw = resp.read()
        ct = resp.headers.get("Content-Type", "")
        if "json" in ct:
            data = json.loads(raw)
            parts = []
            for event in data.get("events", []):
                for seg in event.get("segs", []):
                    t = seg.get("utf8", "")
                    if t:
                        parts.append(t)
            return " ".join(parts)
        else:
            text = raw.decode("utf-8", errors="replace")
            lines = []
            for line in text.split("\n"):
                line = line.strip()
                if not line or line.startswith("WEBVTT") or line.startswith("NOTE") or "-->" in line:
                    continue
                if re.match(r"^\d", line):
                    continue
                line = re.sub(r"<[^>]+>", "", line)
                if line:
                    lines.append(line)
            return " ".join(lines)
    except Exception:
        return None
