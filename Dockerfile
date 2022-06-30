FROM python:3.10

WORKDIR /code
COPY requirements-lock.txt requirements-lock.txt
RUN pip install -U pip
RUN pip install -r requirements-lock.txt

EXPOSE 8005
CMD ["/code/manage.py", "runserver", "0.0.0.0:8005"]
