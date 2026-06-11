# Base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKDIR=/app

# Set work directory
WORKDIR $WORKDIR

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    netcat-openbsd \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/base.txt requirements/local.txt ./requirements/
RUN pip install --no-cache-dir -r requirements/local.txt

# Copy project files
COPY . .

# Create a non-root user and assign permissions
RUN groupadd -r appgroup && useradd -r -g appgroup -d $WORKDIR appuser \
    && chown -R appuser:appgroup $WORKDIR

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Set entrypoint script
ENTRYPOINT ["/bin/bash", "/app/docker/entrypoint.sh"]
