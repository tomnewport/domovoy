FROM python:3.12
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry install --no-root
CMD ["python", "domovoy/manage.py", "runserver"]
