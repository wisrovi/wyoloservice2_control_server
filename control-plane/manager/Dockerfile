FROM python:3.10-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY celery_config.py .
COPY user_orchestrator.py .

CMD ["celery", "-A", "user_orchestrator", "worker", "-Q", "managers", "--loglevel=info"]
