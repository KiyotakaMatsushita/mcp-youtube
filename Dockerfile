FROM python:3.12-slim

# --- System dependencies ----------------------------------------------------
# yt-dlp relies on ffmpeg for muxing & audio extraction. We only
# install the runtime binaries to keep the image size small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# --- Project setup ----------------------------------------------------------
WORKDIR /app

# Copy project files first so that Docker cache is leveraged when the
# source code changes less frequently than the dependency list.
COPY pyproject.toml ./
COPY uv.lock ./

# Upgrade pip & install project and production dependencies.
# We use PEP‑517 (pyproject.toml) so a simple `pip install .` is enough.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy the rest of the source tree.
COPY . .

# The server saves downloaded media to the current working directory.
# Mount this as a volume so the host can access the files easily.
VOLUME ["/app"]

# Expose the default HTTP port just in case the user wants to run
# `mcp_youtube.py` with `transport="http"`.
EXPOSE 8000

# --- Entrypoint -------------------------------------------------------------
# By default the server runs on STDIO transport which is detected by
# most MCP‑aware clients (Cursor, Claude Desktop, FastMCP CLI, etc.).
CMD ["python", "mcp_youtube.py"] 