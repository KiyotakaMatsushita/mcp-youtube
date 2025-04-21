#!/usr/bin/env python3
"""MCP-YouTube - A MCP server wrapper for yt-dlp"""

from pathlib import Path
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP, Context
from yt_dlp import YoutubeDL

class UserError(Exception):
    """Error caused by user input"""
    pass

server = FastMCP("mcp-youtube")
OUTTMPL = "%(title)s [%(id)s].%(ext)s"

def _progress_hook(d: Dict[str, Any], ctx: Context) -> None:
    """Log download progress"""
    status = d["status"]
    if status == "downloading":
        if "_percent_str" in d:
            ctx.info("downloading", {
                "progress": d["_percent_str"].strip(),
                "speed": d.get("_speed_str", "N/A"),
                "eta": d.get("_eta_str", "N/A")
            })
    elif status == "finished":
        ctx.info("download_complete", {"filename": d["filename"]})
    elif status == "error":
        ctx.error("download_error", {"error": str(d.get("error", "Unknown error"))})

def _logging_func(msg: Dict[str, Any], ctx: Context) -> None:
    """Forward yt-dlp log messages to MCP logs"""
    if msg.get("type") == "info":
        ctx.info("yt_dlp_info", {"message": msg.get("msg", "")})
    elif msg.get("type") == "warning":
        ctx.warn("yt_dlp_warning", {"message": msg.get("msg", "")})
    elif msg.get("type") == "error":
        ctx.error("yt_dlp_error", {"message": msg.get("msg", "")})

def _run_dl(urls: List[str], ydl_opts: Dict[str, Any], ctx: Context) -> List[str]:
    """Execute download and return list of saved file paths"""
    paths: List[str] = []
    
    # Set base options
    base_opts = {
        "progress_hooks": [lambda d: _progress_hook(d, ctx)],
        "logger": lambda msg: _logging_func(msg, ctx),
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": False,
        "nooverwrites": True,
        "retries": 3,
    }
    ydl_opts.update(base_opts)
    
    with YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            ctx.info("processing_url", {"url": url})
            try:
                # Check video availability and restrictions
                info = ydl.extract_info(url, download=False)
                
                if info.get("duration"):
                    ctx.info("video_info", {
                        "title": info.get("title", "Unknown"),
                        "duration": info.get("duration", 0),
                        "filesize": info.get("filesize", 0),
                        "format": info.get("format", "Unknown"),
                    })
                
                # Check size/duration limits if specified
                if ydl_opts.get("max_duration") and info.get("duration", 0) > ydl_opts["max_duration"]:
                    raise UserError(f"Video duration ({info['duration']} seconds) exceeds limit ({ydl_opts['max_duration']} seconds)")
                
                if ydl_opts.get("max_filesize") and info.get("filesize", 0) > ydl_opts["max_filesize"]:
                    raise UserError(f"File size ({info['filesize']} bytes) exceeds limit ({ydl_opts['max_filesize']} bytes)")
                
                # Proceed with download
                info = ydl.extract_info(url, download=not ydl_opts.get("skip_download"))
                if ydl_opts.get("skip_download"):
                    paths.append(info)
                    continue
                
                path = Path(ydl.prepare_filename(info))
                if ydl_opts.get("merge_output_format"):
                    path = path.with_suffix(f".{ydl_opts['merge_output_format']}")
                paths.append(str(path.resolve()))
                
                ctx.info("file_saved", {
                    "file": str(path),
                    "title": info.get("title", "Unknown"),
                    "format": info.get("format", "Unknown"),
                    "filesize": info.get("filesize", 0),
                    "duration": info.get("duration", 0),
                })
            except Exception as e:
                ctx.error("download_failed", {
                    "url": url,
                    "error": str(e)
                })
                raise UserError(f"Download failed: {str(e)}")
    
    return paths

# 既存: 単一動画ダウンロード（省略）

