FROM python:3.11-slim


WORKDIR /app/

COPY requirements.txt /app/

RUN pip install --upgrade pip && pip install -r /app/requirements.txt --no-cache-dir

COPY api/ /app/api/
COPY connects/ /app/connects/
COPY functions/ /app/functions/
COPY handlers/ /app/handlers/
COPY logs/ /app/logs/
COPY bot.py /app/
COPY anon.session /app/
COPY config.py /app/