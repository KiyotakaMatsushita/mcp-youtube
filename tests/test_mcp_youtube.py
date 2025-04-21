import pathlib
import sys
from typing import Any, Callable, Dict, List, Tuple, Union
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.server.fastmcp import Context

# Add project root to sys.path so that `import mcp_youtube` works when the
# package is not installed (tests run from source checkout).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mcp_youtube


def _make_stub(return_value: Union[List[str], List[Dict[str, Any]]]) -> Tuple[Callable[..., Any], Dict[str, Any]]:
    """Return a stub function that captures its kwargs and returns value."""
    captured: Dict[str, Any] = {}

    async def _stub(urls: List[str], ydl_opts: Dict[str, Any], ctx: Context[Any, Any]) -> List[Any]:
        captured["urls"] = urls
        captured["ydl_opts"] = ydl_opts
        # Simulate the path list expected by callers
        return return_value

    return _stub, captured


@pytest.fixture
def mock_context() -> Context[Any, Any]:
    """Create a mock Context object."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_download_video(monkeypatch: pytest.MonkeyPatch, mock_context: Context[Any, Any]) -> None:
    stub, captured = _make_stub(["/path/to/video.mp4"])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = await mcp_youtube.download_video(
        "https://youtu.be/dummy",
        quality="best",
        format="mp4",
        resolution="720p",
        ctx=mock_context
    )

    assert result == "/path/to/video.mp4"
    assert captured["urls"] == ["https://youtu.be/dummy"]
    assert captured["ydl_opts"]["merge_output_format"] == "mp4"
    # Ensure format string reflects resolution cap (720p -> height<=720)
    assert "height<=720" in captured["ydl_opts"]["format"]


@pytest.mark.asyncio
async def test_download_audio(monkeypatch: pytest.MonkeyPatch, mock_context: Context[Any, Any]) -> None:
    stub, captured = _make_stub(["/path/to/audio.mp3"])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = await mcp_youtube.download_audio(
        "https://youtu.be/dummy",
        codec="mp3",
        quality="192K",
        ctx=mock_context
    )

    assert result == "/path/to/audio.mp3"
    postprocessors = captured["ydl_opts"]["postprocessors"]
    assert postprocessors[0]["key"] == "FFmpegExtractAudio"
    assert postprocessors[0]["preferredcodec"] == "mp3"
    assert postprocessors[0]["preferredquality"] == "192"


@pytest.mark.asyncio
async def test_download_playlist_invalid_url(mock_context: Context[Any, Any]) -> None:
    with pytest.raises(mcp_youtube.UserError):
        await mcp_youtube.download_playlist("https://youtu.be/single-video", ctx=mock_context)


@pytest.mark.asyncio
async def test_download_with_limits(monkeypatch: pytest.MonkeyPatch, mock_context: Context[Any, Any]) -> None:
    stub, captured = _make_stub(["/path/to/video.mp4"])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = await mcp_youtube.download_with_limits(
        "https://youtu.be/dummy",
        max_filesize=10,
        max_duration=2,
        ctx=mock_context
    )

    assert result == "/path/to/video.mp4"
    # 10 MB -> bytes
    assert captured["ydl_opts"]["max_filesize"] == str(10 * 1024 * 1024)
    # 2 min -> seconds
    assert captured["ydl_opts"]["max_duration"] == str(120)


@pytest.mark.asyncio
async def test_get_metadata(monkeypatch: pytest.MonkeyPatch, mock_context: Context[Any, Any]) -> None:
    dummy_info = {"title": "Dummy", "duration": 60}
    stub, _captured = _make_stub([dummy_info])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = await mcp_youtube.get_metadata("https://youtu.be/dummy", ctx=mock_context)

    assert result == dummy_info 