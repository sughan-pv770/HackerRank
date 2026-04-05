FROM python:3.11-slim

# Install system dependencies for code execution (C, C++, Java, Node.js)
RUN apt-get update && apt-get install -y \
    nodejs \
    default-jdk \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .



# Expose port (Render sets the PORT environment variable, defaulting to 10000)
# We use a default of 5000 if PORT is not set
EXPOSE 5000

# Start Gunicorn with a 180s timeout to prevent 502s when waiting for AI API
CMD gunicorn --timeout 180 --bind 0.0.0.0:${PORT:-5000} "app:create_app()"
