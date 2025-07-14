FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create sessions directory and subdirectories
RUN mkdir -p sessions verified
# Create some common country directories for better organization
RUN mkdir -p sessions/+1 sessions/+44 sessions/+91 sessions/+86 sessions/+81 sessions/+49 sessions/+33 sessions/+39 sessions/+34 sessions/+7

# Expose port (Koyeb will handle this)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run the bot
CMD ["python", "main.py"]