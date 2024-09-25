FROM python:3.12
RUN curl -sSL https://install.python-poetry.org | python
COPY . /app
WORKDIR /app
RUN poetry install
CMD ["python", "manage.py", "runserver"]
