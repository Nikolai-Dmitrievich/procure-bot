FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

FROM python:3.13-slim
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/celery /usr/local/bin/celery
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=builder /app /app
RUN useradd -m app && chown -R app:app /app
USER app

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn procure.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2 --access-logfile - --error-logfile -"]
