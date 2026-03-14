FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir aiohttp

COPY scrape_sports_tracker.py /app/

ENTRYPOINT ["python", "scrape_sports_tracker.py"]
