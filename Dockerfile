# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set a working directory
WORKDIR /app

# Copy only requirements first for layered caching
COPY requirements.txt ./

# Install dependencies (Flask, paramiko, transformers, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . . 

# Expose the Flask port
EXPOSE 5000

# Set environment variables (can be overridden in docker-compose)
ENV FLASK_ENV=production
ENV SECRET_KEY=supersecret

# Create upload directory (for Flask file uploads)
RUN mkdir -p /app/api/uploads

# Default command to run the Flask web UI
CMD ["python", "api/webui.py"]