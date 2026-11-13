# API server (with the Chat AI) for Hugging Face Spaces or any Docker host.
# Serves the results bundled in public/demo, so no dataset is needed on the server.
FROM python:3.11-slim

WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY src ./src
COPY public/demo ./public/demo

# Hugging Face Spaces expects port 7860; other hosts can override PORT.
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]
