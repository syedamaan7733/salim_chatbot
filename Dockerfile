# Use Python slim image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Fly.io sets PORT at runtime; gunicorn binds to 0.0.0.0 so it accepts external connections
EXPOSE 8080

# Use shell form so $PORT is expanded at container runtime
CMD ["sh", "-c", "gunicorn main:app -b 0.0.0.0:${PORT:-8080} --workers 1 --threads 2"]
