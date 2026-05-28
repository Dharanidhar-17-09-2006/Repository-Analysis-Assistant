FROM python:3.11-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build frontend
COPY frontend ./frontend
RUN cd frontend && npm install && npm run build

# Copy app
COPY . .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]