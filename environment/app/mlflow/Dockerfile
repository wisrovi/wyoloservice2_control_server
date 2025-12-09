# esta es la version mas reciente pero tiene problemas con cors
# FROM ghcr.io/mlflow/mlflow:v3.7.0

# version funcional
FROM ghcr.io/mlflow/mlflow:v2.17.2

# Instalar psycopg2
RUN pip install --no-cache-dir psycopg2-binary boto3

COPY . .
