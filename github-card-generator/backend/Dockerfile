# Use a official slim Python runtime
FROM python:3.12-slim

# Install system dependencies and uv for high-speed package management
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 755 /install.sh && /install.sh && rm /install.sh
ENV PATH="/root/.local/bin/:${PATH}"

# Set the working directory
WORKDIR /app

# Copy requirements file first to utilize Docker layer caching
COPY requirements.txt .

# Install dependencies globally in the container using uv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose FastAPI server port
EXPOSE 8080

# Run FastAPI using uvicorn, dynamically binding to the port specified by Cloud Run
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
