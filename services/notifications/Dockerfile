# Build stage
FROM python:3.11-slim as builder

# Install Rust and other build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Final stage
FROM python:3.11-slim

# Copy site-packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy bin directory that contains executables like uvicorn
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application
COPY --from=builder /app /app

WORKDIR /app

# Expose the port
ARG PORT=8002
ENV PORT=$PORT
EXPOSE $PORT

# Command to run the application
# CMD ["uvicorn", "services.notifications.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
CMD ["sh", "-c", "gunicorn -c gunicorn_config.py app.main:app --bind 0.0.0.0:${PORT} --worker-class uvicorn.workers.UvicornWorker"]