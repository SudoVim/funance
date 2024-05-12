FROM python:3.10

RUN apt update && apt install -y pipenv python3-setuptools

WORKDIR /funance
EXPOSE 8005
CMD ["pipenv", "run", "python", "/funance/manage.py", "runserver", "0.0.0.0:8005"]
