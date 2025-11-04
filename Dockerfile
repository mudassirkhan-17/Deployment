FROM python:3.11-slim

# Install system dependencies for PyMuPDF only
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (for better caching)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code to root of /app (not /app/backend/)
COPY backend/ .

# Copy credentials
COPY credentials/ ./credentials/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/insurance-sheets-474717-7fc3fd9736bc.json

EXPOSE 8000

# Start FastAPI (app.py is now at /app/app.py)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]