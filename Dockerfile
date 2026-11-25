FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.10 /uv /bin/uv

# Use the image's Python, compile bytecode at build time, and put the
# project's virtualenv first on PATH.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
# Dependencies first, so a code-only change reuses this layer.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev
COPY . /app
WORKDIR /app/domovoy

# Bake Django/admin static assets into the image; WhiteNoise serves them.
# DmvSettings requires these variables at import time, but collectstatic uses
# none of them, so placeholders are set for this one command only. They are not
# persisted as ENV and no real secrets are needed to build.
RUN domovoy_server_secret_key=collectstatic-placeholder \
    domovoy_smtp_server=unused \
    domovoy_smtp_port=0 \
    domovoy_smtp_username=unused \
    domovoy_smtp_password=unused \
    domovoy_frontend_root=http://unused \
    python manage.py collectstatic --noinput

# TLS is terminated by the platform proxy (Cloud Run), whose address isn't
# fixed, so trust X-Forwarded-* from any peer. Override at runtime to restrict it.
ENV FORWARDED_ALLOW_IPS="*"

# Cloud Run injects PORT (default 8080); a local `docker run` gets 8000.
CMD ["sh", "-c", "exec uvicorn domovoy.asgi:application --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers"]
