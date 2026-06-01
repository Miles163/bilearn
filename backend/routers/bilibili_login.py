"""
B站网页扫码登录 API
"""
import uuid
import time
import shutil
import threading
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from bilibili_api import login_v2, sync

from services.bilibili import set_session_credential

router = APIRouter(prefix="/api/bilibili/login", tags=["bilibili_login"])
_QR_DIR = Path(__file__).resolve().parent.parent.parent / "temp_qrcodes"

# In-memory login sessions: token -> {"qr": QrCodeLogin, "status": str, "cred": dict|None, "expires": float}
_login_sessions: dict[str, dict] = {}
_lock = threading.Lock()
_CLEANUP_INTERVAL = 120  # clean expired sessions every 2 min


def _cleanup_sessions():
    now = time.time()
    with _lock:
        expired = [k for k, v in _login_sessions.items() if v.get("expires", 0) < now]
        for k in expired:
            del _login_sessions[k]


def _get_or_cleanup():
    _cleanup_sessions()
    if _QR_DIR.exists():
        for f in _QR_DIR.iterdir():
            if f.suffix == ".png" and (time.time() - f.stat().st_mtime) > 300:
                f.unlink(missing_ok=True)
    return _QR_DIR


@router.get("/qrcode")
def generate_qrcode():
    qr = login_v2.QrCodeLogin()
    sync(qr.generate_qrcode())

    token = uuid.uuid4().hex[:16]

    pic = qr.get_qrcode_picture()
    if not pic or not pic.url:
        raise HTTPException(500, "生成二维码失败")

    src = pic.url.replace("file://", "")
    png_bytes = Path(src).read_bytes()
    import base64
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode()

    with _lock:
        _login_sessions[token] = {
            "qr": qr,
            "status": "pending",
            "cred": None,
            "expires": time.time() + 300,
        }

    return {
        "token": token,
        "qr_data_url": data_url,
    }


@router.get("/qrcode/{token}/status")
def poll_status(token: str):
    with _lock:
        session = _login_sessions.get(token)
    if not session:
        raise HTTPException(404, "登录会话已过期")

    qr = session["qr"]
    try:
        sync(qr.check_state())
    except Exception:
        pass

    if qr.has_done():
        cred = qr.get_credential()
        data = {
            "sessdata": cred.sessdata,
            "bili_jct": cred.bili_jct,
            "buvid3": cred.buvid3,
            "dedeuserid": cred.dedeuserid,
        }
        set_session_credential(token, data)
        with _lock:
            session["status"] = "done"
            session["cred"] = data
            session["expires"] = time.time() + 3600  # keep session 1h
        return {"status": "done", "dedeuserid": cred.dedeuserid}

    return {"status": "pending"}


@router.get("/qrcode/{token}/credential")
def get_credential_info(token: str):
    with _lock:
        session = _login_sessions.get(token)
    if not session or session["status"] != "done":
        raise HTTPException(400, "尚未登录")
    return {
        "dedeuserid": session["cred"]["dedeuserid"],
        "logged_in": True,
    }
