# Use Python 3.10 slim image for smaller size
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY web/ ./web/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Create data directory for database persistence
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    FLASK_APP=src/jar/app.py \
    DATABASE_PATH=/app/data/oracle_pilot.db

# Expose port 5001
EXPOSE 5001

# Health check to ensure the app is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5001', timeout=5)" || exit 1

# Run the application
CMD ["python", "src/jar/app.py"]
