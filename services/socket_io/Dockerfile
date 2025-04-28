# services/socket_io/Dockerfile

FROM python:3.12-alpine

# 1) Install system deps
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev

# 2) Set /app as our workspace
WORKDIR /app

# 3) Copy only what we need for pip install (cache layer)
COPY services/socket_io/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 4) Bring in the entire services/ folder from context
COPY services ./services

# 5) Expose your app port (default to 8000 if not set)
ARG PORT=8000
ENV PORT=$PORT
EXPOSE $PORT

# 6) Launch via the top-level services namespace
CMD ["sh", "-c", "gunicorn -c services/socket_io/gunicorn_config.py services.socket_io.app.main:app --bind 0.0.0.0:${PORT} --worker-class uvicorn.workers.UvicornWorker"]
