FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-traditional \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir .

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads && chmod 755 /app/uploads

# Create wait-for-postgres script
RUN echo '#!/bin/bash' > /app/wait-for-postgres.sh && \
    echo 'set -e' >> /app/wait-for-postgres.sh && \
    echo 'host="$1"' >> /app/wait-for-postgres.sh && \
    echo 'port="$2"' >> /app/wait-for-postgres.sh && \
    echo 'shift 2' >> /app/wait-for-postgres.sh && \
    echo 'cmd="$@"' >> /app/wait-for-postgres.sh && \
    echo 'until nc -z "$host" "$port"; do' >> /app/wait-for-postgres.sh && \
    echo '  >&2 echo "Postgres is unavailable - sleeping"' >> /app/wait-for-postgres.sh && \
    echo '  sleep 1' >> /app/wait-for-postgres.sh && \
    echo 'done' >> /app/wait-for-postgres.sh && \
    echo '>&2 echo "Postgres is up - executing command"' >> /app/wait-for-postgres.sh && \
    echo 'exec $cmd' >> /app/wait-for-postgres.sh && \
    chmod +x /app/wait-for-postgres.sh

# Expose ports for web interface and flow collectors
EXPOSE 5000 2055/udp 6343/udp

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1

# Set entrypoint
ENTRYPOINT ["/app/wait-for-postgres.sh", "postgres", "5432"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "main:app"]