FROM python:3.10-bookworm

ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code

RUN pip install --upgrade pip==23.2.1
RUN pip install --upgrade pip-tools
