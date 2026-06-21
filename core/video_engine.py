#!/usr/bin/env python3
"""
Video Storyboard Engine — API-ready video processing core.

Adapted from the original video-storyboard skill (v2.1) for the AI Skills Hub project.

Features:
  1. Local video + online video URL support (yt-dlp download, whitelist check)
  2. Auto-install ffmpeg / yt-dlp
  3. Video info retrieval (duration / resolution / fps / orientation)
  4. Smart scene detection + key scene filtering (long video optimisation)
  5. Keyframe extraction (scene-based / uniform / smart-hybrid modes)
  6. Speech recognition via Whisper (optional, requires openai-whisper)
  7. Structured metadata generation (dict, not file)
  8. FCPXML export (Final Cut Pro)

Security hardening:
  - URL whitelist validation
  - Path traversal prevention
  - Download size limit (default 2 GB)
  - FCPXML XML escaping
  - subprocess list-mode + strict timeouts
  - pip install limited to whitelisted package names

Public API:
  process_video_api(...) -> dict   — unified entry point, returns JSON-serialisable result
  get_video_info(path)   -> dict   — video metadata only
  check_ffmpeg() / check_whisper() — environment probes
"""

import os
import sys
import json
import subprocess
import re
import tempfile
import shutil
import base64
from pathlib import Path
from html import escape as xml_escape
from typing import Optional, Dict, Any, List

# ============================================================
# Security constants
# ============================================================

ALLOWED_DOMAINS = [
    "youtube.com", "www.youtube.com", "youtu.be",
    "bilibili.com", "www.bilibili.com",
    "vimeo.com", "www.vimeo.com",
    "tiktok.com", "www.tiktok.com",
    "douyin.com", "v.douyin.com", "www.douyin.com",
    "dailymotion.com", "www.dailymotion.com",
    "twitch.tv", "www.twitch.tv",
]

MAX_DOWNLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB

ALLOWED_PIP_PACKAGES = {"yt-dlp", "openai-whisper"}


# ============================================================
# Security utilities
# ============================================================

