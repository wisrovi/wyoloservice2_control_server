# https://fastapi.tiangolo.com/deployment/docker/#create-the-fastapi-code

FROM wisrovi/agents:gpu

USER root
SHELL ["/usr/bin/bash", "-c"]


# Configurar el entorno de trabajo
WORKDIR /requirements


# Instalar dependencias
COPY requirements.txt /requirements
RUN pip install -r /requirements/requirements.txt


WORKDIR /code/app
COPY ./code_api .

WORKDIR /code/app

EXPOSE 8000


# CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--port", "8000", "--workers", "8"]

# with gunicorn: gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind
# CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "8"]



# with uvicorn: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]