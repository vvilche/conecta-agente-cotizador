# Production Dockerfile for Commercial Intelligence Swarm App
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5001

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy requirements / pyproject.toml
COPY pyproject.toml .
RUN uv pip install --system . --extra dev gunicorn

# Copy application source code and databases
COPY src/ src/
COPY scripts/ scripts/
COPY matriz_conocimiento_2026.sqlite .
COPY matriz_conocimiento_2026.json .
COPY rag_store_2026.json .
COPY gunicorn.conf.py .

# Expose server port
EXPOSE 5001

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/ || exit 1

# Start production WSGI server with Gunicorn
CMD ["python", "scripts/run_production_server.py"]