@server.tool(
    name="download_playlist",
    description="Download a range of videos from a YouTube playlist and return list of saved paths.",
)
def download_playlist(url: str, start: int = 1, end: int | None = None,
                      ctx: Context = None) -> List[str]:
    if "playlist" not in url:
        raise UserError("Please provide a playlist URL.")
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "playliststart": start,
        "playlistend": end,
    }
    return _run_dl([url], ydl_opts, ctx)

@server.tool(
    name="download_audio",
    description="Extract audio from video and save it in specified codec.",
)
def download_audio(url: str, codec: str = "mp3", quality: str = "192K",
                   ctx: Context = None) -> str:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": OUTTMPL,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": codec,
            "preferredquality": quality.rstrip("Kk"),
        }],
    }
    return _run_dl([url], ydl_opts, ctx)[0]

@server.tool(
    name="get_metadata",
    description="Return video metadata in JSON format (no download).",
)
def get_metadata(url: str, ctx: Context = None) -> Dict[str, Any]:
    info = _run_dl([url], {"skip_download": True}, ctx)[0]
    return info  # FastMCP handles dict→JSON conversion

@server.tool(
    name="download_subtitles",
    description="Download subtitles and optionally embed them into the video.",
)
def download_subtitles(url: str, lang: str = "en", embed: bool = False,
                       ctx: Context = None) -> str:
    ydl_opts = {
        "writesubtitles": True,
        "subtitleslangs": [lang],
        "embedsubtitles": embed,
        "skip_download": False,  # Set True if main content not needed
        "outtmpl": OUTTMPL,
    }
    return _run_dl([url], ydl_opts, ctx)[0]

@server.tool(
    name="download_video",
    description="Download a single video with specified quality options.",
)
def download_video(
    url: str,
    quality: str = "best",
    format: str = "mp4",
    resolution: str = "1080p",
    ctx: Context = None
) -> str:
    """
    Download a single video.
    
    Args:
        url: Video URL
        quality: Quality preference ('best', 'worst', or specific like '1080p', '720p')
        format: Output format ('mp4', 'mkv', 'webm')
        resolution: Preferred resolution ('1080p', '720p', '480p', etc.)
    """
    format_spec = f"bestvideo[height<={resolution[:-1]}]+bestaudio/best"
    if quality == "worst":
        format_spec = "worstvideo+worstaudio/worst"
    
    ydl_opts = {
        "format": format_spec,
        "outtmpl": OUTTMPL,
        "merge_output_format": format,
    }
    return _run_dl([url], ydl_opts, ctx)[0]

@server.tool(
    name="download_thumbnail",
    description="Download video thumbnail in the highest available quality.",
)
def download_thumbnail(url: str, ctx: Context = None) -> str:
    """Download video thumbnail."""
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "writethumbnail": True,
        "skip_download": True,
        "postprocessors": [{
            "key": "FFmpegThumbnailsConvertor",
            "format": "jpg",
        }],
    }
    return _run_dl([url], ydl_opts, ctx)[0]

@server.tool(
    name="download_with_limits",
    description="Download video with size and duration limits.",
)
def download_with_limits(
    url: str,
    max_filesize: float = None,  # in MB
    max_duration: float = None,  # in minutes
    ctx: Context = None
) -> str:
    """
    Download video with size and duration restrictions.
    
    Args:
        url: Video URL
        max_filesize: Maximum file size in MB
        max_duration: Maximum duration in minutes
    """
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "format": "best",
    }
    
    if max_filesize:
        ydl_opts["max_filesize"] = max_filesize * 1024 * 1024  # Convert to bytes
    
    if max_duration:
        ydl_opts["max_duration"] = max_duration * 60  # Convert to seconds
    
    return _run_dl([url], ydl_opts, ctx)[0]

@server.tool(
    name="resume_download",
    description="Resume a partially downloaded video.",
)
def resume_download(url: str, ctx: Context = None) -> str:
    """Resume an interrupted download."""
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "format": "best",
        "continuedl": True,
        "nopart": False,
    }
    return _run_dl([url], ydl_opts, ctx)[0]

if __name__ == "__main__":
    server.run()
