# --- Build stage: resolve dependencies into a self-contained venv ------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

# Use the image's interpreter (don't let uv fetch its own, so the venv it builds
# is valid in the runtime stage), copy files into the venv, and compile bytecode.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Install dependencies first so this layer is cached unless the lockfile changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Then the application source (package = false, so no project build step).
COPY . .

# --- Runtime stage: slim image with just the venv + source -------------------
FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --from=builder /app /app

WORKDIR /app/domovoy

# Bake Django/admin static into the image; the serverless filesystem is
# ephemeral/read-only so collecting at runtime is unreliable. The placeholder
# env vars satisfy settings instantiation for this command only (not persisted).
RUN domovoy_server_secret_key=build-only \
    domovoy_frontend_root=http://localhost/ \
    domovoy_smtp_server=localhost \
    domovoy_smtp_port=25 \
    domovoy_smtp_username=build \
    domovoy_smtp_password=build \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Listen on $PORT when the platform provides it (Cloud Run), else default 8000.
CMD ["sh", "-c", "uvicorn domovoy.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]
