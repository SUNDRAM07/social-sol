# Multi-stage build for Social Media Agent
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including dev dependencies needed for build)
RUN npm install

# Copy frontend source
COPY . .

# Build the frontend
RUN npm run build

# Stage 2: Python backend with static files
FROM python:3.11-slim AS backend

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy backend requirements and install dependencies
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY server/ .

# NOTE: Environment variables are injected by Railway/Docker at runtime
# Do NOT copy .env or Credentials.json - use environment variables instead

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/dist ./static

# Create uploads directory
RUN mkdir -p ./public

# Expose port (Railway uses PORT env var)
EXPOSE 8000

# NOTE: Healthcheck is handled by Railway, not Docker
# Railway will check /health endpoint

# Start command - Railway sets PORT env var
CMD ["python", "main.py"]
