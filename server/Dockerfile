# PTH server (Flask + SQLite). Build context: this directory.
FROM python:3.12-slim

# uv installs dependencies exactly as pinned in uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    TZ=UTC \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/app/.venv/bin:$PATH \
    PTH_DB_PATH=/data/pth_data.db

WORKDIR /app

# dependencies first: this layer is cached and only rebuilt when the lockfile changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# then the application code
COPY app.py ./
COPY pth_server ./pth_server
RUN uv sync --frozen --no-dev

# run as a non-root user; /data is where the SQLite database lives (mounted from the host)
RUN useradd --system --uid 1001 pth && mkdir -p /data && chown pth:pth /data
USER pth
VOLUME ["/data"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/pth/api/ndays?days=1', timeout=4).status==200 else 1)"

# 2 workers: enough for one sensor plus dashboard users; access log to stdout for `docker logs`
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--access-logfile", "-", "app:app"]
