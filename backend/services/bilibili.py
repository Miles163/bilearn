import os
import json
import time
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from bilibili_api import video, sync, Credential
from bilibili_api.exceptions.ResponseCodeException import ResponseCodeException

_CRED_FILE = Path(__file__).resolve().parent.parent / 'bilearn_credential.json'
_CRED_STORE: dict[str, dict] = {}  # token -> {sessdata, bili_jct, buvid3, dedeuserid}

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def _get_mixin_key(orig: str) -> str:
    return ''.join(orig[i] for i in mixinKeyEncTab if i < len(orig))


def _wbi_sign(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = _get_mixin_key(img_key + sub_key)
    params['wts'] = round(time.time())
    params = dict(sorted(params.items()))
    params = {k: ''.join(filter(lambda c: c not in "!'()*", str(v))) for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    params['w_rid'] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def _get_wbi_keys() -> tuple[str, str]:
    headers = _headers('https://www.bilibili.com/')
    req = urllib.request.Request('https://api.bilibili.com/x/web-interface/nav', headers=headers)
    r = urllib.request.urlopen(req, timeout=10)
    data = json.loads(r.read())
    wbi = data['data']['wbi_img']
    img_key = wbi['img_url'].rsplit('/', 1)[1].split('.')[0]
    sub_key = wbi['sub_url'].rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key


def _headers(referer: str = 'https://www.bilibili.com') -> dict:
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': referer,
    }


def set_session_credential(token: str, data: dict):
    _CRED_STORE[token] = {
        'sessdata': data.get('sessdata', ''),
        'bili_jct': data.get('bili_jct', ''),
        'buvid3': data.get('buvid3', ''),
        'dedeuserid': data.get('dedeuserid', ''),
    }


def get_session_credential(token: str) -> dict | None:
    return _CRED_STORE.get(token)


def remove_session_credential(token: str):
    _CRED_STORE.pop(token, None)


def _get_credential(token: str | None = None) -> Credential | None:
    sessdata = ""
    bili_jct = ""
    buvid3 = ""

    if token and token in _CRED_STORE:
        c = _CRED_STORE[token]
        sessdata = c.get('sessdata', '')
        bili_jct = c.get('bili_jct', '')
        buvid3 = c.get('buvid3', '')

    if not sessdata:
        sessdata = os.environ.get("BILIBILI_SESSDATA", "")
    if not sessdata and _CRED_FILE.exists():
        try:
            data = json.loads(_CRED_FILE.read_text(encoding='utf-8'))
            sessdata = data.get('sessdata', '')
            if not bili_jct:
                bili_jct = data.get('bili_jct', '')
            if not buvid3:
                buvid3 = data.get('buvid3', '')
        except Exception:
            pass

    if sessdata:
        if not bili_jct:
            bili_jct = os.environ.get("BILIBILI_BILI_JCT", "")
        if not buvid3:
            buvid3 = os.environ.get("BILIBILI_BUVID3", "")
        return Credential(sessdata=sessdata, bili_jct=bili_jct, buvid3=buvid3)
    return None


def _build_cookie_string(cred: Credential | None) -> str:
    parts = []
    if cred:
        if hasattr(cred, 'sessdata') and cred.sessdata:
            parts.append(f'SESSDATA={cred.sessdata}')
        if hasattr(cred, 'bili_jct') and cred.bili_jct:
            parts.append(f'bili_jct={cred.bili_jct}')
        if hasattr(cred, 'buvid3') and cred.buvid3:
            parts.append(f'buvid3={cred.buvid3}')
    buvid3_env = os.environ.get("BILIBILI_BUVID3", "")
    if buvid3_env and not any('buvid3' in p for p in parts):
        parts.append(f'buvid3={buvid3_env}')
    return '; '.join(parts)


def _urllib_get(url: str, headers: dict | None = None, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers=headers or _headers())
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())


def _download_subtitle_json(subtitle_url: str) -> str | None:
    if not subtitle_url:
        return None
    if subtitle_url.startswith('//'):
        subtitle_url = 'https:' + subtitle_url
    try:
        data = _urllib_get(subtitle_url)
        body = data.get('body', [])
        if body:
            return ' '.join(b['content'] for b in body)
    except Exception:
        return None
    return None


# ── public API ──────────────────────────────────────────────────────

def extract_bvid(url: str) -> str:
    if "bilibili.com/video/" in url:
        after = url.split("video/")[1]
        bvid = after.split("/")[0].split("?")[0]
        return bvid
    if "/bangumi/play/ep" in url:
        ep_id = int(url.split("/ep")[1].split("?")[0].split("/")[0])
        from bilibili_api.bangumi import Episode as BangumiEpisode
        ep = BangumiEpisode(epid=ep_id)
        info = sync(ep.get_info())
        return info["bvid"]
    raise ValueError("无效的 B站链接，需包含 bilibili.com/video/ 或 /bangumi/play/ep")


async def _get_video_info(bvid: str, token: str | None = None) -> dict:
    cred = _get_credential(token)
    v = video.Video(bvid=bvid, credential=cred)
    info = await v.get_info()
    pages = info.get("pages", [])
    cid = pages[0].get("cid", 0) if pages else 0
    return {
        "bvid": info["bvid"],
        "title": info["title"],
        "description": info.get("desc", ""),
        "duration": info["duration"],
        "cid": cid,
    }


def get_video_info(bvid: str, token: str | None = None) -> dict:
    try:
        return sync(_get_video_info(bvid, token))
    except ResponseCodeException as e:
        raise ValueError(f"B站 API 错误: {e.msg} (code={e.code})")
    except Exception as e:
        raise ValueError(f"获取视频信息失败: {str(e)}")


def get_subtitle(bvid: str, cid: int = 0, token: str | None = None) -> str:
    """
    Try to fetch subtitles via multiple strategies:
      1. Player WBI v2 API (with credential if available)
      2. Player WBI v2 API (without credential)
      3. bilibili-api get_subtitle (with credential)
      4. Fallback to video title + description
    """
    cred = _get_credential(token)
    base_headers = _headers(f'https://www.bilibili.com/video/{bvid}/')
    cookie_str = _build_cookie_string(cred)
    if cookie_str:
        base_headers['Cookie'] = cookie_str

    # Strategy 1 & 2: Player WBI v2 API
    try:
        img_key, sub_key = _get_wbi_keys()
        if img_key and sub_key:
            params = {'cid': str(cid), 'bvid': bvid}
            params = _wbi_sign(params, img_key, sub_key)
            url = 'https://api.bilibili.com/x/player/wbi/v2?' + urllib.parse.urlencode(params)
            data = _urllib_get(url, base_headers)
            if data.get('code') == 0:
                subs = data.get('data', {}).get('subtitle', {}).get('subtitles', [])
                for s in subs:
                    text = _download_subtitle_json(s.get('subtitle_url', ''))
                    if text:
                        return text
    except Exception:
        pass

    # Strategy 3: bilibili-api get_subtitle (with credential)
    if cred and cid:
        try:
            v = video.Video(bvid=bvid, credential=cred)
            subs_data = sync(v.get_subtitle(cid=cid))
            if isinstance(subs_data, dict):
                for entry in subs_data.get("subtitles", []):
                    url = entry.get("url", "")
                    if url:
                        text = _download_subtitle_json(url)
                        if text:
                            return text
        except Exception:
            pass

    return ""


def get_video_detail(bvid: str) -> dict:
    return get_video_info(bvid)
