#!/bin/bash
# Script para correr los tests en un contenedor Docker
# Se usa el entorno de la API como base para las pruebas.

echo "--- Preparando entorno de pruebas ---"
# Asegurar que el Dockerfile de la API pueda encontrar el requirements.txt
cp api/requirements.txt ./requirements_test.txt

echo "--- Construyendo contenedor de pruebas ---"
# Construir desde la raíz para incluir todos los módulos (api, manager, worker)
docker build -t ml_cluster_test -f - . <<EOF
FROM python:3.10-slim
WORKDIR /app
COPY requirements_test.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt pytest pytest-cov httpx PyYAML optuna celery redis
COPY . .
ENV PYTHONPATH=/app
CMD ["pytest", "--cov=.", "tests/", "--cov-report=term-missing"]
EOF

echo "--- Ejecutando tests ---"
docker run --rm ml_cluster_test

# Limpieza
rm requirements_test.txt
