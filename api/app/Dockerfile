# https://fastapi.tiangolo.com/deployment/docker/#create-the-fastapi-code

FROM python:3.10.16-alpine3.20

USER root

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# Configurar el entorno de trabajo
WORKDIR /code

# Instalar dependencias
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


WORKDIR /code/app
COPY ./code_api /code/app

WORKDIR /code/

CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--port", "8000", "--workers", "8"]