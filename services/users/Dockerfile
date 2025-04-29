FROM python:3.12-alpine


RUN apk add --no-cache \
    postgresql-libs \
    build-base \
    linux-headers \
    postgresql-dev \
    libffi-dev \
    openssl-dev

# 2) Set /app as our workspace
WORKDIR /app

# 3) Copy only what we need for pip install (cache layer)
COPY services/users/requirements.txt .

# Install dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# 4) Bring in the entire services/ folder from context
COPY services ./services

ARG PORT=8001
ENV PORT=$PORT
EXPOSE $PORT

CMD ["sh", "-c", "gunicorn -c services/users/gunicorn_config.py services.users.app.main:app --bind 0.0.0.0:${PORT} --worker-class uvicorn.workers.UvicornWorker"]
