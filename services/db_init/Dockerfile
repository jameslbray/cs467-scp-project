# services/db_init/Dockerfile
FROM python:3.12-alpine

WORKDIR /app/services/db_init/app

# Install system dependencies needed for PostgreSQL client
RUN apk add --no-cache postgresql-client postgresql-dev gcc musl-dev

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the services directory
COPY ../../.. /app

# Run the initialization script
CMD ["python", "main.py"]
