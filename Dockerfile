FROM python:3.10-bookworm

ENV PYTHONUNBUFFERED 1
ARG REQUIREMENT_FILE

RUN apt update

RUN mkdir /code
WORKDIR /code

COPY $REQUIREMENT_FILE /code/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /code/requirements.txt
