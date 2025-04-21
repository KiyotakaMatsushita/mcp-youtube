import pathlib
import sys
from typing import Any, Callable, Dict, List, Tuple, Union, Optional
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

    async def _stub(args: List[str], ctx: Optional[Context[Any, Any]] = None) -> Any:
        captured["args"] = args
        # Simulate the path list expected by callers
        if isinstance(return_value[0], dict):
            return return_value[0]
        return return_value[0]

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
    assert "--format" in captured["args"]
    assert "--merge-output-format" in captured["args"]
    assert "mp4" in captured["args"]
    # Ensure format string reflects resolution cap (720p -> height<=720)
    format_str = captured["args"][captured["args"].index("--format") + 1]
    assert "height<=720" in format_str


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
    assert "--extract-audio" in captured["args"]
    assert "--audio-format" in captured["args"]
    assert "mp3" in captured["args"]
    assert "--audio-quality" in captured["args"]
    assert "192" in captured["args"]


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
    assert "--max-filesize" in captured["args"]
    assert "10M" in captured["args"]
    assert "--max-duration" in captured["args"]
    assert "120" in captured["args"]


@pytest.mark.asyncio
async def test_get_metadata(monkeypatch: pytest.MonkeyPatch, mock_context: Context[Any, Any]) -> None:
    dummy_info = {"title": "Dummy", "duration": 60}
    stub, captured = _make_stub([dummy_info])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = await mcp_youtube.get_metadata("https://youtu.be/dummy", ctx=mock_context)

    assert result == dummy_info
    assert "--dump-json" in captured["args"]
    assert "--no-download" in captured["args"] 