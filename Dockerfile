FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

RUN apt-get -y update && \
    apt-get -y install vim freetds-dev freetds-bin unixodbc-dev tdsodbc poppler-utils libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN useradd -m app

RUN mkdir /code
RUN chown app.app /code
WORKDIR /code

ARG UV_NO_DEV=0
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

COPY --chown=app:app . /code/
EXPOSE 8005
CMD ["python", "/code/manage.py", "runserver", "0.0.0.0:8005"]
