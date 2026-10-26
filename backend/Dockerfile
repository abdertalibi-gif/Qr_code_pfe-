# Multi-stage build: Backend (Django)
FROM python:3.13-slim as backend-builder

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt .

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client libpq-dev gcc python3-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY backend/ .

# Collect static files
RUN python manage.py collectstatic --noinput --no-default-ignore

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=backend-builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=backend-builder /app /app

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health/', timeout=5)"

# Run with Gunicorn + Daphne for ASGI
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
