# services/db_init/Dockerfile
FROM python:3.12-alpine

WORKDIR /app

# Install system dependencies needed for PostgreSQL client
RUN apk add --no-cache postgresql-client postgresql-dev gcc musl-dev

# Install dependencies
COPY services/db_init/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/db_init/app/ ./

# Run the initialization script
CMD ["python", "main.py"]