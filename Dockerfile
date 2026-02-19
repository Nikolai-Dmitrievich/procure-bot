FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
