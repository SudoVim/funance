FROM python:3.10

WORKDIR /funance
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN pip install -U pip && pip install pipenv && pipenv install

EXPOSE 8005
CMD ["pipenv", "run", "python", "/funance/manage.py", "runserver", "0.0.0.0:8005"]
