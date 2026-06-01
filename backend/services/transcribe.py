import os
import math
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

import shutil

FFMPEG = shutil.which("ffmpeg") or os.environ.get("FFMPEG_PATH", "ffmpeg")

ENGINE = os.environ.get("TRANSCRIBE_ENGINE", "google")

_TMP_DIR = os.path.join(os.path.dirname(__file__), "..", "temp_audio")


def _ensure_ffmpeg():
    if not os.environ.get("PATH", "").startswith(os.path.dirname(FFMPEG)):
        os.environ["PATH"] = os.path.dirname(FFMPEG) + os.pathsep + os.environ.get("PATH", "")


def get_audio_path(url: str, video_id: str) -> str | None:
    """Download audio and return path to m4a file (or existing one)."""
    _ensure_ffmpeg()
    os.makedirs(_TMP_DIR, exist_ok=True)
    # Check for existing m4a
    for f in os.listdir(_TMP_DIR):
        if f.startswith(video_id) and f.endswith(".m4a"):
            return os.path.join(_TMP_DIR, f)
    # Download
    import yt_dlp
    ydl_opts = {
        "quiet": True, "no_warnings": True,
        "format": "bestaudio[ext=m4a]/bestaudio",
        "ffmpeg_location": FFMPEG,
        "outtmpl": os.path.join(_TMP_DIR, f"{video_id}.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    for f in os.listdir(_TMP_DIR):
        if f.startswith(video_id) and f.endswith(".m4a"):
            return os.path.join(_TMP_DIR, f)
    return None


def transcribe_from_youtube(url: str, video_id: str, on_progress: callable = None) -> str:
    _ensure_ffmpeg()

    tmp_dir = os.path.join(os.path.dirname(__file__), "..", "temp_audio")
    os.makedirs(tmp_dir, exist_ok=True)
    wav_path = os.path.join(tmp_dir, f"{video_id}.wav")

    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
        return _transcribe_wav(wav_path, on_progress)

    import yt_dlp
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "ffmpeg_location": FFMPEG,
        "outtmpl": os.path.join(tmp_dir, f"{video_id}.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if os.path.exists(wav_path):
        return _transcribe_wav(wav_path, on_progress)
    return ""


def _transcribe_wav(wav_path: str, on_progress: callable = None) -> str:
    if ENGINE == "whisper":
        return _transcribe_whisper(wav_path, on_progress)
    if ENGINE == "vosk":
        return _transcribe_vosk(wav_path, on_progress)
    return _transcribe_google(wav_path, on_progress)


# ── Google Speech Recognition (fast, online) ──

def _transcribe_google(wav_path: str, on_progress: callable = None) -> str:
    import speech_recognition as sr

    duration = _get_duration(wav_path)
    if duration <= 0:
        return ""

    if duration <= 55:
        return _recognize_google(wav_path) or ""

    chunk_dur = 50
    num_chunks = math.ceil(duration / chunk_dur)
    chunk_paths = []

    for i in range(num_chunks):
        chunk_path = wav_path.replace(".wav", f"_chunk{i}.wav")
        start = i * chunk_dur
        _cut_audio(wav_path, chunk_path, start, min(chunk_dur, duration - start))
        chunk_paths.append(chunk_path)

    results = [None] * num_chunks
    with ThreadPoolExecutor(max_workers=20) as pool:
        fut_map = {pool.submit(_recognize_google, p): i for i, p in enumerate(chunk_paths)}
        for fut in as_completed(fut_map):
            idx = fut_map[fut]
            results[idx] = fut.result()
            if on_progress:
                done = sum(1 for r in results if r is not None)
                on_progress(done / num_chunks)

    for p in chunk_paths:
        try:
            os.remove(p)
        except Exception:
            pass

    return " ".join(t for t in results if t)


def _recognize_google(path: str, langs=("zh-CN", "en-US", "ja-JP")) -> str | None:
    import speech_recognition as sr
    r = sr.Recognizer()
    for lang in langs:
        try:
            with sr.AudioFile(path) as source:
                audio = r.record(source)
            text = r.recognize_google(audio, language=lang)
            if text:
                return text
        except sr.UnknownValueError:
            return None
        except Exception:
            continue
    return None


# ── faster-whisper (offline, higher quality, slower) ──

_whisper_model = None


def _transcribe_whisper(wav_path: str, on_progress: callable = None) -> str:
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        model_dir = os.path.join(os.path.dirname(__file__), "..", "whisper_models")
        os.makedirs(model_dir, exist_ok=True)
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=model_dir)

    segments, info = _whisper_model.transcribe(wav_path, language="zh", beam_size=5)
    texts = []
    for seg in segments:
        texts.append(seg.text.strip())
        if on_progress:
            on_progress(seg.end / info.duration)
    return " ".join(texts)


# ── Vosk (offline, lightweight, good for Chinese) ──

_vosk_model = None


def _transcribe_vosk(wav_path: str, on_progress: callable = None) -> str:
    global _vosk_model
    if _vosk_model is None:
        from vosk import Model as VoskModel
        model_dir = os.path.join(os.path.dirname(__file__), "..", "vosk_models")
        model_path = os.path.join(model_dir, "vosk-model-small-cn-0.22")
        if not os.path.isdir(model_path):
            import zipfile, urllib.request
            os.makedirs(model_dir, exist_ok=True)
            url = "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
            zip_path = os.path.join(model_dir, "model.zip")
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(model_dir)
            os.remove(zip_path)
        _vosk_model = VoskModel(model_path)

    import wave, json
    from vosk import KaldiRecognizer

    wf = wave.open(wav_path, "rb")
    rec = KaldiRecognizer(_vosk_model, wf.getframerate())
    rec.SetWords(True)

    total_frames = wf.getnframes()
    texts = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            if result.get("text"):
                texts.append(result["text"])
        if on_progress and total_frames:
            on_progress(wf.tell() / total_frames)

    final = json.loads(rec.FinalResult())
    if final.get("text"):
        texts.append(final["text"])
    wf.close()
    return " ".join(texts)


# ── Shared helpers ──

def _get_duration(wav_path: str) -> float:
    try:
        result = subprocess.run(
            [FFMPEG, "-i", wav_path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stderr.split("\n"):
            if "Duration" in line:
                parts = line.strip().split(",")[0].split("Duration:")[-1].strip()
                h, m, s = parts.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 0


def _cut_audio(src: str, dst: str, start: float, dur: float):
    subprocess.run(
        [FFMPEG, "-y", "-i", src, "-ss", str(start), "-t", str(dur),
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", dst],
        capture_output=True, timeout=120,
    )


def cleanup_temp(video_id: str):
    tmp_dir = os.path.join(os.path.dirname(__file__), "..", "temp_audio")
    if not os.path.isdir(tmp_dir):
        return
    for f in os.listdir(tmp_dir):
        if f.startswith(video_id):
            try:
                os.remove(os.path.join(tmp_dir, f))
            except Exception:
                pass
