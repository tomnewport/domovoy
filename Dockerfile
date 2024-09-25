FROM python:3.12
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry install
CMD ["python", "manage.py", "runserver"]
