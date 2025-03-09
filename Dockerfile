FROM python:3.10

RUN apt-get -y update && \
    apt-get -y install vim freetds-dev freetds-bin unixodbc-dev tdsodbc poppler-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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
CMD ["/root/.local/bin/poetry", "run", "python", "/code/manage.py", "runserver", "0.0.0.0:8005"]
