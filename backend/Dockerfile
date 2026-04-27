FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Run the application (using app.py as entry point)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
