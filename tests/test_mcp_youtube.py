import pathlib
import sys

import pytest

# Add project root to sys.path so that `import mcp_youtube` works when the
# package is not installed (tests run from source checkout).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mcp_youtube


def _make_stub(return_value):
    """Return a stub function that captures its kwargs and returns value."""
    captured = {}

    def _stub(urls, ydl_opts, ctx):  # noqa: D401, ANN001
        captured["urls"] = urls
        captured["ydl_opts"] = ydl_opts
        # Simulate the path list expected by callers
        return return_value

    return _stub, captured


def test_download_video(monkeypatch):
    stub, captured = _make_stub(["/path/to/video.mp4"])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = mcp_youtube.download_video(
        "https://youtu.be/dummy", quality="best", format="mp4", resolution="720p"
    )

    assert result == "/path/to/video.mp4"
    assert captured["urls"] == ["https://youtu.be/dummy"]
    assert captured["ydl_opts"]["merge_output_format"] == "mp4"
    # Ensure format string reflects resolution cap (720p -> height<=720)
    assert "height<=720" in captured["ydl_opts"]["format"]


def test_download_audio(monkeypatch):
    stub, captured = _make_stub(["/path/to/audio.mp3"])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = mcp_youtube.download_audio(
        "https://youtu.be/dummy", codec="mp3", quality="192K"
    )

    assert result == "/path/to/audio.mp3"
    postprocessors = captured["ydl_opts"]["postprocessors"]
    assert postprocessors[0]["key"] == "FFmpegExtractAudio"
    assert postprocessors[0]["preferredcodec"] == "mp3"
    assert postprocessors[0]["preferredquality"] == "192"


def test_download_playlist_invalid_url():
    with pytest.raises(mcp_youtube.UserError):
        mcp_youtube.download_playlist("https://youtu.be/single-video")


def test_download_with_limits(monkeypatch):
    stub, captured = _make_stub(["/path/to/video.mp4"])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = mcp_youtube.download_with_limits(
        "https://youtu.be/dummy", max_filesize=10, max_duration=2
    )

    assert result == "/path/to/video.mp4"
    # 10 MB -> bytes
    assert captured["ydl_opts"]["max_filesize"] == 10 * 1024 * 1024
    # 2 min -> seconds
    assert captured["ydl_opts"]["max_duration"] == 120


def test_get_metadata(monkeypatch):
    dummy_info = {"title": "Dummy", "duration": 60}
    stub, _captured = _make_stub([dummy_info])
    monkeypatch.setattr(mcp_youtube, "_run_dl", stub)

    result = mcp_youtube.get_metadata("https://youtu.be/dummy")

    assert result == dummy_info 