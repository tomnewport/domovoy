FROM python:3.12
RUN pip install poetry
COPY . /app
WORKDIR /app
RUN poetry config virtualenvs.create false
RUN poetry install
CMD ["python", "domovoy/manage.py", "runserver"]
