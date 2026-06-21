#!/usr/bin/env python3
"""
FastAPI router — Video Storyboard module.

Endpoints
---------
POST   /analyze             — Full video analysis (URL or upload)
GET    /info                — Video metadata only (no processing)
GET    /supported-domains   — List supported online-video domains
GET    /health              — Check ffmpeg / whisper availability
"""

import os
import sys
import json
import shutil
import tempfile
import traceback
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Ensure core is importable
_CORE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core")
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

import video_engine

router = APIRouter()

# ============================================================
# Shared temp directory for downloadable results
# ============================================================
_RESULTS_DIR = os.path.join(tempfile.gettempdir(), "video_api_results")
os.makedirs(_RESULTS_DIR, exist_ok=True)


# ============================================================
# Pydantic models
# ============================================================

class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze when using a URL (JSON body)."""
    video_url: Optional[str] = Field(None, description="Online video URL (whitelisted domains)")
    mode: str = Field("scene", description="Extraction mode: scene / uniform / smart")
    max_scenes: int = Field(20, ge=1, le=200, description="Max scenes for smart mode")
    asr: bool = Field(False, description="Enable Whisper speech recognition")
    whisper_model: str = Field("base", description="Whisper model: tiny/base/small/medium/large")
    whisper_lang: Optional[str] = Field(None, description="Language hint (e.g. zh, en)")
    scene_threshold: float = Field(0.3, ge=0.01, le=1.0, description="Scene detection threshold")
    frame_interval: float = Field(5.0, ge=0.5, le=3600, description="Frame interval (uniform mode)")
    export_fcpxml: bool = Field(False, description="Export FCPXML file")


class VideoInfoRequest(BaseModel):
    """Request body for GET /info."""
    video_url: str = Field(..., description="Online video URL")


# ============================================================
# POST /analyze
# ============================================================

@router.post("/analyze", summary="Full video analysis")
async def analyze_video(
    background_tasks: BackgroundTasks,
    video_url: Optional[str] = Form(None, description="Online video URL"),
    video_file: Optional[UploadFile] = File(None, description="Uploaded video file"),
    mode: str = Form("scene"),
    max_scenes: int = Form(20),
    asr: bool = Form(False),
    whisper_model: str = Form("base"),
    whisper_lang: Optional[str] = Form(None),
    scene_threshold: float = Form(0.3),
    frame_interval: float = Form(5.0),
    export_fcpxml: bool = Form(False),
):
    """
    Analyse a video (online URL **or** uploaded file) and return:
    - video metadata
    - detected scenes
    - keyframe count + file paths
    - full metadata dict
    - ASR results (if enabled)
    - a download URL for the metadata JSON

    Either ``video_url`` **or** ``video_file`` must be provided.
    """
    # --- Validate input ---
    if not video_url and not video_file:
        raise HTTPException(status_code=422, detail="Either video_url or video_file must be provided")
    if video_url and video_file:
        raise HTTPException(status_code=422, detail="Provide video_url OR video_file, not both")

    if mode not in ("scene", "uniform", "smart"):
        raise HTTPException(status_code=422, detail="mode must be one of: scene, uniform, smart")

    # --- Prepare working directory ---
    work_dir = tempfile.mkdtemp(prefix="video_analyze_", dir=_RESULTS_DIR)

    try:
        # --- Resolve video source ---
        if video_url:
            video_source = video_url
            # validate_url is called inside process_video_api -> download_online_video
        else:
            # Save uploaded file
            if not video_file.filename:
                raise HTTPException(status_code=422, detail="Uploaded file has no filename")
            safe_name = os.path.basename(video_file.filename)
            video_path = os.path.join(work_dir, safe_name)
            with open(video_path, "wb") as f:
                shutil.copyfileobj(video_file.file, f)
            if os.path.getsize(video_path) == 0:
                raise HTTPException(status_code=422, detail="Uploaded file is empty")
            video_source = video_path

        # --- Run engine ---
        result = video_engine.process_video_api(
            video_path_or_url=video_source,
            mode=mode,
            scene_threshold=scene_threshold,
            frame_interval=frame_interval,
            max_scenes=max_scenes,
            asr=asr,
            whisper_model=whisper_model,
            whisper_lang=whisper_lang,
            export_fcpxml_flag=export_fcpxml,
            output_dir=work_dir,
        )

        # --- Persist metadata JSON for download ---
        metadata_filename = "metadata.json"
        metadata_path = os.path.join(work_dir, metadata_filename)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(result["metadata"], f, ensure_ascii=False, indent=2)

        download_url = f"/video/download/{os.path.basename(work_dir)}"

        # --- Build response (exclude raw keyframe file paths; return relative) ---
        keyframe_files_relative = [
            os.path.relpath(p, work_dir) for p in result.get("keyframe_files", [])
        ]

        response = {
            "video_info": result["video_info"],
            "scenes": result["scenes"],
            "keyframes_count": result["keyframes_count"],
            "keyframe_files": keyframe_files_relative,
            "metadata": result["metadata"],
            "asr": result.get("asr"),
            "fcpxml_path": result.get("fcpxml_path"),
            "mode": result["mode"],
            "output_dir": work_dir,
            "download_url": download_url,
        }

        return response

    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


# ============================================================
# GET /info
# ============================================================

@router.get("/info", summary="Get video metadata only")
async def get_video_info(video_url: str):
    """
    Retrieve metadata for an online video URL (duration, resolution, fps, etc.)
    without performing scene detection or keyframe extraction.
    """
    try:
        video_engine.validate_url(video_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not video_engine.check_ytdlp():
        raise HTTPException(status_code=503, detail="yt-dlp is not available")

    work_dir = tempfile.mkdtemp(prefix="video_info_", dir=_RESULTS_DIR)
    try:
        video_path = video_engine.download_online_video(video_url, work_dir)
        info = video_engine.get_video_info(video_path)
        return {"video_url": video_url, "video_info": info}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get video info: {exc}")
    finally:
        # Clean up downloaded video (keep only the info response)
        shutil.rmtree(work_dir, ignore_errors=True)


# ============================================================
# GET /supported-domains
# ============================================================

@router.get("/supported-domains", summary="List supported online video domains")
async def supported_domains():
    """Return the list of whitelisted online-video domains."""
    return {
        "count": len(video_engine.ALLOWED_DOMAINS),
        "domains": sorted(set(video_engine.ALLOWED_DOMAINS)),
    }


# ============================================================
# GET /health
# ============================================================

@router.get("/health", summary="Check environment dependencies")
async def health():
    """Check ffmpeg and whisper availability."""
    ffmpeg_ok = video_engine.check_ffmpeg()
    ytdlp_ok = video_engine.check_ytdlp()
    whisper_ok = video_engine.check_whisper()

    return {
        "ffmpeg": "available" if ffmpeg_ok else "unavailable",
        "yt-dlp": "available" if ytdlp_ok else "unavailable",
        "whisper": "available" if whisper_ok else "unavailable (optional)",
        "max_download_size_mb": video_engine.MAX_DOWNLOAD_SIZE // (1024 * 1024),
    }


# ============================================================
# GET /download/{task_id} — metadata JSON download
# ============================================================

@router.get("/download/{task_id}", summary="Download metadata JSON")
async def download_metadata(task_id: str):
    """
    Download the metadata.json file generated by a previous /analyze call.
    ``task_id`` is the directory name returned in ``output_dir``.
    """
    # Sanitize task_id to prevent path traversal
    safe_id = os.path.basename(task_id)
    if safe_id != task_id:
        raise HTTPException(status_code=422, detail="Invalid task ID")

    metadata_path = os.path.join(_RESULTS_DIR, safe_id, "metadata.json")
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Metadata file not found (may have been cleaned up)")

    return FileResponse(
        metadata_path,
        media_type="application/json",
        filename="metadata.json",
    )
