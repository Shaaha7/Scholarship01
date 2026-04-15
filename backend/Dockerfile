FROM python:3.11-slim

WORKDIR /app

# System dependencies for PyMuPDF and ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    libmupdf-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate RSA keys if not present
RUN mkdir -p keys && \
    if [ ! -f keys/private.pem ]; then \
      openssl genrsa -out keys/private.pem 2048 && \
      openssl rsa -in keys/private.pem -pubout -out keys/public.pem; \
    fi

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "2"]
