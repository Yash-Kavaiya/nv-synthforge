FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    SYNTHFORGE_DATA_DIR=/data

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libjpeg62-turbo libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 synthforge

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra nemo --extra parquet --extra pdf
COPY app ./app

RUN mkdir -p /data && chown -R synthforge:synthforge /app /data
USER synthforge
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
