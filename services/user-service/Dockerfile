
# Stage 1: Builder
FROM python:3.12-slim AS builder

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
ENV PYTHONPATH=/app
ENV PATH=/usr/local/bin:/usr/bin

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=3)"]

# Run the application
CMD ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
