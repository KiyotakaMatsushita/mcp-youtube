#!/usr/bin/env python3
"""MCP-YouTube - A MCP server wrapper for yt-dlp"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context
from yt_dlp import YoutubeDL

class UserError(Exception):
    """Error caused by user input"""
    pass

server = FastMCP("mcp-youtube")
OUTTMPL = "%(title)s [%(id)s].%(ext)s"

async def _progress_hook(d: Dict[str, Any], ctx: Context[Any, Any]) -> None:
    """Log download progress"""
    status = d["status"]
    if status == "downloading":
        if "_percent_str" in d:
            await ctx.info(
                f"Downloading: {d['_percent_str'].strip()} Speed: {d.get('_speed_str', 'N/A')} ETA: {d.get('_eta_str', 'N/A')}"
            )
    elif status == "finished":
        await ctx.info(f"Download complete: {d['filename']}")
    elif status == "error":
        await ctx.error(f"Download error: {d.get('error', 'Unknown error')}")

async def _logging_func(msg: Dict[str, Any], ctx: Context[Any, Any]) -> None:
    """Forward yt-dlp log messages to MCP logs"""
    message = msg.get("msg", "")
    if msg.get("type") == "info":
        await ctx.info(f"yt-dlp: {message}")
    elif msg.get("type") == "warning":
        await ctx.info(f"yt-dlp warning: {message}")
    elif msg.get("type") == "error":
        await ctx.error(f"yt-dlp error: {message}")

async def _run_dl(urls: List[str], ydl_opts: Dict[str, Any], ctx: Context[Any, Any]) -> List[str]:
    """Execute download and return list of saved file paths"""
    paths: List[str] = []
    
    # Set base options
    base_opts = {
        "progress_hooks": [lambda d: ctx.info(
            f"Progress: {d.get('_percent_str', 'N/A')} "
            f"Speed: {d.get('_speed_str', 'N/A')} "
            f"ETA: {d.get('_eta_str', 'N/A')}"
        ) if d.get("status") == "downloading" and "_percent_str" in d else None],
        "logger": lambda msg: ctx.info(
            f"yt-dlp: {msg.get('msg', '')}"
        ) if msg.get("type") == "info" else (
            ctx.error(f"yt-dlp error: {msg.get('msg', '')}") if msg.get("type") == "error" else None
        ),
        "quiet": False,
        "no_warnings": False,
        "ignoreerrors": False,
        "nooverwrites": True,
        "retries": 3,
    }
    ydl_opts.update(base_opts)
    
    with YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            await ctx.info(f"Processing URL: {url}")
            try:
                # Check video availability and restrictions
                info = ydl.extract_info(url, download=False)
                
                if info.get("duration"):
                    await ctx.info(
                        f"Video info: {info.get('title', 'Unknown')} "
                        f"Duration: {info.get('duration', 0)}s "
                        f"Size: {info.get('filesize', 0)} bytes "
                        f"Format: {info.get('format', 'Unknown')}"
                    )
                
                # Check size/duration limits if specified
                if ydl_opts.get("max_duration") and info.get("duration", 0) > ydl_opts["max_duration"]:
                    msg = f"Video duration ({info['duration']} seconds) exceeds limit ({ydl_opts['max_duration']} seconds)"
                    await ctx.error(msg)
                    raise UserError(msg)
                
                if ydl_opts.get("max_filesize") and info.get("filesize", 0) > ydl_opts["max_filesize"]:
                    msg = f"File size ({info['filesize']} bytes) exceeds limit ({ydl_opts['max_filesize']} bytes)"
                    await ctx.error(msg)
                    raise UserError(msg)
                
                # Proceed with download
                info = ydl.extract_info(url, download=not ydl_opts.get("skip_download"))
                if ydl_opts.get("skip_download"):
                    paths.append(info)
                    continue
                
                path = Path(ydl.prepare_filename(info))
                if ydl_opts.get("merge_output_format"):
                    path = path.with_suffix(f".{ydl_opts['merge_output_format']}")
                paths.append(str(path.resolve()))
                
                await ctx.info(
                    f"File saved: {path} "
                    f"Title: {info.get('title', 'Unknown')} "
                    f"Format: {info.get('format', 'Unknown')} "
                    f"Size: {info.get('filesize', 0)} bytes "
                    f"Duration: {info.get('duration', 0)}s"
                )
            except Exception as e:
                msg = f"Download failed for {url}: {str(e)}"
                await ctx.error(msg)
                raise UserError(msg)
    
    return paths

@server.tool(
    name="download_playlist",
    description="Download a range of videos from a YouTube playlist and return list of saved paths.",
)
async def download_playlist(
    url: str,
    start: int = 1,
    end: Optional[int] = None,
    ctx: Optional[Context[Any, Any]] = None
) -> List[str]:
    if not ctx:
        raise ValueError("Context is required")
    if "playlist" not in url:
        raise UserError("Please provide a playlist URL.")
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "playliststart": start,
        "playlistend": end,
    }
    return await _run_dl([url], ydl_opts, ctx)

@server.tool(
    name="download_audio",
    description="Extract audio from video and save it in specified codec.",
)
async def download_audio(
    url: str,
    codec: str = "mp3",
    quality: str = "192K",
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    if not ctx:
        raise ValueError("Context is required")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": OUTTMPL,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": codec,
            "preferredquality": quality.rstrip("Kk"),
        }],
    }
    result = await _run_dl([url], ydl_opts, ctx)
    return result[0]

@server.tool(
    name="get_metadata",
    description="Return video metadata in JSON format (no download).",
)
async def get_metadata(
    url: str,
    ctx: Optional[Context[Any, Any]] = None
) -> Dict[str, Any]:
    if not ctx:
        raise ValueError("Context is required")
    result = await _run_dl([url], {"skip_download": True}, ctx)
    info = result[0]
    try:
        return dict(info)  # type: ignore
    except (TypeError, ValueError):
        raise ValueError("Failed to convert metadata to dictionary")

@server.tool(
    name="download_subtitles",
    description="Download subtitles and optionally embed them into the video.",
)
async def download_subtitles(
    url: str,
    lang: str = "en",
    embed: bool = False,
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    if not ctx:
        raise ValueError("Context is required")
    ydl_opts = {
        "writesubtitles": True,
        "subtitleslangs": [lang],
        "embedsubtitles": embed,
        "skip_download": False,
        "outtmpl": OUTTMPL,
    }
    result = await _run_dl([url], ydl_opts, ctx)
    return result[0]

@server.tool(
    name="download_video",
    description="Download a single video with specified quality options.",
)
async def download_video(
    url: str,
    quality: str = "best",
    format: str = "mp4",
    resolution: str = "1080p",
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    if not ctx:
        raise ValueError("Context is required")
    format_spec = f"bestvideo[height<={resolution[:-1]}]+bestaudio/best"
    if quality == "worst":
        format_spec = "worstvideo+worstaudio/worst"
    
    ydl_opts = {
        "format": format_spec,
        "outtmpl": OUTTMPL,
        "merge_output_format": format,
    }
    result = await _run_dl([url], ydl_opts, ctx)
    return result[0]

@server.tool(
    name="download_thumbnail",
    description="Download video thumbnail in the highest available quality.",
)
async def download_thumbnail(
    url: str,
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    if not ctx:
        raise ValueError("Context is required")
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "writethumbnail": True,
        "skip_download": True,
        "postprocessors": [{
            "key": "FFmpegThumbnailsConvertor",
            "format": "jpg",
        }],
    }
    result = await _run_dl([url], ydl_opts, ctx)
    return result[0]

@server.tool(
    name="download_with_limits",
    description="Download video with size and duration limits.",
)
async def download_with_limits(
    url: str,
    max_filesize: Optional[float] = None,  # in MB
    max_duration: Optional[float] = None,  # in minutes
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    if not ctx:
        raise ValueError("Context is required")
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "format": "best",
    }
    
    if max_filesize is not None:
        ydl_opts["max_filesize"] = str(int(max_filesize * 1024 * 1024))  # Convert to bytes
    
    if max_duration is not None:
        ydl_opts["max_duration"] = str(int(max_duration * 60))  # Convert to seconds
    
    result = await _run_dl([url], ydl_opts, ctx)
    return result[0]

@server.tool(
    name="resume_download",
    description="Resume a partially downloaded video.",
)
async def resume_download(
    url: str,
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    if not ctx:
        raise ValueError("Context is required")
    ydl_opts = {
        "outtmpl": OUTTMPL,
        "continuedl": True,
    }
    result = await _run_dl([url], ydl_opts, ctx)
    return result[0]

def main() -> None:
    server.run(transport="stdio")

if __name__ == "__main__":
    main()
