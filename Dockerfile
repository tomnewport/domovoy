FROM python:3.12
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/
COPY . /app
WORKDIR /app
# Install runtime dependencies into /app/.venv (no dev group, locked versions).
RUN uv sync --frozen --no-dev
WORKDIR /app/domovoy
CMD ["uv", "run", "--no-sync", "uvicorn", "domovoy.asgi:application", "--host", "0.0.0.0"]
