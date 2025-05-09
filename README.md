# MCP‑YouTube 🚀

[![MCP](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![yt‑dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-red)](https://github.com/yt-dlp/yt-dlp)

**MCP‑YouTube** exposes the power of [yt‑dlp](https://github.com/yt-dlp/yt-dlp) as a [Model Context Protocol (MCP)](#about-mcp) server – download videos, playlists, audio, subtitles and more through a single JSON call.

---

## ✨ Highlights

• **Drop‑in server** – start it and invoke high‑level tools immediately  
• **Works with any MCP client**: CLI, Cursor (VS Code), Claude Desktop, HTTP fetchers, ChatGPT plug‑ins & more  
• **Rich logs** – progress, speed, ETA and errors stream back to the caller  
• **Fully async** – multiple downloads at once without blocking  

---

## 🗒️ Requirements

| Component | Why it's needed | Install (macOS / Ubuntu / Windows) |
|-----------|----------------|-----------------------------------|
| **Python 3.8+** | Runs the MCP‑YouTube server | Built‑in / `brew install python` / `sudo apt install python3` / <https://www.python.org/downloads/> |
| **ffmpeg** | Used by yt‑dlp to merge video & audio, extract audio, convert thumbnails | `brew install ffmpeg` / `sudo apt install ffmpeg` / `choco install ffmpeg` |
| **yt‑dlp** | Core downloader library | Installed automatically via `uv sync` or `pip install -e .[all]` |

*If you use the provided Docker image, both `yt-dlp` and `ffmpeg` are already included.*

---

## ⚡️ Quick Start

```bash
# 1. Create & activate a virtualenv (using uv)
uv venv && source .venv/bin/activate

# 2. Install project dependencies
uv sync   # reads pyproject / uv.lock

# 3. Run the server (STDIO transport)
uv run python mcp_youtube.py
```

The banner should show:
```text
✔ FastMCP server "mcp-youtube" is ready (stdio)
```
> Hot‑reload for development: `uv run dev python mcp_youtube.py`

---

## 🛠️ Available Tools

| Tool | Purpose |
|------|---------|
| `download_video` | Download a single video (select quality / resolution) |
| `download_playlist` | Download a range of items from a playlist |
| `download_audio` | Extract audio only (mp3 / aac / opus …) |
| `download_subtitles` | Fetch or embed subtitles |
| `download_thumbnail` | Highest‑quality thumbnail |
| `get_metadata` | Return video metadata as JSON |

### 📂 Output paths

Files generated by each tool are saved in type‑specific sub‑folders under the `downloads/` directory.

| Type | Path | Example |
|------|------|---------|
| Video | `downloads/videos/` | `downloads/videos/Summer Festival [abc123].mp4` |
| Audio | `downloads/audio/` | `downloads/audio/Summer Festival [abc123].mp3` |
| Subtitles | `downloads/subtitles/` | `downloads/subtitles/Summer Festival [abc123].ja.vtt` |
| Thumbnail | `downloads/thumbnails/` | `downloads/thumbnails/Summer Festival [abc123].jpg` |

Naming template:

```text
{title} [{id}][.{lang}].{ext}
```

`{lang}` is only appended for subtitle files.

---

## 🌐 Using MCP‑YouTube with different clients

| Client | How to connect |
|--------|---------------|
| **FastMCP CLI** | `fastmcp call download_video '{"url":"…"}'` |
| **Cursor (VS Code)** | Place this repo in your workspace – Cursor auto‑detects `.cursorrules` and spawns the server on demand |
| **Claude Desktop** | Add a `mcpServers` entry (see below) |
| **Any HTTP tool** (curl, Postman, JS fetch, etc.) | Start server with HTTP transport – `uv run python -m fastmcp.server http mcp_youtube.py --port 8000` |
| **Python code** | `from mcp.client import Client` (example below) |
| **ChatGPT Plugins / LLM Agents** | Register the server's schema endpoint (served automatically when using HTTP) |

### FastMCP CLI example
```bash
fastmcp call download_video '{
  "url": "https://youtu.be/dQw4w9WgXcQ",
  "quality": "best",
  "format": "mp4",
  "resolution": "1080p"
}'
```

### Python client example
```python
from mcp.client import Client

client = Client.spawn("mcp-youtube")  # auto‑spawns the process
path = client.download_video(
    url="https://youtu.be/dQw4w9WgXcQ",
    quality="best",
    format="mp4",
    resolution="1080p",
)
print("Saved to", path)
```

### Claude Desktop config (macOS)
Create/append `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "youtube": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABS/PATH/TO/mcp-youtube",
        "run",
        "python",
        "mcp_youtube.py"
      ]
    }
  }
}
```


---

## ⚖️ Legal Notice & Compliance

MCP‑YouTube is **strictly a convenience wrapper** around the publicly available `yt‑dlp` project.
It is **your responsibility** to ensure that any content you access, download, or redistribute through this tool **does not violate**:

1. Copyright and neighbouring‑rights legislation that applies in your jurisdiction.
2. The [YouTube Terms of Service](https://www.youtube.com/static?gl=US&template=terms).

By using this software you acknowledge that:

• You will only download material when you have a legal right to do so (e.g. content in the public domain, your own uploads, or where the copyright holder has granted permission).
• You will **not** use MCP‑YouTube to circumvent technical protection measures or content access restrictions.
• You assume **full responsibility** for any legal consequences arising from your use of this project.

### No Warranty / No Liability

This software is provided **"as is"**, without warranty of any kind.
In no event shall the authors or contributors be liable for **any claim, damages, or other liability** arising from, out of, or in connection with the software or the use or other dealings in the software.
---

## 🐳 Docker

```bash
docker build -t mcp-youtube .
docker run -it --rm -v "$PWD:/downloads" mcp-youtube
```

---

## 🛠 Development

```bash
uv run ruff check .   # lint
uv run black .        # format
uv run mypy .         # type‑check
```
*PRs & tests welcome!*

---

## 📜 License

[MIT](LICENSE)

---

## About MCP <a id="about-mcp"></a>

The **Model Context Protocol** standardises how LLMs interact with external *tools*, *resources* and *prompts*. An MCP *server* (like MCP‑YouTube) advertises a JSON schema for each tool; an MCP *client* validates arguments before forwarding the call, ensuring safe and predictable execution.

Learn more at the [official repo](https://github.com/modelcontextprotocol/servers).