def validate_url(url: str) -> str:
    """Validate URL format and domain whitelist."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL cannot be empty")

    if not re.match(r'^https?://', url):
        raise ValueError("URL must start with http:// or https://")

    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname
    except Exception:
        raise ValueError("Invalid URL format")

    if not domain:
        raise ValueError("URL is missing hostname")

    if domain not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain '{domain}' is not in the allowed list. "
            f"Supported: {', '.join(sorted(set(ALLOWED_DOMAINS)))}"
        )

    return url


def sanitize_path(path: str, base_dir: Optional[str] = None) -> str:
    """Prevent path traversal attacks."""
    abs_path = os.path.abspath(path)

    if ".." in Path(abs_path).parts:
        raise ValueError(f"Path contains illegal parent reference: {path}")

    if base_dir:
        base_abs = os.path.abspath(base_dir)
        if not abs_path.startswith(base_abs):
            raise ValueError(f"Path is outside the allowed directory: {path}")

    return abs_path


def safe_pip_install(package_name: str) -> bool:
    """Safely install a pip package (whitelisted names only)."""
    if package_name not in ALLOWED_PIP_PACKAGES:
        raise ValueError(f"Package not allowed: {package_name} (whitelist: {ALLOWED_PIP_PACKAGES})")

    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", package_name],
        capture_output=True, text=True, timeout=180
    )
    return r.returncode == 0


def xml_safe(text: Any) -> str:
    """XML-safe escaping."""
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return xml_escape(text)


# ============================================================
# Environment preparation (auto-install)
# ============================================================

def check_ffmpeg() -> bool:
    """Check for ffmpeg; auto-install if missing."""
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Auto-install
    try:
        subprocess.run(["apt-get", "update", "-qq"], capture_output=True, timeout=60)
    except Exception:
        pass

    for install_cmd in [
        ["apt-get", "install", "-y", "-qq", "ffmpeg"],
        ["apk", "add", "--no-cache", "ffmpeg"],
    ]:
        try:
            r = subprocess.run(install_cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                return True
        except Exception:
            continue

    return False


def check_ytdlp() -> bool:
    """Check for yt-dlp; auto-install if missing."""
    try:
        r = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        if safe_pip_install("yt-dlp"):
            return True
    except Exception:
        pass

    return False


def check_whisper() -> bool:
    """Check for openai-whisper; auto-install if missing."""
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        pass

    try:
        if safe_pip_install("openai-whisper"):
            import whisper  # noqa: F401
            return True
    except Exception:
        pass

    return False


# ============================================================
# Online video download
# ============================================================

def is_online_url(path: str) -> bool:
    """Check whether *path* is an allowed online video URL."""
    if not isinstance(path, str):
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(path)
        if parsed.scheme not in ("http", "https"):
            return False
        return parsed.hostname in ALLOWED_DOMAINS
    except Exception:
        return False


def download_online_video(url: str, output_dir: str, max_size: int = MAX_DOWNLOAD_SIZE) -> str:
    """Download an online video via yt-dlp (with size limit)."""
    validate_url(url)

    if not check_ytdlp():
        raise RuntimeError("yt-dlp is not available and could not be installed")

    output_template = os.path.join(output_dir, "downloaded_video.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", f"best[filesize<{max_size}]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        url
    ]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        err_msg = r.stderr[:300] if r.stderr else "unknown error"
        raise RuntimeError(f"Download failed: {err_msg}")

    for ext in ["mp4", "mkv", "webm", "flv"]:
        candidate = os.path.join(output_dir, f"downloaded_video.{ext}")
        if os.path.exists(candidate):
            fsize = os.path.getsize(candidate)
            if fsize > max_size:
                os.remove(candidate)
                raise RuntimeError(
                    f"Downloaded file exceeds size limit "
                    f"({fsize / 1024 / 1024:.0f}MB > {max_size / 1024 / 1024:.0f}MB)"
                )
            return candidate

    raise RuntimeError("Download completed but no video file was found")


# ============================================================
# Video information
# ============================================================

def get_video_info(video_path: str) -> Dict[str, Any]:
    """Retrieve basic video metadata via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"Cannot retrieve video info: {r.stderr[:200]}")

    info = json.loads(r.stdout)
    fmt = info.get("format", {})
    duration = float(fmt.get("duration", 0))

    video_stream = None
    audio_stream = None
    for s in info.get("streams", []):
        if s.get("codec_type") == "video" and video_stream is None:
            video_stream = s
        if s.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = s

    if not video_stream:
        raise RuntimeError("No video stream found")

    w = int(video_stream.get("width", 0))
    h = int(video_stream.get("height", 0))

    fps = 0.0
    fps_str = video_stream.get("r_frame_rate", "0/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        if int(den) > 0:
            fps = int(num) / int(den)

    has_audio = audio_stream is not None

    return {
        "duration": round(duration, 2),
        "width": w,
        "height": h,
        "fps": round(fps, 2),
        "format": fmt.get("format_name", "unknown"),
        "orientation": "landscape" if w >= h else "portrait",
        "aspect_ratio": f"{w}:{h}",
        "has_audio": has_audio,
        "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
    }


# ============================================================
# Scene detection
# ============================================================

def detect_scenes(video_path: str, threshold: float = 0.3) -> List[float]:
    """Detect scene-change timestamps via ffmpeg."""
    threshold = max(0.01, min(1.0, float(threshold)))

    cmd = [
        "ffmpeg", "-i", video_path,
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    scenes = [0.0]
    for line in r.stderr.split("\n"):
        if "pts_time:" in line:
            try:
                pts = float(line.split("pts_time:")[1].split()[0].rstrip(","))
                if 0.1 < pts < 86400:
                    scenes.append(round(pts, 3))
            except (ValueError, IndexError):
                continue

    scenes = sorted(set(scenes))
    # Merge neighbours closer than 0.5 s
    merged = [scenes[0]]
    for s in scenes[1:]:
        if s - merged[-1] >= 0.5:
            merged.append(s)
    return merged


def score_scene_importance(scene_ranges: List[Dict], total_duration: float) -> List[Dict]:
    """Score each scene's importance (for long-video filtering)."""
    n = len(scene_ranges)
    scored = []
    for i, sr in enumerate(scene_ranges):
        score = 0
        dur = sr["duration"]
        if i < 3:
            score += 2
        if i >= n - 2:
            score += 2
        if dur < 2:
            score += 3
        elif 3 <= dur <= 15:
            score += 1
        elif dur > 30:
            score += 1
        scored.append({**sr, "importance_score": score})
    return scored


def select_key_scenes(scored_scenes: List[Dict], max_scenes: int = 20) -> List[Dict]:
    """Select the top-N key scenes by importance score."""
    if len(scored_scenes) <= max_scenes:
        return scored_scenes
    by_score = sorted(scored_scenes, key=lambda x: x["importance_score"], reverse=True)
    selected = by_score[:max_scenes]
    selected.sort(key=lambda x: x["start_time"])
    return selected


# ============================================================
# Keyframe extraction
# ============================================================

def extract_frame(video_path: str, timestamp: float, output_path: str) -> bool:
    """Extract a single frame at *timestamp*."""
    timestamp = max(0.0, float(timestamp))
    cmd = [
        "ffmpeg", "-ss", str(timestamp),
        "-i", video_path,
        "-frames:v", "1", "-q:v", "2", "-y", output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode == 0 and os.path.exists(output_path)


def extract_keyframes_scene(
    video_path: str, output_dir: str, scenes: List[float], video_duration: float
) -> tuple:
    """Scene-based keyframe extraction."""
    frames_dir = os.path.join(output_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    frame_list: List[Dict[str, Any]] = []
    scene_ranges: List[Dict[str, Any]] = []

    for i, start_ts in enumerate(scenes):
        end_ts = scenes[i + 1] if i + 1 < len(scenes) else video_duration
        dur = round(end_ts - start_ts, 3)
        sr = {
            "scene_index": i + 1,
            "start_time": start_ts,
            "end_time": round(end_ts, 3),
            "duration": dur,
        }
        scene_ranges.append(sr)

        fp = os.path.join(frames_dir, f"scene_{i+1:02d}_start.jpg")
        if extract_frame(video_path, start_ts, fp):
            frame_list.append({
                "scene_index": i + 1,
                "timestamp": start_ts,
                "frame_type": "start",
                "file": fp,
            })

        if dur > 8:
            mid_ts = round(start_ts + dur / 2, 3)
            mp = os.path.join(frames_dir, f"scene_{i+1:02d}_mid.jpg")
            if extract_frame(video_path, mid_ts, mp):
                frame_list.append({
                    "scene_index": i + 1,
                    "timestamp": mid_ts,
                    "frame_type": "mid",
                    "file": mp,
                })

        if dur > 15:
            end_safe = round(end_ts - 0.1, 3)
            ep = os.path.join(frames_dir, f"scene_{i+1:02d}_end.jpg")
            if extract_frame(video_path, end_safe, ep):
                frame_list.append({
                    "scene_index": i + 1,
                    "timestamp": end_safe,
                    "frame_type": "end",
                    "file": ep,
                })

    return frame_list, scene_ranges


def extract_keyframes_smart(
    video_path: str, output_dir: str, scenes: List[float],
    video_duration: float, max_scenes: int = 20
) -> tuple:
    """Smart-hybrid mode: score scenes first, then extract keyframes from top-N."""
    all_ranges = []
    for i, start_ts in enumerate(scenes):
        end_ts = scenes[i + 1] if i + 1 < len(scenes) else video_duration
        all_ranges.append({
            "scene_index": i + 1,
            "start_time": start_ts,
            "end_time": round(end_ts, 3),
            "duration": round(end_ts - start_ts, 3),
        })

    scored = score_scene_importance(all_ranges, video_duration)
    key_scenes = select_key_scenes(scored, max_scenes=max_scenes)

    frames_dir = os.path.join(output_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    frame_list: List[Dict[str, Any]] = []
    for sr in key_scenes:
        i = sr["scene_index"] - 1
        start_ts = sr["start_time"]
        dur = sr["duration"]

        fp = os.path.join(frames_dir, f"scene_{i+1:02d}_start.jpg")
        if extract_frame(video_path, start_ts, fp):
            frame_list.append({
                "scene_index": i + 1,
                "timestamp": start_ts,
                "frame_type": "start",
                "file": fp,
                "importance_score": sr["importance_score"],
            })

        if dur > 8:
            mid_ts = round(start_ts + dur / 2, 3)
            mp = os.path.join(frames_dir, f"scene_{i+1:02d}_mid.jpg")
            if extract_frame(video_path, mid_ts, mp):
                frame_list.append({
                    "scene_index": i + 1,
                    "timestamp": mid_ts,
                    "frame_type": "mid",
                    "file": mp,
                    "importance_score": sr["importance_score"],
                })

    return frame_list, scored


def extract_keyframes_uniform(
    video_path: str, output_dir: str, interval: float, video_duration: float
) -> List[Dict[str, Any]]:
    """Uniform-interval keyframe extraction."""
    interval = max(0.5, float(interval))

    frames_dir = os.path.join(output_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    frame_list: List[Dict[str, Any]] = []
    t, idx = 0.0, 0
    while t < video_duration:
        fp = os.path.join(frames_dir, f"frame_{idx:04d}.jpg")
        if extract_frame(video_path, t, fp):
            frame_list.append({
                "frame_index": idx,
                "timestamp": round(t, 3),
                "frame_type": "uniform",
                "file": fp,
            })
        t += interval
        idx += 1
    return frame_list


# ============================================================
# Speech recognition (Whisper) — optional
# ============================================================

def extract_audio(video_path: str, output_dir: str) -> Optional[str]:
    """Extract audio track from video as 16 kHz mono WAV."""
    audio_path = os.path.join(output_dir, "audio.wav")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-y", audio_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode == 0 and os.path.exists(audio_path):
        return audio_path
    return None


def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    model_size: str = "base"
) -> Optional[Dict[str, Any]]:
    """
    Run Whisper speech recognition.

    .. note::
        This is an **optional** feature. It requires ``openai-whisper`` to be
        installed. If the package is missing it will be auto-installed; if
        installation fails the function returns ``None``.
    """
    allowed_models = {"tiny", "base", "small", "medium", "large"}
    if model_size not in allowed_models:
        raise ValueError(
            f"Unsupported Whisper model: {model_size}. Options: {allowed_models}"
        )

    try:
        import whisper
    except ImportError:
        if not check_whisper():
            return None
        import whisper

    model = whisper.load_model(model_size)

    options: Dict[str, Any] = {}
    if language:
        if not re.match(r'^[a-z]{2,3}$', language):
            raise ValueError(f"Invalid language code: {language}")
        options["language"] = language

    result = model.transcribe(audio_path, **options)

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text": seg["text"].strip(),
        })

    return {
        "language": result.get("language", "unknown"),
        "full_text": result.get("text", "").strip(),
        "segments": segments,
    }


# ============================================================
# FCPXML export
# ============================================================

def generate_fcpxml(
    scene_ranges: List[Dict[str, Any]],
    video_info: Dict[str, Any],
    video_name: str,
    output_dir: str,
) -> str:
    """Export a Final Cut Pro XML storyboard file (all text XML-escaped)."""
    fcpxml_path = os.path.join(output_dir, f"{xml_safe(video_name)}_storyboard.fcpxml")

    fps = video_info.get("fps", 24) or 24
    int_fps = int(fps) if fps > 0 else 24
    duration_frames = int(video_info["duration"] * int_fps)

    safe_name = xml_safe(video_name)
    safe_width = int(video_info["width"])
    safe_height = int(video_info["height"])

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE fcpxml>',
        '<fcpxml version="1.9">',
        '  <resources>',
        f'    <format id="r1" name="FFVideoFormat{safe_width}p{int_fps}fps" '
        f'frameDuration="1/{int_fps}s" width="{safe_width}" height="{safe_height}"/>',
        f'    <asset id="r2" name="{safe_name}" hasVideo="1" hasAudio="1">',
        f'      <media-rep kind="original-media" src="file://{safe_name}.mp4"/>',
        '    </asset>',
        '  </resources>',
        '  <library>',
        '    <event name="Storyboard">',
        f'      <project name="{safe_name} - Storyboard">',
        f'        <sequence format="r1" duration="{duration_frames}/{int_fps}s">',
        '          <spine>',
    ]

    for sr in scene_ranges:
        idx = sr["scene_index"]
        start_f = int(sr["start_time"] * int_fps)
        dur_f = int(sr["duration"] * int_fps)
        safe_idx = xml_safe(str(idx))
        xml_parts.append(
            f'            <asset-clip ref="r2" name="Scene{safe_idx}" '
            f'offset="{start_f}/{int_fps}s" duration="{dur_f}/{int_fps}s" '
            f'start="{start_f}/{int_fps}s"/>'
        )

    xml_parts += [
        '          </spine>',
        '        </sequence>',
        '      </project>',
        '    </event>',
        '  </library>',
        '</fcpxml>',
    ]

    with open(fcpxml_path, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_parts))

    return fcpxml_path


# ============================================================
# Metadata generation (in-memory dict)
# ============================================================

def build_metadata(
    video_info: Dict[str, Any],
    scenes: List[float],
    frames: List[Dict[str, Any]],
    mode: str,
    scene_ranges: Optional[List[Dict]] = None,
    scene_scored: Optional[List[Dict]] = None,
    asr_result: Optional[Dict] = None,
    fcpxml_path: Optional[str] = None,
    frame_interval: Optional[float] = None,
    scene_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a structured metadata dict (does NOT write to disk)."""
    meta: Dict[str, Any] = {
        "video_info": video_info,
        "mode": mode,
        "scene_threshold": scene_threshold,
        "total_scenes_detected": len(scenes),
        "keyframes_count": len(frames),
        "keyframes": [
            {k: v for k, v in f.items() if k != "file"} for f in frames
        ],
    }

    if scene_ranges:
        meta["scene_ranges"] = scene_ranges
    if scene_scored:
        meta["scene_scored"] = scene_scored
    if frame_interval is not None:
        meta["frame_interval"] = frame_interval
    if asr_result:
        meta["asr"] = asr_result
    if fcpxml_path:
        meta["fcpxml_path"] = fcpxml_path

    return meta


# ============================================================
# Unified API entry point
# ============================================================

def process_video_api(
    video_path_or_url: str,
    mode: str = "scene",
    scene_threshold: float = 0.3,
    frame_interval: float = 5.0,
    max_scenes: int = 20,
    asr: bool = False,
    whisper_model: str = "base",
    whisper_lang: Optional[str] = None,
    export_fcpxml_flag: bool = False,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified video processing API.

    Accepts a local path or an online URL. Returns a JSON-serialisable dict
    containing video info, scene list, keyframe file paths, metadata, and
    optionally ASR results and FCPXML path.

    Keyframes are saved as JPEG files inside *output_dir*/frames/ and their
    absolute file paths are returned in the ``keyframe_files`` list.

    Parameters
    ----------
    video_path_or_url : str
        Local file path or whitelisted online video URL.
    mode : str
        ``"scene"``, ``"uniform"``, or ``"smart"``.
    scene_threshold : float
        ffmpeg scene-detection threshold (0.01–1.0).
    frame_interval : float
        Interval in seconds for uniform mode.
    max_scenes : int
        Maximum scenes for smart mode.
    asr : bool
        Whether to run Whisper speech recognition.
    whisper_model : str
        Whisper model size (tiny/base/small/medium/large).
    whisper_lang : str | None
        Language hint for Whisper (e.g. ``"zh"``, ``"en"``).
    export_fcpxml_flag : bool
        Whether to export an FCPXML file.
    output_dir : str | None
        Working directory. A temporary directory is created when ``None``.

    Returns
    -------
    dict
        {
            "video_info": {...},
            "scenes": [timestamp, ...],
            "keyframes_count": int,
            "keyframe_files": [path, ...],
            "metadata": {...},
            "asr": {...} | None,
            "fcpxml_path": str | None,
            "output_dir": str,
            "mode": str,
        }
    """
    # --- 0. Environment ---
    if not check_ffmpeg():
        raise RuntimeError("ffmpeg is not available and could not be installed")

    # --- 1. Resolve video source ---
    is_online = is_online_url(video_path_or_url)
    cleanup_temp = False

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="video_api_")
        cleanup_temp = True
    else:
        output_dir = sanitize_path(output_dir)
        os.makedirs(output_dir, exist_ok=True)

    if is_online:
        video_path = download_online_video(video_path_or_url, output_dir)
    else:
        video_path = sanitize_path(video_path_or_url)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if os.path.getsize(video_path) == 0:
            raise RuntimeError("Video file is empty")

    try:
        # --- 2. Video info ---
        video_info = get_video_info(video_path)

        # --- 3. Scene detection ---
        scenes = detect_scenes(video_path, threshold=scene_threshold)

        # --- 4. Keyframe extraction ---
        frame_list: List[Dict[str, Any]] = []
        scene_ranges: Optional[List[Dict]] = None
        scene_scored: Optional[List[Dict]] = None
        actual_mode = mode

        if mode == "smart" and len(scenes) > max_scenes:
            frame_list, scene_scored = extract_keyframes_smart(
                video_path, output_dir, scenes, video_info["duration"], max_scenes
            )
            actual_mode = "smart"
        elif mode == "uniform" or len(scenes) <= 1:
            frame_list = extract_keyframes_uniform(
                video_path, output_dir, frame_interval, video_info["duration"]
            )
            actual_mode = "uniform"
        else:
            frame_list, scene_ranges = extract_keyframes_scene(
                video_path, output_dir, scenes, video_info["duration"]
            )
            actual_mode = "scene"

        # --- 5. Speech recognition (optional) ---
        asr_result: Optional[Dict[str, Any]] = None
        if asr and video_info.get("has_audio"):
            audio_path = extract_audio(video_path, output_dir)
            if audio_path:
                asr_result = transcribe_audio(
                    audio_path,
                    language=whisper_lang,
                    model_size=whisper_model,
                )

        # --- 6. FCPXML export (optional) ---
        fcpxml_path: Optional[str] = None
        if export_fcpxml_flag:
            ranges_for_xml = scene_ranges or scene_scored or []
            if ranges_for_xml:
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                fcpxml_path = generate_fcpxml(
                    ranges_for_xml, video_info, video_name, output_dir
                )

        # --- 7. Build metadata dict ---
        metadata = build_metadata(
            video_info=video_info,
            scenes=scenes,
            frames=frame_list,
            mode=actual_mode,
            scene_ranges=scene_ranges,
            scene_scored=scene_scored,
            asr_result=asr_result,
            fcpxml_path=fcpxml_path,
            frame_interval=frame_interval if actual_mode == "uniform" else None,
            scene_threshold=scene_threshold,
        )

        # --- 8. Collect keyframe file paths ---
        keyframe_files = [f["file"] for f in frame_list if "file" in f]

        return {
            "video_info": video_info,
            "scenes": scenes,
            "keyframes_count": len(frame_list),
            "keyframe_files": keyframe_files,
            "metadata": metadata,
            "asr": asr_result,
            "fcpxml_path": fcpxml_path,
            "output_dir": output_dir,
            "mode": actual_mode,
        }

    except Exception:
        if cleanup_temp:
            shutil.rmtree(output_dir, ignore_errors=True)
        raise
