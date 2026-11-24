FROM python:3.12
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry config virtualenvs.create false
RUN poetry install
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

# TLS is terminated by the platform proxy, whose address isn't fixed (Cloud Run,
# or the docker bridge gateway behind nginx), so trust X-Forwarded-* from any
# peer. Override at runtime to restrict it.
ENV FORWARDED_ALLOW_IPS="*"

# Cloud Run injects PORT (default 8080); docker-compose relies on the 8000 default.
CMD ["sh", "-c", "exec uvicorn domovoy.asgi:application --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers"]
