FROM python:3.11-slim

WORKDIR /app
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8080"]
