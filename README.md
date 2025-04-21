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
| `download_with_limits` | Enforce max file size / duration |
| `resume_download` | Resume a partial download |
| `get_metadata` | Return video metadata as JSON |

Files are saved as:
```text
{title} [{video_id}].{ext}
```

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
      "command": "uvx",
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

### HTTP example (curl)
```bash
curl -X POST http://localhost:8000/download_video \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://youtu.be/dQw4w9WgXcQ"}'
```
The response contains streamed progress updates followed by the saved file path.

---

## 🔧 Advanced recipes

```bash
# Audio only (320 kbps mp3)
fastmcp call download_audio '{"url":"…","codec":"mp3","quality":"320K"}'

# Enforce 100 MB & 20 min limits
fastmcp call download_with_limits '{"url":"…","max_filesize":100,"max_duration":20}'

# Download & embed Japanese subtitles
fastmcp call download_subtitles '{"url":"…","lang":"ja","embed":true}'
```

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

