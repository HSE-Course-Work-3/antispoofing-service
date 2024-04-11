FROM python:3.10-slim-buster

WORKDIR  /usr/src/app

ENV PYTOHDONTWRITEBYTECODE 3.10
ENV PYTHONUNBUFFERED 1


RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y

COPY . .
