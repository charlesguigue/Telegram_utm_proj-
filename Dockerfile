# Use official lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Ensure scripts executable
RUN chmod +x /app/run.sh || true

# Default environment (can be overridden)
ENV PYTHONUNBUFFERED=1

CMD ["./run.sh"]
