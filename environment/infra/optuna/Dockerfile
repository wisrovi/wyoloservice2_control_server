FROM python:3.10-slim

RUN apt-get update && apt-get install -y libpq-dev gcc netcat-openbsd postgresql-client && rm -rf /var/lib/apt/lists/*
RUN pip install optuna-dashboard psycopg2-binary optuna plotly

EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]