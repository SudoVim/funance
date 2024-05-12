#!/bin/bash

docker pull python:3.10
docker-compose build
docker-compose run web pipenv install --dev --python 3.10
