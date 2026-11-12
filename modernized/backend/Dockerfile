FROM python:3.12-slim

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY seed ./seed

ENV PORT=8080
ENV CARDDEMO_DB=/srv/app/data/carddemo.db
RUN mkdir -p /srv/app/data
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
