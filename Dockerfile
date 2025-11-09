FROM python:3.11-alpine

ENV TZ=Europe/Moscow

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/src
CMD ["python", "-u", "main.py"]