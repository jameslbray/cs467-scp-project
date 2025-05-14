FROM python:3.12-alpine

RUN apk add --no-cache \
    curl \
    build-base \
    linux-headers \
    python3-dev \
    py3-pip \
    rust \
    cargo

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
ARG PORT=8002
ENV PORT=$PORT
EXPOSE $PORT

# Command to run the application
CMD ["sh", "-c", "gunicorn -c services/notifications/gunicorn_config.py services.notifications.app.main:app --bind 0.0.0.0:${PORT} --worker-class uvicorn.workers.UvicornWorker"]