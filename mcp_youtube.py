#!/usr/bin/env python3
"""MCP-YouTube - A MCP server wrapper for yt-dlp"""

import asyncio
from pathlib import Path
import json
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP, Context
import subprocess
import os

class UserError(Exception):
    """Error caused by user input"""
    pass

server = FastMCP("mcp-youtube")

# 出力ディレクトリの定義
OUTPUT_DIR = Path("downloads")
VIDEO_DIR = OUTPUT_DIR / "videos"
AUDIO_DIR = OUTPUT_DIR / "audio"
SUBTITLE_DIR = OUTPUT_DIR / "subtitles"
THUMBNAIL_DIR = OUTPUT_DIR / "thumbnails"

def ensure_output_dirs():
    """出力用のディレクトリを作成"""
    for directory in [VIDEO_DIR, AUDIO_DIR, SUBTITLE_DIR, THUMBNAIL_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# 出力テンプレートの更新
def get_output_template(media_type: str) -> str:
    """メディアタイプに応じた出力テンプレートを返す"""
    base_template = "%(title)s [%(id)s]"
    if media_type == "video":
        return str(VIDEO_DIR / f"{base_template}.%(ext)s")
    elif media_type == "audio":
        return str(AUDIO_DIR / f"{base_template}.%(ext)s")
    elif media_type == "subtitle":
        return str(SUBTITLE_DIR / f"{base_template}.%(lang)s.%(ext)s")
    elif media_type == "thumbnail":
        return str(THUMBNAIL_DIR / f"{base_template}.%(ext)s")
    return base_template + ".%(ext)s"

async def _run_yt_dlp(args: List[str], ctx: Optional[Context[Any, Any]] = None) -> str:
    """Execute yt-dlp command and return output"""
    # ディレクトリの作成を確認
    ensure_output_dirs()
    
    base_args = ["yt-dlp", "--no-warnings"]
    
    # Add output template - moved to individual functions
    
    # Combine with user args
    cmd = base_args + args
    
    try:
        # Run yt-dlp command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            if ctx:
                await ctx.error(f"yt-dlp error: {error_msg}")
            raise UserError(f"yt-dlp failed: {error_msg}")
            
        output = stdout.decode().strip()
        if ctx:
            await ctx.info(f"yt-dlp completed successfully: {output}")
            
        return output
        
    except Exception as e:
        if ctx:
            await ctx.error(f"Failed to run yt-dlp: {str(e)}")
        raise UserError(f"Failed to run yt-dlp: {str(e)}")

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
    if "playlist" not in url:
        raise UserError("Please provide a playlist URL.")
        
    args = [
        "--format", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "--playlist-start", str(start),
        "--output", get_output_template("video")
    ]
    
    if end:
        args.extend(["--playlist-end", str(end)])
        
    args.append(url)
    
    output = await _run_yt_dlp(args, ctx)
    return [line for line in output.split("\n") if line.strip()]

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
    args = [
        "--extract-audio",
        "--audio-format", codec,
        "--audio-quality", quality.rstrip("Kk"),
        "--output", get_output_template("audio"),
        url
    ]
    
    return await _run_yt_dlp(args, ctx)

@server.tool(
    name="get_metadata",
    description="Return video metadata in JSON format (no download).",
)
async def get_metadata(
    url: str,
    ctx: Optional[Context[Any, Any]] = None
) -> Dict[str, Any]:
    args = [
        "--dump-json",
        "--no-download",
        url
    ]
    
    output = await _run_yt_dlp(args, ctx)
    return json.loads(output)

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
    args = [
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", lang,
        "--sub-format", "vtt",
        "--output", get_output_template("subtitle"),
    ]
    
    if embed:
        args.append("--embed-subs")
    else:
        args.append("--skip-download")
        
    args.append(url)
    
    return await _run_yt_dlp(args, ctx)

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
    format_spec = f"bestvideo[height<={resolution[:-1]}]+bestaudio/best"
    if quality == "worst":
        format_spec = "worstvideo+worstaudio/worst"
    
    args = [
        "--format", format_spec,
        "--merge-output-format", format,
        "--output", get_output_template("video"),
        url
    ]
    
    return await _run_yt_dlp(args, ctx)

@server.tool(
    name="download_thumbnail",
    description="Download video thumbnail in the highest available quality.",
)
async def download_thumbnail(
    url: str,
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    args = [
        "--write-thumbnail",
        "--skip-download",
        "--convert-thumbnails", "jpg",
        "--output", get_output_template("thumbnail"),
        url
    ]
    
    return await _run_yt_dlp(args, ctx)

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
    args = ["--format", "best"]
    
    if max_filesize is not None:
        args.extend(["--max-filesize", f"{int(max_filesize)}M"])
    
    if max_duration is not None:
        args.extend(["--max-duration", str(int(max_duration * 60))])
    
    args.append(url)
    
    return await _run_yt_dlp(args, ctx)

@server.tool(
    name="resume_download",
    description="Resume a partially downloaded video.",
)
async def resume_download(
    url: str,
    ctx: Optional[Context[Any, Any]] = None
) -> str:
    args = [
        "--continue",
        url
    ]
    
    return await _run_yt_dlp(args, ctx)

def main() -> None:
    server.run(transport="stdio")

if __name__ == "__main__":
    main()
