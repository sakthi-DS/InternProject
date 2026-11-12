
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Distroless Runtime
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime

WORKDIR /app

# Copy installed dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app

# Python environment
ENV PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages:/usr/local/lib/python3.11/dist-packages

# Application port
EXPOSE 8002

# Start FastAPI
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

