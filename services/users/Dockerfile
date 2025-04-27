FROM python:3.12-alpine

ENV PIP_ROOT_USER_ACTION=ignore

# 1) Runtime dependency
RUN apk add --no-cache postgresql-libs

# 2) Build-time dependencies (including linux-headers)
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    linux-headers \
    postgresql-dev \
    libffi-dev openssl-dev \
    rust cargo

WORKDIR /app
COPY requirements.txt .

# 3) Install Python packages
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir -r requirements.txt

# 4) Remove build deps
RUN apk del .build-deps

# 5) Non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Copy the application code
COPY --chown=appuser:appgroup . .
CMD ["/usr/local/bin/gunicorn", "app.main:app", "--bind", "0.0.0.0:8001", "--worker-class", "uvicorn.workers.UvicornWorker"]
