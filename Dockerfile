FROM python:3.10

WORKDIR /code
COPY requirements.txt requirements.txt
RUN pip install -U pip
RUN pip install -r requirements.txt

EXPOSE 8005
CMD ["/code/manage.py", "runserver", "0.0.0.0:8005"]
