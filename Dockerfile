FROM python:3.12
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry config virtualenvs.create false
RUN poetry install
WORKDIR /app/domovoy
CMD ["uvicorn", "domovoy.asgi:application", "--host", "0.0.0.0"]
