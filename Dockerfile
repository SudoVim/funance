FROM python:3.10

RUN apt update && \
    apt install -y python3-setuptools

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN /root/.local/bin/poetry config virtualenvs.create false

RUN useradd -m app

RUN mkdir /code
RUN chown app.app /code
WORKDIR /code

# copy only the poetry files to install the dependencies in a separate layer
COPY --chown=app:app pyproject.toml poetry.lock /code/

RUN /root/.local/bin/poetry install --no-root

COPY --chown=app:app . /code/
EXPOSE 8005
CMD ["poetry", "run", "python", "/code/manage.py", "runserver", "0.0.0.0:8005"]
